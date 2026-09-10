[ ! -d "${UV_PROJECT}/.venv" ] && uv venv ${UV_PROJECT}/.venv

uv sync --dev