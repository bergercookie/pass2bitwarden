#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "bubop"
# ]
# ///

"""
Export notes / text files from the Standard UNIX Password Manager to Bitwarden.

The card information should be stored in the following format. Each given GPG encrypted file,
either specified explicitly or found under the specified directory is considered a different
note and is added to Bitwarden as such.
"""

import json
import logging
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Literal
from pass_bitwarden import non_existing_file, short_name, decode_gpg_file

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def export_note(note_path: Path) -> dict[str, Any]:
    short_name_ = short_name(note_path)
    logger.info(f"Exporting note details from -> {short_name_} ...")

    name = (
        note_path.with_suffix("")
        .name.replace(".", " ")
        .replace("-", " ")
        .replace("_", " ")
        .capitalize()
    )

    fields = []
    notes = decode_gpg_file(note_path)

    dict_: dict[str, Any] = {
        "type": 2,
        "reprompt": 0,
        "name": name,
        "notes": notes,
        "secureNote": {
            "type": 0
        },
        "favorite": False,
        "fields": fields,
        "card": None,
    }
    logger.info(f"Exported note details from -> {short_name_} .")

    return dict_


def main():
    parser = ArgumentParser(description=__doc__)

    parser.add_argument(
        "-i",
        "--inputs",
        nargs="+",
        help=(
            "Path to the note details directories to  traverse and/or note GPG files."
        ),
        dest="inputs",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Bitwarden-compatible output JSON file to write the notes to",
        required=True,
        type=non_existing_file,
    )

    parser.add_argument(
        "--reprompt",
        help="Reprompt before viewing the note details in Bitwarden",
        action="store_true",
    )

    args = parser.parse_args()
    inputs = args.inputs
    output_path = args.output
    reprompt = args.reprompt

    num_notes = 0

    # find all the GPG files to export to Bitwarden
    input_dirs = [input_ for input_ in inputs if input_.is_dir()]
    input_files = [input_ for input_ in inputs if input_.is_file()]
    input_files.extend([file_ for dir_ in input_dirs for file_ in dir_.rglob("*.gpg")])

    # proceed with the export
    output_dict = {"items": []}
    for note in input_files:
        dict_section = export_note(note)
        if reprompt:
            dict_section["reprompt"] = 1
        output_dict["items"].append(dict_section)
        num_notes += 1

    with output_path.open("w") as f:
        json.dump(output_dict, f, indent=4, ensure_ascii=False)
    logger.info(f"Successfully wrote {num_notes} notes to -> {output_path} .")

    return 0


if __name__ == "__main__":
    sys.exit(main())
