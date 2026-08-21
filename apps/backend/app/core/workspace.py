from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class WorkspaceError(Exception):
    pass


class WorkspacePathError(WorkspaceError):
    pass


class WorkspaceNotFoundError(WorkspaceError):
    pass


class WorkspacePermissionError(WorkspaceError):
    pass


class WorkspaceService:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def list_directory(self, relative_path: str = "") -> dict[str, object]:
        path = self._resolve(relative_path)
        if not path.exists():
            raise WorkspaceNotFoundError("Workspace path was not found.")
        if not path.is_dir():
            raise WorkspacePathError("Workspace path must be a directory.")
        try:
            entries = [entry for entry in (self._metadata(item) for item in path.iterdir()) if entry is not None]
        except PermissionError as error:
            raise WorkspacePermissionError("Permission denied while reading the workspace.") from error
        entries.sort(key=lambda item: (not item["is_directory"], item["name"].lower()))
        return {"path": self._relative(path), "parent_path": self._parent(path), "entries": entries}

    def _resolve(self, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise WorkspacePathError("Workspace path is invalid.")
        try:
            resolved = (self.root / candidate).resolve(strict=False)
            resolved.relative_to(self.root)
            return resolved
        except ValueError as error:
            raise WorkspacePathError("Workspace path is invalid.") from error

    def _metadata(self, entry: Path) -> dict[str, object] | None:
        try:
            resolved = entry.resolve(strict=True)
            resolved.relative_to(self.root)
            stat = entry.stat()
        except (FileNotFoundError, ValueError):
            return None
        except PermissionError as error:
            raise WorkspacePermissionError("Permission denied while reading the workspace.") from error
        return {
            "name": entry.name,
            "path": self._relative(entry),
            "is_directory": resolved.is_dir(),
            "size": None if resolved.is_dir() else stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        }

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def _parent(self, path: Path) -> str | None:
        return None if path == self.root else self._relative(path.parent)
