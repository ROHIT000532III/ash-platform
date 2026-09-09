const { app, BrowserWindow, dialog, net, protocol } = require("electron");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

protocol.registerSchemesAsPrivileged([
  {
    scheme: "app",
    privileges: { standard: true, secure: true, supportFetchAPI: true },
  },
]);

const backendUrl = process.env.ASH_BACKEND_URL || "http://127.0.0.1:8000";
let backendProcess = null;
let backendStartup = null;
let quitting = false;

const hasSingleInstanceLock = app.requestSingleInstanceLock();
if (!hasSingleInstanceLock) {
  app.quit();
}

function checkBackend() {
  return new Promise((resolve) => {
    const request = require("http").get(`${backendUrl}/health`, (response) => {
      response.resume();
      resolve(response.statusCode === 200);
    });
    request.on("error", () => resolve(false));
    request.setTimeout(1000, () => {
      request.destroy();
      resolve(false);
    });
  });
}

async function waitForBackend() {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    if (await checkBackend()) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

function packagedBackendPath() {
  return path.join(process.resourcesPath, "backend", "ASHBackend.exe");
}

function startPackagedBackend() {
  if (backendProcess !== null) {
    return;
  }
  const executable = packagedBackendPath();
  const userData = app.getPath("userData");
  backendProcess = spawn(executable, [], {
    cwd: path.dirname(executable),
    env: {
      ...process.env,
      ASH_BACKEND_HOST: "127.0.0.1",
      ASH_BACKEND_PORT: "8000",
      ASH_DATABASE_PATH: path.join(userData, "data", "ash_ai.db"),
      ASH_WORKSPACE_ROOT: path.join(userData, "workspace"),
    },
    stdio: "ignore",
    windowsHide: true,
  });
  backendProcess.once("error", (error) => {
    console.error("Unable to start packaged ASH backend:", error.message);
  });
  backendProcess.once("exit", (code, signal) => {
    if (backendProcess !== null) {
      console.error(`Packaged ASH backend exited (code=${code}, signal=${signal}).`);
    }
    backendProcess = null;
  });
}

async function ensureBackend() {
  if (await checkBackend()) {
    return true;
  }
  if (app.isPackaged) {
    if (backendStartup === null) {
      backendStartup = (async () => {
        try {
          startPackagedBackend();
        } catch (error) {
          console.error("Unable to launch packaged ASH backend:", error);
          return false;
        }
        return await waitForBackend();
      })().finally(() => {
        backendStartup = null;
      });
    }
    return await backendStartup;
  }
  return false;
}

function createWindow(backendAvailable) {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    autoHideMenuBar: true,
    backgroundColor: "#080b12",
    title: "ASH AI Enterprise",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (app.isPackaged || process.env.ASH_ELECTRON_PRODUCTION === "1") {
    win.loadURL("app://./index.html");
  } else {
    win.loadURL("http://localhost:5173");
  }
  if (!backendAvailable) {
    dialog.showMessageBox(win, {
      type: "warning",
      title: "ASH AI backend unavailable",
      message: `ASH AI could not connect to the backend at ${backendUrl}.`,
      detail: "Start the FastAPI backend, then retry from the application.",
    });
  }
}

function stopPackagedBackend() {
  if (backendProcess === null) {
    return Promise.resolve();
  }
  const processToStop = backendProcess;
  backendProcess = null;
  if (process.platform === "win32") {
    return new Promise((resolve) => {
      const terminator = spawn(
        "taskkill",
        ["/PID", String(processToStop.pid), "/T", "/F"],
        {
          windowsHide: true,
          stdio: "ignore",
        },
      );
      terminator.once("close", resolve);
      terminator.once("error", resolve);
    });
  }
  processToStop.kill();
  return Promise.resolve();
}

app.whenReady().then(async () => {
  const rendererRoot = path.join(
    process.resourcesPath,
    "app.asar.unpacked",
    "dist",
  );
  protocol.handle("app", (request) => {
    const requestPath = decodeURIComponent(new URL(request.url).pathname);
    const requestedFile = path.resolve(rendererRoot, `.${requestPath}`);
    const rootPrefix = `${path.resolve(rendererRoot)}${path.sep}`;
    const filePath = requestedFile.startsWith(rootPrefix) && fs.existsSync(requestedFile)
      ? requestedFile
      : path.join(rendererRoot, "index.html");
    return net.fetch(`file://${filePath.replace(/\\/g, "/")}`);
  });
  const backendAvailable = await ensureBackend();
  createWindow(backendAvailable);
});

app.on("before-quit", async (event) => {
  if (quitting) {
    return;
  }
  event.preventDefault();
  quitting = true;
  await stopPackagedBackend();
  app.quit();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});