/**
 * App Component
 *
 * Main application with routing and layout.
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardLayout from './components/Layout/DashboardLayout';
import Dashboard from './pages/Dashboard';
import Workflows from './pages/Workflows';
import Bots from './pages/Bots';
import Metrics from './pages/Metrics';
import Emergency from './pages/Emergency';
import History from './pages/History';
import Events from './pages/Events';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="workflows" element={<Workflows />} />
          <Route path="bots" element={<Bots />} />
          <Route path="metrics" element={<Metrics />} />
          <Route path="emergency" element={<Emergency />} />
          <Route path="history" element={<History />} />
          <Route path="events" element={<Events />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
