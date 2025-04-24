import logging.config
import os
from datetime import date, timedelta

if not os.path.isdir("logs"):
    os.mkdir("logs")

get_current_date = date.today()
log_file_path = "logs/" + str(get_current_date) + ".log"

def delete_old_logs(directory, days=30):
    current_time = date.today()
    cutoff_time = current_time - timedelta(days=days)
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            file_date = date.fromisoformat(filename.split('.')[0])
            if file_date < cutoff_time:
                os.remove(file_path)
                print(f"Deleted old log file: {file_path}")

# Delete logs older than 30 days
delete_old_logs("logs")
def logger():
    """
    Creates a rotating log
    """
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,  # Allow modifying existing loggers
        "formatters": {
            "simple": {
                "format": "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
                "datefmt": "%d/%m/%Y %H:%M:%S",
            },
        },
        "handlers": {
            "RotatingFileHandler": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",  # Prevent debug logs in the file
                "formatter": "simple",
                "filename": log_file_path,
                "backupCount": 10,
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["RotatingFileHandler"],
                "level": "INFO",  # Prevent debug messages globally
                "propagate": False,
            },
            "h5py": {  # Suppress h5py logs
                "handlers": ["RotatingFileHandler"],
                "level": "WARNING",  # Show only warnings/errors
                "propagate": False,
            },
            "watchdog": {  # Suppress watchdog logs
                "handlers": ["RotatingFileHandler"],
                "level": "WARNING",  # Show only warnings/errors
                "propagate": False,
            },
            "watchdog.observers.inotify_buffer": {  # Specific suppression
                "handlers": ["RotatingFileHandler"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(LOGGING_CONFIG)
    logging.captureWarnings(True)

    # Explicitly suppress logs after configuring dictConfig
    logging.getLogger("h5py").setLevel(logging.WARNING)
    logging.getLogger("h5py._conv").setLevel(logging.WARNING)  # Additional submodule
    logging.getLogger("watchdog").setLevel(logging.WARNING)  # Suppress watchdog logs
    logging.getLogger("watchdog.observers.inotify_buffer").setLevel(logging.WARNING)  # Suppress inotify_buffer logs

    return logging
