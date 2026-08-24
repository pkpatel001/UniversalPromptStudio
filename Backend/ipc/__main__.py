"""Run the application IPC server over standard input/output."""

from .server import serve_stdio

raise SystemExit(serve_stdio())

