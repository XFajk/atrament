from pathlib import Path

import platformdirs
from filelock import FileLock

USER_DATA_PATH = platformdirs.user_data_path("Atrament")

# Format: project_name, last_time_edited(YYYY-MM-DD), project_dir
PROJECT_TRACKER_FILE: Path = USER_DATA_PATH / "project_tracker.txt"

PROJECT_TRACKER_LOCK = FileLock(
    PROJECT_TRACKER_FILE.with_suffix(PROJECT_TRACKER_FILE.suffix + ".lock"),
    timeout=5,
)

USER_SETTINGS_FILE: Path = USER_DATA_PATH / "user_settings.json"

USER_SETTINGS_LOCK = FileLock(
    USER_SETTINGS_FILE.with_suffix(USER_SETTINGS_FILE.suffix + ".lock"),
    timeout=5,
)

DEFAULT_SETTINGS = {
    "ChatGPT": {
        "api-key": None,
    },
    "Claude": {"api-key": None},
}
