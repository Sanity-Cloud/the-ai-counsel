const test = require('node:test');
const assert = require('node:assert/strict');

const {
  localPortFromUrl,
  processMatchesService,
} = require('./process-control');

test('localPortFromUrl accepts managed loopback URLs', () => {
  assert.equal(localPortFromUrl('http://127.0.0.1:8001/api/health'), 8001);
  assert.equal(localPortFromUrl('http://localhost:5173'), 5173);
  assert.equal(localPortFromUrl('http://[::1]:8120/v1'), 8120);
  assert.equal(localPortFromUrl('https://127.0.0.1/health'), 443);
});

test('localPortFromUrl rejects remote hosts and malformed URLs', () => {
  assert.equal(localPortFromUrl('https://example.com:8120/v1'), null);
  assert.equal(localPortFromUrl('not a url'), null);
});

test('processMatchesService recognizes managed launcher commands', () => {
  assert.equal(processMatchesService({ CommandLine: 'uv.exe run python -m backend.main' }, 'backend'), true);
  assert.equal(processMatchesService({ CommandLine: 'python -m uvicorn app.server:app --port 8120' }, 'notion2api'), true);
  assert.equal(processMatchesService({ CommandLine: 'cmd.exe /c npm.cmd run dev -- --host 127.0.0.1' }, 'frontend'), true);
  assert.equal(processMatchesService({ CommandLine: 'node vite/bin/vite.js --host 127.0.0.1' }, 'frontend'), true);
});

test('processMatchesService does not claim unrelated processes', () => {
  assert.equal(processMatchesService({ CommandLine: 'python unrelated.py' }, 'backend'), false);
  assert.equal(processMatchesService({ CommandLine: 'electron .' }, 'frontend'), false);
});
