import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCw,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  PlusCircle,
  Eye,
} from 'lucide-react';
import { listReports, seedReports, Report } from '../api/reports';
import { ApiError } from '../api/apiClient';
import { Sparkles } from 'lucide-react';

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [reports, setReports] = useState<Report[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(0);
  const [limit] = useState<number>(10);
  const [loading, setLoading] = useState<boolean>(true);
  const [isSeeding, setIsSeeding] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listReports(page * limit, limit);
      setReports(response.items);
      setTotal(response.total);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch clinical reports list.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSeedReports = async () => {
    setIsSeeding(true);
    setError(null);
    try {
      const response = await seedReports();
      setReports(response.items);
      setTotal(response.total);
      setPage(0);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to seed demo reports.');
      }
    } finally {
      setIsSeeding(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [page]);

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="history-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '0.25rem' }}>
            Clinical Reports History
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            Review past extractions, safety flags, and processing statuses.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={handleSeedReports}
            disabled={isSeeding || loading}
            title="Populate synthetic clinical demo sample reports"
          >
            <Sparkles size={14} color="#60a5fa" className={isSeeding ? 'animate-spin' : ''} />
            <span>{isSeeding ? 'Seeding...' : 'Load Demo Reports'}</span>
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={fetchReports}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          <Link to="/" className="btn-primary">
            <PlusCircle size={16} />
            <span>New Submission</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="alert-banner alert-danger">
          <XCircle size={20} style={{ flexShrink: 0 }} />
          <div>{error}</div>
        </div>
      )}

      {loading && reports.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '4rem 1rem' }}>
          <RefreshCw size={32} className="animate-spin" style={{ color: '#60a5fa', margin: '0 auto 1rem auto' }} />
          <p style={{ color: 'var(--text-secondary)' }}>Loading reports history...</p>
        </div>
      ) : reports.length === 0 ? (
        <div className="form-card" style={{ textAlign: 'center', padding: '4rem 1rem' }}>
          <FileText size={48} color="#60a5fa" style={{ margin: '0 auto 1rem auto', opacity: 0.8 }} />
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            No Reports Submitted Yet
          </h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', maxWidth: '450px', margin: '0 auto 1.5rem auto' }}>
            Submit a clinical note, protocol PDF, or medical image. Or load synthetic demo reports to explore safety flags and extraction capabilities.
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleSeedReports}
              disabled={isSeeding}
            >
              <Sparkles size={16} color="#60a5fa" />
              <span>Load Demo Reports</span>
            </button>
            <Link to="/" className="btn-primary">
              <PlusCircle size={16} /> Submit First Document
            </Link>
          </div>
        </div>
      ) : (
        <div className="form-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Status</th>
                <th>Submission Date</th>
                <th>Clinical Summary / Source Excerpt</th>
                <th>Safety Flags</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => {
                const requiresReview = report.structured_report?.requires_review;
                const hasInconsistencies =
                  report.structured_report?.potential_inconsistencies &&
                  report.structured_report.potential_inconsistencies.length > 0;

                return (
                  <tr
                    key={report.id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/reports/${report.id}`)}
                  >
                    <td style={{ fontWeight: 700, color: '#60a5fa' }}>#{report.id}</td>
                    <td>
                      <span className="type-badge">{report.input_type}</span>
                    </td>
                    <td>
                      <span className={`status-badge status-${report.status}`}>
                        {report.status === 'completed' && <CheckCircle2 size={12} />}
                        {report.status === 'processing' && <RefreshCw size={12} className="animate-spin" />}
                        {report.status === 'pending' && <Clock size={12} />}
                        {report.status === 'failed' && <XCircle size={12} />}
                        {report.status}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
                      {new Date(report.created_at).toLocaleString()}
                    </td>
                    <td style={{ maxWidth: '380px' }}>
                      <div
                        style={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          color: report.status === 'failed' ? '#fb7185' : 'var(--text-primary)',
                        }}
                      >
                        {report.status === 'failed'
                          ? `Failed: ${report.error_message || 'Processing error'}`
                          : report.report_summary || report.extracted_text || report.raw_input_ref}
                      </div>
                    </td>
                    <td>
                      {hasInconsistencies ? (
                        <span
                          className="status-badge status-failed"
                          style={{ fontSize: '0.72rem' }}
                          title="Contraindications detected"
                        >
                          <AlertTriangle size={11} /> Contraindication
                        </span>
                      ) : requiresReview ? (
                        <span
                          className="status-badge status-processing"
                          style={{ fontSize: '0.72rem' }}
                          title="Review required"
                        >
                          <AlertTriangle size={11} /> Needs Review
                        </span>
                      ) : report.status === 'completed' ? (
                        <span className="status-badge status-completed" style={{ fontSize: '0.72rem' }}>
                          <CheckCircle2 size={11} /> Verified
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>—</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <Link
                        to={`/reports/${report.id}`}
                        className="btn-secondary"
                        style={{ padding: '0.35rem 0.65rem', fontSize: '0.8rem' }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Eye size={13} /> View
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '1rem 1.5rem',
                borderTop: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-card)',
              }}
            >
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                Showing {page * limit + 1} - {Math.min((page + 1) * limit, total)} of {total} reports
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  style={{ padding: '0.35rem 0.65rem' }}
                >
                  <ChevronLeft size={16} /> Previous
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  style={{ padding: '0.35rem 0.65rem' }}
                >
                  Next <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
