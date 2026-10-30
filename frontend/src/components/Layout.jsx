import { NavLink, Outlet } from "react-router-dom";

import { IS_STANDALONE_DEMO } from "../api/endpoints.js";
import logo from "../assets/logo.svg";
import { useAuth } from "../auth.jsx";

// The shared page frame: top bar with navigation and account, then the current page.
export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="app">
      {/* Logo, main navigation and the logged-in account. */}
      <header className="topbar">
        <NavLink to="/" className="brand">
          <img src={logo} alt="" width="28" height="28" />
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

      {/* Reminder that changes in the demo account don't last. */}
      {user.is_demo && (
        <div className="demo-banner">
          You're exploring the demo account. Feel free to add, edit or delete anything:{" "}
          {IS_STANDALONE_DEMO ? "it all resets when you reload the page." : "it all resets automatically."}
        </div>
      )}

      {/* The current page renders here. */}
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
