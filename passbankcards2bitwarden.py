#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "bubop"
# ]
# ///

"""
Export bank card details from the Standard UNIX Password Manager to Bitwarden.

The card information should be stored in the following format

```
bank-card-name/
├── number.gpg # bank card number
├── ccv.gpg # bank card ccv
├── date.gpg # bank card expiry
├── pin.gpg # bank card pin
└── name.gpg # bank card owner name
```


This will populate the number , ccv, expiry fields in Bitwarden and will create a new hidden
field for the pin in each one of the cards.

## Notes

* The pin.gpg file is optional. If it's not there, the custom field will not be created.
* The date.gpg file should have the expiry date in the format `MM/YY`.
* The name of the card item that will be added to Bitwarden will be the name of the directory,
  capitalized and with "-", and "_" replaced with spaces.
"""

import json
import logging
import subprocess
import sys
from argparse import ArgumentParser, ArgumentTypeError
from pathlib import Path
from typing import Any, Literal

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
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


def determine_card_type(card_number: str) -> Literal["Visa", "Mastercard", "Amex", ""]:
    """Determine the type of the card based on the card number.

    If no match is found, an empty string is returned.
    """
    if card_number.startswith("4") and len(card_number) in [13, 16]:
        return "Visa"
    elif card_number.startswith("5") and len(card_number) == 16:
        return "Mastercard"
    elif (
        card_number.startswith("34")
        or card_number.startswith("37")
        and len(card_number) == 15
    ):
        return "Amex"
    else:
        return ""


def export_bank_card(dir_path: Path) -> dict[str, Any]:
    def _decode(fname: str) -> str:
        return decode_gpg_file(dir_path / f"{fname}.gpg").strip()

    short_name_ = short_name(dir_path)
    logger.info(f"Exporting bank card details from -> {short_name_} ...")

    card_name = dir_path.name.replace("-", " ").replace("_", " ").capitalize()

    # read the contents of the gpg files
    number = _decode("number")
    ccv = _decode("ccv")
    month, year = _decode("date").split("/")
    name = _decode("name")

    if (dir_path / "pin.gpg").is_file():
        fields = [
            {
                "name": "pin",
                "value": _decode("pin"),
                "type": 1,
            }
        ]
    else:
        fields = []

    dict_: dict[str, Any] = {
        "type": 3,
        "reprompt": 0,
        "name": card_name,
        "notes": None,
        "favorite": False,
        "fields": fields,
        "card": {
            "cardholderName": name,
            "number": number,
            "expMonth": month,
            "expYear": year,
            "code": ccv,
            "brand": determine_card_type(number),
        },
    }
    logger.info(f"Exported bank card details from -> {short_name_} .")

    return dict_


def main():
    parser = ArgumentParser(description=__doc__)

    parser.add_argument(
        "-d",
        "--input-dirs",
        nargs="+",
        help=(
            "Path to the bank card directories."
            "These should have the right gpg files directly under them."
        ),
        dest="dirs",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Bitwarden-compatible output JSON file to write the passwords to",
        required=True,
        type=non_existing_file,
    )

    args = parser.parse_args()
    input_dirs = args.dirs
    output_path = args.output

    num_cards = len(input_dirs)

    # sanity checks ---------------------------------------------------------------------------
    # make sure that all input dirs have 4 gpg filse under them with the right names
    for dir_ in input_dirs:
        dir_path = Path(dir_)
        if not dir_path.is_dir():
            raise ValueError(f"Given path is not a directory -> {dir_path} .")

        # make sure that the directory has 4 files in it - with files number.gpg, ccv.gpg,
        # date.gpg, pin.gpg
        files = list(dir_path.iterdir())
        for required_path in [
            dir_path / f"{fname}.gpg" for fname in ["number", "ccv", "date", "name"]
        ]:
            if required_path not in files:
                raise ValueError(
                    f"Given directory does not have any file named {required_path}."
                    " Cannot proceed."
                )

    # proceed with the export
    output_dict = {"items": []}
    for dir_ in input_dirs:
        dict_section = export_bank_card(dir_)
        output_dict["items"].append(dict_section)

    with output_path.open("w") as f:
        json.dump(output_dict, f, indent=4)
    logger.info(
        f"Successfully wrote {num_cards} bank card details to -> {output_path} ."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
