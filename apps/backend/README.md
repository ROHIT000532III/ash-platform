# ASH AI Backend

## Setup

From the repository root, create or activate the existing virtual environment and
install the backend dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r apps\backend\requirements.txt
```

Copy `apps\backend\.env.example` to `apps\backend\.env` and set a long
`AUTH_TOKEN_SECRET`. The default workspace is `apps\backend\workspace`.

## Run

Run Uvicorn from the backend directory so the `app` package resolves correctly:

```powershell
Set-Location apps\backend
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is
available at `/docs`.

## Tests

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest apps.backend.tests.test_api_integration -v
```

## Desktop packaging

Install the build-only packaging dependency into the development environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r apps\backend\requirements-build.txt
```

From the repository root, build the standalone backend and Windows installer:

```powershell
npm run electron:build
```

The installer contains the standalone backend executable. Ollama remains an
external local service.