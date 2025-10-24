import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
import subprocess
import os
from . import config
from . import weather as weather_mod

class JournalWriter:
    def __init__(self, repo: Path, with_weather: bool, queue):
        self.repo = Path(repo).resolve()
        self.entries_dir = self.repo / config.ENTRIES_DIRNAME
        self.logs_dir = self.repo / config.LOGS_DIRNAME
        self.with_weather = with_weather
        self.queue = queue
        self._logger = None
        self._ensure_dirs()
        self._setup_logging()

    def _ensure_dirs(self):
        """Make sure entries/ and logs/ directories exist."""
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self):
        """Configure rotating file logging."""
        log_path = self.logs_dir / config.LOG_FILE_NAME
        handler = RotatingFileHandler(
            log_path,
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT
        )
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s [writer] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(fmt)
        logger = logging.getLogger("daily_journal_writer")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        self._logger = logger
        self._logger.info("Writer initialized. repo=%s with_weather=%s", self.repo, self.with_weather)

    def _today_md_path(self):
        today = datetime.now().strftime(config.DATE_FMT)
        return self.entries_dir / f"{today}.md"

    def _ensure_header(self, md_path: Path):
        """Create file and header if it doesn't exist."""
        if not md_path.exists() or md_path.stat().st_size == 0:
            header_lines = [f"# {md_path.stem}"]
            if self.with_weather:
                try:
                    header_lines.append(weather_mod.get_weather())
                except Exception as e:
                    self._logger.warning("Weather fetch failed: %s", e)
            header = "\n".join(header_lines).strip() + "\n\n"
            md_path.write_text(header, encoding="utf-8")
            self._logger.info("Created header in %s", md_path)

    def _append_note(self, md_path: Path, message: str):
        """Append timestamped note."""
        ts = datetime.now().strftime(config.TIME_FMT)
        line = f"- {ts} {message}\n"
        with md_path.open("a", encoding="utf-8") as f:
            f.write(line)
        self._logger.info("Appended note (%d bytes)", len(line.encode("utf-8")))





    def _maybe_trigger_push(self, md_path: Path):
        """Check file size and fork a child process to run push.sh if >= 10 KB."""
        try:
            size = md_path.stat().st_size
        except FileNotFoundError:
            return

        if size >= config.MAX_MD_SIZE_BYTES:
            self._logger.info("File size %d ≥ threshold — forking push.sh", size)
            push_script = self.repo / "push.sh"
            if not push_script.exists():
                self._logger.warning("push.sh not found — skipping git push")
                return

            try:
                pid = os.fork()  # 🔹 fork a child process
                if pid == 0:
                    # child executes push.sh
                    os.execv("/bin/bash", ["/bin/bash", str(push_script)])
                else:
                    self._logger.info("Forked child PID %d to run push.sh", pid)
            except OSError as e:
                self._logger.error("Fork failed: %s", e)

















    def run(self):
        """Main loop reading from the queue and writing to files."""
        self._logger.info("Writer loop started.")
        while True:
            message = self.queue.get()  # blocks until a message arrives
            if message is None:
                self._logger.info("Shutdown signal received.")
                break
            try:
                md_path = self._today_md_path()
                self._ensure_header(md_path)
                self._append_note(md_path, message)
                self._maybe_trigger_push(md_path)
            except Exception as e:
                self._logger.exception("Failed to process message: %s", e)
        self._logger.info("Writer loop exited.")
