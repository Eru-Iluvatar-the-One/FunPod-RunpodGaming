import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('api', {
  store: {
    get: (key) => ipcRenderer.invoke('store:get', key),
    set: (key, val) => ipcRenderer.invoke('store:set', key, val),
  },
  gql: (query, variables) => ipcRenderer.invoke('runpod:gql', query, variables),
  openExternal: (url) => ipcRenderer.invoke('shell:open', url),
  minimize: () => ipcRenderer.invoke('window:minimize'),
  close: () => ipcRenderer.invoke('window:close'),
})
