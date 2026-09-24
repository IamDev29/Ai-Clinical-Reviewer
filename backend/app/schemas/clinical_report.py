"""Pydantic schema definitions for Structured Clinical Document Extraction."""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class PatientInformation(BaseModel):
    name: Optional[str] = Field(None, description="Patient full name if documented")
    age: Optional[Union[int, str]] = Field(None, description="Patient age or age string")
    gender: Optional[str] = Field(None, description="Patient biological sex or gender")
    mrn: Optional[str] = Field(None, description="Medical Record Number or Patient ID")
    dob: Optional[str] = Field(None, description="Date of birth")


class MedicationItem(BaseModel):
    name: str = Field(..., description="Medication generic or brand name")
    dosage: Optional[str] = Field(None, description="Dosage amount and strength (e.g. 500mg)")
    frequency: Optional[str] = Field(None, description="Administration frequency (e.g. twice daily)")
    route: Optional[str] = Field(None, description="Route of administration (e.g. oral, IV)")
    status: Optional[str] = Field(None, description="Active, discontinued, or prescribed")


class AllergyItem(BaseModel):
    substance: str = Field(..., description="Allergen or drug substance (e.g. Penicillin)")
    reaction: Optional[str] = Field(None, description="Allergic reaction description (e.g. Anaphylaxis, Rash)")
    severity: Optional[str] = Field(None, description="Severity rating if documented (e.g. Mild, Severe)")


class Vitals(BaseModel):
    blood_pressure: Optional[str] = Field(None, description="Blood pressure (e.g. 120/80 mmHg)")
    heart_rate: Optional[Union[int, str]] = Field(None, description="Heart rate in bpm")
    respiratory_rate: Optional[Union[int, str]] = Field(None, description="Respiratory rate in breaths/min")
    temperature: Optional[str] = Field(None, description="Body temperature (e.g. 98.6 F or 37 C)")
    o2_saturation: Optional[str] = Field(None, description="Oxygen saturation (e.g. 98% on room air)")
    bmi: Optional[Union[float, str]] = Field(None, description="Body Mass Index")


class StructuredClinicalReport(BaseModel):
    patient_information: PatientInformation = Field(
        default_factory=PatientInformation,
        description="Patient demographic and identification details",
    )
    symptoms: List[str] = Field(
        default_factory=list,
        description="List of patient symptoms and chief complaints",
    )
    diagnoses: List[str] = Field(
        default_factory=list,
        description="List of primary and secondary clinical diagnoses/conditions",
    )
    medications: List[MedicationItem] = Field(
        default_factory=list,
        description="List of medications, prescriptions, and dosages",
    )
    vitals: Vitals = Field(
        default_factory=Vitals,
        description="Recorded physiological vital signs",
    )
    allergies: List[AllergyItem] = Field(
        default_factory=list,
        description="Known drug and environmental allergies",
    )
    clinical_observations: List[str] = Field(
        default_factory=list,
        description="Physical exam findings, lab results, and diagnostic observations",
    )
    clinical_concerns: List[str] = Field(
        default_factory=list,
        description="Critical clinical issues, abnormal lab markers, and urgent risks",
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Explicitly detected missing critical fields, incomplete dosages, or absent vitals",
    )
    potential_inconsistencies: List[str] = Field(
        default_factory=list,
        description="Explicitly detected contradictions (e.g. medication prescribed despite documented allergy)",
    )
    requires_review: bool = Field(
        ...,
        description="True if critical information is missing, inconsistencies exist, or high clinical concerns present",
    )


class ClinicalExtractionResult(BaseModel):
    structured_report: StructuredClinicalReport
    report_summary: str
    extracted_text: str
    confidence_score: float = Field(0.95, ge=0.0, le=1.0)
