"""
IELTS Vocabulary Project Manager
NSSM-managed service - monitors and keeps project processes alive.
"""
import subprocess
import time
import os
import sys
import signal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
LOG_DIR = r"D:\logs"
BACKEND_LOG = os.path.join(LOG_DIR, "ielts-vocab-backend.log")
FRONTEND_LOG = os.path.join(LOG_DIR, "ielts-vocab-frontend.log")
PROJECT_LOG = os.path.join(LOG_DIR, "ielts-vocab.log")
PYTHON_EXE = r"D:\Program Files\Python\python.exe"

RUNNING = True
MANAGER_PID = os.getpid()

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    sys.stdout.flush()
    try:
        with open(PROJECT_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass

def kill_proc_tree(pid):
    """Kill a process and all its children."""
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                      capture_output=True,
                      creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
    except:
        pass

def get_port_in_use(port):
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except ConnectionRefusedError:
        return True  # Port is in LISTEN state but refused (shouldn't happen)
    except Exception:
        return False

class ProjectManager:
    def __init__(self):
        self.backend_proc = None
        self.frontend_proc = None

    def cleanup(self):
        log("Cleaning up...")
        for name, proc in [("backend", self.backend_proc), ("frontend", self.frontend_proc)]:
            if proc:
                try:
                    kill_proc_tree(proc.pid)
                    log(f"[{name}] Stopped")
                except:
                    pass

    def start_backend(self):
        """Start the Flask/SocketIO backend."""
        log("Starting backend...")
        cmd = [PYTHON_EXE, os.path.join(BACKEND_DIR, "app.py")]
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        try:
            self.backend_proc = subprocess.Popen(
                cmd,
                cwd=BACKEND_DIR,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                env=os.environ.copy()
            )
            log(f"[backend] Started PID={self.backend_proc.pid}")
            return True
        except Exception as e:
            log(f"[backend] Failed: {e}")
            return False

    def start_frontend(self):
        """Start the Vite preview server."""
        log("Starting frontend...")
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        try:
            self.frontend_proc = subprocess.Popen(
                ["pnpm", "run", "preview"],
                cwd=BASE_DIR,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                env=os.environ.copy()
            )
            log(f"[frontend] Started PID={self.frontend_proc.pid}")
            return True
        except Exception as e:
            log(f"[frontend] Failed: {e}")
            return False

    def check_backend(self):
        """Check if backend is alive."""
        if self.backend_proc is None:
            return False
        ret = self.backend_proc.poll()
        return ret is None

    def check_frontend(self):
        """Check if frontend is alive."""
        if self.frontend_proc is None:
            return False
        return self.frontend_proc.poll() is None

    def health_check(self):
        """Check health of all services."""
        backend_ok = get_port_in_use(5000)
        frontend_ok = get_port_in_use(3002)
        return backend_ok, frontend_ok

    def run(self):
        log("=" * 50)
        log("IELTS Vocabulary Project Manager Started")
        log("=" * 50)

        os.makedirs(LOG_DIR, exist_ok=True)

        # Initial start
        self.start_backend()
        time.sleep(3)
        self.start_frontend()
        time.sleep(2)

        check_count = 0
        while RUNNING:
            time.sleep(10)
            check_count += 1

            backend_ok, frontend_ok = self.health_check()

            # Restart dead processes
            if not backend_ok:
                log("[backend] Not responding, restarting...")
                if self.backend_proc:
                    kill_proc_tree(self.backend_proc.pid)
                self.backend_proc = None
                self.start_backend()
                time.sleep(3)

            if not frontend_ok:
                log("[frontend] Not responding, restarting...")
                if self.frontend_proc:
                    kill_proc_tree(self.frontend_proc.pid)
                self.frontend_proc = None
                self.start_frontend()
                time.sleep(2)

            if check_count % 6 == 0:  # Every minute
                log(f"Health OK - backend:{backend_ok} frontend:{frontend_ok}")

        self.cleanup()
        log("Project Manager stopped")


def signal_handler(signum, frame):
    global RUNNING
    log("Received shutdown signal")
    RUNNING = False


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    manager = ProjectManager()
    try:
        manager.run()
    except KeyboardInterrupt:
        log("Interrupted")
        manager.cleanup()
    except Exception as e:
        log(f"FATAL: {e}")
        import traceback
        traceback.print_exc()
        manager.cleanup()
        sys.exit(1)
