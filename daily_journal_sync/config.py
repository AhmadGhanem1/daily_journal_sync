from pathlib import Path
import os 


SOCKET_PATH = "/tmp/daily_journal_sync.sock"

DEFAULT_REPO = Path.cwd()
ENTRIES_DIRNAME = "entries"
LOGS_DIRNAME = "logs"

MAX_MD_SIZE_BYTES = 10 * 1024  # 10 KB threshold
DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%H:%M"

LOG_FILE_NAME = "app.log"
LOG_MAX_BYTES = 256 * 1024
LOG_BACKUP_COUNT = 3
SERVICE_NAME = "myApp"
