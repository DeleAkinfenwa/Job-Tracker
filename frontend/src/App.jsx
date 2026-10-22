import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import ServerWakeNotice from "./components/ServerWakeNotice.jsx";
import ApplicationFormPage from "./pages/ApplicationFormPage.jsx";
import ApplicationsPage from "./pages/ApplicationsPage.jsx";
import CompaniesPage from "./pages/CompaniesPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";

function RequireLogin({ children }) {
  const { user, status } = useAuth();
  if (status === "checking") return <p className="page-message">Loading…</p>;
  return user ? children : <Navigate to="/login" replace />;
}

function GuestOnly({ children }) {
  const { user } = useAuth();
  return user ? <Navigate to="/" replace /> : children;
}

export default function App() {
  return (
    <>
      <ServerWakeNotice />
      <Routes>
        <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
        <Route path="/register" element={<GuestOnly><RegisterPage /></GuestOnly>} />
        <Route
          element={
            <RequireLogin>
              <Layout />
            </RequireLogin>
          }
        >
          <Route index element={<ApplicationsPage />} />
          <Route path="applications/new" element={<ApplicationFormPage />} />
          <Route path="applications/:id" element={<ApplicationFormPage />} />
          <Route path="companies" element={<CompaniesPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
