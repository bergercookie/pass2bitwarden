#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
# ]

import logging
import subprocess
from argparse import ArgumentParser
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Iterable
import csv

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def decrypt_file(filepath: Path) -> tuple[Path, str]:
    if "pdf" in filepath.suffixes:
        raise ValueError(f"Can't process GPG-encrypted PDF file -> {filepath} .")

    cmd = ["gpg", "--decrypt", "--batch", str(filepath)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise ValueError(f"Failed to decrypt -> {filepath} .")
    if result.stdout == "":
        raise ValueError(f"Empty decrypted content -> {filepath} .")

    return filepath, result.stdout


def password_iterator(password_store_dir) -> Iterable[Path]:
    for path in password_store_dir.rglob("*.gpg"):
        yield path


def main():
    # argument parsing ------------------------------------------------------------------------
    parser = ArgumentParser(
        "Export passwords from the Standard UNIX Password Manager to Bitwarden"
    )
    parser.add_argument(
        "-d",
        "--input-dir",
        help="Path to the top-level directory to look for GPG-encrypted passwords",
        required=False,
        type=Path,
        default=(Path.home() / ".password-store").expanduser().resolve(),
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Bitwarden-compatible output CSV file to write the passwords to",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "-p",
        "--passphrase",
        help="GPG passphrase (otherwise will use the GPG agent if that's running",
        required=False,
        type=str,
        default="",
    )
    parser.add_argument(
        "-j",
        "--num-processes",
        dst="num_processes",
        help="Number of processes to use for decryption - default=cpu_count",
        type=int,
        default=cpu_count(),
    )

    args = parser.parse_args()
    output_path = args.output
    passphrase = args.passphrase
    num_processes = args.num_processes

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

    password_store_dir = (Path.home() / ".password-store").expanduser().resolve()
    if not password_store_dir.is_dir():
        raise ValueError(
            f"Expected to find password store directory, but did not find a directory -> {password_store_dir} ."
        )

    # print configuration ---------------------------------------------------------------------
    logger.info(f"* Password store directory\t-> \n{password_store_dir}")
    logger.info(f"* Output file\t-> {output_path}")
    logger.info(f"* With GPG passphrase\t-> {'Yes' if passphrase else 'No'}")
    logger.info(f"* Number of processes\t-> {num_processes}")

    # main logic ------------------------------------------------------------------------------
    num_processes = cpu_count()
    password_iterable = password_iterator(password_store_dir)
    with Pool(processes=4) as pool:  # Adjust based on your CPU cores
        password_names_to_decrypted_texts = pool.map(decrypt_file, password_iterable)

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

        for path, text in password_names_to_decrypted_texts:
            # TODO handle cases where the username is the parent directory name and the password is in
            # <parent>/password.gpg

            # Handle passwords of the form <websiteaddr>/<emailaddr>.gpg
            folder = ""
            favorite = 0
            type_ = "login"
            name = path.parent.name.split(".")[0]
            notes = ""
            fields = []
            reprompt = 0
            login_uri = path.parent.name
            login_username = path.stem
            login_password = text.strip()
            login_totp = ""
            logger.info(f"Writing password for -> {path.parent}/{path.stem} ...")
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

    logger.info(f"Done writing passwords to output file -> {output_path} .")
    # TODO Print some statistics


if __name__ == "__main__":
    main()
