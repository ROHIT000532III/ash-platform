export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

const AUTH_SESSION_KEY = "ash-auth-session";
let unauthorizedHandler: (() => void) | null = null;

export type AuthUser = { id: string; username: string };
export type AuthSession = { access_token: string; token_type: "bearer"; user: AuthUser };
export function getAuthSession(): AuthSession | null {
  try { return JSON.parse(localStorage.getItem(AUTH_SESSION_KEY) ?? "null") as AuthSession | null; } catch { return null; }
}
export function saveAuthSession(session: AuthSession): void { localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session)); }
export function clearAuthSession(): void { localStorage.removeItem(AUTH_SESSION_KEY); }
export function setUnauthorizedHandler(handler: (() => void) | null): void { unauthorizedHandler = handler; }
async function authenticatedFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers); const token = getAuthSession()?.access_token;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(input, { ...init, headers });
  if (response.status === 401) { clearAuthSession(); unauthorizedHandler?.(); }
  return response;
}

export async function register(username: string, password: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) });
  if (!response.ok) throw await responseError(response); const session: AuthSession = await response.json(); saveAuthSession(session); return session;
}
export async function login(username: string, password: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) });
  if (!response.ok) throw await responseError(response); const session: AuthSession = await response.json(); saveAuthSession(session); return session;
}

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type SavedMessage = ChatMessage & {
  id: string;
  conversation_id: string;
  created_at: string;
};

export type ConversationDetail = Conversation & {
  messages: SavedMessage[];
};

export type ChatSettings = { temperature: number; maxTokens: number; contextMessageLimit: number; streaming: boolean };
const CHAT_SETTINGS_KEY = "ash-chat-settings";
export const defaultChatSettings: ChatSettings = { temperature: 0.7, maxTokens: 512, contextMessageLimit: 30, streaming: true };
export function getChatSettings(): ChatSettings {
  try { return { ...defaultChatSettings, ...JSON.parse(localStorage.getItem(CHAT_SETTINGS_KEY) ?? "{}") }; }
  catch { return defaultChatSettings; }
}
export function saveChatSettings(settings: ChatSettings): void {
  localStorage.setItem(CHAT_SETTINGS_KEY, JSON.stringify(settings));
}

export type HealthStatus = {
  status: string;
  backend: string;
  ai_engine: string;
  provider: string;
  model: string;
  provider_available?: boolean;
  model_available?: boolean;
  fallback_enabled?: boolean;
  detail?: string;
};

export type EngineStatus = {
  provider: string;
  model: string;
  available: boolean;
  provider_available?: boolean;
  model_available?: boolean;
  fallback_enabled?: boolean;
  detail?: string;
};

export type BackendSettings = {
  ai_provider: string;
  ollama_base_url: string;
  ollama_model: string;
  request_timeout_seconds: number;
  request_retries: number;
  fallback_provider: string | null;
  fallback_enabled: boolean;
  provider_available: boolean;
  model_available: boolean;
  available: boolean;
  detail: string;
};

export type InstalledModel = { name: string; size?: number; modified_at?: string; active: boolean };
export type ModelsResponse = { provider: string; models: InstalledModel[] };

export type ExplorerEntry = {
  name: string;
  path: string;
  is_directory: boolean;
  size: number | null;
  modified_at: string;
};

export type ExplorerDirectory = {
  path: string;
  parent_path: string | null;
  entries: ExplorerEntry[];
};

export async function getWorkspaceDirectory(path: string = ""): Promise<ExplorerDirectory> {
  const query = path ? `?path=${encodeURIComponent(path)}` : "";
  const response = await authenticatedFetch(`${API_BASE_URL}/api/explorer${query}`);
  if (!response.ok) throw await responseError(response);
  return await response.json();
}

export type StreamPayload = {
  delta?: string;
  done?: boolean;
  detail?: string;
};

export async function responseError(response: Response): Promise<Error> {
  try {
    const data: { detail?: string } = await response.json();
    if (data.detail) {
      return new Error(data.detail);
    }
  } catch {
    // The API can return an empty non-JSON error response.
  }
  return new Error(`ASH AI request failed (${response.status}).`);
}

export async function logout(): Promise<void> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/auth/logout`, { method: "POST" });
  if (!response.ok) throw await responseError(response);
}

export async function getHealth(): Promise<HealthStatus> {
  const response = await authenticatedFetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error("Backend is offline");
  }

  return await response.json();
}

export async function getEngineStatus(): Promise<EngineStatus> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/engine/status`);

  if (!response.ok) {
    throw new Error("Unable to load engine status.");
  }

  return await response.json();
}

export async function getBackendSettings(): Promise<BackendSettings> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/settings`);
  if (!response.ok) throw await responseError(response);
  return await response.json();
}

export async function getInstalledModels(): Promise<ModelsResponse> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/models`);
  if (!response.ok) throw await responseError(response);
  return await response.json();
}

export async function createConversation(): Promise<Conversation> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/conversations`, { method: "POST" });
  if (!response.ok) throw await responseError(response);
  return await response.json();
}

export async function getConversations(): Promise<Conversation[]> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/conversations`);
  if (!response.ok) throw await responseError(response);
  return await response.json();
}

export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/conversations/${conversationId}`);
  if (!response.ok) throw await responseError(response);
  return await response.json();
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/conversations/${conversationId}`, {
    method: "DELETE",
  });
  if (!response.ok) throw await responseError(response);
}

export async function renameConversation(conversationId: string, title: string): Promise<Conversation> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/conversations/${conversationId}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title }),
  });
  if (!response.ok) throw await responseError(response);
  return await response.json();
}

export async function sendChat(
  message: string,
  history: ChatMessage[],
  conversationId?: string,
  settings: ChatSettings = getChatSettings(),
  regenerate = false,
): Promise<string> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, conversation_id: conversationId, temperature: settings.temperature, max_tokens: settings.maxTokens, context_message_limit: settings.contextMessageLimit, regenerate }),
  });

  if (!response.ok) {
    throw await responseError(response);
  }

  const data: { response?: string } = await response.json();
  if (!data.response?.trim()) {
    throw new Error("ASH AI returned an empty response.");
  }
  return data.response;
}

export async function streamChat(
  message: string,
  history: ChatMessage[],
  onDelta: (delta: string) => void,
  conversationId?: string,
  settings: ChatSettings = getChatSettings(),
  regenerate = false,
  signal?: AbortSignal,
): Promise<string> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ message, history, conversation_id: conversationId, temperature: settings.temperature, max_tokens: settings.maxTokens, context_message_limit: settings.contextMessageLimit, regenerate }),
    signal,
  });

  if (!response.ok) {
    throw await responseError(response);
  }
  if (!response.body) {
    throw new Error("ASH AI did not return a response stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let responseText = "";

  const handleEvent = (eventText: string) => {
    const lines = eventText.split("\n");
    const eventType = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
    const dataLine = lines.find((line) => line.startsWith("data:"));
    if (!dataLine) {
      return;
    }

    const payload: StreamPayload = JSON.parse(dataLine.slice(5).trim());
    if (eventType === "error") {
      throw new Error(payload.detail ?? "ASH AI could not complete the request.");
    }
    if (payload.delta) {
      responseText += payload.delta;
      onDelta(payload.delta);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      handleEvent(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }

    if (done) {
      break;
    }
  }

  if (buffer.trim()) {
    handleEvent(buffer);
  }
  if (!responseText.trim()) {
    throw new Error("ASH AI returned an empty response.");
  }

  return responseText;
}
