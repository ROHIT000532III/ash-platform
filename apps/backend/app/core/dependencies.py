from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.database import ConversationRepository, DatabaseError, User
from app.core.security import hash_password, new_session_token, session_token_hash, verify_password
from app.core.workspace import WorkspaceService


conversation_repository = ConversationRepository(get_settings().database_path)
settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)
workspace_service = WorkspaceService(settings.workspace_root)


class AuthenticationService:
    def __init__(self, repository: ConversationRepository):
        self.repository = repository

    def register(self, username: str, password: str) -> tuple[User, str]:
        user = self.repository.create_user(username, hash_password(password))
        return user, self._session(user.id)

    def login(self, username: str, password: str) -> tuple[User, str] | None:
        record = self.repository.user_by_username(username)
        if record is None or not verify_password(password, record[1]):
            return None
        return record[0], self._session(record[0].id)

    def current_user(self, token: str) -> User | None:
        return self.repository.user_for_session(
            session_token_hash(token, settings.auth_token_secret), datetime.now(timezone.utc).isoformat()
        )

    def logout(self, token: str) -> bool:
        user = self.current_user(token)
        if user is None:
            return False
        self.repository.delete_session(session_token_hash(token, settings.auth_token_secret))
        return True

    def _session(self, user_id: str) -> str:
        token = new_session_token()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=settings.auth_session_days)).isoformat()
        self.repository.create_session(user_id, session_token_hash(token, settings.auth_token_secret), expires_at)
        return token


authentication_service = AuthenticationService(conversation_repository)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")
    user = authentication_service.current_user(credentials.credentials)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")
    return user
