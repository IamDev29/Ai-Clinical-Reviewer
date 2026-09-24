"""Unit tests for AI/ML Clinical Extraction Pipeline."""
import pytest
from app.core.exceptions import (
    DocumentQualityError,
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
from app.services.clinical_extractor import (
    check_document_quality,
    extract_structured_clinical_data,
    generate_clinical_summary,
    process_clinical_document,
)
from app.services.gemini_client import GeminiClient


class MockGeminiClient(GeminiClient):
    """Configurable mock for Gemini AI responses."""

    def __init__(
        self,
        json_responses: list[str] = None,
        text_responses: list[str] = None,
        repair_responses: list[str] = None,
    ):
        super().__init__()
        self.json_responses = json_responses or []
        self.text_responses = text_responses or []
        self.repair_responses = repair_responses or []
        self.json_call_count = 0
        self.text_call_count = 0
        self.repair_call_count = 0

    def generate_structured_json(self, prompt: str, image_path=None, schema=None) -> str:
        if self.json_call_count < len(self.json_responses):
            res = self.json_responses[self.json_call_count]
            self.json_call_count += 1
            return res
        # Default fallback response
        return StructuredClinicalReport(
            patient_information=PatientInformation(name="Default Patient", age=45),
            symptoms=["Fatigue"],
            diagnoses=["General Malaise"],
            requires_review=False,
        ).model_dump_json()

    def generate_text(self, prompt: str, image_path=None) -> str:
        if self.text_call_count < len(self.text_responses):
            res = self.text_responses[self.text_call_count]
            self.text_call_count += 1
            return res
        return "Dedicated Narrative Summary: Patient evaluated and documented in stable condition."

    def repair_json_output(self, original_text: str, malformed_output: str, validation_error: str, schema=None) -> str:
        self.repair_call_count += 1
        if self.repair_responses:
            return self.repair_responses.pop(0)
        raise ValueError("Repair failed")


# =====================================================================
# 1. CLEAN SYNTHETIC NOTE TEST
# =====================================================================

def test_clean_synthetic_note_extraction():
    """
    Clean note: comprehensive patient information, vitals, complete medications,
    no allergy conflicts. Should produce requires_review=False (or clean status).
    """
    clean_note = """
    PATIENT PROGRESS NOTE
    Patient: John Doe, 58yo Male. MRN: 109283. DOB: 1968-04-12.
    Chief Complaint: Routine follow-up for well-managed hypertension.
    Vitals: BP 122/78 mmHg, HR 72 bpm, Temp 98.6 F, O2 Sat 99% on RA, BMI 24.5.
    Diagnoses: Essential Hypertension (stable).
    Medications: Lisinopril 10mg oral once daily (active).
    Allergies: NKDA (No Known Drug Allergies).
    Observations: S1/S2 regular, no murmurs, lungs clear to auscultation bilaterally.
    Plan: Continue current regimen. Return in 6 months.
    """

    mock_llm_json = StructuredClinicalReport(
        patient_information=PatientInformation(
            name="John Doe",
            age=58,
            gender="Male",
            mrn="109283",
            dob="1968-04-12",
        ),
        symptoms=["Routine follow-up"],
        diagnoses=["Essential Hypertension"],
        medications=[
            MedicationItem(
                name="Lisinopril",
                dosage="10mg",
                frequency="once daily",
                route="oral",
                status="active",
            )
        ],
        vitals=Vitals(
            blood_pressure="122/78 mmHg",
            heart_rate=72,
            temperature="98.6 F",
            o2_saturation="99%",
            bmi=24.5,
        ),
        allergies=[],
        clinical_observations=["Lungs clear to auscultation", "S1/S2 regular"],
        clinical_concerns=[],
        missing_information=[],
        potential_inconsistencies=[],
        requires_review=False,
    ).model_dump_json()

    mock_client = MockGeminiClient(
        json_responses=[mock_llm_json],
        text_responses=[
            "58-year-old male John Doe evaluated for routine follow-up of stable hypertension. "
            "Vital signs and physical exam are unremarkable. Lisinopril 10mg continued without changes."
        ],
    )

    result = process_clinical_document(
        extracted_text=clean_note,
        client=mock_client,
    )

    assert result.structured_report.patient_information.name == "John Doe"
    assert result.structured_report.patient_information.age == 58
    assert len(result.structured_report.medications) == 1
    assert result.structured_report.medications[0].dosage == "10mg"
    assert len(result.structured_report.missing_information) == 0
    assert len(result.structured_report.potential_inconsistencies) == 0
    assert result.structured_report.requires_review is False
    assert "John Doe" in result.report_summary
    assert result.confidence_score > 0.90


# =====================================================================
# 2. SPARSE / INCOMPLETE NOTE TEST
# =====================================================================

def test_sparse_incomplete_note_flags_missing_data():
    """
    Sparse note: missing age/DOB, missing vitals, medication missing dosage.
    Should explicitly populate missing_information and set requires_review=True.
    """
    sparse_note = """
    Patient came in complaining of severe chest tightness and shortness of breath.
    Diagnosed with acute bronchitis.
    Started on Azithromycin.
    """

    mock_llm_json = StructuredClinicalReport(
        patient_information=PatientInformation(name=None, age=None),
        symptoms=["Severe chest tightness", "Shortness of breath"],
        diagnoses=["Acute bronchitis"],
        medications=[MedicationItem(name="Azithromycin", dosage=None)],
        vitals=Vitals(),
        allergies=[],
        clinical_observations=[],
        clinical_concerns=["Severe chest tightness in uncharacterized patient"],
        missing_information=[
            "Patient age/DOB missing",
            "Dosage and duration missing for Azithromycin",
            "Vital signs (BP, HR, SpO2) completely unrecorded for acute dyspnea",
        ],
        potential_inconsistencies=[],
        requires_review=True,
    ).model_dump_json()

    mock_client = MockGeminiClient(
        json_responses=[mock_llm_json],
        text_responses=[
            "Patient presented with acute chest tightness and dyspnea. Azithromycin was initiated. "
            "WARNING: Patient demographics, drug dosages, and vital signs are missing. CLINICIAN REVIEW REQUIRED."
        ],
    )

    result = process_clinical_document(
        extracted_text=sparse_note,
        client=mock_client,
    )

    report = result.structured_report
    assert report.requires_review is True
    assert len(report.missing_information) > 0
    # Verify specific flags are present
    missing_str = " ".join(report.missing_information)
    assert "age" in missing_str.lower() or "dob" in missing_str.lower()
    assert "dosage" in missing_str.lower() or "vital" in missing_str.lower()
    assert "CLINICIAN REVIEW REQUIRED" in result.report_summary or "WARNING" in result.report_summary or "Review" in result.report_summary


# =====================================================================
# 3. DELIBERATELY CONTRADICTORY NOTE TEST (ALLERGY + CONFLICTING MEDICATION)
# =====================================================================

def test_contradictory_note_flags_allergy_medication_conflict():
    """
    Contradictory note: documented Penicillin allergy (anaphylaxis) but prescribed Amoxicillin 500mg.
    Must flag in potential_inconsistencies and enforce requires_review=True.
    """
    contradictory_note = """
    EMERGENCY ENCOUNTER
    Patient: Jane Smith, 42yo Female.
    Allergies: Penicillin (Severe Anaphylaxis).
    Chief Complaint: Dental abscess with facial swelling.
    Diagnoses: Periapical abscess.
    Prescription / Treatment: Amoxicillin 500mg PO TID x 7 days.
    Vitals: BP 130/85, HR 88.
    """

    mock_llm_json = StructuredClinicalReport(
        patient_information=PatientInformation(name="Jane Smith", age=42, gender="Female"),
        symptoms=["Dental abscess", "Facial swelling"],
        diagnoses=["Periapical abscess"],
        medications=[
            MedicationItem(
                name="Amoxicillin",
                dosage="500mg",
                frequency="TID",
                route="PO",
                status="prescribed",
            )
        ],
        vitals=Vitals(blood_pressure="130/85", heart_rate=88),
        allergies=[
            AllergyItem(
                substance="Penicillin",
                reaction="Anaphylaxis",
                severity="Severe",
            )
        ],
        clinical_observations=["Facial swelling"],
        clinical_concerns=["Life-threatening drug-allergy contraindication"],
        missing_information=[],
        potential_inconsistencies=[
            "CRITICAL CONTRAINDICATION: Patient has documented severe allergy to Penicillin, but Amoxicillin (penicillin-class antibiotic) was prescribed."
        ],
        requires_review=True,
    ).model_dump_json()

    mock_client = MockGeminiClient(json_responses=[mock_llm_json])

    result = process_clinical_document(
        extracted_text=contradictory_note,
        client=mock_client,
    )

    report = result.structured_report
    assert report.requires_review is True
    assert len(report.potential_inconsistencies) > 0

    inconsistency_text = " ".join(report.potential_inconsistencies)
    assert "penicillin" in inconsistency_text.lower()
    assert "amoxicillin" in inconsistency_text.lower()


# =====================================================================
# 4. DOCUMENT QUALITY GUARDRAIL TESTS
# =====================================================================

def test_document_quality_guardrail_empty_text():
    """Empty or whitespace text must raise DocumentQualityError."""
    with pytest.raises(DocumentQualityError) as exc:
        process_clinical_document(extracted_text="    \n   ")
    assert "Document quality is too poor" in str(exc.value)


def test_document_quality_guardrail_gibberish():
    """Random non-clinical symbols or gibberish must raise DocumentQualityError."""
    with pytest.raises(DocumentQualityError) as exc:
        process_clinical_document(extracted_text="!@#$%^&*()_+=-~`")
    assert "Document quality is too poor" in str(exc.value)


# =====================================================================
# 5. SCHEMA VALIDATION & ONE-STEP REPAIR RETRY TESTS
# =====================================================================

def test_extraction_repair_prompt_success():
    """
    Simulate initial malformed JSON (e.g. invalid syntax), then successful repair prompt.
    """
    malformed_initial = '{"patient_information": "bad_type_not_dict", "requires_review": "invalid_bool"}'
    valid_repaired = StructuredClinicalReport(
        patient_information=PatientInformation(name="Repaired Patient", age=30),
        symptoms=["Cough"],
        diagnoses=["Upper Respiratory Infection"],
        requires_review=False,
    ).model_dump_json()

    mock_client = MockGeminiClient(
        json_responses=[malformed_initial],
        repair_responses=[valid_repaired],
    )

    report = extract_structured_clinical_data(
        text="Patient presents with cough for 3 days. Diagnosed with URI.",
        client=mock_client,
    )

    assert mock_client.repair_call_count == 1
    assert report.patient_information.name == "Repaired Patient"
    assert report.patient_information.age == 30


def test_extraction_repair_prompt_failure_raises():
    """
    Simulate initial malformed JSON and repair also returning unparseable garbage.
    Must fail gracefully with ExtractionRepairFailedError.
    """
    malformed_initial = '{"corrupted": true'
    malformed_repair = '{"still_broken": true'

    mock_client = MockGeminiClient(
        json_responses=[malformed_initial],
        repair_responses=[malformed_repair],
    )

    with pytest.raises(ExtractionRepairFailedError) as exc:
        extract_structured_clinical_data(
            text="Valid patient clinical note content here for processing.",
            client=mock_client,
        )
    assert "Failed to produce valid clinical report schema after repair retry" in str(exc.value)


# =====================================================================
# 6. DISTINCT SUMMARY STEP TEST
# =====================================================================

def test_distinct_summary_generation():
    """
    Verify that report_summary is generated through a distinct narrative synthesis step.
    """
    structured_data = StructuredClinicalReport(
        patient_information=PatientInformation(name="Alice Brown", age=65),
        diagnoses=["Type 2 Diabetes Mellitus"],
        medications=[MedicationItem(name="Metformin", dosage="1000mg", frequency="BID")],
        vitals=Vitals(blood_pressure="128/82"),
        requires_review=False,
    )

    mock_summary_text = (
        "Alice Brown, a 65-year-old patient, presented for chronic diabetes management. "
        "Blood pressure is well-controlled at 128/82. Metformin 1000mg twice daily is maintained."
    )

    mock_client = MockGeminiClient(text_responses=[mock_summary_text])

    summary = generate_clinical_summary(
        text="Source note text here",
        structured_report=structured_data,
        client=mock_client,
    )

    assert mock_client.text_call_count == 1
    assert "Alice Brown" in summary
    assert "Metformin 1000mg" in summary
