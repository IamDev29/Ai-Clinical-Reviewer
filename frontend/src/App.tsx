import React, { useEffect, useState } from 'react';
import { BrowserRouter, Link, useLocation } from 'react-router-dom';
import { Stethoscope, FileText, History, PlusCircle, ExternalLink, Cpu, Info } from 'lucide-react';
import { AppRoutes } from './routes';
import { getHealthCheck, HealthCheckResponse } from './api/health';

const NavigationBar: React.FC = () => {
  const location = useLocation();
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);

  useEffect(() => {
    getHealthCheck()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const hasApiKey = health?.has_api_key ?? false;

  return (
    <>
      <header className="navbar">
        <Link to="/" className="nav-brand">
          <div className="brand-icon">
            <Stethoscope size={20} />
          </div>
          <span>AI Clinical Reviewer</span>
        </Link>
        <nav className="nav-links">
          <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}>
            <PlusCircle size={15} /> Submit Document
          </Link>
          <Link
            to="/reports"
            className={`nav-link ${location.pathname.startsWith('/reports') ? 'active' : ''}`}
          >
            <History size={15} /> Reports History
          </Link>
          <a
            href="http://localhost:8000/api/v1/docs"
            target="_blank"
            rel="noreferrer"
            className="nav-link"
          >
            <FileText size={15} /> Swagger Docs <ExternalLink size={12} />
          </a>
          <div
            title={
              hasApiKey
                ? 'Gemini 2.5 Flash API Connected'
                : 'No GEMINI_API_KEY provided in .env. Running in Offline Rule-Based Extraction Mode.'
            }
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.3rem 0.65rem',
              borderRadius: '20px',
              fontSize: '0.78rem',
              fontWeight: 600,
              backgroundColor: hasApiKey ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
              border: hasApiKey ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(245, 158, 11, 0.3)',
              color: hasApiKey ? '#34d399' : '#fbbf24',
              marginLeft: '0.5rem',
            }}
          >
            <Cpu size={13} />
            <span>{hasApiKey ? 'Gemini 2.5 Flash' : 'Offline Rule Engine'}</span>
          </div>
        </nav>
      </header>

      {!hasApiKey && (
        <div
          style={{
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            borderBottom: '1px solid rgba(245, 158, 11, 0.25)',
            color: '#fbbf24',
            padding: '0.5rem 1.5rem',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            justifyContent: 'center',
          }}
        >
          <Info size={15} style={{ flexShrink: 0 }} />
          <span>
            <strong>Demo / Offline Rule-Based Mode Active:</strong> No <code>GEMINI_API_KEY</code> detected in <code>.env</code>. Processing clinical notes & sample reports using built-in deterministic clinical extraction rules. Add your API key to <code>.env</code> to activate live Gemini AI.
          </span>
        </div>
      )}
    </>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="app-container">
        <NavigationBar />

        <main className="main-content">
          <AppRoutes />
        </main>

        <footer className="footer">
          <p>
            AI Clinical Document Reviewer &bull; Intelligent Document Review, Entity Extraction & Safety Verification
          </p>
        </footer>
      </div>
    </BrowserRouter>
  );
};

export default App;
