#!/usr/bin/env bash

set -euo pipefail

preview=$(git clean -ndX)

if [[ -z "$preview" ]]; then
    echo "There are no ignored files or directories to remove."
    exit 0
fi

echo "The following ignored files/directories will be removed:"
echo
echo "$preview"

echo
read -r -p "Proceed with deletion? [y/N] " answer

case "$answer" in
    [yY]|[yY][eE][sS])
        echo
        git clean -fdX
        echo
        echo "Ignored files removed."
        ;;
    *)
        echo
        echo "Operation cancelled."
        ;;
esac