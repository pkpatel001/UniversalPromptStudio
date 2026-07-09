Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

python -m compileall Backend Tests
python -m pytest Tests

