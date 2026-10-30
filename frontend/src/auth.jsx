import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { setSessionExpiredHandler, tokens } from "./api/client.js";
import { api, DEMO_CREDENTIALS } from "./api/endpoints.js";

// Shares the logged-in user and login actions with every component.
const AuthContext = createContext(null);

// Holds who is logged in and provides login, logout and sign-up actions.
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // "checking" while we find out whether a saved login is still valid.
  const [status, setStatus] = useState(tokens.access ? "checking" : "ready");

  // Forget the saved tokens and the current user.
  const logout = useCallback(() => {
    tokens.clear();
    setUser(null);
  }, []);

  // On start-up, check whether a saved login is still valid.
  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null));
    if (!tokens.access) return;
    api
      .me()
      .then(setUser)
      .catch(logout)
      .finally(() => setStatus("ready"));
  }, [logout]);

  // Swap an email and password for tokens, then load the user's profile.
  const login = useCallback(async (email, password) => {
    tokens.save(await api.login(email.trim().toLowerCase(), password));
    setUser(await api.me());
  }, []);

  // Everything the rest of the app can read from useAuth().
  const value = useMemo(
    () => ({
      user,
      status,
      login,
      logout,
      loginAsDemo: () => login(DEMO_CREDENTIALS.email, DEMO_CREDENTIALS.password),
      register: async (data) => {
        await api.register(data);
        await login(data.email, data.password);
      },
    }),
    [user, status, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Lets any component read the login state.
export function useAuth() {
  return useContext(AuthContext);
}
