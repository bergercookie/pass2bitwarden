#!/usr/bin/env bash
if [ $# -ne 1 ]; then
  echo "Usage: $0 <file>"
  exit 1
fi

file_="$1"

while read -r dir_; do
  rm -rfv "$dir_" 2> /dev/null || echo "Failed to remove: $dir_"
  # echo "$dir_"
done < "$file_"
