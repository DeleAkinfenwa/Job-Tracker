import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, MemoryRouter } from "react-router-dom";

import { IS_STANDALONE_DEMO } from "./api/endpoints.js";
import App from "./App.jsx";
import { AuthProvider } from "./auth.jsx";
import "./styles.css";

// The standalone demo runs inside an embedded page, where the address bar can't change, so it keeps pages in memory.
const Router = IS_STANDALONE_DEMO ? MemoryRouter : BrowserRouter;

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Router>
      <AuthProvider>
        <App />
      </AuthProvider>
    </Router>
  </StrictMode>,
);
