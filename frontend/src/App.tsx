import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppShell from './components/AppShell';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import Integrations from './pages/Integrations';
import AdminPanel from './pages/AdminPanel';
import Settings from './pages/Settings';
import Docs from './pages/Docs';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />
          <Route path="integrations" element={<Integrations />} />
          <Route path="admin" element={<AdminPanel />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        {/* Docs routes - separate from AppShell for custom layout */}
        <Route path="docs/*" element={<Docs />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
