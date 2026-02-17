const { app, BrowserWindow, protocol } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const net = require("net");

const APP_NAME = "Portfolio App";
const BACKEND_BIN_NAME = "backend";

/** Write a line to the app log file (userData/log.txt) for debugging. */
function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  try {
    const logPath = path.join(app.getPath("userData"), "log.txt");
    fs.appendFileSync(logPath, line);
  } catch (_) {}
  console.error(line.trim());
}

/** Get path to backend executable (inside app resources when packaged). */
function getBackendPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "backend", BACKEND_BIN_NAME);
  }
  return path.join(__dirname, "..", "resources", "backend", BACKEND_BIN_NAME);
}

/** Get path to frontend static files (inside app resources when packaged). */
function getFrontendDir() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "frontend");
  }
  return path.join(__dirname, "..", "resources", "frontend");
}

/** Find an available port on 127.0.0.1. */
function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer(() => {});
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
    server.on("error", reject);
  });
}

/** Poll URL until it returns 200 or timeout. */
function waitForBackend(url, maxWaitMs = 15000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    function poll() {
      fetch(url)
        .then((res) => {
          if (res.ok) return resolve();
          if (Date.now() - start > maxWaitMs) return reject(new Error("Backend timeout"));
          setTimeout(poll, 200);
        })
        .catch(() => {
          if (Date.now() - start > maxWaitMs) return reject(new Error("Backend timeout"));
          setTimeout(poll, 200);
        });
    }
    poll();
  });
}

let backendProcess = null;
let mainWindow = null;

function launchBackend(userDataDir, port) {
  const backendPath = getBackendPath();
  if (!fs.existsSync(backendPath)) {
    log(`ERROR: Backend binary not found at ${backendPath}`);
    throw new Error(`Backend binary not found at ${backendPath}`);
  }
  log(`Starting backend: ${backendPath} (port ${port})`);

  const env = {
    ...process.env,
    APP_DATA_DIR: userDataDir,
    BACKEND_PORT: String(port),
    // Allow adding transactions when yfinance fails (timeout/network in packaged app).
    SKIP_SYMBOL_VALIDATION: "1",
  };

  const backendLogPath = path.join(userDataDir, "backend-log.txt");
  backendProcess = spawn(backendPath, [], {
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });

  function writeBackendLog(prefix, data) {
    const text = (data && data.toString()) || "";
    if (!text.trim()) return;
    try {
      fs.appendFileSync(backendLogPath, `[${prefix}] ${text}`);
    } catch (_) {}
    console.error(`[backend ${prefix}]`, text.trim());
  }

  backendProcess.stdout.on("data", (data) => writeBackendLog("stdout", data));
  backendProcess.stderr.on("data", (data) => writeBackendLog("stderr", data));

  backendProcess.on("error", (err) => {
    log(`Backend spawn error: ${err.message}`);
  });

  backendProcess.on("exit", (code, signal) => {
    if (code != null && code !== 0) log(`Backend exited with code ${code}. See ${backendLogPath}`);
    if (signal) log(`Backend killed with signal ${signal}. See ${backendLogPath}`);
    backendProcess = null;
  });
}

function ensureFrontendWithBackendUrl(userDataDir, backendUrl) {
  const frontendSource = getFrontendDir();
  const frontendDest = path.join(userDataDir, "frontend");

  if (!fs.existsSync(frontendSource)) {
    log(`ERROR: Frontend not found at ${frontendSource}`);
    throw new Error(`Frontend not found at ${frontendSource}`);
  }

  if (!fs.existsSync(frontendDest)) {
    copyDirSync(frontendSource, frontendDest);
  }

  // Always patch index from bundle so BACKEND_URL is correct (handles old userData copies).
  const indexSource = path.join(frontendSource, "index.html");
  const indexDest = path.join(frontendDest, "index.html");
  let html = fs.readFileSync(indexSource, "utf8");
  html = html.replace(/\{\{BACKEND_URL\}\}/g, backendUrl);
  fs.writeFileSync(indexDest, html, "utf8");

  return indexDest;
}

function copyDirSync(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const name of fs.readdirSync(src)) {
    const srcPath = path.join(src, name);
    const destPath = path.join(dest, name);
    if (fs.statSync(srcPath).isDirectory()) {
      copyDirSync(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function createWindow(backendUrl) {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    title: APP_NAME,
  });

  const userDataDir = app.getPath("userData");
  const indexHtmlPath = ensureFrontendWithBackendUrl(userDataDir, backendUrl);
  mainWindow.loadFile(indexHtmlPath);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  const userDataDir = app.getPath("userData");
  log(`userData: ${userDataDir}`);
  const port = await findFreePort();
  const backendUrl = `http://127.0.0.1:${port}`;

  launchBackend(userDataDir, port);

  try {
    await waitForBackend(`${backendUrl}/health`);
    log("Backend ready");
  } catch (err) {
    log(`Backend failed to become ready: ${err.message}`);
    app.quit();
    return;
  }

  createWindow(backendUrl);
});

app.on("window-all-closed", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
  app.quit();
});

app.on("quit", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
});
