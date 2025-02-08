#!/usr/bin/env bash
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <file-containing-directory-paths>"
    exit 1
fi
while read -r dir; do
    rmdir "$dir" 2>/dev/null || echo "Failed to remove: $dir"
done < $1
