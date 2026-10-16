#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
    echo "Install Python 3.10+ from https://www.python.org/downloads/macos/"
    read -r -p "Press Enter to close " _qp_reply
    exit 1
fi
python3 bootstrap.py "$@"
qp_status=$?
if [ "$qp_status" -ne 0 ]; then
    read -r -p "Press Enter to close " _qp_reply
fi
exit "$qp_status"
