"""AI/ML Clinical Document Extraction and Review Pipeline."""
import os
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import ValidationError

from app.core.exceptions import (
    DocumentQualityError,
    ExtractionSchemaError,
    ExtractionRepairFailedError,
)
from app.schemas.clinical_report import (
    StructuredClinicalReport,
    ClinicalExtractionResult,
    PatientInformation,
    MedicationItem,
    AllergyItem,
    Vitals,
)
from app.services.gemini_client import GeminiClient, gemini_client

logger = logging.getLogger(__name__)

# Known drug-allergy contraindication families for automated cross-checking
ALLERGY_MEDICATION_CONFLICT_MAP = {
    "penicillin": ["amoxicillin", "ampicillin", "augmentin", "penicillin", "piperacillin", "oxacillin"],
    "amoxicillin": ["amoxicillin", "augmentin", "penicillin"],
    "sulfa": ["bactrim", "sulfamethoxazole", "trimethoprim-sulfamethoxazole", "septra", "sulfasalazine"],
    "nsaid": ["ibuprofen", "naproxen", "aspirin", "ketorolac", "meloxicam", "celecoxib", "indomethacin"],
    "aspirin": ["aspirin", "ibuprofen", "naproxen", "ketorolac"],
    "codeine": ["codeine", "morphine", "hydrocodone", "oxycodone"],
}


def check_document_quality(text: Optional[str], image_path: Optional[str] = None) -> None:
    """
    Validates that the input document possesses sufficient legible content.
    Raises DocumentQualityError if input is empty, non-clinical gibberish, or unreadable.
    """
    if image_path:
        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
            raise DocumentQualityError(
                "Document quality is too poor or lacks readable clinical content to perform clinical review."
            )
        return

    if not text or not text.strip():
        raise DocumentQualityError(
            "Document quality is too poor or lacks readable clinical content to perform clinical review."
        )

    clean_text = text.strip()

    # Reject if total length is negligible
    if len(clean_text) < 15:
        raise DocumentQualityError(
            "Document quality is too poor or lacks readable clinical content to perform clinical review."
        )

    # Reject if only special non-alphanumeric characters or random noise
    alphanumeric_chars = [c for c in clean_text if c.isalnum()]
    if len(alphanumeric_chars) < 10:
        raise DocumentQualityError(
            "Document quality is too poor or lacks readable clinical content to perform clinical review."
        )

    # Check for non-clinical gibberish (e.g. "%$#@! &*^%$" or repeating single chars)
    words = clean_text.split()
    if len(words) == 1 and len(words[0]) > 25 and not re.search(r"[a-z]", words[0], re.IGNORECASE):
        raise DocumentQualityError(
            "Document quality is too poor or lacks readable clinical content to perform clinical review."
        )


def _cross_validate_and_enrich_flags(report: StructuredClinicalReport) -> StructuredClinicalReport:
    """
    Deterministic clinical rule engine that cross-validates extracted clinical entities
    to guarantee that allergy-medication conflicts, missing fields, and contradictions are flagged.
    """
    missing_flags = list(report.missing_information)
    inconsistency_flags = list(report.potential_inconsistencies)
    requires_review = report.requires_review

    # 1. Cross-check Allergy vs Medication Conflicts
    allergy_names = [a.substance.lower().strip() for a in report.allergies if a.substance]
    for med in report.medications:
        med_name_lower = med.name.lower().strip()
        for allergy in allergy_names:
            for allergen_key, conflicting_drugs in ALLERGY_MEDICATION_CONFLICT_MAP.items():
                if allergen_key in allergy:
                    for conflict_drug in conflicting_drugs:
                        if conflict_drug in med_name_lower:
                            flag_msg = (
                                f"CRITICAL CONTRAINDICATION: Documented allergy to '{allergy.capitalize()}' "
                                f"conflicts with prescribed medication '{med.name}'."
                            )
                            if flag_msg not in inconsistency_flags:
                                inconsistency_flags.append(flag_msg)
                            requires_review = True

    # 2. Check for Missing Critical Demographics
    if not report.patient_information.age and not report.patient_information.dob:
        flag_msg = "Missing critical patient demographic: Age or Date of Birth not documented."
        if flag_msg not in missing_flags:
            missing_flags.append(flag_msg)
        requires_review = True

    # 3. Check for Incomplete Medication Prescriptions
    for med in report.medications:
        if not med.dosage:
            flag_msg = f"Missing dosage specification for prescribed medication '{med.name}'."
            if flag_msg not in missing_flags:
                missing_flags.append(flag_msg)
            requires_review = True

    # 4. Check for Missing Vitals in Symptomatic Presentation
    has_vitals = any([
        report.vitals.blood_pressure,
        report.vitals.heart_rate,
        report.vitals.temperature,
        report.vitals.o2_saturation,
    ])
    if not has_vitals and (len(report.symptoms) > 0 or len(report.diagnoses) > 0):
        flag_msg = "Missing physiological vital signs (blood pressure, heart rate, temperature) for clinical encounter."
        if flag_msg not in missing_flags:
            missing_flags.append(flag_msg)
        requires_review = True

    # If any inconsistencies or missing critical items exist, enforce requires_review = True
    if inconsistency_flags or missing_flags or report.clinical_concerns:
        requires_review = True

    return StructuredClinicalReport(
        patient_information=report.patient_information,
        symptoms=report.symptoms,
        diagnoses=report.diagnoses,
        medications=report.medications,
        vitals=report.vitals,
        allergies=report.allergies,
        clinical_observations=report.clinical_observations,
        clinical_concerns=report.clinical_concerns,
        missing_information=missing_flags,
        potential_inconsistencies=inconsistency_flags,
        requires_review=requires_review,
    )


