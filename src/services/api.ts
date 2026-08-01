const API_URL = "http://127.0.0.1:8000";

export async function healthCheck() {
  const response = await fetch(`${API_URL}/health`);

  if (!response.ok) {
    throw new Error("Backend is offline");
  }

  return response.json();
}