import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Upload,
  Image as ImageIcon,
  Send,
  AlertCircle,
  Sparkles,
  Loader2,
} from 'lucide-react';
import { submitClinicalReport } from '../api/reports';
import { ApiError } from '../api/apiClient';

const SAMPLE_NOTES = {
  clean: `PATIENT PROGRESS NOTE
Patient: John Doe, 58yo Male. MRN: 109283. DOB: 1968-04-12.
Chief Complaint: Routine follow-up for well-managed essential hypertension.
Vitals: BP 122/78 mmHg, HR 72 bpm, Temp 98.6 F, O2 Sat 99% on RA, BMI 24.5.
Diagnoses: Essential Hypertension (stable).
Medications: Lisinopril 10mg oral once daily (active).
Allergies: NKDA (No Known Drug Allergies).
Observations: S1/S2 regular, no murmurs, lungs clear to auscultation bilaterally.
Plan: Continue current regimen. Return in 6 months.`,

  incomplete: `PATIENT VISIT NOTE
Patient came in complaining of severe chest tightness and shortness of breath.
Diagnosed with acute bronchitis.
Started on Azithromycin.`,

  contradictory: `EMERGENCY ENCOUNTER NOTE
Patient: Jane Smith, 42yo Female.
Allergies: Penicillin (Severe Anaphylaxis).
Chief Complaint: Severe dental abscess with facial swelling.
Diagnoses: Periapical abscess.
Prescription: Amoxicillin 500mg PO TID x 7 days.
Vitals: BP 130/85, HR 88 bpm.`,
};

export const SubmitPage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'text' | 'pdf' | 'image'>('text');
  const [textContent, setTextContent] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setErrorMessage(null);
    }
  };

  const loadSample = (type: 'clean' | 'incomplete' | 'contradictory') => {
    setTextContent(SAMPLE_NOTES[type]);
    setActiveTab('text');
    setErrorMessage(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);
    setErrorCode(null);

    try {
      let result;
      if (activeTab === 'text') {
        if (!textContent.trim()) {
          setErrorMessage('Please enter clinical text or choose a sample template.');
          setIsSubmitting(false);
          return;
        }
        result = await submitClinicalReport({ text: textContent });
      } else {
        if (!selectedFile) {
          setErrorMessage(`Please select a ${activeTab === 'pdf' ? 'PDF' : 'image'} file to upload.`);
          setIsSubmitting(false);
          return;
        }
        result = await submitClinicalReport({ file: selectedFile });
      }

      // Navigate to detail report view where live polling will track review status
      navigate(`/reports/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
        setErrorCode(err.code);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to submit clinical document for processing.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="submit-page">
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2.25rem', fontWeight: 800, marginBottom: '0.5rem' }}>
          Clinical Document Review
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', maxWidth: '650px', margin: '0 auto' }}>
          Upload patient progress notes, digital or scanned protocols (PDF), or medical imagery for automated AI extraction and safety validation.
        </p>
      </div>

      {/* Input Mode Selector Tabs */}
      <div className="tabs-header">
        <button
          type="button"
          className={`tab-btn ${activeTab === 'text' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('text');
            setErrorMessage(null);
          }}
        >
          <FileText size={18} /> Plain Text Note
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'pdf' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('pdf');
            setSelectedFile(null);
            setErrorMessage(null);
          }}
        >
          <Upload size={18} /> PDF Protocol / Record
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'image' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('image');
            setSelectedFile(null);
            setErrorMessage(null);
          }}
        >
          <ImageIcon size={18} /> Medical Scan / Image
        </button>
      </div>

      {/* Error Alert Banner */}
      {errorMessage && (
        <div className="alert-banner alert-danger">
          <AlertCircle size={20} style={{ flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 700, marginBottom: '0.2rem' }}>
              Submission Error {errorCode ? `(${errorCode})` : ''}
            </div>
            <div>{errorMessage}</div>
          </div>
        </div>
      )}

      {/* Form Card */}
      <div className="form-card">
        <form onSubmit={handleSubmit}>
          {activeTab === 'text' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <label className="form-label" style={{ margin: 0 }}>
                  Clinical Note Content
                </label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Sparkles size={14} color="#60a5fa" />
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Quick Samples:</span>
                  <div className="template-pills" style={{ margin: 0 }}>
                    <button type="button" className="pill-btn" onClick={() => loadSample('clean')}>
                      Clean Note
                    </button>
                    <button type="button" className="pill-btn" onClick={() => loadSample('incomplete')}>
                      Incomplete
                    </button>
                    <button type="button" className="pill-btn" onClick={() => loadSample('contradictory')}>
                      Contradiction
                    </button>
                  </div>
                </div>
              </div>

              <textarea
                className="textarea-input"
                placeholder="Paste or type clinical note, patient encounter transcript, or discharge summary here..."
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                disabled={isSubmitting}
              />
            </div>
          )}

          {activeTab === 'pdf' && (
            <div>
              <label className="form-label">Select Clinical Document (PDF)</label>
              <div className="file-dropzone">
                <input
                  type="file"
                  accept=".pdf,application/pdf"
                  className="file-input-hidden"
                  onChange={handleFileChange}
                  disabled={isSubmitting}
                />
                <Upload size={40} color="#60a5fa" style={{ marginBottom: '0.75rem' }} />
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  {selectedFile ? selectedFile.name : 'Click to select or drop a PDF file here'}
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  {selectedFile
                    ? `Size: ${(selectedFile.size / 1024).toFixed(1)} KB`
                    : 'Supports digital PDFs and scanned image documents (up to 25 MB)'}
                </p>
              </div>
            </div>
          )}

          {activeTab === 'image' && (
            <div>
              <label className="form-label">Select Medical Scan or Photo (JPG / PNG)</label>
              <div className="file-dropzone">
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                  className="file-input-hidden"
                  onChange={handleFileChange}
                  disabled={isSubmitting}
                />
                <ImageIcon size={40} color="#06b6d4" style={{ marginBottom: '0.75rem' }} />
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  {selectedFile ? selectedFile.name : 'Click to select or drop an image file here'}
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  {selectedFile
                    ? `Size: ${(selectedFile.size / 1024).toFixed(1)} KB`
                    : 'Supports JPG and PNG formats (up to 25 MB)'}
                </p>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem', gap: '1rem' }}>
            <button
              type="submit"
              className="btn-primary"
              disabled={isSubmitting}
              style={{ minWidth: '180px' }}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>Submitting...</span>
                </>
              ) : (
                <>
                  <Send size={18} />
                  <span>Submit for Review</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
