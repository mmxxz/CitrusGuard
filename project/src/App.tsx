import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import AuthWrapper from './components/AuthWrapper';
import Dashboard from './pages/Dashboard';
import Alerts from './pages/Alerts';
import Diagnosis from './pages/Diagnosis';
import Cases from './pages/Cases';
import Login from './pages/Login';
import Register from './pages/Register';
import OrchardSetup from './pages/OrchardSetup';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/orchard-setup" element={<OrchardSetup />} />
        <Route path="/edit-orchard" element={<OrchardSetup />} />
        <Route path="/diagnosis" element={<Diagnosis />} />
        
        <Route 
          path="/" 
          element={
            <AuthWrapper>
              <Layout />
            </AuthWrapper>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="cases" element={<Cases />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
