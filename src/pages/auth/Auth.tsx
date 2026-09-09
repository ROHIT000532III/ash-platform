import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/useAuth";

export default function Auth() {
  const { session, login, register } = useAuth(); const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login"); const [username, setUsername] = useState(""); const [password, setPassword] = useState(""); const [loading, setLoading] = useState(false); const [error, setError] = useState("");
  if (session) return <Navigate to="/chat" replace />;
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(""); if (!username.trim() || !password) { setError("Enter your username and password."); return; } setLoading(true); try { if (mode === "login") await login(username.trim(), password); else await register(username.trim(), password); navigate("/chat", { replace: true }); } catch (reason) { setError(reason instanceof Error ? reason.message : "Authentication request failed."); } finally { setLoading(false); } };
  return <main className="auth-page"><form className="auth-form" onSubmit={submit}><p className="eyebrow">ASH AI ENTERPRISE</p><h1>{mode === "login" ? "Welcome back" : "Create account"}</h1><p className="subtitle">{mode === "login" ? "Sign in to your local workspace." : "Create your private local workspace."}</p>{error && <p className="chat-error">{error}</p>}<label>Username<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} disabled={loading} /></label><label>Password<input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(event) => setPassword(event.target.value)} disabled={loading} /></label><button className="primary-button" disabled={loading} type="submit">{loading ? "Please wait..." : mode === "login" ? "Login" : "Register"}</button><button className="auth-switch" type="button" disabled={loading} onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>{mode === "login" ? "Need an account? Register" : "Already have an account? Login"}</button></form></main>;
}
