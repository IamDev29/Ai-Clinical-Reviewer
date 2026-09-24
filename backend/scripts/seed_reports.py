"""Seed script for populating synthetic clinical sample reports."""
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
        "input_type": InputType.PDF,
        "raw_input_ref": "/storage/clinical_docs/protocol_oncology_phase3_001.pdf",
        "extracted_text": (
            "STUDY PROTOCOL: Phase 3 Randomized Study of Immuno-Oncology Compound XYZ-101 "
            "in Patients with Advanced Non-Small Cell Lung Cancer (NSCLC). "
            "Inclusion Criteria: Age >= 18, Histologically confirmed stage IV NSCLC, "
            "ECOG performance status 0-1, adequate organ function. "
            "Exclusion Criteria: Prior exposure to PD-1/PD-L1 inhibitors, untreated CNS metastases."
        ),
        "report_summary": (
            "Phase 3 NSCLC immuno-oncology protocol reviewed. Identifies key inclusion requirements "
            "(age >= 18, ECOG 0-1, stage IV NSCLC) and exclusion conditions (prior checkpoint therapy, CNS lesions)."
        ),
        "structured_report": {
            "protocol_id": "XYZ-101-P3",
            "therapeutic_area": "Oncology",
            "indication": "Non-Small Cell Lung Cancer (Stage IV)",
            "phase": "Phase 3",
            "eligibility": {
                "min_age": 18,
                "ecog_performance": ["0", "1"],
                "biomarkers_required": ["PD-L1 expression >= 1%"],
                "exclusions": [
                    "Active CNS metastases",
                    "Autoimmune disease requiring systemic steroids",
                ],
            },
            "endpoints": {
                "primary": "Overall Survival (OS)",
                "secondary": ["Progression-Free Survival (PFS)", "Objective Response Rate (ORR)"],
            },
            "review_confidence_score": 0.96,
        },
        "error_message": None,
    },
    {
        "status": ReportStatus.PROCESSING,
        "input_type": InputType.TEXT,
        "raw_input_ref": "CLINICAL_NOTE_REF_98432",
        "extracted_text": (
            "PATIENT VISIT NOTE: 62-year-old male with history of Type 2 Diabetes Mellitus "
            "and hypertensive nephropathy. Current HbA1c: 8.4%, eGFR: 52 mL/min/1.73m2. "
            "Reviewing for eligibility in Renal SGLT2-Inhibitor Clinical Evaluation Trial."
        ),
        "report_summary": (
            "Patient note under review for diabetic nephropathy trial protocol matching."
        ),
        "structured_report": {
            "patient_cohort": "Cardiorenal / Metabolic",
            "extracted_parameters": {
                "age": 62,
                "gender": "Male",
                "hba1c": 8.4,
                "egfr": 52,
                "conditions": ["T2D", "Hypertensive Nephropathy"],
            },
            "pipeline_stage": "entity_resolution_in_progress",
        },
        "error_message": None,
    },
]


def seed_sample_reports(db: Session) -> List[Report]:
    """Insert 2 synthetic sample reports if not already present."""
    seeded_reports: List[Report] = []
    for report_dict in SAMPLE_REPORTS_DATA:
        # Check if already exists by raw_input_ref to avoid duplicate seeding
        existing = (
            db.query(Report)
            .filter(Report.raw_input_ref == report_dict["raw_input_ref"])
            .first()
        )
        if not existing:
            created = create_report(db, report_in=report_dict)
            seeded_reports.append(created)
            print(f"[+] Seeded report #{created.id} ({created.input_type.value} - {created.status.value})")
        else:
            seeded_reports.append(existing)
            print(f"[*] Report already present: #{existing.id}")
    return seeded_reports


def main():
    print("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Seeding synthetic sample reports...")
        seeded = seed_sample_reports(db)
        print(f"Successfully seeded {len(seeded)} reports.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
