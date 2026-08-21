import { useEffect, useState } from "react";
import { getBackendSettings } from "../../services/api";
import type { BackendSettings } from "../../services/api";

export default function Settings() {
  const [settings, setSettings] = useState<BackendSettings | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { void getBackendSettings().then(setSettings).catch((e: unknown) => setError(e instanceof Error ? e.message : "Backend settings are unavailable.")); }, []);
  return <div className="page"><h1>Application Settings</h1>{error && <p>{error}</p>}{!settings && !error && <p>Loading backend configuration...</p>}{settings && <section className="settings-grid"><p><strong>AI provider:</strong> {settings.ai_provider}</p><p><strong>Ollama URL:</strong> {settings.ollama_base_url}</p><p><strong>Model:</strong> {settings.ollama_model}</p><p><strong>Request timeout:</strong> {settings.request_timeout_seconds}s</p><p><strong>Retries:</strong> {settings.request_retries}</p><p><strong>Fallback:</strong> {settings.fallback_enabled ? settings.fallback_provider : "Disabled"}</p><p><strong>Provider:</strong> {settings.provider_available ? "Available" : "Unavailable"}</p><p><strong>Configured model:</strong> {settings.model_available ? "Available" : "Unavailable"}</p><p>{settings.detail}</p><small>Configuration is read from backend environment settings. Restart the backend after changing environment values.</small></section>}</div>;
}
