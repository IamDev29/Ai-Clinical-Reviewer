"""Pydantic schemas for Report."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.report import ReportStatus, InputType


class ReportBase(BaseModel):
    input_type: InputType
    raw_input_ref: str
    extracted_text: Optional[str] = None
    report_summary: Optional[str] = None
    structured_report: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class ReportCreate(ReportBase):
    status: ReportStatus = ReportStatus.PENDING


class ReportUpdateStatus(BaseModel):
    status: ReportStatus
    error_message: Optional[str] = None
    extracted_text: Optional[str] = None
    report_summary: Optional[str] = None
    structured_report: Optional[Dict[str, Any]] = None


class ReportInDBBase(ReportBase):
    id: int
    status: ReportStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportResponse(ReportInDBBase):
    pass


class ReportListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[ReportResponse]
