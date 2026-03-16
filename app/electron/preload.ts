import { contextBridge, ipcRenderer } from 'electron'

// 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 应用信息
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  
  // 窗口控制
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  maximizeWindow: () => ipcRenderer.invoke('maximize-window'),
  closeWindow: () => ipcRenderer.invoke('close-window'),
  
  // 自动启动设置
  getAutoLaunch: () => ipcRenderer.invoke('get-auto-launch'),
  setAutoLaunch: (enabled: boolean) => ipcRenderer.invoke('set-auto-launch', enabled),
  isAutoLaunched: () => ipcRenderer.invoke('is-auto-launched'),
  
  // 语言设置
  getLanguage: () => ipcRenderer.invoke('get-language'),
  setLanguage: (language: string) => ipcRenderer.invoke('set-language', language),
  
  // 平台信息
  platform: process.platform
})

// 类型声明
declare global {
  interface Window {
    electronAPI: {
      getAppVersion: () => Promise<string>
      minimizeWindow: () => Promise<void>
      maximizeWindow: () => Promise<void>
      closeWindow: () => Promise<void>
      getAutoLaunch: () => Promise<boolean>
      setAutoLaunch: (enabled: boolean) => Promise<boolean>
      isAutoLaunched: () => Promise<boolean>
      getLanguage: () => Promise<string>
      setLanguage: (language: string) => Promise<string>
      platform: string
    }
  }
}
