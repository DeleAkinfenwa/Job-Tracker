import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import ServerWakeNotice from "./components/ServerWakeNotice.jsx";
import ApplicationFormPage from "./pages/ApplicationFormPage.jsx";
import ApplicationsPage from "./pages/ApplicationsPage.jsx";
import CompaniesPage from "./pages/CompaniesPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";

// Only lets logged-in users through; everyone else is sent to the login page.
function RequireLogin({ children }) {
  const { user, status } = useAuth();
  if (status === "checking") return <p className="page-message">Loading…</p>;
  return user ? children : <Navigate to="/login" replace />;
}

// Keeps logged-in users away from the login and sign-up pages.
function GuestOnly({ children }) {
  const { user } = useAuth();
  return user ? <Navigate to="/" replace /> : children;
}

// The app's pages and which URL shows each one.
export default function App() {
  return (
    <>
      {/* Warns visitors while the free-tier server wakes up. */}
      <ServerWakeNotice />
      <Routes>
        <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
        <Route path="/register" element={<GuestOnly><RegisterPage /></GuestOnly>} />
        {/* Pages behind the login share the top bar layout. */}
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
        {/* Any unknown URL goes back to the applications list. */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
