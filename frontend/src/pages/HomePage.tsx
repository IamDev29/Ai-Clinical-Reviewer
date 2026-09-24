import React, { useEffect, useState } from 'react';
import { getHealthCheck, HealthCheckResponse } from '../api/health';
import { API_BASE_URL } from '../api/apiClient';
import {
  FileText,
  Activity,
  AlertCircle,
  RefreshCw,
  Search,
  ShieldCheck,
  Database,
} from 'lucide-react';

export const HomePage: React.FC = () => {
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const checkStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getHealthCheck();
      setHealth(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reach backend API');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  return (
    <div className="home-page">
      <section className="hero-section">
        <div className="hero-badge">
          <Activity size={14} /> Full-Stack Architecture Scaffolded
        </div>
        <h1 className="hero-title">AI Clinical Document Reviewer</h1>
        <p className="hero-subtitle">
          Intelligent automated review, criteria validation, and clinical trial matching platform.
        </p>
      </section>

      {/* Backend Health Check Card */}
      <section className="status-card">
        <div className="status-header">
          <div className="status-indicator">
            {loading ? (
              <>
                <span className="dot dot-yellow" />
                <span>Checking Backend Connection...</span>
              </>
            ) : error ? (
              <>
                <span className="dot dot-red" />
                <span style={{ color: 'var(--accent-rose)' }}>Backend Unreachable</span>
              </>
            ) : (
              <>
                <span className="dot dot-green" />
                <span style={{ color: 'var(--accent-emerald)' }}>Backend Online & Healthy</span>
              </>
            )}
          </div>
          <button className="btn-refresh" onClick={checkStatus} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>{loading ? 'Polling...' : 'Recheck API'}</span>
          </button>
        </div>

        <div className="status-details">
          <div className="detail-box">
            <div className="detail-label">Configured API Base URL</div>
            <div className="detail-value">{API_BASE_URL}</div>
          </div>
          <div className="detail-box">
            <div className="detail-label">Backend Service</div>
            <div className="detail-value">{health?.app || (error ? 'Unavailable' : 'Loading...')}</div>
          </div>
          <div className="detail-box">
            <div className="detail-label">Environment</div>
            <div className="detail-value">{health?.environment || (error ? 'N/A' : 'Loading...')}</div>
          </div>
          <div className="detail-box">
            <div className="detail-label">API Status</div>
            <div className="detail-value" style={{ color: health?.status === 'ok' ? 'var(--accent-emerald)' : 'inherit' }}>
              {health?.status ? health.status.toUpperCase() : error ? 'DISCONNECTED' : 'CHECKING'}
            </div>
          </div>
        </div>

        {error && (
          <div
            style={{
              marginTop: '1rem',
              padding: '0.75rem 1rem',
              backgroundColor: 'rgba(244, 63, 94, 0.1)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              borderRadius: '6px',
              color: '#fda4af',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
      </section>

      {/* Feature Modules Grid */}
      <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1.25rem', color: '#e2e8f0' }}>
        System Capabilities (Ready for Business Logic)
      </h2>

      <div className="cards-grid">
        <div className="card">
          <div className="card-icon">
            <FileText size={22} />
          </div>
          <h3 className="card-title">Document Ingestion</h3>
          <p className="card-text">
            Upload and extract structured clinical data from protocols, medical records, and PDFs.
          </p>
          <span className="card-badge">Module Scaffolded</span>
        </div>

        <div className="card">
          <div className="card-icon">
            <Search size={22} />
          </div>
          <h3 className="card-title">Clinical Criteria Matcher</h3>
          <p className="card-text">
            Evaluate patient inclusion/exclusion criteria against clinical study protocols using AI.
          </p>
          <span className="card-badge">Module Scaffolded</span>
        </div>

        <div className="card">
          <div className="card-icon">
            <ShieldCheck size={22} />
          </div>
          <h3 className="card-title">Compliance & Validation</h3>
          <p className="card-text">
            Audit trail logging and regulatory compliance checks for clinical document workflows.
          </p>
          <span className="card-badge">Module Scaffolded</span>
        </div>

        <div className="card">
          <div className="card-icon">
            <Database size={22} />
          </div>
          <h3 className="card-title">PostgreSQL Persistence</h3>
          <p className="card-text">
            Containerized relational storage for patient studies, review results, and audit trails.
          </p>
          <span className="card-badge">Docker Ready</span>
        </div>
      </div>
    </div>
  );
};
