import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { setSessionExpiredHandler, tokens } from "./api/client.js";
import { api, DEMO_CREDENTIALS } from "./api/endpoints.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // "checking" while we find out whether a saved login is still valid.
  const [status, setStatus] = useState(tokens.access ? "checking" : "ready");

  const logout = useCallback(() => {
    tokens.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null));
    if (!tokens.access) return;
    api
      .me()
      .then(setUser)
      .catch(logout)
      .finally(() => setStatus("ready"));
  }, [logout]);

  const login = useCallback(async (email, password) => {
    tokens.save(await api.login(email, password));
    setUser(await api.me());
  }, []);

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

export function useAuth() {
  return useContext(AuthContext);
}
