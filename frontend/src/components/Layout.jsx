import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth.jsx";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="app">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <img src="/favicon.svg" alt="" width="28" height="28" />
          Job Tracker
        </NavLink>
        <nav className="nav">
          <NavLink to="/" end>
            Applications
          </NavLink>
          <NavLink to="/companies">Companies</NavLink>
        </nav>
        <div className="account">
          <span className="account-email">{user.email}</span>
          <button type="button" className="btn btn-ghost" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      {user.is_demo && (
        <div className="demo-banner">
          You're exploring the demo account. Feel free to add, edit or delete anything: it all resets automatically.
        </div>
      )}

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
