const { spawn } = require('child_process');
const http = require('http');
const https = require('https');

function isChildRunning(child) {
  return !!(child && child.pid && child.exitCode === null && !child.killed);
}

function localPortFromUrl(urlText) {
  try {
    const parsed = new URL(urlText);
    const host = parsed.hostname.replace(/^\[|\]$/g, '').toLowerCase();
    if (!['127.0.0.1', 'localhost', '::1', '0.0.0.0', '::'].includes(host)) {
      return null;
    }
    if (parsed.port) return Number(parsed.port);
    return parsed.protocol === 'https:' ? 443 : 80;
  } catch (_error) {
    return null;
  }
}

function runCaptured(command, args) {
  return new Promise(resolve => {
    const child = spawn(command, args, {
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', data => { stdout += data.toString(); });
    child.stderr.on('data', data => { stderr += data.toString(); });
    child.on('error', error => resolve({ code: -1, stdout, stderr, error }));
    child.on('close', code => resolve({ code, stdout, stderr, error: null }));
  });
}

async function findWindowsListenerPids(urlText) {
  const port = localPortFromUrl(urlText);
  if (!port) return [];

  const result = await runCaptured('netstat.exe', ['-ano', '-p', 'tcp']);
  if (result.code !== 0) return [];

  const pids = new Set();
  for (const line of result.stdout.split(/\r?\n/)) {
    const fields = line.trim().split(/\s+/);
    if (fields.length < 5 || fields[0].toUpperCase() !== 'TCP') continue;
    if (fields[3].toUpperCase() !== 'LISTENING') continue;
    const portMatch = fields[1].match(/:(\d+)$/);
    if (!portMatch || Number(portMatch[1]) !== port) continue;
    const pid = Number(fields[4]);
    if (Number.isInteger(pid) && pid > 0 && pid !== process.pid) pids.add(pid);
  }
  return [...pids];
}

async function getWindowsProcessInfo(pid) {
  const command = [
    '-NoProfile',
    '-NonInteractive',
    '-Command',
    `$p=Get-CimInstance Win32_Process -Filter "ProcessId=${Number(pid)}"; ` +
      'if($p){$p | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress}',
  ];
  const result = await runCaptured('powershell.exe', command);
  if (result.code !== 0 || !result.stdout.trim()) return null;
  try {
    return JSON.parse(result.stdout.trim());
  } catch (_error) {
    return null;
  }
}

function processMatchesService(processInfo, name) {
  const commandLine = String(processInfo?.CommandLine || '');
  if (name === 'backend') return /(?:^|\s)-m\s+backend\.main(?:\s|$)/i.test(commandLine);
  if (name === 'notion2api') return /(?:^|\s)-m\s+uvicorn\s+app\.server:app(?:\s|$)/i.test(commandLine);
  if (name === 'frontend') {
    return /(?:vite(?:\.js)?|npm(?:\.cmd)?\s+run\s+dev)/i.test(commandLine);
  }
  return false;
}

async function findWindowsManagedRootPid(listenerPid, name) {
  let currentPid = Number(listenerPid);
  let managedRootPid = currentPid;
  const visited = new Set();

  for (let depth = 0; depth < 10 && currentPid > 4 && !visited.has(currentPid); depth += 1) {
    visited.add(currentPid);
    const processInfo = await getWindowsProcessInfo(currentPid);
    if (!processInfo) break;
    if (String(processInfo.Name || '').toLowerCase() === 'electron.exe') break;
    if (processMatchesService(processInfo, name)) managedRootPid = currentPid;
    currentPid = Number(processInfo.ParentProcessId || 0);
  }

  return managedRootPid;
}

async function killWindowsProcessTree(pid) {
  return runCaptured('taskkill.exe', ['/pid', String(pid), '/T', '/F']);
}

function isUrlAvailable(urlText, timeoutMs = 1200) {
  return new Promise(resolve => {
    const client = urlText.startsWith('https:') ? https : http;
    const request = client.get(urlText, response => {
      response.resume();
      resolve(true);
    });
    request.on('error', () => resolve(false));
    request.setTimeout(timeoutMs, () => {
      request.destroy();
      resolve(false);
    });
  });
}

async function waitForUrlUnavailable(urlText, timeoutMs = 12000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (!(await isUrlAvailable(urlText))) return true;
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  return !(await isUrlAvailable(urlText));
}

async function stopService({ child, name, url, log = () => {} }) {
  const killedPids = new Set();

  if (isChildRunning(child)) {
    log(`Stopping ${name} child tree (pid=${child.pid})`);
    if (process.platform === 'win32') {
      const result = await killWindowsProcessTree(child.pid);
      if (result.code !== 0 && isChildRunning(child)) {
        log(`Failed to stop ${name} child tree: taskkill exited with code ${result.code}`);
      }
      killedPids.add(child.pid);
    } else {
      try {
        process.kill(-child.pid, 'SIGTERM');
      } catch (error) {
        log(`Failed to stop ${name} child tree: ${error.message}`);
      }
    }
  }

  if (process.platform === 'win32' && url) {
    const listenerPids = await findWindowsListenerPids(url);
    for (const listenerPid of listenerPids) {
      const rootPid = await findWindowsManagedRootPid(listenerPid, name);
      if (killedPids.has(rootPid)) continue;
      log(
        `Stopping ${name} listener at ${url} ` +
        `(listener pid=${listenerPid}, managed root pid=${rootPid})`,
      );
      const result = await killWindowsProcessTree(rootPid);
      if (result.code !== 0) {
        log(
          `Failed to stop ${name} managed root pid=${rootPid}: ` +
          `taskkill exited with code ${result.code}`,
        );
      }
      killedPids.add(rootPid);
    }
  }

  if (url) {
    const stopped = await waitForUrlUnavailable(url);
    if (!stopped) {
      throw new Error(`${name} remained reachable at ${url} after shutdown`);
    }
  }
}

module.exports = {
  findWindowsListenerPids,
  findWindowsManagedRootPid,
  isChildRunning,
  isUrlAvailable,
  localPortFromUrl,
  processMatchesService,
  stopService,
  waitForUrlUnavailable,
};
