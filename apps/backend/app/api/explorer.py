from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user, workspace_service
from app.core.database import User
from app.core.workspace import WorkspaceError, WorkspaceNotFoundError, WorkspacePermissionError

router = APIRouter(prefix="/api/explorer", tags=["explorer"])


@router.get("")
def list_directory(
    path: str = Query(default="", max_length=1024), user: User = Depends(get_current_user)
) -> dict[str, object]:
    del user
    try:
        return workspace_service.list_directory(path)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except WorkspacePermissionError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except WorkspaceError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
