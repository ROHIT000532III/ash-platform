import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { clearAuthSession, getAuthSession, login as loginRequest, logout as logoutRequest, register as registerRequest, setUnauthorizedHandler } from "../services/api";
import type { AuthSession } from "../services/api";
import { AuthContext } from "./context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate(); const [session, setSession] = useState<AuthSession | null>(getAuthSession);
  const logout = useCallback(() => {
    void logoutRequest().catch(() => {});
    clearAuthSession();
    setSession(null);
    navigate("/chat", { replace: true });
  }, [navigate]);
  useEffect(() => { setUnauthorizedHandler(logout); return () => setUnauthorizedHandler(null); }, [logout]);
  const value = useMemo(() => ({ session, logout, login: async (username: string, password: string) => setSession(await loginRequest(username, password)), register: async (username: string, password: string) => setSession(await registerRequest(username, password)) }), [logout, session]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
