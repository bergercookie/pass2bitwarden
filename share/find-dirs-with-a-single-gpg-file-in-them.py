import os
import sys


def find_single_gpg_dirs(root_dir):
    result = {}

    for subdir in next(os.walk(root_dir))[1]:  # Get immediate subdirectories
        subdir_path = os.path.join(root_dir, subdir)
        files = [f for f in os.listdir(subdir_path)]

        # if the stem doesn't have two parts, continue
        if len(subdir.split(".")) == 1:
            continue

        if len(files) == 1 and files[0].endswith(".gpg"):
            result[subdir_path] = files[0]

    return result


root_directory = sys.argv[1]
matching_dirs_to_single_password = find_single_gpg_dirs(root_directory)

for directory, gpg_file in matching_dirs_to_single_password.items():
    del gpg_file
    print(directory)
