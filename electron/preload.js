// Preload runs in isolated context. BACKEND_URL is injected via index.html script
// so the renderer (React) can read window.BACKEND_URL. No additional exposure needed.
const { contextBridge } = require("electron");
contextBridge.exposeInMainWorld("electronAPI", {});
// BACKEND_URL is set in the HTML before the app bundle loads.
