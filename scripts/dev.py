"""Run API, worker, live camera service, and frontend; Ctrl+C stops them."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
NPM = shutil.which("npm.cmd" if os.name == "nt" else "npm")


def main():
    if not NPM:
        raise SystemExit("npm was not found on PATH")
    commands = [
        [sys.executable, "-m", "uvicorn", "backend.argus.main:app", "--host", "127.0.0.1", "--port", "8000"],
        [sys.executable, "-m", "backend.argus.worker"],
        [sys.executable, "-m", "backend.argus.live"],
        [NPM, "run", "dev", "--prefix", "frontend"],
    ]
    names = ["API", "vision worker", "live camera service", "frontend"]
    processes = []
    try:
        for command in commands:
            processes.append(subprocess.Popen(command, cwd=ROOT))
        print("ARGUS: http://127.0.0.1:5173 | API: http://127.0.0.1:8000/docs", flush=True)
        while True:
            for name, process in zip(names, processes):
                if process.poll() is not None:
                    print(f"{name} exited with code {process.returncode}; stopping ARGUS.", flush=True)
                    return process.returncode or 1
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
