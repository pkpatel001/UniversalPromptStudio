# Developer Onboarding

## Backend

Install Python 3.12 and development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run checks:

```powershell
python -m compileall Backend
python -m pytest Tests
python -m ruff check Backend Tests
python -m mypy Backend
```

## Frontend

The frontend shell is prepared for Vite, Tailwind CSS, and Tauri.

