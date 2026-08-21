"""Integration tests for the active ASH FastAPI backend.

These tests intentionally use only the standard library.  The ASGI harness keeps
the suite independent of Ollama, httpx, and the production SQLite database.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from collections.abc import AsyncIterator, Sequence
from typing import Any

# Ensure the backend app package is importable when tests run from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.security import new_session_token, session_token_hash

from app.api import chat as chat_api
from app.api import conversations as conversations_api
from app.api import explorer as explorer_api
from app.core import dependencies
from app.core.database import ConversationRepository
from app.core.workspace import WorkspaceService
from app.engine.base import (
    ConversationMessage,
    GenerationOptions,
    ProviderResponseError,
    ProviderUnavailableError,
)
from app.main import app


class FakeEngine:
    """A deterministic engine which records the API inputs it receives."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[ConversationMessage], GenerationOptions]] = []
        self.response = "Fake response"
        self.chunks = ["Fake ", "response"]
        self.generate_error: Exception | None = None
        self.stream_error: Exception | None = None

    async def generate(
        self,
        message: str,
        history: Sequence[ConversationMessage] = (),
        options: GenerationOptions = GenerationOptions(),
    ) -> str:
        self.calls.append((message, list(history), options))
        if self.generate_error is not None:
            raise self.generate_error
        return self.response

    async def generate_stream(
        self,
        message: str,
        history: Sequence[ConversationMessage] = (),
        options: GenerationOptions = GenerationOptions(),
    ) -> AsyncIterator[str]:
        self.calls.append((message, list(history), options))
        for chunk in self.chunks:
            yield chunk
        if self.stream_error is not None:
            raise self.stream_error


async def asgi_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    query: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    """Submit one complete HTTP request to FastAPI without an external client."""
    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    sent: list[dict[str, Any]] = []
    request_sent = False
    disconnected = asyncio.Event()

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    request_headers = [(b"content-type", b"application/json")]
    if token:
        request_headers.append((b"authorization", f"Bearer {token}".encode()))
    if headers:
        for key, value in headers.items():
            request_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": urlencode(query or {}).encode("ascii"),
        "headers": request_headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)

    start = next(item for item in sent if item["type"] == "http.response.start")
    response_body = b"".join(
        item.get("body", b"") for item in sent if item["type"] == "http.response.body"
    )
    headers = {key.decode("latin-1"): value.decode("latin-1") for key, value in start["headers"]}
    return start["status"], headers, response_body


class ApiIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_temp_dir = tempfile.TemporaryDirectory()
        self.repository = ConversationRepository(Path(self.temp_dir.name) / "ash_test.db")
        self.repository.initialize()
        self.engine = FakeEngine()

        self.original_chat_repository = chat_api.conversation_repository
        self.original_conversations_repository = conversations_api.conversation_repository
        self.original_engine_manager = chat_api.engine_manager
        self.original_auth_repository = dependencies.authentication_service.repository
        self.original_workspace_service = explorer_api.workspace_service
        chat_api.conversation_repository = self.repository
        conversations_api.conversation_repository = self.repository
        chat_api.engine_manager = self.engine
        dependencies.authentication_service.repository = self.repository
        self.workspace = WorkspaceService(Path(self.workspace_temp_dir.name)); self.workspace.initialize()
        explorer_api.workspace_service = self.workspace
        self.user, self.token = dependencies.authentication_service.register("primary-user", "correct-horse-battery-staple")

    async def asyncTearDown(self) -> None:
        chat_api.conversation_repository = self.original_chat_repository
        conversations_api.conversation_repository = self.original_conversations_repository
        chat_api.engine_manager = self.original_engine_manager
        dependencies.authentication_service.repository = self.original_auth_repository
        explorer_api.workspace_service = self.original_workspace_service
        self.temp_dir.cleanup()
        self.workspace_temp_dir.cleanup()

    async def create_conversation(self, token: str | None = None) -> dict[str, Any]:
        status, _, body = await asgi_request("POST", "/api/conversations", token=token or self.token)
        self.assertEqual(status, 201)
        return json.loads(body)

    async def test_conversation_crud_and_persistence(self) -> None:
        created = await self.create_conversation()
        conversation_id = created["id"]

        status, _, body = await asgi_request("GET", "/api/conversations", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in json.loads(body)], [conversation_id])

        status, _, body = await asgi_request(
            "PATCH", f"/api/conversations/{conversation_id}", {"title": "Project plan"}, self.token
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["title"], "Project plan")

        # A fresh repository instance must see persisted data in the temporary database.
        reopened = ConversationRepository(self.repository.database_path)
        self.assertEqual(reopened.get_conversation(conversation_id, self.user.id).conversation.title, "Project plan")

        status, _, body = await asgi_request("GET", f"/api/conversations/{conversation_id}", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["messages"], [])

        status, _, _ = await asgi_request("DELETE", f"/api/conversations/{conversation_id}", token=self.token)
        self.assertEqual(status, 204)
        status, _, body = await asgi_request("GET", f"/api/conversations/{conversation_id}", token=self.token)
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body)["detail"], "Conversation not found.")

    async def test_normal_chat_persists_messages_and_passes_history(self) -> None:
        conversation = await self.create_conversation()
        conversation_id = conversation["id"]
        self.engine.response = "First response"

        status, _, body = await asgi_request(
            "POST", "/api/chat", {"message": "First question", "conversation_id": conversation_id}, self.token
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"success": True, "response": "First response"})
        self.assertEqual(self.engine.calls[0][1], [])

        self.engine.response = "Second response"
        status, _, _ = await asgi_request(
            "POST", "/api/chat", {"message": "Second question", "conversation_id": conversation_id}, self.token
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            self.engine.calls[1][1],
            [
                ConversationMessage(role="user", content="First question"),
                ConversationMessage(role="assistant", content="First response"),
            ],
        )

        detail = self.repository.get_conversation(conversation_id, self.user.id)
        self.assertEqual(
            [(message.role, message.content) for message in detail.messages],
            [
                ("user", "First question"),
                ("assistant", "First response"),
                ("user", "Second question"),
                ("assistant", "Second response"),
            ],
        )

    async def test_streaming_chat_emits_deltas_done_and_persists_on_success(self) -> None:
        conversation = await self.create_conversation()
        self.engine.chunks = ["Hello", " world"]

        status, headers, body = await asgi_request(
            "POST",
            "/api/chat/stream",
            {"message": "Stream this", "conversation_id": conversation["id"]}, self.token,
        )
        text = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertIn("text/event-stream", headers["content-type"])
        self.assertIn('data: {"delta": "Hello"}', text)
        self.assertIn('data: {"delta": " world"}', text)
        self.assertIn('data: {"done": true}', text)
        self.assertEqual(
            [(message.role, message.content) for message in self.repository.get_conversation(conversation["id"], self.user.id).messages],
            [("user", "Stream this"), ("assistant", "Hello world")],
        )

    async def test_stream_failure_does_not_persist_an_assistant_response(self) -> None:
        conversation = await self.create_conversation()
        self.engine.chunks = ["Partial"]
        self.engine.stream_error = ProviderResponseError("Model generation failed.")

        status, _, body = await asgi_request(
            "POST",
            "/api/chat/stream",
            {"message": "Fail while streaming", "conversation_id": conversation["id"]}, self.token,
        )
        self.assertEqual(status, 200)
        self.assertIn("event: error", body.decode("utf-8"))
        self.assertEqual(
            [(message.role, message.content) for message in self.repository.get_conversation(conversation["id"], self.user.id).messages],
            [("user", "Fail while streaming")],
        )

    async def test_regeneration_replaces_only_the_previous_assistant_message(self) -> None:
        conversation = await self.create_conversation()
        conversation_id = conversation["id"]
        self.engine.response = "Original answer"
        await asgi_request(
            "POST", "/api/chat", {"message": "Explain this", "conversation_id": conversation_id}, self.token
        )

        self.engine.response = "Regenerated answer"
        status, _, body = await asgi_request(
            "POST",
            "/api/chat",
            {"message": "Explain this", "conversation_id": conversation_id, "regenerate": True}, self.token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["response"], "Regenerated answer")

        messages = self.repository.get_conversation(conversation_id, self.user.id).messages
        self.assertEqual(
            [(message.role, message.content) for message in messages],
            [("user", "Explain this"), ("assistant", "Regenerated answer")],
        )
        self.assertEqual(
            self.engine.calls[-1][1],
            [],
            "The regenerated request must not include the old user/assistant pair.",
        )

    async def test_provider_errors_have_clean_json_and_sse_responses(self) -> None:
        self.engine.generate_error = ProviderUnavailableError("Ollama is unavailable.")
        status, _, body = await asgi_request("POST", "/api/chat", {"message": "Hello"}, self.token)
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)["detail"], "Ollama is unavailable.")

        self.engine.generate_error = ProviderResponseError("Configured model failed.")
        status, _, body = await asgi_request("POST", "/api/chat", {"message": "Hello"}, self.token)
        self.assertEqual(status, 502)
        self.assertEqual(json.loads(body)["detail"], "Configured model failed.")

        self.engine.generate_error = None
        self.engine.stream_error = ProviderUnavailableError("Ollama is unavailable.")
        status, _, body = await asgi_request("POST", "/api/chat/stream", {"message": "Hello"}, self.token)
        self.assertEqual(status, 200)
        text = body.decode("utf-8")
        self.assertIn("event: error", text)
        self.assertIn("Ollama is unavailable.", text)

    async def test_registration_login_and_duplicate_rejection(self) -> None:
        status, _, body = await asgi_request(
            "POST", "/api/auth/register", {"username": "new-user", "password": "another-secure-password"}
        )
        self.assertEqual(status, 201)
        registered = json.loads(body)
        self.assertEqual(registered["user"]["username"], "new-user")
        self.assertTrue(registered["access_token"])
        self.assertNotIn("password", body.decode("utf-8").lower())

        status, _, _ = await asgi_request(
            "POST", "/api/auth/register", {"username": "new-user", "password": "another-secure-password"}
        )
        self.assertEqual(status, 409)
        status, _, body = await asgi_request(
            "POST", "/api/auth/login", {"username": "new-user", "password": "another-secure-password"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["access_token"])
        status, _, _ = await asgi_request(
            "POST", "/api/auth/login", {"username": "new-user", "password": "wrong-password-value"}
        )
        self.assertEqual(status, 401)

    async def test_users_cannot_access_each_others_conversations(self) -> None:
        owner = await self.create_conversation()
        other, other_token = dependencies.authentication_service.register("second-user", "second-secure-password")
        self.assertNotEqual(other.id, self.user.id)

        status, _, body = await asgi_request("GET", "/api/conversations", token=other_token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), [])
        for method, payload in (
            ("GET", None),
            ("DELETE", None),
            ("PATCH", {"title": "Unauthorized"}),
        ):
            status, _, _ = await asgi_request(
                method, f"/api/conversations/{owner['id']}", payload, other_token
            )
            self.assertEqual(status, 404)

        status, _, _ = await asgi_request("POST", "/api/chat", {"message": "Hello", "conversation_id": owner["id"]}, other_token)
        self.assertEqual(status, 404)

    async def test_protected_routes_reject_unauthenticated_requests(self) -> None:
        status, _, _ = await asgi_request("POST", "/api/conversations")
        self.assertEqual(status, 401)

    async def test_auth_responses_do_not_expose_password_fields(self) -> None:
        status, _, body = await asgi_request("POST", "/api/auth/register", {"username": "security-user", "password": "validpassword123"})
        self.assertEqual(status, 201)
        response = json.loads(body)
        self.assertIn("access_token", response)
        self.assertIn("user", response)
        self.assertNotIn("password", response)
        self.assertNotIn("password_hash", response)

        status, _, body = await asgi_request("POST", "/api/auth/login", {"username": "security-user", "password": "validpassword123"})
        self.assertEqual(status, 200)
        response = json.loads(body)
        self.assertIn("access_token", response)
        self.assertIn("user", response)
        self.assertNotIn("password", response)
        self.assertNotIn("password_hash", response)

    async def test_logout_revokes_session(self) -> None:
        status, _, _ = await asgi_request("POST", "/api/auth/logout", token=self.token)
        self.assertEqual(status, 204)
        status, _, _ = await asgi_request("GET", "/api/conversations", token=self.token)
        self.assertEqual(status, 401)

    async def test_expired_session_rejected(self) -> None:
        token = new_session_token()
        expires_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self.repository.create_session(self.user.id, session_token_hash(token, get_settings().auth_token_secret), expires_at)
        status, _, _ = await asgi_request("GET", "/api/conversations", token=token)
        self.assertEqual(status, 401)

    async def test_invalid_registration_input(self) -> None:
        status, _, body = await asgi_request("POST", "/api/auth/register", {"username": "x", "password": "short"})
        self.assertEqual(status, 422)
        self.assertNotIn("password_hash", body.decode("utf-8"))

    async def test_cors_and_security_headers_on_auth_endpoints(self) -> None:
        status, headers, _ = await asgi_request(
            "POST",
            "/api/auth/login",
            {"username": "primary-user", "password": "wrong-password"},
            token=None,
            headers={"Origin": "http://localhost:5173"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(headers.get("access-control-allow-credentials"), "true")

        status, headers, _ = await asgi_request("GET", "/health", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(headers.get("x-frame-options"), "DENY")
        self.assertEqual(headers.get("referrer-policy"), "strict-origin-when-cross-origin")

    async def test_workspace_explorer_is_authenticated_and_root_confined(self) -> None:
        root = Path(self.workspace_temp_dir.name); nested = root / "projects" / "alpha"; nested.mkdir(parents=True)
        document = nested / "notes.txt"; document.write_text("private workspace note", encoding="utf-8")
        status, _, body = await asgi_request("GET", "/api/explorer", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["entries"][0]["path"], "projects")
        status, _, body = await asgi_request("GET", "/api/explorer", token=self.token, query={"path": "projects/alpha"})
        self.assertEqual(status, 200)
        entry = json.loads(body)["entries"][0]
        self.assertEqual((entry["name"], entry["path"], entry["is_directory"], entry["size"]), ("notes.txt", "projects/alpha/notes.txt", False, 22))
        for path, expected in (("missing", 404), ("../", 400), (str(Path(self.temp_dir.name).resolve()), 400)):
            status, _, _ = await asgi_request("GET", "/api/explorer", token=self.token, query={"path": path})
            self.assertEqual(status, expected)
        status, _, _ = await asgi_request("GET", "/api/explorer")
        self.assertEqual(status, 401)

        outside = Path(self.temp_dir.name) / "outside.txt"; outside.write_text("outside", encoding="utf-8")
        link = root / "escape-link"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("Symlink creation is unavailable on this Windows configuration.")
        status, _, body = await asgi_request("GET", "/api/explorer", token=self.token)
        self.assertEqual(status, 200)
        self.assertNotIn("escape-link", [item["name"] for item in json.loads(body)["entries"]])
        status, _, _ = await asgi_request("POST", "/api/chat", {"message": "Hello"})
        self.assertEqual(status, 401)
        status, _, _ = await asgi_request("POST", "/api/chat/stream", {"message": "Hello"})
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
