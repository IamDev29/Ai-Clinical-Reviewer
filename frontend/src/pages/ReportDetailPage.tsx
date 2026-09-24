import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  Clock,
  RefreshCw,
  User,
  HeartPulse,
  Activity,
  Pill,
  ShieldAlert,
  Microscope,
  FileText,
  ChevronDown,
  ChevronUp,
  XCircle,
  FileCode,
} from 'lucide-react';
import { getReportById, Report, StructuredClinicalReport } from '../api/reports';
import { ApiError } from '../api/apiClient';

export const ReportDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Collapsible section states
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    patient: true,
    vitals: true,
    diagnoses: true,
    medications: true,
    allergies: true,
    observations: true,
    concerns: true,
    rawText: false,
  });

  const toggleSection = (section: string) => {
    setOpenSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchReport = async (showLoadingSpinner: boolean = false) => {
    if (!id) return;
    if (showLoadingSpinner) setLoading(true);
    setError(null);

    try {
      const data = await getReportById(id);
      setReport(data);

      // Continue polling if status is pending or processing
      if (data.status === 'pending' || data.status === 'processing') {
        pollTimerRef.current = setTimeout(() => {
          fetchReport(false);
        }, 1500);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to load clinical report.');
      }
    } finally {
      if (showLoadingSpinner) setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport(true);

    return () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
      }
    };
  }, [id]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '5rem 1rem' }}>
        <RefreshCw size={36} className="animate-spin" style={{ color: '#60a5fa', margin: '0 auto 1rem auto' }} />
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Retrieving Clinical Report...</h2>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
          Loading document and telemetry...
        </p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ padding: '2rem 1rem' }}>
        <Link to="/reports" className="btn-secondary" style={{ marginBottom: '1.5rem' }}>
          <ArrowLeft size={16} /> Back to Reports History
        </Link>
        <div className="alert-banner alert-danger">
          <XCircle size={24} style={{ flexShrink: 0 }} />
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.25rem' }}>
              Report Not Found or Unreachable
            </h3>
            <p>{error || `Report with ID #${id} could not be loaded.`}</p>
          </div>
        </div>
      </div>
    );
  }

  const structured: StructuredClinicalReport | undefined = report.structured_report || undefined;
  const isPendingOrProcessing = report.status === 'pending' || report.status === 'processing';
  const isFailed = report.status === 'failed';
  const isCompleted = report.status === 'completed';

  return (
    <div className="report-detail-page">
      {/* Header & Meta */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <Link to="/reports" className="btn-secondary" style={{ marginBottom: '1rem' }}>
            <ArrowLeft size={16} /> Back to Reports
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.5rem' }}>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>Clinical Review #{report.id}</h1>
            <span className="type-badge">{report.input_type}</span>
            <span className={`status-badge status-${report.status}`}>
              {report.status === 'completed' && <CheckCircle2 size={12} />}
              {report.status === 'processing' && <RefreshCw size={12} className="animate-spin" />}
              {report.status === 'pending' && <Clock size={12} />}
              {report.status === 'failed' && <XCircle size={12} />}
              {report.status}
            </span>
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            Submitted on {new Date(report.created_at).toLocaleString()}
          </div>
        </div>

        <button
          type="button"
          className="btn-secondary"
          onClick={() => fetchReport(true)}
          title="Refresh report state"
        >
          <RefreshCw size={14} className={isPendingOrProcessing ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Processing State Banner */}
      {isPendingOrProcessing && (
        <div className="alert-banner alert-warning">
          <RefreshCw size={20} className="animate-spin" style={{ flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 700 }}>AI Extraction & Clinical Analysis in Progress</div>
            <div>
              PyMuPDF and Gemini are actively extracting clinical entities, safety cross-checks, and narrative summaries. This page will automatically update in real-time.
            </div>
          </div>
        </div>
      )}

      {/* Failure State Banner (Legible and structured) */}
      {isFailed && (
        <div className="alert-banner alert-danger">
          <AlertOctagon size={24} style={{ flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.05rem', marginBottom: '0.3rem' }}>
              Clinical Extraction Failed
            </div>
            <div style={{ fontSize: '0.95rem' }}>
              {report.error_message || 'An unhandled exception occurred during document processing.'}
            </div>
          </div>
        </div>
      )}

      {/* COMPLETED REPORT CONTENT */}
      {isCompleted && (
        <>
          {/* Prominent Narrative Report Summary */}
          {report.report_summary && (
            <div className="summary-card">
              <div className="summary-header">
                <FileText size={20} />
                <span>Executive Clinical Summary</span>
              </div>
              <div className="summary-prose">{report.report_summary}</div>
            </div>
          )}

          {/* Clinician Review Required Warning Callout */}
          {structured?.requires_review && (
            <div className="alert-banner alert-warning" style={{ borderLeftWidth: '5px', borderLeftColor: 'var(--accent-amber)' }}>
              <AlertTriangle size={24} style={{ flexShrink: 0, color: 'var(--accent-amber)' }} />
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.05rem', marginBottom: '0.25rem' }}>
                  Action Required: Clinician Verification Needed
                </div>
                <div>
                  This document has been flagged due to potential clinical inconsistencies, contraindications, or missing critical data. Review the highlighted items below prior to clinical decision-making.
                </div>
              </div>
            </div>
          )}

          {/* Potential Inconsistencies & Contraindications Callouts */}
          {structured?.potential_inconsistencies && structured.potential_inconsistencies.length > 0 && (
            <div className="alert-banner alert-danger" style={{ borderLeftWidth: '5px', borderLeftColor: 'var(--accent-rose)' }}>
              <AlertOctagon size={24} style={{ flexShrink: 0, color: 'var(--accent-rose)' }} />
              <div style={{ width: '100%' }}>
                <div style={{ fontWeight: 700, fontSize: '1.05rem', marginBottom: '0.5rem' }}>
                  Critical Inconsistencies & Contraindications Detected
                </div>
                <ul style={{ paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {structured.potential_inconsistencies.map((item, idx) => (
                    <li key={idx} style={{ fontWeight: 600 }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Missing Information Callouts */}
          {structured?.missing_information && structured.missing_information.length > 0 && (
            <div className="alert-banner alert-warning">
              <AlertTriangle size={20} style={{ flexShrink: 0 }} />
              <div style={{ width: '100%' }}>
                <div style={{ fontWeight: 700, marginBottom: '0.4rem' }}>
                  Missing Critical Clinical Information
                </div>
                <ul style={{ paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {structured.missing_information.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Collapsible Structured Schema Sections */}
          <div className="accordion-group">
            {/* 1. Patient Demographics */}
            <div className="accordion-item">
              <button
                type="button"
                className={`accordion-header ${openSections.patient ? 'open' : ''}`}
                onClick={() => toggleSection('patient')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <User size={18} color="#60a5fa" />
                  <span>Patient Demographics</span>
                </div>
                {openSections.patient ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>
              {openSections.patient && (
                <div className="accordion-content">
                  <div className="vitals-grid">
                    <div className="vital-box">
                      <div className="vital-label">Patient Name</div>
                      <div className="vital-value">{structured?.patient_information?.name || 'Not Documented'}</div>
                    </div>
                    <div className="vital-box">
                      <div className="vital-label">Age</div>
                      <div className="vital-value">
                        {structured?.patient_information?.age !== null && structured?.patient_information?.age !== undefined
                          ? `${structured.patient_information.age} yrs`
                          : 'Unrecorded'}
                      </div>
                    </div>
                    <div className="vital-box">
                      <div className="vital-label">Gender / Sex</div>
                      <div className="vital-value">{structured?.patient_information?.gender || 'Unrecorded'}</div>
                    </div>
                    <div className="vital-box">
                      <div className="vital-label">MRN / ID</div>
                      <div className="vital-value">{structured?.patient_information?.mrn || 'N/A'}</div>
                    </div>
                    <div className="vital-box">
                      <div className="vital-label">Date of Birth</div>
                      <div className="vital-value">{structured?.patient_information?.dob || 'Unrecorded'}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* 2. Vital Signs */}
            <div className="accordion-item">
              <button
                type="button"
                className={`accordion-header ${openSections.vitals ? 'open' : ''}`}
                onClick={() => toggleSection('vitals')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <HeartPulse size={18} color="#f43f5e" />
                  <span>Physiological Vital Signs</span>
                </div>
                {openSections.vitals ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>
              {openSections.vitals && (
                <div className="accordion-content">
                  <div className="vitals-grid">
                    <div className="vital-box">
                      <div className="vital-label">Blood Pressure</div>
                      <div className="vital-value">{structured?.vitals?.blood_pressure || 'Unrecorded'}</div>
                    </div>
                    <div className="vital-box">
                      <div className="vital-label">Heart Rate</div>
                      <div className="vital-value">
                        {structured?.vitals?.heart_rate ? `${structured.vitals.heart_rate} bpm` : 'Unrecorded'}
                      </div>
                    </div>
                    <div className="vital-box">
                      <div className="vital-label">Respiratory Rate</div>
                      <div className="vital-value">
                        {structured?.vitals?.respiratory_rate ? `${structured.vitals.respiratory_rate} /min` : 'Unrecorded'}
                      </div>
                    </div>
                    <div className="vital-box">
                      <div className="vital-label">Temperature</div>
                      <div className="vital-value">{structured?.vitals?.temperature || 'Unrecorded'}</div>
                    </div>
                    <div className="vital-box">
                      <div className="vital-label">O2 Saturation</div>
                      <div className="vital-value">{structured?.vitals?.o2_saturation || 'Unrecorded'}</div>
                    </div>
                    <div className="vital-box">
                      <div className="vital-label">BMI</div>
                      <div className="vital-value">{structured?.vitals?.bmi || 'Unrecorded'}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* 3. Diagnoses & Symptoms */}
            <div className="accordion-item">
              <button
                type="button"
                className={`accordion-header ${openSections.diagnoses ? 'open' : ''}`}
                onClick={() => toggleSection('diagnoses')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <Activity size={18} color="#06b6d4" />
                  <span>Diagnoses & Symptoms</span>
                </div>
                {openSections.diagnoses ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>
              {openSections.diagnoses && (
                <div className="accordion-content">
                  <div style={{ marginBottom: '1.25rem' }}>
                    <div className="vital-label" style={{ marginBottom: '0.5rem' }}>
                      Clinical Diagnoses
                    </div>
                    {structured?.diagnoses && structured.diagnoses.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                        {structured.diagnoses.map((dx, i) => (
                          <span
                            key={i}
                            style={{
                              backgroundColor: 'rgba(6, 182, 212, 0.15)',
                              border: '1px solid rgba(6, 182, 212, 0.3)',
                              color: '#67e8f9',
                              padding: '0.35rem 0.75rem',
                              borderRadius: '6px',
                              fontWeight: 600,
                              fontSize: '0.9rem',
                            }}
                          >
                            {dx}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <div style={{ color: 'var(--text-muted)' }}>None recorded</div>
                    )}
                  </div>

                  <div>
                    <div className="vital-label" style={{ marginBottom: '0.5rem' }}>
                      Symptoms & Chief Complaints
                    </div>
                    {structured?.symptoms && structured.symptoms.length > 0 ? (
                      <ul style={{ paddingLeft: '1.25rem', color: 'var(--text-primary)' }}>
                        {structured.symptoms.map((sym, i) => (
                          <li key={i} style={{ marginBottom: '0.25rem' }}>
                            {sym}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div style={{ color: 'var(--text-muted)' }}>None recorded</div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* 4. Medications & Prescriptions */}
            <div className="accordion-item">
              <button
                type="button"
                className={`accordion-header ${openSections.medications ? 'open' : ''}`}
                onClick={() => toggleSection('medications')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <Pill size={18} color="#a855f7" />
                  <span>Medications & Prescriptions</span>
                </div>
                {openSections.medications ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>
              {openSections.medications && (
                <div className="accordion-content" style={{ padding: 0 }}>
                  {structured?.medications && structured.medications.length > 0 ? (
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Medication</th>
                          <th>Dosage</th>
                          <th>Frequency</th>
                          <th>Route</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {structured.medications.map((med, i) => (
                          <tr key={i}>
                            <td style={{ fontWeight: 600 }}>{med.name}</td>
                            <td>{med.dosage || <span style={{ color: 'var(--accent-amber)' }}>Missing</span>}</td>
                            <td>{med.frequency || 'N/A'}</td>
                            <td>{med.route || 'N/A'}</td>
                            <td>
                              <span className="type-badge">{med.status || 'Active'}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div style={{ padding: '1.25rem', color: 'var(--text-muted)' }}>
                      No active medications recorded.
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 5. Allergies */}
            <div className="accordion-item">
              <button
                type="button"
                className={`accordion-header ${openSections.allergies ? 'open' : ''}`}
                onClick={() => toggleSection('allergies')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <ShieldAlert size={18} color="#f59e0b" />
                  <span>Allergies & Adverse Reactions</span>
                </div>
                {openSections.allergies ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>
              {openSections.allergies && (
                <div className="accordion-content" style={{ padding: 0 }}>
                  {structured?.allergies && structured.allergies.length > 0 ? (
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Allergen / Substance</th>
                          <th>Reaction</th>
                          <th>Severity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {structured.allergies.map((allergy, i) => (
                          <tr key={i}>
                            <td style={{ fontWeight: 700, color: '#fca5a5' }}>{allergy.substance}</td>
                            <td>{allergy.reaction || 'Unspecified'}</td>
                            <td>
                              <span className="status-badge status-failed">{allergy.severity || 'Documented'}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div style={{ padding: '1.25rem', color: 'var(--text-muted)' }}>
                      NKDA (No Known Drug Allergies) or none documented.
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 6. Clinical Observations & Concerns */}
            <div className="accordion-item">
              <button
                type="button"
                className={`accordion-header ${openSections.observations ? 'open' : ''}`}
                onClick={() => toggleSection('observations')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <Microscope size={18} color="#10b981" />
                  <span>Clinical Observations & Objective Findings</span>
                </div>
                {openSections.observations ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>
              {openSections.observations && (
                <div className="accordion-content">
                  {structured?.clinical_observations && structured.clinical_observations.length > 0 ? (
                    <ul style={{ paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      {structured.clinical_observations.map((obs, i) => (
                        <li key={i}>{obs}</li>
                      ))}
                    </ul>
                  ) : (
                    <div style={{ color: 'var(--text-muted)' }}>No objective observations recorded.</div>
                  )}
                </div>
              )}
            </div>

            {/* 7. Raw Extracted Source Content */}
            <div className="accordion-item">
              <button
                type="button"
                className={`accordion-header ${openSections.rawText ? 'open' : ''}`}
                onClick={() => toggleSection('rawText')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <FileCode size={18} color="#94a3b8" />
                  <span>Extracted Source Text / Document Reference</span>
                </div>
                {openSections.rawText ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>
              {openSections.rawText && (
                <div className="accordion-content">
                  <div style={{ marginBottom: '0.75rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Raw Reference: {report.raw_input_ref}
                  </div>
                  <pre
                    style={{
                      background: 'var(--bg-primary)',
                      padding: '1rem',
                      borderRadius: '6px',
                      overflowX: 'auto',
                      fontSize: '0.85rem',
                      lineHeight: 1.5,
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {report.extracted_text || report.raw_input_ref}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
