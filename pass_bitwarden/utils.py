import logging
import subprocess
from argparse import ArgumentTypeError
from pathlib import Path

logger = logging.getLogger(__name__)


def non_existing_file(path: str) -> Path:
    path_ = Path(path)
    if path_.exists():
        raise ArgumentTypeError(f"Given path already exists -> {path_} .")
    return path_


def short_name(filepath: Path) -> str:
    return f"{filepath.parent.name}/{filepath.stem}"


def catch_and_log_exception(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

    return wrapper


@catch_and_log_exception
def decode_gpg_file(filepath: Path) -> str:
    short_name_ = short_name(filepath)
    cmd = ["gpg", "--decrypt", "--batch", str(filepath)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise ValueError(f"Failed to decrypt -> {short_name_} .")
    if result.stdout == "":
        raise ValueError(f"Empty decrypted content -> {short_name_} .")

    logger.info(f"Decrypted GPG file -> {short_name_} .")
    return result.stdout
