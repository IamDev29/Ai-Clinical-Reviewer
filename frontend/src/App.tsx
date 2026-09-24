import React from 'react';
import { BrowserRouter, Link, useLocation } from 'react-router-dom';
import { Stethoscope, FileText, History, PlusCircle, ExternalLink } from 'lucide-react';
import { AppRoutes } from './routes';

const NavigationBar: React.FC = () => {
  const location = useLocation();

  return (
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
      </nav>
    </header>
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
