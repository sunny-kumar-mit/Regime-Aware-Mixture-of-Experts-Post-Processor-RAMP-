import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Shell } from './components/layout/Shell';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/Dashboard';
import { DataFeedsPage } from './pages/DataFeeds';
import { WeatherRegimesPage } from './pages/WeatherRegimes';
import { BaselineBenchmarkingPage } from './pages/BaselineBenchmarking';
import { RAMPDashboardPage } from './pages/RAMPDashboard';
import { ExtremeRainfallPage } from './pages/ExtremeRainfall';
import { OperationalPage } from './pages/Operational';
import { SpatialForecastPage } from './pages/SpatialForecast';
import { VerificationPage } from './pages/Verification';
import { ExplainabilityPage } from './pages/Explainability';
import { JuryDemoPage } from './pages/JuryDemo';
import { AboutPage } from './pages/About';
import { ModelRegistryPage } from './pages/ModelRegistry';
import { ModelTrainingPage } from './pages/ModelTraining';
import { OperationalForecastPage } from './pages/OperationalForecast';
import { OperationsPage } from './pages/Operations';
import { ActivationPage } from './pages/Activation';
import { DataIngestionPage } from './pages/DataIngestion';
import { ForecastVerificationPage } from './pages/ForecastVerification';
import { OperationalCyclesPage } from './pages/OperationalCycles';
import { DataHealthPage } from './pages/DataHealth';
import { VerificationHistoryPage } from './pages/VerificationHistory';
import { ProductionStatusPage } from './pages/ProductionStatus';
import { AcceptancePage } from './pages/Acceptance';
import { RealDataCasesPage } from './pages/RealDataCases';
import { RealDataLabPage } from './pages/RealDataLab';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* ── Public landing page (no Shell / sidebar) ── */}
        <Route path="/" element={<LandingPage />} />

        {/* ── All dashboard routes wrapped in Shell ── */}
        <Route path="/*" element={
          <Shell>
            <Routes>
              <Route path="real-data" element={<RealDataLabPage />} />
              <Route path="real-data/history" element={<RealDataLabPage initialTab="lineage" />} />
              <Route path="real-data/lineage" element={<RealDataLabPage initialTab="lineage" />} />
              <Route path="forecast" element={<OperationalForecastPage />} />
              <Route path="forecast/cases" element={<RealDataCasesPage />} />
              <Route path="forecast/verification" element={<ForecastVerificationPage />} />
              <Route path="forecast/verification/history" element={<VerificationHistoryPage />} />
              <Route path="acceptance" element={<AcceptancePage />} />
              <Route path="activation" element={<ActivationPage />} />
              <Route path="data/ingestion" element={<DataIngestionPage />} />
              <Route path="operations" element={<OperationsPage />} />
              <Route path="operations/cycles" element={<OperationalCyclesPage />} />
              <Route path="operations/data-health" element={<DataHealthPage />} />
              <Route path="production" element={<ProductionStatusPage />} />
              <Route path="ramp" element={<RAMPDashboardPage />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="data" element={<DataFeedsPage />} />
              <Route path="models" element={<ModelRegistryPage />} />
              <Route path="training" element={<ModelTrainingPage />} />
              <Route path="regime" element={<WeatherRegimesPage />} />
              <Route path="baseline" element={<BaselineBenchmarkingPage />} />
              <Route path="extreme" element={<ExtremeRainfallPage />} />
              <Route path="operational" element={<OperationalPage />} />
              <Route path="spatial" element={<SpatialForecastPage />} />
              <Route path="verification" element={<VerificationPage />} />
              <Route path="explainability" element={<ExplainabilityPage />} />
              <Route path="jury-demo" element={<JuryDemoPage />} />
              <Route path="jury/phase18" element={<JuryDemoPage />} />
              <Route path="about" element={<AboutPage />} />
              <Route path="*" element={<Navigate to="/forecast" replace />} />
            </Routes>
          </Shell>
        } />
      </Routes>
    </BrowserRouter>
  );
};


export default App;

