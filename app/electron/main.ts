import {
  app,
  BrowserWindow,
  ipcMain,
  Menu,
  Tray,
  nativeImage,
  session,
} from "electron";
import { join } from "path";
import Store from "electron-store";

// Initialize electron-store for persistent settings
const store = new Store({
  defaults: {
    autoLaunch: true,
    language: "zh",
    windowBounds: { width: 1280, height: 800 },
  },
});

// 禁用硬件加速以避免某些显示问题
// app.disableHardwareAcceleration()

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;

const MEDIA_PERMISSIONS = new Set(["media", "audioCapture", "videoCapture"]);
const TRUSTED_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

function isTrustedOrigin(requestingOrigin: string) {
  try {
    const url = new URL(requestingOrigin);
    return url.protocol === "file:" || TRUSTED_HOSTS.has(url.hostname);
  } catch {
    return false;
  }
}

function configureMediaPermissions() {
  const defaultSession = session.defaultSession;

  defaultSession.setPermissionCheckHandler(
    (_webContents, permission, requestingOrigin) => {
      if (MEDIA_PERMISSIONS.has(permission)) {
        return isTrustedOrigin(requestingOrigin);
      }
      return true;
    },
  );

  defaultSession.setPermissionRequestHandler(
    (_webContents, permission, callback, details) => {
      if (MEDIA_PERMISSIONS.has(permission)) {
        callback(isTrustedOrigin(details.requestingOrigin));
        return;
      }
      callback(true);
    },
  );
}

// Set app to launch at login based on stored preference
function setupAutoLaunch() {
  const autoLaunch = store.get("autoLaunch", true);

  app.setLoginItemSettings({
    openAtLogin: autoLaunch,
    openAsHidden: false,
    path: app.getPath("exe"),
    args: ["--auto-launched"],
  });
}

function createTray() {
  // Create a simple tray icon (you can replace with actual icon)
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: "显示主窗口",
      click: () => {
        mainWindow?.show();
        mainWindow?.focus();
      },
    },
    {
      label: "开机自启动",
      type: "checkbox",
      checked: store.get("autoLaunch", true) as boolean,
      click: (menuItem) => {
        store.set("autoLaunch", menuItem.checked);
        setupAutoLaunch();
      },
    },
    { type: "separator" },
    {
      label: "退出",
      click: () => {
        app.quit();
      },
    },
  ]);

  tray.setToolTip("智能疗愈仓");
  tray.setContextMenu(contextMenu);

  tray.on("click", () => {
    mainWindow?.show();
    mainWindow?.focus();
  });
}

function createWindow() {
  const bounds = store.get("windowBounds", { width: 1280, height: 800 }) as {
    width: number;
    height: number;
  };

  mainWindow = new BrowserWindow({
    width: bounds.width,
    height: bounds.height,
    minWidth: 1024,
    minHeight: 768,
    webPreferences: {
      preload: join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
    },
    titleBarStyle: "hiddenInset",
    backgroundColor: "#1a1a2e",
    show: false,
  });

  // Save window bounds on resize
  mainWindow.on("resize", () => {
    if (mainWindow) {
      const { width, height } = mainWindow.getBounds();
      store.set("windowBounds", { width, height });
    }
  });

  // 开发模式加载本地服务器
  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    mainWindow.webContents.openDevTools();
  } else {
    // 生产模式加载打包后的文件
    mainWindow.loadFile(join(__dirname, "../dist/index.html"));
  }

  // 窗口准备好后显示，避免白屏
  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  // Hide window instead of closing on macOS (minimize to tray behavior)
  mainWindow.on("close", (event) => {
    if (process.platform === "darwin" && !app.isQuitting) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });
}

// Extend app with isQuitting property
declare module "electron" {
  interface App {
    isQuitting?: boolean;
  }
}

// 应用准备就绪时创建窗口
app.whenReady().then(() => {
  configureMediaPermissions();

  // Setup auto-launch on first run
  setupAutoLaunch();

  // Create system tray
  createTray();

  // Create main window
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else {
      mainWindow?.show();
    }
  });
});

// Handle before-quit to properly close the app
app.on("before-quit", () => {
  app.isQuitting = true;
});

// 所有窗口关闭时退出应用（macOS 除外）
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

// IPC 通信处理
ipcMain.handle("get-app-version", () => {
  return app.getVersion();
});

ipcMain.handle("minimize-window", () => {
  mainWindow?.minimize();
});

ipcMain.handle("maximize-window", () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});

ipcMain.handle("close-window", () => {
  mainWindow?.close();
});

// Auto-launch settings IPC handlers
ipcMain.handle("get-auto-launch", () => {
  return store.get("autoLaunch", true);
});

ipcMain.handle("set-auto-launch", (_event, enabled: boolean) => {
  store.set("autoLaunch", enabled);
  setupAutoLaunch();
  return enabled;
});

// Language settings IPC handlers
ipcMain.handle("get-language", () => {
  return store.get("language", "zh");
});

ipcMain.handle("set-language", (_event, language: string) => {
  store.set("language", language);
  return language;
});

// Check if app was auto-launched
ipcMain.handle("is-auto-launched", () => {
  return process.argv.includes("--auto-launched");
});
