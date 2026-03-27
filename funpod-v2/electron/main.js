import { app, BrowserWindow, ipcMain, shell } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'
import Store from 'electron-store'

const store = new Store({ name: 'funpod-config' })
const __dirname = path.dirname(fileURLToPath(import.meta.url))

process.env.DIST_ELECTRON = __dirname
process.env.DIST = path.join(__dirname, '../dist')
const VITE_DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL

function createWindow() {
  const win = new BrowserWindow({
    width: 960, height: 720,
    minWidth: 800, minHeight: 600,
    title: 'FunPod',
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#11111b',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    show: false,
  })

  win.on('ready-to-show', () => win.show())

  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL)
  } else {
    win.loadFile(path.join(process.env.DIST, 'index.html'))
  }
}

app.whenReady().then(createWindow)
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })

ipcMain.handle('store:get', (_e, key) => store.get(key))
ipcMain.handle('store:set', (_e, key, val) => { store.set(key, val); return true })

ipcMain.handle('runpod:gql', async (_e, query, variables) => {
  const apiKey = store.get('apiKey')
  if (!apiKey) return { error: 'No API key set' }
  try {
    const res = await fetch(`https://api.runpod.io/graphql?api_key=${apiKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, variables }),
    })
    const json = await res.json()
    if (json.errors) return { error: json.errors[0].message }
    return { data: json.data }
  } catch (e) {
    return { error: e.message }
  }
})

ipcMain.handle('shell:open', (_e, url) => shell.openExternal(url))
ipcMain.handle('window:minimize', (e) => BrowserWindow.fromWebContents(e.sender)?.minimize())
ipcMain.handle('window:close', (e) => BrowserWindow.fromWebContents(e.sender)?.close())
