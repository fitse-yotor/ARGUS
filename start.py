"""Set up and start ARGUS locally with `python start.py`."""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
NPM = shutil.which("npm.cmd" if os.name == "nt" else "npm")


def run(*command):
    print("+", " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if sys.version_info < (3, 11):
        raise SystemExit("ARGUS requires Python 3.11 or newer.")
    if not NPM:
        raise SystemExit("Node.js and npm are required. Install Node 22.12+ and try again.")

    if not PYTHON.exists():
        print("Creating local Python environment...", flush=True)
        venv.EnvBuilder(with_pip=True).create(VENV)

    requirements = ROOT / "requirements.txt"
    python_stamp = VENV / ".argus-requirements"
    requirements_hash = digest(requirements)
    if not python_stamp.exists() or python_stamp.read_text() != requirements_hash:
        run(PYTHON, "-m", "pip", "install", "-r", requirements)
        python_stamp.write_text(requirements_hash)

    frontend = ROOT / "frontend"
    node_stamp = frontend / "node_modules" / ".argus-package-lock"
    lock_hash = digest(frontend / "package-lock.json")
    if not node_stamp.exists() or node_stamp.read_text() != lock_hash:
        run(NPM, "ci", "--prefix", "frontend")
        node_stamp.write_text(lock_hash)

    env_file = ROOT / ".env"
    if not env_file.exists():
        shutil.copyfile(ROOT / ".env.example", env_file)
        print("Created .env from .env.example", flush=True)

    run(PYTHON, "scripts/init_db.py")
    run(PYTHON, "scripts/download_model.py")
    print("Starting ARGUS. Press Ctrl+C to stop all services.", flush=True)
    try:
        return subprocess.call([str(PYTHON), "scripts/dev.py"], cwd=ROOT)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"Setup stopped: {error}") from error
