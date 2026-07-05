# Starts the NEXUS web interface. Backend (python scripts/run_api.py) must be
# running separately on port 8400.
Write-Host "Starting NEXUS web interface on http://localhost:5173" -ForegroundColor Cyan
Write-Host "(make sure the backend is running: python scripts/run_api.py)" -ForegroundColor DarkGray
if (-not (Test-Path node_modules)) { npm install }
npm run dev
