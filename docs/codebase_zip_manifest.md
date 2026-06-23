# Codebase Zipping Manifest for Remote Analysis

This document outlines the manifest of necessary codebase files and folders required for remote analysis of `the-ai-counsel`. It lists what should be included, what must be excluded (to prevent leaking API keys, credentials, and uploading large dependencies), and provides copy-paste commands to perform the zipping.

---

## 1. Directory Exclusion & Inclusion Rules

When zipping the project for remote analysis, you must omit local dependencies, caches, git history, and local user data (especially the `data/` directory which contains settings with active API keys).

### Exclude List
*   **Caches:** `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`
*   **Dependencies:** `.venv/`, `node_modules/`, `frontend/node_modules/`, `*.egg-info/`
*   **Data & Logs:** `data/` (contains local database and `settings.json` with **API keys**!), `logs/`, `.runtime-logs/`
*   **Version Control:** `.git/`

---

## 2. Codebase Manifest

### Required Files & Directories
*   `backend/` — Python backend engine (endpoints, routing, pricing, providers).
*   `frontend/` — React frontend interface (components, styles, package.json).
*   `electron/` — Desktop wrapper files.
*   `scripts/` & `skills/` — Custom shell scripts and agent configurations.
*   **Root Configs:** `pyproject.toml`, `uv.lock`, `package.json`, `AGENTS.md`, `README.md`, `CHANGELOG.md`, `start.sh`

---

## 3. Zipping Commands

Run these commands from the root of `the-ai-counsel` directory:

### Option A: PowerShell (Windows)
```powershell
Compress-Archive -Path backend, frontend, electron, scripts, skills, pyproject.toml, uv.lock, package.json, AGENTS.md, README.md, CHANGELOG.md, start.sh -DestinationPath the_ai_counsel_codebase.zip -Force
```

*To compress dynamically while automatically omitting caches and virtual envs in PowerShell:*
```powershell
Get-ChildItem -Path . -Recurse | 
  Where-Object { 
    $_.FullName -notmatch 'node_modules|venv|__pycache__|data|\.git|\.ruff_cache|\.pytest_cache' 
  } | 
  Compress-Archive -DestinationPath the_ai_counsel_clean.zip -Force
```

### Option B: Bash (macOS/Linux)
```bash
zip -r the_ai_counsel_clean.zip . -x "node_modules/*" "frontend/node_modules/*" ".venv/*" "data/*" ".git/*" "*/__pycache__/*" ".ruff_cache/*" ".pytest_cache/*" ".runtime-logs/*"
```
