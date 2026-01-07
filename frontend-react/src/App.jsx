import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { store } from './store/store';
// v4.4 - Case Context
import { CaseContextProvider } from './context/CaseContext';
// v4.5 - Auth Context
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import LoginPage from './pages/Auth/LoginPage';
import ProfilePage from './pages/Auth/ProfilePage';
// v4.6 - Registration & Pricing
import RegisterPage from './pages/Register/RegisterPage';
import PricingPage from './pages/Pricing/PricingPage';
// v4.6 - Landing Page
import LandingPage from './pages/Landing/LandingPage';
import { Layout } from './components/Layout';
import { Dashboard } from './components/Dashboard';
import { Investigations } from './components/Investigations';
import { MobileAgents } from './components/MobileAgents';
import { ActiveInvestigation } from './components/ActiveInvestigation';
import { AttackGraph } from './components/Graph';
import { IOCStore } from './components/IOCStore';
import KaliTools from './components/KaliTools';
// v4.1 - New components
import { PlaybookRunner } from './components/SOAR';
import { CorrelationDashboard } from './components/Correlation';
import { AgentsDashboard } from './components/Agents';
import ThreatIntel from './components/ThreatIntel/ThreatIntel';
import { M365 } from './components/M365';
import TenantsPage from './components/Tenants/TenantsPage';
// v4.3 - LLM Studio
import LLMSettings from './components/Settings/LLMSettings';
import MaintenancePanel from './components/Settings/MaintenancePanel';
// v4.5 - M365 Cloud Security (Monkey365)
import M365CloudPage from './pages/M365Cloud/M365CloudPage';
// v4.6 - Global Admin Pages
import {
  GlobalAdminDashboard,
  GlobalUsersPage,
  GlobalTenantsPage,
  GlobalBillingPage,
  GlobalSettingsPage,
  LandingContentPage
} from './pages/GlobalAdmin';
// v4.3 - New modules
import ThreatHuntingPage from './components/ThreatHunting/ThreatHuntingPage';
import TimelinePage from './components/Timeline/TimelinePage';
import ReportsPage from './components/Reports/ReportsPage';
import './styles/globals.css';

import CredentialsPage from './components/Credentials/CredentialsPage';

const GraphPage = () => {
  const params = new URLSearchParams(window.location.search);
  const caseId = params.get('case') || 'IR-2025-001';
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Grafo de Ataque</h1>
      <p className="text-gray-400 mb-4">
        Caso: <span className="text-blue-400 font-mono">{caseId}</span>
        {' • '}
        <a href="/graph?case=IR-2024-001" className="text-blue-400 hover:underline">IR-2024-001</a>
        {' • '}
        <a href="/graph?case=IR-2025-001" className="text-blue-400 hover:underline">IR-2025-001</a>
      </p>
      <AttackGraph caseId={caseId} />
    </div>
  );
};

const IOCs = () => (
  <IOCStore />
);

function App() {
  return (
    <Provider store={store}>
      <AuthProvider>
        <CaseContextProvider>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/pricing" element={<PricingPage />} />
              
              {/* Protected routes */}
              <Route path="/dashboard" element={
                <ProtectedRoute>
                  <Layout><Dashboard /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/profile" element={
                <ProtectedRoute>
                  <Layout><ProfilePage /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/investigations" element={
                <ProtectedRoute>
                  <Layout><Investigations /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/active-investigation" element={
                <ProtectedRoute>
                  <Layout><ActiveInvestigation /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/m365" element={
                <ProtectedRoute>
                  <Layout><M365 /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/m365-cloud" element={
                <ProtectedRoute>
                  <Layout><M365CloudPage /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/agents" element={
                <ProtectedRoute>
                  <Layout><MobileAgents /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/graph" element={
                <ProtectedRoute>
                  <Layout><GraphPage /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/credentials" element={
                <ProtectedRoute>
                  <Layout><CredentialsPage /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/threat-hunting" element={
                <ProtectedRoute>
                  <Layout><ThreatHuntingPage /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/iocs" element={
                <ProtectedRoute>
                  <Layout><IOCs /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/timeline" element={
                <ProtectedRoute>
                  <Layout><TimelinePage /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/reports" element={
                <ProtectedRoute>
                  <Layout><ReportsPage /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/tenants" element={
                <ProtectedRoute>
                  <Layout><TenantsPage /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/kali-tools" element={
                <ProtectedRoute>
                  <Layout><KaliTools /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/threat-intel" element={
                <ProtectedRoute>
                  <Layout><ThreatIntel /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/playbooks" element={
                <ProtectedRoute>
                  <Layout><PlaybookRunner /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/correlation" element={
                <ProtectedRoute>
                  <Layout><CorrelationDashboard /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/agents-v41" element={
                <ProtectedRoute>
                  <Layout><AgentsDashboard /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/settings/llm" element={
                <ProtectedRoute>
                  <Layout><LLMSettings /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/maintenance" element={
                <ProtectedRoute requiredRole="admin">
                  <Layout><MaintenancePanel /></Layout>
                </ProtectedRoute>
              } />

              {/* Global Admin Routes - Only accessible by is_global_admin=true */}
              <Route path="/admin" element={
                <ProtectedRoute requiredGlobalAdmin>
                  <Layout><GlobalAdminDashboard /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/admin/users" element={
                <ProtectedRoute requiredGlobalAdmin>
                  <Layout><GlobalUsersPage /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/admin/tenants" element={
                <ProtectedRoute requiredGlobalAdmin>
                  <Layout><GlobalTenantsPage /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/admin/billing" element={
                <ProtectedRoute requiredGlobalAdmin>
                  <Layout><GlobalBillingPage /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/admin/settings" element={
                <ProtectedRoute requiredGlobalAdmin>
                  <Layout><GlobalSettingsPage /></Layout>
                </ProtectedRoute>
              } />

              <Route path="/admin/landing" element={
                <ProtectedRoute requiredGlobalAdmin>
                  <Layout><LandingContentPage /></Layout>
                </ProtectedRoute>
              } />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/dashboard" />} />
            </Routes>

            {/* Toast notifications */}
            <ToastContainer
              position="bottom-right"
              autoClose={5000}
              hideProgressBar={false}
              newestOnTop={false}
              closeOnClick
              rtl={false}
              pauseOnFocusLoss
              draggable
              pauseOnHover
            />
          </BrowserRouter>
        </CaseContextProvider>
      </AuthProvider>
    </Provider>
  );
}

export default App;
