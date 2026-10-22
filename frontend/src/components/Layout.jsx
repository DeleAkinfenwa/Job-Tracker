import { NavLink, Outlet } from "react-router-dom";

import { IS_STANDALONE_DEMO } from "../api/endpoints.js";
import logo from "../assets/logo.svg";
import { useAuth } from "../auth.jsx";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="app">
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

      {user.is_demo && (
        <div className="demo-banner">
          You're exploring the demo account. Feel free to add, edit or delete anything:{" "}
          {IS_STANDALONE_DEMO ? "it all resets when you reload the page." : "it all resets automatically."}
        </div>
      )}

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
