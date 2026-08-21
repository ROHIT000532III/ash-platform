import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { clearAuthSession, getAuthSession, login as loginRequest, logout as logoutRequest, register as registerRequest, setUnauthorizedHandler } from "../services/api";
import type { AuthSession } from "../services/api";

type AuthContextValue = {
  session: AuthSession | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
};
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate(); const [session, setSession] = useState<AuthSession | null>(getAuthSession);
  const logout = () => {
    void logoutRequest().catch(() => {});
    clearAuthSession();
    setSession(null);
    navigate("/login", { replace: true });
  };
  useEffect(() => { setUnauthorizedHandler(logout); return () => setUnauthorizedHandler(null); }, []);
  const value = useMemo(() => ({ session, logout, login: async (username: string, password: string) => setSession(await loginRequest(username, password)), register: async (username: string, password: string) => setSession(await registerRequest(username, password)) }), [session]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth(): AuthContextValue { const value = useContext(AuthContext); if (!value) throw new Error("useAuth must be used inside AuthProvider."); return value; }
