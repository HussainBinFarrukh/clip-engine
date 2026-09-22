$ErrorActionPreference = "Stop"

$nodeCandidates = @(@(
    (Get-Command node -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.19.0-win-x64\node.exe"
) | Where-Object { $_ -and (Test-Path $_) })

$npmCandidates = @(@(
    (Get-Command npm.cmd -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.19.0-win-x64\npm.cmd"
) | Where-Object { $_ -and (Test-Path $_) })

if (-not $nodeCandidates -or -not $npmCandidates) {
    throw "Node.js/npm were not found. Install Node.js LTS before running web checks."
}

$nodeDir = Split-Path -Parent $nodeCandidates[0]
$env:Path = "$nodeDir;$env:Path"
$npm = $npmCandidates[0]

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Python virtual environment not found. Create it and install requirements before running Python checks."
}

& $npm --workspace @clip-engine/web test
& $npm --workspace @clip-engine/web run lint
& $npm --workspace @clip-engine/web run format
& .\.venv\Scripts\python.exe -m pytest
& .\.venv\Scripts\python.exe -m ruff check apps\api workers
