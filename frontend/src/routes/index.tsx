import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { SubmitPage } from '../pages/SubmitPage';
import { HistoryPage } from '../pages/HistoryPage';
import { ReportDetailPage } from '../pages/ReportDetailPage';
import { NotFoundPage } from '../pages/NotFoundPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<SubmitPage />} />
      <Route path="/reports" element={<HistoryPage />} />
      <Route path="/reports/:id" element={<ReportDetailPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};