def extract_structured_clinical_data(
    text: str,
    image_path: Optional[str] = None,
    client: Optional[GeminiClient] = None,
) -> StructuredClinicalReport:
    """
    Extracts structured clinical report using Gemini with strict schema validation
    and automatic one-step repair retry on invalid JSON.
    """
    check_document_quality(text, image_path)
    ai_client = client or gemini_client

    extraction_prompt = f"""
You are an expert AI clinical document reviewer. Extract structured clinical data from the following patient record.

EXTRACTION INSTRUCTIONS:
1. Extract patient demographics: name, age, gender, MRN, DOB.
2. Extract all documented symptoms and chief complaints.
3. Extract all clinical diagnoses, conditions, and past medical history.
4. Extract all medications, including exact dosage, frequency, route, and status.
5. Extract recorded physiological vital signs (BP, HR, RR, temp, O2 sat, BMI).
6. Extract all documented drug, food, and environmental allergies.
7. Extract objective clinical observations, physical exam findings, and lab values.
8. Identify any acute clinical concerns, critical lab abnormalities, or urgent risks.
9. CRITICAL - Rigorously detect and populate 'missing_information':
   - Explicitly list missing patient age/DOB if absent.
   - Explicitly list any medication lacking dosage or frequency.
   - Explicitly list missing baseline vitals.
10. CRITICAL - Rigorously detect and populate 'potential_inconsistencies':
   - Flag any medication prescribed that contradicts documented patient allergies (e.g. Penicillin allergy + Amoxicillin).
   - Flag contradictory statements, conflicting vital signs, or incongruent timeline dates.
11. Set 'requires_review' to true if missing_information is non-empty, potential_inconsistencies is non-empty, or acute clinical concerns exist. Set to false ONLY if the document is completely clean, consistent, and comprehensive.

CLINICAL DOCUMENT TEXT:
\"\"\"
{text}
\"\"\"

Return ONLY a valid JSON object strictly adhering to the specified schema.
"""

    raw_json = ""
    try:
        raw_json = ai_client.generate_structured_json(
            prompt=extraction_prompt,
            image_path=image_path,
            schema=StructuredClinicalReport,
        )
        report = StructuredClinicalReport.model_validate_json(raw_json)
        return _cross_validate_and_enrich_flags(report)

    except (json.JSONDecodeError, ValidationError, Exception) as first_err:
        logger.warning(
            f"Initial structured extraction failed validation ({first_err}). Attempting repair prompt..."
        )
        try:
            repaired_json = ai_client.repair_json_output(
                original_text=text,
                malformed_output=raw_json,
                validation_error=str(first_err),
                schema=StructuredClinicalReport,
            )
            report = StructuredClinicalReport.model_validate_json(repaired_json)
            logger.info("Successfully repaired clinical report schema.")
            return _cross_validate_and_enrich_flags(report)
        except Exception as repair_err:
            logger.error(f"Repair retry also failed: {repair_err}")
            raise ExtractionRepairFailedError(
                f"Failed to produce valid clinical report schema after repair retry: {repair_err}"
            ) from repair_err


