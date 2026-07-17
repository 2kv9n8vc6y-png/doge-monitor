const { app, BrowserWindow, shell, session } = require('electron');
const fs = require('fs');
const path = require('path');

const smokeTest = process.argv.includes('--smoke-test');
const smokeOutputArg = process.argv.find(arg => arg.startsWith('--smoke-output='));

function smokeOutputPath() {
  if (smokeOutputArg) return smokeOutputArg.slice('--smoke-output='.length);
  return path.join(app.getPath('temp'), 'doge-dashboard-smoke.json');
}

function finishSmoke(exitCode, result) {
  try {
    fs.writeFileSync(smokeOutputPath(), JSON.stringify(result, null, 2), 'utf8');
  } catch (_) {}
  app.exit(exitCode);
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    show: !smokeTest,
    autoHideMenuBar: true,
    backgroundColor: '#0a0a1a',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  });

  const dashboardPath = app.isPackaged
    ? path.join(process.resourcesPath, 'pc-dashboard.html')
    : path.join(__dirname, '..', 'pc-dashboard.html');

  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://')) shell.openExternal(url);
    return { action: 'deny' };
  });
  win.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith('file:')) event.preventDefault();
  });

  if (smokeTest) {
    const timeout = setTimeout(() => {
      finishSmoke(2, { ok: false, reason: 'dashboard load timeout' });
    }, 30000);

    win.webContents.once('did-fail-load', (_event, code, description) => {
      clearTimeout(timeout);
      finishSmoke(2, { ok: false, reason: description, code });
    });
    win.webContents.once('did-finish-load', () => {
      setTimeout(async () => {
        try {
          const result = await win.webContents.executeJavaScript(`(() => ({
            title: document.title,
            price: document.getElementById('price')?.textContent?.trim() || '',
            status: document.getElementById('wsStatus')?.textContent?.trim() || '',
            signal: document.getElementById('signalHeadline')?.textContent?.trim() || '',
            signalPanelPresent: Boolean(document.getElementById('signalPanel'))
          }))()`);
          clearTimeout(timeout);
          const ok = result.signalPanelPresent && result.price && result.price !== '---';
          finishSmoke(ok ? 0 : 2, { ok, ...result });
        } catch (error) {
          clearTimeout(timeout);
          finishSmoke(2, { ok: false, reason: error.message });
        }
      }, 12000);
    });
  }

  win.loadFile(dashboardPath);
  return win;
}

app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
