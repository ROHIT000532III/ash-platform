import { createContext } from "react";
import type { AuthSession } from "../services/api";

export type AuthContextValue = {
  session: AuthSession | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
