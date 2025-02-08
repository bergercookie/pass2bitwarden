#!/usr/bin/env python3
from pathlib import Path
import sys


def find_gpg_only_dirs(root_dir):
    result = []

    for subdir in root_dir.iterdir():
        if subdir.is_dir():
            files = list(subdir.iterdir())  # Get all items in the directory
            if files and all(
                f.is_file() and f.suffix == ".gpg" for f in files
            ):  # Ensure all files are .gpg
                result.append(subdir)

    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <root_directory>")
        sys.exit(1)

    root_directory = Path(sys.argv[1]).resolve()

    if not root_directory.is_dir():
        print("Error: Provided path is not a directory")
        sys.exit(1)

    matching_dirs = find_gpg_only_dirs(root_directory)

    for d in matching_dirs:
        print(d)
