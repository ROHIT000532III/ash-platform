from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.engine.base import ConversationMessage


class DatabaseError(Exception):
    """A safe database error that can be returned by the API."""


class ConversationNotFoundError(DatabaseError):
    pass


class UserAlreadyExistsError(DatabaseError):
    pass


@dataclass(frozen=True)
class Conversation:
    id: str
    title: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class User:
    id: str
    username: str
    created_at: str


@dataclass(frozen=True)
class StoredMessage:
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str


@dataclass(frozen=True)
class ConversationDetail:
    conversation: Conversation
    messages: list[StoredMessage]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def title_from_message(content: str) -> str:
    normalized = " ".join(content.split())
    return normalized if len(normalized) <= 60 else f"{normalized[:57].rstrip()}..."


class ConversationRepository:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def initialize(self) -> None:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS sessions (
                        token_hash TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        title TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                        content TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                    );
                    CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
                        ON conversations(updated_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation_created_at
                        ON messages(conversation_id, created_at, id);
                    """
                )
                columns = {row["name"] for row in connection.execute("PRAGMA table_info(conversations)")}
                if "user_id" not in columns:
                    connection.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT")
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_conversations_user_updated_at "
                    "ON conversations(user_id, updated_at DESC)"
                )
        except sqlite3.Error as error:
            raise DatabaseError("Unable to initialize the conversation database.") from error

    def create_user(self, username: str, password_hash: str) -> User:
        user = User(str(uuid4()), username, _timestamp())
        try:
            with self._connect() as connection:
                connection.execute("INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)", (user.id, user.username, password_hash, user.created_at))
            return user
        except sqlite3.IntegrityError as error:
            raise UserAlreadyExistsError("Username is already registered.") from error
        except sqlite3.Error as error:
            raise DatabaseError("Unable to create the user.") from error

    def user_by_username(self, username: str) -> tuple[User, str] | None:
        try:
            with self._connect() as connection:
                row = connection.execute("SELECT id, username, password_hash, created_at FROM users WHERE username = ?", (username,)).fetchone()
            return (User(id=row["id"], username=row["username"], created_at=row["created_at"]), row["password_hash"]) if row else None
        except sqlite3.Error as error:
            raise DatabaseError("Unable to load the user.") from error

    def create_session(self, user_id: str, token_hash: str, expires_at: str) -> None:
        try:
            with self._connect() as connection:
                connection.execute("INSERT INTO sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)", (token_hash, user_id, expires_at, _timestamp()))
        except sqlite3.Error as error:
            raise DatabaseError("Unable to create the session.") from error

    def delete_session(self, token_hash: str) -> None:
        try:
            with self._connect() as connection:
                connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        except sqlite3.Error as error:
            raise DatabaseError("Unable to delete the session.") from error

    def user_for_session(self, token_hash: str, now: str) -> User | None:
        try:
            with self._connect() as connection:
                connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
                row = connection.execute("SELECT users.id, users.username, users.created_at FROM sessions JOIN users ON users.id = sessions.user_id WHERE sessions.token_hash = ? AND sessions.expires_at > ?", (token_hash, now)).fetchone()
            return User(**dict(row)) if row else None
        except sqlite3.Error as error:
            raise DatabaseError("Unable to validate the session.") from error

    def create_conversation(self, user_id: str) -> Conversation:
        now = _timestamp()
        conversation = Conversation(str(uuid4()), "New conversation", now, now)
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (conversation.id, user_id, conversation.title, conversation.created_at, conversation.updated_at),
                )
            return conversation
        except sqlite3.Error as error:
            raise DatabaseError("Unable to create the conversation.") from error

    def list_conversations(self, user_id: str) -> list[Conversation]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id = ? "
                    "ORDER BY updated_at DESC, id DESC", (user_id,)
                ).fetchall()
            return [self._conversation(row) for row in rows]
        except sqlite3.Error as error:
            raise DatabaseError("Unable to load conversations.") from error

    def get_conversation(self, conversation_id: str, user_id: str) -> ConversationDetail:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ? AND user_id = ?",
                    (conversation_id, user_id),
                ).fetchone()
                if row is None:
                    raise ConversationNotFoundError("Conversation not found.")
                message_rows = connection.execute(
                    "SELECT id, conversation_id, role, content, created_at FROM messages "
                    "WHERE conversation_id = ? ORDER BY created_at ASC, id ASC",
                    (conversation_id,),
                ).fetchall()
            return ConversationDetail(
                conversation=self._conversation(row),
                messages=[self._message(message_row) for message_row in message_rows],
            )
        except ConversationNotFoundError:
            raise
        except sqlite3.Error as error:
            raise DatabaseError("Unable to load the conversation.") from error

    def delete_conversation(self, conversation_id: str, user_id: str) -> None:
        try:
            with self._connect() as connection:
                result = connection.execute(
                    "DELETE FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)
                )
                if result.rowcount == 0:
                    raise ConversationNotFoundError("Conversation not found.")
        except ConversationNotFoundError:
            raise
        except sqlite3.Error as error:
            raise DatabaseError("Unable to delete the conversation.") from error

    def rename_conversation(self, conversation_id: str, user_id: str, title: str) -> Conversation:
        now = _timestamp()
        try:
            with self._connect() as connection:
                result = connection.execute(
                    "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                    (title, now, conversation_id, user_id),
                )
                if result.rowcount == 0:
                    raise ConversationNotFoundError("Conversation not found.")
                row = connection.execute(
                    "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ? AND user_id = ?",
                    (conversation_id, user_id),
                ).fetchone()
            return self._conversation(row)
        except ConversationNotFoundError:
            raise
        except sqlite3.Error as error:
            raise DatabaseError("Unable to rename the conversation.") from error

    def add_message(self, conversation_id: str, user_id: str, role: str, content: str) -> StoredMessage:
        now = _timestamp()
        message = StoredMessage(str(uuid4()), conversation_id, role, content, now)
        try:
            with self._connect() as connection:
                conversation = connection.execute(
                    "SELECT title FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)
                ).fetchone()
                if conversation is None:
                    raise ConversationNotFoundError("Conversation not found.")
                if role == "user" and conversation["title"] == "New conversation":
                    connection.execute(
                        "UPDATE conversations SET title = ? WHERE id = ?",
                        (title_from_message(content), conversation_id),
                    )
                connection.execute(
                    "INSERT INTO messages (id, conversation_id, role, content, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (message.id, message.conversation_id, message.role, message.content, message.created_at),
                )
                connection.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?",
                    (now, conversation_id),
                )
            return message
        except ConversationNotFoundError:
            raise
        except sqlite3.Error as error:
            raise DatabaseError("Unable to save the message.") from error

    def delete_message(self, message_id: str, user_id: str) -> None:
        try:
            with self._connect() as connection:
                connection.execute("DELETE FROM messages WHERE id = ? AND conversation_id IN (SELECT id FROM conversations WHERE user_id = ?)", (message_id, user_id))
        except sqlite3.Error as error:
            raise DatabaseError("Unable to update the response.") from error

    def history(self, conversation_id: str, user_id: str) -> list[ConversationMessage]:
        detail = self.get_conversation(conversation_id, user_id)
        return [ConversationMessage(role=message.role, content=message.content) for message in detail.messages]

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _conversation(row: sqlite3.Row) -> Conversation:
        return Conversation(**dict(row))

    @staticmethod
    def _message(row: sqlite3.Row) -> StoredMessage:
        return StoredMessage(**dict(row))
