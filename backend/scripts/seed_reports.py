"""Seed script for populating synthetic clinical sample reports with strictly validated schema."""
import os
import sys
from typing import List
from sqlalchemy.orm import Session

# Add backend directory to sys.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal, Base, engine
from app.models.report import Report, ReportStatus, InputType
from app.crud.crud_report import create_report

SAMPLE_REPORTS_DATA = [
    {
        "status": ReportStatus.COMPLETED,
        "input_type": InputType.TEXT,
        "raw_input_ref": "PATIENT_NOTE_CLEAN_001",
        "extracted_text": (
            "PATIENT PROGRESS NOTE\n"
            "Patient: John Doe, 58yo Male. MRN: 109283. DOB: 1968-04-12.\n"
            "Chief Complaint: Routine follow-up for well-managed essential hypertension.\n"
            "Vitals: BP 122/78 mmHg, HR 72 bpm, Temp 98.6 F, O2 Sat 99% on RA, BMI 24.5.\n"
            "Diagnoses: Essential Hypertension (stable).\n"
            "Medications: Lisinopril 10mg oral once daily (active).\n"
            "Allergies: NKDA (No Known Drug Allergies).\n"
            "Observations: S1/S2 regular, no murmurs, lungs clear to auscultation bilaterally.\n"
            "Plan: Continue current regimen. Return in 6 months."
        ),
        "report_summary": (
            "Clinical Review for John Doe, 58 years old (Male). Presenting diagnosis: Essential Hypertension (stable).\n\n"
            "Documented medications: Lisinopril 10mg. Vital signs: BP 122/78, HR 72 bpm, Temp 98.6 F. No known drug allergies documented.\n\n"
            "Status: Document extraction complete and verified consistent."
        ),
        "structured_report": {
            "patient_information": {
                "name": "John Doe",
                "age": 58,
                "gender": "Male",
                "mrn": "109283",
                "dob": "1968-04-12"
            },
            "symptoms": ["Routine follow-up"],
            "diagnoses": ["Essential Hypertension"],
            "medications": [
                {
                    "name": "Lisinopril",
                    "dosage": "10mg",
                    "frequency": "once daily",
                    "route": "oral",
                    "status": "active"
                }
            ],
            "vitals": {
                "blood_pressure": "122/78",
                "heart_rate": 72,
                "respiratory_rate": 16,
                "temperature": "98.6 F",
                "o2_saturation": "99%",
                "bmi": 24.5
            },
            "allergies": [],
            "clinical_observations": [
                "S1/S2 regular, no murmurs",
                "Lungs clear to auscultation bilaterally"
            ],
            "clinical_concerns": [],
            "missing_information": [],
            "potential_inconsistencies": [],
            "requires_review": False
        },
        "error_message": None,
    },
    {
        "status": ReportStatus.COMPLETED,
        "input_type": InputType.TEXT,
        "raw_input_ref": "PATIENT_NOTE_CONTRADICTORY_002",
        "extracted_text": (
            "EMERGENCY ENCOUNTER NOTE\n"
            "Patient: Jane Smith, 42yo Female. MRN: 449210.\n"
            "Allergies: Penicillin (Severe Anaphylaxis).\n"
            "Chief Complaint: Severe dental abscess with facial swelling.\n"
            "Diagnoses: Periapical abscess.\n"
            "Prescription: Amoxicillin 500mg PO TID x 7 days.\n"
            "Vitals: BP 130/85 mmHg, HR 88 bpm."
        ),
        "report_summary": (
            "Clinical Review for Jane Smith, 42 years old (Female). Presenting diagnosis: Periapical abscess.\n\n"
            "Documented medications: Amoxicillin 500mg PO TID. Vital signs: BP 130/85 mmHg, HR 88 bpm. Documented allergy to Penicillin.\n\n"
            "WARNING - POTENTIAL INCONSISTENCIES FLAGGED: CRITICAL CONTRAINDICATION: Documented allergy to 'Penicillin' conflicts with prescribed medication 'Amoxicillin'.\n\n"
            "Status: MANUAL CLINICIAN REVIEW REQUIRED due to flagged clinical discrepancies."
        ),
        "structured_report": {
            "patient_information": {
                "name": "Jane Smith",
                "age": 42,
                "gender": "Female",
                "mrn": "449210",
                "dob": None
            },
            "symptoms": ["Severe dental abscess", "Facial swelling"],
            "diagnoses": ["Periapical abscess"],
            "medications": [
                {
                    "name": "Amoxicillin",
                    "dosage": "500mg",
                    "frequency": "TID",
                    "route": "PO",
                    "status": "prescribed"
                }
            ],
            "vitals": {
                "blood_pressure": "130/85",
                "heart_rate": 88,
                "respiratory_rate": None,
                "temperature": None,
                "o2_saturation": None,
                "bmi": None
            },
            "allergies": [
                {
                    "substance": "Penicillin",
                    "reaction": "Severe Anaphylaxis",
                    "severity": "High Risk"
                }
            ],
            "clinical_observations": ["Facial swelling observed on physical exam"],
            "clinical_concerns": ["Acute dental abscess requiring immediate antibiotic modification"],
            "missing_information": [
                "Missing critical patient demographic: Date of Birth not documented.",
                "Missing physiological vital signs: Temperature unrecorded for acute infectious presentation."
            ],
            "potential_inconsistencies": [
                "CRITICAL CONTRAINDICATION: Documented allergy to 'Penicillin' conflicts with prescribed medication 'Amoxicillin'."
            ],
            "requires_review": True
        },
        "error_message": None,
    },
    {
        "status": ReportStatus.COMPLETED,
        "input_type": InputType.PDF,
        "raw_input_ref": "/storage/uploads/protocol_oncology_phase3_sample.pdf",
        "extracted_text": (
            "CLINICAL TRIAL PROTOCOL\n"
            "Study Title: Phase 3 Randomized Study of Immuno-Oncology Compound XYZ-101 in Stage IV NSCLC.\n"
            "Eligibility Criteria: Adults age >= 18 with confirmed Non-Small Cell Lung Cancer.\n"
            "Primary Endpoints: Overall Survival (OS) and Progression-Free Survival (PFS).\n"
            "Investigational Arm: Compound XYZ-101 200mg IV Q3W."
        ),
        "report_summary": (
            "Clinical Protocol Review: Phase 3 Immuno-Oncology Study for Stage IV NSCLC.\n\n"
            "Investigational arm involves Compound XYZ-101 200mg IV every 3 weeks. Inclusion requires age >= 18 and histologically confirmed NSCLC.\n\n"
            "Status: Document extraction complete and verified."
        ),
        "structured_report": {
            "patient_information": {
                "name": "Cohort Protocol (NSCLC)",
                "age": None,
                "gender": "All",
                "mrn": "PROTOCOL-XYZ-101",
                "dob": None
            },
            "symptoms": ["Stage IV Non-Small Cell Lung Cancer"],
            "diagnoses": ["Non-Small Cell Lung Cancer"],
            "medications": [
                {
                    "name": "Compound XYZ-101",
                    "dosage": "200mg",
                    "frequency": "Q3W",
                    "route": "IV",
                    "status": "investigational"
                }
            ],
            "vitals": {
                "blood_pressure": None,
                "heart_rate": None,
                "respiratory_rate": None,
                "temperature": None,
                "o2_saturation": None,
                "bmi": None
            },
            "allergies": [],
            "clinical_observations": ["Phase 3 study protocol design reviewed"],
            "clinical_concerns": [],
            "missing_information": ["Protocol document does not record individual patient demographics or baseline vitals."],
            "potential_inconsistencies": [],
            "requires_review": True
        },
        "error_message": None,
    }
]


def seed_sample_reports(db: Session) -> List[Report]:
    """Upsert synthetic sample reports with clean structure."""
    seeded_reports: List[Report] = []
    for report_dict in SAMPLE_REPORTS_DATA:
        existing = (
            db.query(Report)
            .filter(Report.raw_input_ref == report_dict["raw_input_ref"])
            .first()
        )
        if existing:
            existing.status = report_dict["status"]
            existing.input_type = report_dict["input_type"]
            existing.extracted_text = report_dict["extracted_text"]
            existing.report_summary = report_dict["report_summary"]
            existing.structured_report = report_dict["structured_report"]
            existing.error_message = report_dict["error_message"]
            db.commit()
            db.refresh(existing)
            seeded_reports.append(existing)
            print(f"[+] Updated sample report #{existing.id} ({existing.status.value})")
        else:
            created = create_report(db, report_in=report_dict)
            seeded_reports.append(created)
            print(f"[+] Seeded new report #{created.id} ({created.status.value})")
    return seeded_reports


def main():
    print("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Seeding synthetic sample reports...")
        seeded = seed_sample_reports(db)
        print(f"Successfully seeded/updated {len(seeded)} reports.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
