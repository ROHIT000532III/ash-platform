# ASH AI

ASH AI is a Windows desktop AI chat application built with Electron, React/Vite,
and a local Python/FastAPI backend. It provides a direct Chat workspace,
conversation history, model information, workspace browsing, backend settings,
and streaming responses from a locally running Ollama model.

## Project idea and purpose

ASH AI is designed to make local AI assistance available from a focused desktop
workspace. The Electron shell hosts the React interface, while the bundled
FastAPI service handles conversations, workspace operations, model status, and
communication with Ollama.

The desktop application opens directly to Chat. It does not require a
Login/Register screen or a user account for normal local desktop use.

## Key features

- Direct ASH AI Chat startup
- Normal and streaming chat responses
- Persistent local conversations stored in SQLite
- Conversation selection, search, rename, and delete actions
- Ollama provider and installed-model discovery
- Configurable generation settings
- Local workspace Explorer
- Backend health and engine status reporting
- Windows Electron desktop packaging with an included FastAPI executable
- Dark desktop interface

## Technology stack

- Electron 43
- React 19
- React Router
- TypeScript
- Vite
- Python 3 with FastAPI and Uvicorn
- SQLite
- Ollama
- PyInstaller
- Electron Builder

## Repository structure

This is the current repository structure relevant to development and release:

```text
ash-platform/
├── apps/
│   └── backend/
│       ├── app/
│       │   ├── api/             # Chat, conversations, explorer, models, settings, auth
│       │   ├── core/            # Configuration, database, dependencies, security, workspace
│       │   ├── engine/          # Engine manager and Ollama/demo adapters
│       │   └── main.py          # FastAPI application
│       ├── packaging/
│       │   └── backend.spec    # PyInstaller configuration
│       ├── tests/
│       │   └── test_api_integration.py
│       ├── backend_launcher.py  # Packaged Uvicorn entrypoint
│       ├── requirements.txt
│       ├── requirements-build.txt
│       └── README.md
├── assets/
│   └── logo/
├── electron/
│   └── main.cjs                 # Electron main process and app:// protocol
├── public/
├── src/
│   ├── auth/                    # Retained authentication support
│   ├── components/
│   ├── core/
│   ├── layouts/
│   ├── pages/
│   │   ├── auth/
│   │   ├── chat/
│   │   ├── dashbord/
│   │   ├── explorer/
│   │   ├── models/
│   │   └── settings/
│   ├── routers/
│   ├── services/
│   │   └── api.ts               # Frontend API client
│   ├── styles/
│   ├── App.tsx
│   └── main.tsx
├── app/                         # Legacy backend tree; not used by current packaging
├── build/                       # Build resources/generated files
├── dist/                        # Vite production output
├── docs/
├── packages/
├── scripts/
├── tests/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig*.json
├── LICENSE
└── README.md
```

Generated directories such as `node_modules`, `.venv`, `apps/backend/build`,
`apps/backend/dist`, and `release` are local development or release artifacts
and are not required in a source checkout.

## Windows installation and use

The current Windows x64 NSIS installer is:

```text
ASH-AI-Setup-0.1.0.exe
```

To install:

1. Download `ASH-AI-Setup-0.1.0.exe` from the GitHub Release.
2. Run the installer.
3. Choose the installation directory if desired.
4. Launch **ASH AI** from the Start Menu or desktop shortcut.
5. The app starts its bundled backend and opens directly to Chat.

The installed application does not require the Vite development server.
Ollama must be installed and running locally for Ollama-powered responses.

## Developer setup

### Prerequisites

- Windows
- Node.js and npm
- Python
- Ollama for local model responses

### Frontend dependencies

From the repository root:

```powershell
npm install
```

### Backend environment

Create or activate the repository virtual environment, then install the backend
dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r apps\backend\requirements.txt
```

For Windows backend packaging, install the build dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install -r apps\backend\requirements-build.txt
```

### Run the backend directly

Run Uvicorn from the backend directory so the `app` package resolves correctly:

```powershell
Set-Location apps\backend
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The backend listens on:

```text
http://127.0.0.1:8000
```

Health endpoint:

```text
http://127.0.0.1:8000/health
```

### Run the desktop app during development

With the backend running, start Vite and Electron:

```powershell
npm run desktop
```

The development renderer is served by Vite at `http://localhost:5173`.
Packaged builds do not use this development server.

### Checks and builds

```powershell
npm run lint
npm run build
.\.venv\Scripts\python.exe -m pytest apps\backend\tests
```

Build the standalone backend:

```powershell
npm run backend:build
```

Build the Windows x64 NSIS installer:

```powershell
npx electron-builder --win nsis --x64
```

The installer is written to `release\`.

## Local AI architecture with Ollama

The request flow is:

```text
React Chat UI
    ↓
Electron-hosted frontend API client
    ↓
FastAPI backend at 127.0.0.1:8000
    ↓
Ollama at localhost:11434
    ↓
Configured local model (default: llama3.2)
```

The backend's `EngineManager` uses the Ollama adapter for normal generation,
streaming, model discovery, availability checks, and retry handling. A demo
provider can be configured as a fallback through the existing backend settings.

ASH AI does **not** require OpenAI, Gemini, Claude, or any other external/cloud
AI API. The normal AI path uses Ollama running locally on the user's machine.

## Releases

The Windows distribution artifact is an x64 NSIS installer:

```text
release\ASH-AI-Setup-0.1.0.exe
```

For a GitHub Release, upload the installer as the primary Windows download.
Do not upload `node_modules`, build caches, the `win-unpacked` directory, or
source-only development artifacts.

## Developer credit

Instagram: [@mr_hackerr_12k](https://www.instagram.com/mr_hackerr_12k/)

## License

MIT License. See [LICENSE](LICENSE).
