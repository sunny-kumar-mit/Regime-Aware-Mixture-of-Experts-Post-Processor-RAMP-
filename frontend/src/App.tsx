import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Shell } from './components/layout/Shell';
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

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<Navigate to="/ramp" replace />} />
          <Route path="/ramp" element={<RAMPDashboardPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/data" element={<DataFeedsPage />} />
          <Route path="/regime" element={<WeatherRegimesPage />} />
          <Route path="/forecast" element={<RAMPDashboardPage />} />
          <Route path="/baseline" element={<BaselineBenchmarkingPage />} />
          <Route path="/extreme" element={<ExtremeRainfallPage />} />
          <Route path="/operational" element={<OperationalPage />} />
          <Route path="/spatial" element={<SpatialForecastPage />} />
          <Route path="/verification" element={<VerificationPage />} />
          <Route path="/explainability" element={<ExplainabilityPage />} />
          <Route path="/jury-demo" element={<JuryDemoPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  );
};

export default App;
