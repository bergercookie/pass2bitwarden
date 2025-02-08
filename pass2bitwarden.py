#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "bubop"
# ]
# ///

__doc__ = """Export passwords from the Standard UNIX Password Manager to Bitwarden."""


import csv
import logging
import subprocess
from argparse import ArgumentParser
from itertools import chain
from multiprocessing import Pool
from pathlib import Path
from typing import Iterable, Protocol

from bubop.fs import valid_dir
from bubop.string import format_dict

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def short_name(filepath: Path) -> str:
    if filepath.name in ["password.gpg", "passwd.gpg"]:
        return f"{filepath.parent.parent.name}/{filepath.parent.name}"
    else:
        return f"{filepath.parent.name}/{filepath.stem}"


PASSWORD_STORE = Path.home() / ".password-store"


def decrypt_gpg_file(filepath: Path) -> tuple[Path, str] | None:
    short_name_ = short_name(filepath)
    try:
        if "conflict" in filepath.name:
            logger.info(
                f"Skipping syncthing-related conflict file -> {short_name_} ..."
            )
            return None

        logger.info(f"Decrypting GPG file -> {short_name_} ...")
        if "pdf" in filepath.suffixes:
            raise ValueError(f"Can't process GPG-encrypted PDF file -> {short_name_} .")

        cmd = ["gpg", "--decrypt", "--batch", str(filepath)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise ValueError(f"Failed to decrypt -> {short_name_} .")
        if result.stdout == "":
            raise ValueError(f"Empty decrypted content -> {short_name_} .")

        logger.info(f"OK Decrypted GPG file -> {short_name_} .")
        return filepath, result.stdout
    except Exception as e:
        logger.error(f"Error while executing decrypt_gpg_file({short_name_})\n\t{e}")
        return None


def password_iterator(input_dirs: list[Path]) -> Iterable[Path]:
    return chain.from_iterable(input_dir.rglob("*.gpg") for input_dir in input_dirs)


class StrConvertible(Protocol):
    def __str__(self) -> str: ...


class CsvWriter(Protocol):
    def writerow(self, row: list[StrConvertible]): ...


def write_website_password(
    path: Path,
    password_text: str,
    csvwriter: CsvWriter,
    folder,
):
    """Handle passwords of the form <websiteaddr>/<emailaddr>.gpg."""

    def format_uri_fn(path: Path) -> str:
        uri = path.parent.name
        if not uri.startswith("http") and not uri.startswith("https"):
            uri = f"https://{uri}"
        return uri

    # split the password which occupies the first line and potetnial other fields that occupy
    # the rest of the lines
    password_and_fields = password_text.split("\n")
    password = password_and_fields[0]
    if len(password_and_fields) > 1:
        fields = password_and_fields[1:]
    else:
        fields = ""
    fields = ",".join(
        [f"Field {i}: {field}" for i, field in enumerate(fields) if field]
    )

    def get_parent_name(path: Path) -> str:
        if path.name in ["password.gpg", "passwd.gpg"]:
            parent_name = path.parent.parent.name
        else:
            parent_name = path.parent.name

        if "." not in parent_name:
            return parent_name.capitalize()

        # handle cases where the parent directory is a domain name
        parent_name_parts = parent_name.split(".")
        parent_name_wo_ext = ".".join(parent_name_parts[:-1]).capitalize()
        return parent_name_wo_ext

    favorite = 0
    type_ = "login"
    notes = ""
    fields = fields
    reprompt = 0
    name = get_parent_name(path)
    if path.name in ["password.gpg", "passwd.gpg"]:
        login_username = path.parent.name
        login_uri = path.parent.parent.name
    else:
        login_username = path.stem
        login_uri = path.parent.name

    # tweakable
    format_uri = True

    # play it smart - if ther's a dot, it's a domain name -> add https://
    if "." in login_uri:
        login_uri = format_uri_fn(path) if format_uri else login_uri
    else:
        login_uri = ""

    login_password = password
    login_totp = ""
    logger.info(f"Writing password for -> {short_name(path)}...")
    csvwriter.writerow(
        [
            folder,
            favorite,
            type_,
            name,
            notes,
            fields,
            reprompt,
            login_uri,
            login_username,
            login_password,
            login_totp,
        ]
    )
    logger.info(f"OK Wrote password for -> {path.parent}/{path.stem} ...")


def main():
    # argument parsing ------------------------------------------------------------------------
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--folder",
        dest="folder",
        help=(
            "Name of the Bitwarden folder to put the passwords in. "
            "Use / to specify a series of nested folders "
            "(they must pre-exist in Bitwarden otherwise they'll be ignored)."
        ),
        required=False,
        default="",
        type=str,
    )
    parser.add_argument(
        "-d",
        "--input-dirs",
        dest="input_dirs",
        help="Path to the top-level directories to look for GPG-encrypted passwords",
        required=False,
        type=valid_dir,
        default=(Path.home() / ".password-store").expanduser().resolve(),
        nargs="+",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Bitwarden-compatible output CSV file to write the passwords to",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "-j",
        "--num-processes",
        dest="num_processes",
        help="Number of processes to use for decryption - default=cpu_count",
        type=int,
        default=4,
    )
    args = parser.parse_args()
    input_dirs = args.input_dirs
    output_path = args.output
    num_processes = args.num_processes
    folder = args.folder

    # sanity checks ---------------------------------------------------------------------------
    if output_path.is_dir():
        raise ValueError(
            f"Output path is a directory, cannot proceed -> {output_path} ."
        )
    elif output_path.exists():
        raise ValueError(
            f"Output path already exists, cannot proceed -> {output_path} ."
        )
    else:
        logger.info(f"Writing passwords to output file -> {output_path} ...")

    # print configuration ---------------------------------------------------------------------
    logging.info(
        "\n\n"
        + format_dict(
            {
                "Directories to search for GPG files": input_dirs,
                "Output file": output_path,
                "Number of processes": num_processes,
                "Bitwarden folder": folder if folder else "<None>",
            },
            align_items=True,
            header="Configuration",
        )
    )

    # main logic ------------------------------------------------------------------------------
    password_iterable = password_iterator(input_dirs)
    if num_processes == 1:
        password_names_to_decrypted_texts = map(decrypt_gpg_file, password_iterable)
    else:
        with Pool(processes=num_processes) as pool:  # Adjust based on your CPU cores
            password_names_to_decrypted_texts = pool.map(
                decrypt_gpg_file, password_iterable
            )

    # initialize csv writer
    with open(output_path, "w") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(
            [
                "#folder",
                "favorite",
                "type",
                "name",
                "notes",
                "fields",
                "reprompt",
                "login_uri",
                "login_username",
                "login_password",
                "login_totp",
            ]
        )

        password_names_to_decrypted_texts = [
            x for x in password_names_to_decrypted_texts if x is not None
        ]

        for path, password_text in password_names_to_decrypted_texts:
            # TODO handle cases where the username is the parent directory name and the password is in
            # <parent>/password.gpg

            if password_text is None:
                continue

            write_website_password(
                path=path,
                password_text=password_text,
                csvwriter=csvwriter,
                folder=folder,
            )

    logger.info(f"Done writing passwords to output file -> {output_path} .")


if __name__ == "__main__":
    main()
