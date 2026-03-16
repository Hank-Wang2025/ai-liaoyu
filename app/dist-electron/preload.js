"use strict";
const electron = require("electron");
electron.contextBridge.exposeInMainWorld("electronAPI", {
  // 应用信息
  getAppVersion: () => electron.ipcRenderer.invoke("get-app-version"),
  // 窗口控制
  minimizeWindow: () => electron.ipcRenderer.invoke("minimize-window"),
  maximizeWindow: () => electron.ipcRenderer.invoke("maximize-window"),
  closeWindow: () => electron.ipcRenderer.invoke("close-window"),
  // 自动启动设置
  getAutoLaunch: () => electron.ipcRenderer.invoke("get-auto-launch"),
  setAutoLaunch: (enabled) => electron.ipcRenderer.invoke("set-auto-launch", enabled),
  isAutoLaunched: () => electron.ipcRenderer.invoke("is-auto-launched"),
  // 语言设置
  getLanguage: () => electron.ipcRenderer.invoke("get-language"),
  setLanguage: (language) => electron.ipcRenderer.invoke("set-language", language),
  // 平台信息
  platform: process.platform
});
