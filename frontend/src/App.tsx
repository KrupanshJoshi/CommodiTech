import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { LanguageProvider } from './i18n';
import { ThemeProvider } from './context/ThemeContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppLayout } from './components/AppLayout';

// Pages
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { NewScan } from './pages/NewScan';
import { DataReview } from './pages/DataReview';
import { ComplianceResult } from './pages/ComplianceResult';
import { ReportView } from './pages/ReportView';
import { ScanHistory } from './pages/ScanHistory';
import { RulesRegistry } from './pages/RulesRegistry';
import { Settings } from './pages/Settings';

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Authentication Route */}
            <Route path="/login" element={<Login />} />

            {/* Protected Statutory Inspection Routes with v0 AppLayout */}
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<Dashboard />} />
              <Route path="/scan/new" element={<NewScan />} />
              <Route path="/scan/review/:id" element={<DataReview />} />
              <Route path="/compliance/:id" element={<ComplianceResult />} />
              <Route path="/reports/view/:id" element={<ReportView />} />
              <Route path="/history" element={<ScanHistory />} />
              <Route path="/rules" element={<RulesRegistry />} />
              <Route path="/settings" element={<Settings />} />
            </Route>

            {/* Fallback Catch-All */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </LanguageProvider>
    </ThemeProvider>
  );
};

export default App;