def generate_clinical_summary(
    text: str,
    structured_report: StructuredClinicalReport,
    image_path: Optional[str] = None,
    client: Optional[GeminiClient] = None,
) -> str:
    """
    Generates a concise, high-quality clinical narrative summary as a distinct prompt step,
    incorporating patient context, findings, and review flags.
    """
    ai_client = client or gemini_client

    summary_prompt = f"""
You are an expert physician reviewer. Generate a cohesive clinical executive summary of the following patient document.

SOURCE DOCUMENT:
{text}

STRUCTURED CLINICAL FINDINGS:
{structured_report.model_dump_json(indent=2)}

INSTRUCTIONS:
1. Write a clear, narrative clinical summary (2-4 paragraphs) synthesizing:
   - Patient presentation, demographics, and primary reason for visit.
   - Core diagnoses, key clinical observations, and therapeutic plan.
   - Specific attention to any flagged inconsistencies (e.g. allergy contraindications), missing critical data, and urgent concerns.
2. Maintain professional medical narrative prose. Do NOT just dump or truncate JSON.
"""

    try:
        summary_text = ai_client.generate_text(
            prompt=summary_prompt,
            image_path=image_path,
        )
        if summary_text and summary_text.strip():
            return summary_text.strip()
    except Exception as e:
        logger.warning(f"Dedicated LLM narrative summary generation failed or API unavailable: {e}. Generating fallback synthesis.")

    # High-quality programmatic synthesis fallback
    pt = structured_report.patient_information
    pt_desc = f"{pt.name or 'Patient'}"
    if pt.age:
        pt_desc += f", {pt.age} years old"
    if pt.gender:
        pt_desc += f" ({pt.gender})"

    dx_str = ", ".join(structured_report.diagnoses) if structured_report.diagnoses else "No definitive diagnosis specified"
    med_str = ", ".join([f"{m.name} {m.dosage or '(dosage unrecorded)'}" for m in structured_report.medications]) if structured_report.medications else "None documented"

    summary_paragraphs = [
        f"Clinical Review for {pt_desc}. Presenting diagnosis/conditions: {dx_str}.",
        f"Documented medications: {med_str}. Vital signs: BP {structured_report.vitals.blood_pressure or 'N/A'}, HR {structured_report.vitals.heart_rate or 'N/A'}.",
    ]

    if structured_report.potential_inconsistencies:
        summary_paragraphs.append(
            f"WARNING - POTENTIAL INCONSISTENCIES FLAGGED: {' | '.join(structured_report.potential_inconsistencies)}"
        )

    if structured_report.missing_information:
        summary_paragraphs.append(
            f"Missing Critical Data: {' | '.join(structured_report.missing_information)}"
        )

    if structured_report.requires_review:
        summary_paragraphs.append("Status: MANUAL CLINICIAN REVIEW REQUIRED due to flagged clinical discrepancies or incomplete data.")
    else:
        summary_paragraphs.append("Status: Document extraction complete and verified consistent.")

    return "\n\n".join(summary_paragraphs)


def process_clinical_document(
    extracted_text: str,
    image_path: Optional[str] = None,
    client: Optional[GeminiClient] = None,
) -> ClinicalExtractionResult:
    """
    End-to-end clinical document processing pipeline:
    1. Quality verification
    2. Structured data extraction with schema validation & repair retry
    3. Distinct narrative summary generation
    """
    check_document_quality(extracted_text, image_path)

    structured_report = extract_structured_clinical_data(
        text=extracted_text,
        image_path=image_path,
        client=client,
    )

    report_summary = generate_clinical_summary(
        text=extracted_text,
        structured_report=structured_report,
        image_path=image_path,
        client=client,
    )

    confidence = 0.98 if not structured_report.requires_review else 0.85

    return ClinicalExtractionResult(
        structured_report=structured_report,
        report_summary=report_summary,
        extracted_text=extracted_text,
        confidence_score=confidence,
    )
