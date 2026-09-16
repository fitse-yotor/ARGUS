"""Start API, durable worker, live camera service and frontend together; Ctrl-C stops all four."""
import subprocess,sys,time,signal
from pathlib import Path
root=Path(__file__).resolve().parents[1]
commands=[[sys.executable,'-m','uvicorn','backend.argus.main:app','--host','127.0.0.1','--port','8000'],[sys.executable,'-m','backend.argus.worker'],[sys.executable,'-m','backend.argus.live'],['npm','run','dev','--prefix','frontend']]
processes=[]
try:
    for command in commands:processes.append(subprocess.Popen(command,cwd=root))
    print('ARGUS: http://127.0.0.1:5173 · API: http://127.0.0.1:8000/docs',flush=True)
    while all(p.poll() is None for p in processes):time.sleep(1)
except KeyboardInterrupt:pass
finally:
    for p in processes:
        if p.poll() is None:p.terminate()
    for p in processes:
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill()
