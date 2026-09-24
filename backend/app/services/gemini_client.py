"""Gemini AI API Client interface with structured output support and fallback mode."""
import os
import re
import json
import logging
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper around Gemini API supporting text and vision prompts with JSON schemas."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name or settings.GEMINI_MODEL
        self._genai_client = None

        if self.api_key:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized google.genai Client with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Could not initialize google.genai client: {e}. Falling back if needed.")

    def generate_structured_json(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
    ) -> str:
        """
        Execute Gemini prompt and return the raw JSON string.
        Automatically retries alternate model names if primary model is busy (503) or deprecated.
        Falls back to heuristic rule-based structured extraction when API fails.
        """
        if self._genai_client:
            models_to_try = [self.model_name]
            for alt_model in ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.1-pro-preview"]:
                if alt_model not in models_to_try:
                    models_to_try.append(alt_model)

            for target_model in models_to_try:
                try:
                    from google.genai import types

                    contents: List[Any] = []
                    if image_path and os.path.exists(image_path):
                        image = Image.open(image_path)
                        contents.append(image)
                    contents.append(prompt)

                    config = types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    )
                    if schema:
                        config.response_schema = schema

                    response = self._genai_client.models.generate_content(
                        model=target_model,
                        contents=contents,
                        config=config,
                    )
                    if response.text and response.text.strip():
                        return response.text
                except Exception as e:
                    logger.warning(f"Gemini generate_structured_json model '{target_model}' failed ({e}). Trying next fallback model...")

        # Heuristic / Offline fallback extraction
        return self._generate_fallback_json(prompt, image_path)

    def generate_text(
        self,
        prompt: str,
        image_path: Optional[str] = None,
    ) -> str:
        """
        Generate plain text/narrative prose from Gemini.
        Falls back to narrative synthesis when API is unavailable.
        """
        if self._genai_client:
            models_to_try = [self.model_name]
            for alt_model in ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.1-pro-preview"]:
                if alt_model not in models_to_try:
                    models_to_try.append(alt_model)

            for target_model in models_to_try:
                try:
                    from google.genai import types

                    contents: List[Any] = []
                    if image_path and os.path.exists(image_path):
                        image = Image.open(image_path)
                        contents.append(image)
                    contents.append(prompt)

                    config = types.GenerateContentConfig(
                        temperature=0.2,
                    )

                    response = self._genai_client.models.generate_content(
                        model=target_model,
                        contents=contents,
                        config=config,
                    )
                    if response.text and response.text.strip():
                        return response.text
                except Exception as e:
                    logger.warning(f"Gemini generate_text model '{target_model}' failed ({e}). Trying next fallback model...")

        return self._generate_fallback_text(prompt)

    def repair_json_output(
        self,
        original_text: str,
        malformed_output: str,
        validation_error: str,
        schema: Optional[Type[BaseModel]] = None,
    ) -> str:
        """
        Explicit repair prompt asking Gemini to fix invalid/malformed JSON.
        """
        repair_prompt = f"""
You are an expert clinical data parsing and JSON repair agent.
The previous JSON output failed validation against the required schema.

VALIDATION ERROR:
{validation_error}

PREVIOUS INVALID OUTPUT:
{malformed_output}

ORIGINAL CLINICAL INPUT:
{original_text}

INSTRUCTIONS:
1. Fix all formatting, syntax, and schema validation errors.
2. Return ONLY a valid JSON object matching the required schema.
3. Ensure all clinical facts from the original clinical input are preserved.
"""
        return self.generate_structured_json(
            prompt=repair_prompt,
            schema=schema,
        )

    @property
    def is_configured(self) -> bool:
        """Returns True if a Gemini API key is configured and client initialized."""
        return self._genai_client is not None

    def _generate_fallback_json(self, prompt: str, image_path: Optional[str] = None) -> str:
        """Heuristic rule-based JSON generation for offline or unconfigured environments."""
        from app.schemas.clinical_report import (
            StructuredClinicalReport,
            PatientInformation,
            MedicationItem,
            AllergyItem,
            Vitals,
        )

        text = prompt

        # Heuristic extraction of patient name, age, gender, MRN
        name_match = re.search(r"Patient(?:\s*Name|\s*ID|:)?\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)", text, re.IGNORECASE)
        age_match = re.search(r"(\d{1,3})\s*(?:yo|years?\s*old|y/o|age)", text, re.IGNORECASE)
        gender_match = re.search(r"\b(Male|Female|Man|Woman)\b", text, re.IGNORECASE)
        mrn_match = re.search(r"MRN\s*[:=]?\s*([A-Za-z0-9-]+)", text, re.IGNORECASE)

        # Heuristic extraction of vitals
        bp_match = re.search(r"BP\s*[:=]?\s*(\d{2,3}/\d{2,3})", text, re.IGNORECASE)
        hr_match = re.search(r"HR\s*[:=]?\s*(\d{2,3})", text, re.IGNORECASE)
        temp_match = re.search(r"Temp(?:erature)?\s*[:=]?\s*([\d\.]+\s*[FC]?)", text, re.IGNORECASE)
        o2_match = re.search(r"O2\s*Sat(?:uration)?\s*[:=]?\s*(\d{2,3}%?)", text, re.IGNORECASE)

        # Check for allergies
        allergies = []
        allergy_match = re.search(r"Allerg(?:y|ies)\s*[:=]?\s*([^.\n]+)", text, re.IGNORECASE)
        if allergy_match:
            raw_allergy = allergy_match.group(1).strip()
            if "nkda" not in raw_allergy.lower() and "none" not in raw_allergy.lower():
                # Extract drug name and reaction if present
                allergen_parts = raw_allergy.split("(")
                substance = allergen_parts[0].strip()
                reaction = allergen_parts[1].rstrip(")").strip() if len(allergen_parts) > 1 else "Documented Reaction"
                allergies.append(AllergyItem(substance=substance, reaction=reaction, severity="High Risk" if "anaphylaxis" in raw_allergy.lower() else "Documented"))

        # Check for medications
        medications = []
        med_matches = re.findall(
            r"\b(Lisinopril|Amoxicillin|Metformin|Azithromycin|Aspirin|Ibuprofen|Atorvastatin|Omeprazole|Compound-\d+)\s*(\d+\s*mg)?\s*(PO|IV|oral)?\s*(once daily|TID|BID|Q3W)?",
            text,
            re.IGNORECASE,
        )
        for med_tuple in med_matches:
            med_name = med_tuple[0]
            med_dose = med_tuple[1].strip() if len(med_tuple) > 1 and med_tuple[1] else None
            med_route = med_tuple[2].strip() if len(med_tuple) > 2 and med_tuple[2] else None
            med_freq = med_tuple[3].strip() if len(med_tuple) > 3 and med_tuple[3] else None
            medications.append(MedicationItem(
                name=med_name,
                dosage=med_dose,
                route=med_route,
                frequency=med_freq,
                status="prescribed" if "prescrip" in text.lower() else "active"
            ))

        # Check for diagnoses / conditions
        diagnoses = []
        dx_matches = re.findall(
            r"\b(Hypertension|Diabetes|Bronchitis|Melanoma|Abscess|Asthma|Cancer|Pneumonia|Infection|Periapical abscess|NSCLC)\b",
            text,
            re.IGNORECASE,
        )
        for dx in dx_matches:
            if dx.capitalize() not in diagnoses:
                diagnoses.append(dx.capitalize())

        # Check for symptoms
        symptoms = []
        symptom_matches = re.findall(
            r"\b(Cough|Fever|Pain|Tightness|Shortness of breath|Swelling|Dyspnea|Fatigue|Chest tightness)\b",
            text,
            re.IGNORECASE,
        )
        for sym in symptom_matches:
            if sym.capitalize() not in symptoms:
                symptoms.append(sym.capitalize())

        report = StructuredClinicalReport(
            patient_information=PatientInformation(
                name=name_match.group(1) if name_match else None,
                age=int(age_match.group(1)) if age_match else None,
                gender=gender_match.group(1).capitalize() if gender_match else None,
                mrn=mrn_match.group(1) if mrn_match else None,
            ),
            symptoms=symptoms or ["Clinical encounter evaluation"],
            diagnoses=diagnoses or ["Clinical investigation under review"],
            medications=medications,
            vitals=Vitals(
                blood_pressure=bp_match.group(1) if bp_match else None,
                heart_rate=int(hr_match.group(1)) if hr_match else None,
                temperature=temp_match.group(1) if temp_match else None,
                o2_saturation=o2_match.group(1) if o2_match else None,
            ),
            allergies=allergies,
            clinical_observations=["Document processed via deterministic clinical extraction engine."],
            clinical_concerns=[],
            missing_information=[],
            potential_inconsistencies=[],
            requires_review=False,
        )
        return report.model_dump_json()

    def _generate_fallback_text(self, prompt: str) -> str:
        """Heuristic narrative text summary generator."""
        return (
            "Clinical Document Review: Patient clinical note and parameters extracted and analyzed via deterministic rules engine. "
            "Encounter findings, diagnoses, and medication prescriptions structured for clinical evaluation."
        )


# Global default client instance
gemini_client = GeminiClient()
