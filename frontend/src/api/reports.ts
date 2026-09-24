import { apiClient } from './apiClient';

export type ReportStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type InputType = 'text' | 'image' | 'pdf';

export interface PatientInformation {
  name?: string | null;
  age?: number | string | null;
  gender?: string | null;
  mrn?: string | null;
  dob?: string | null;
}

export interface MedicationItem {
  name: string;
  dosage?: string | null;
  frequency?: string | null;
  route?: string | null;
  status?: string | null;
}

export interface AllergyItem {
  substance: string;
  reaction?: string | null;
  severity?: string | null;
}

export interface Vitals {
  blood_pressure?: string | null;
  heart_rate?: number | string | null;
  respiratory_rate?: number | string | null;
  temperature?: string | null;
  o2_saturation?: string | null;
  bmi?: number | string | null;
}

export interface StructuredClinicalReport {
  patient_information?: PatientInformation;
  symptoms?: string[];
  diagnoses?: string[];
  medications?: MedicationItem[];
  vitals?: Vitals;
  allergies?: AllergyItem[];
  clinical_observations?: string[];
  clinical_concerns?: string[];
  missing_information?: string[];
  potential_inconsistencies?: string[];
  requires_review?: boolean;
}

export interface Report {
  id: number;
  created_at: string;
  status: ReportStatus;
  input_type: InputType;
  raw_input_ref: string;
  extracted_text?: string | null;
  report_summary?: string | null;
  structured_report?: StructuredClinicalReport | null;
  error_message?: string | null;
}

export interface ReportListResponse {
  total: number;
  skip: number;
  limit: number;
  items: Report[];
}

export const submitClinicalReport = async (data: {
  text?: string;
  file?: File | null;
}): Promise<Report> => {
  const formData = new FormData();
  if (data.text !== undefined && data.text !== null) {
    formData.append('text', data.text);
  }
  if (data.file) {
    formData.append('file', data.file);
  }
  return apiClient.post<Report>('/reports', formData);
};

export const getReportById = async (reportId: number | string): Promise<Report> => {
  return apiClient.get<Report>(`/reports/${reportId}`);
};

export const listReports = async (
  skip: number = 0,
  limit: number = 20
): Promise<ReportListResponse> => {
  return apiClient.get<ReportListResponse>('/reports', { skip, limit });
};
