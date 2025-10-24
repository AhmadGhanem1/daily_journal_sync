import os
import json
import socket
import threading

from . import config

class SocketCommandServer:
    """
    Small Unix domain socket server.
    Protocol: one JSON object per connection, e.g. {"cmd":"add","msg":"note"}
    """

    def __init__(self, socket_path: str, submit_fn, logger):
        self.socket_path = socket_path
        self._submit = submit_fn
        self._logger = logger
        self._stop_evt = threading.Event()
        self._thread = None
        self._srv_sock = None

    def _cleanup_socket_file(self):
        try:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
        except OSError as e:
            self._logger.warning("Failed to unlink stale socket: %s", e)

    def _handle_conn(self, conn):
        try:
            data = conn.recv(4096)
            if not data:
                return
            text = data.decode("utf-8").strip()
            try:
                obj = json.loads(text)
                cmd = obj.get("cmd")
                msg = obj.get("msg", "").strip()
            except json.JSONDecodeError:
                if text.upper().startswith("ADD "):
                    cmd = "add"
                    msg = text[4:].strip()
                else:
                    cmd = None
                    msg = ""
            if cmd == "add" and msg:
                self._submit(msg)
                resp = {"ok": True, "message": "queued"}
            else:
                resp = {"ok": False, "error": "invalid command"}
            conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
        except Exception as e:
            self._logger.warning("Socket handler error: %s", e)
        finally:
            conn.close()

    def _serve_loop(self):
        self._cleanup_socket_file()
        self._srv_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._srv_sock.bind(self.socket_path)
        os.chmod(self.socket_path, 0o666)
        self._srv_sock.listen(5)
        self._logger.info("Socket server listening on %s", self.socket_path)
        while not self._stop_evt.is_set():
            try:
                self._srv_sock.settimeout(0.5)
                conn, _ = self._srv_sock.accept()
            except socket.timeout:
                continue
            threading.Thread(target=self._handle_conn, args=(conn,), daemon=True).start()
        self._logger.info("Socket server stopped.")

    def start(self):
        self._thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_evt.set()
        try:
            if self._srv_sock:
                self._srv_sock.close()
        except Exception:
            pass
        try:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
        except Exception:
            pass
        if self._thread:
            self._thread.join(timeout=2)
