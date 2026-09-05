#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_FILE="${SCRIPT_DIR}/depth_anything_v2_vits.pth"
EXPECTED_SIZE=99218434
URL="https://huggingface.co/depth-anything/Depth-Anything-V2-Small/resolve/main/depth_anything_v2_vits.pth"

if [ -f "${TARGET_FILE}" ]; then
    ACTUAL_SIZE=$(stat -c%s "${TARGET_FILE}" 2>/dev/null || stat -f%z "${TARGET_FILE}" 2>/dev/null || wc -c < "${TARGET_FILE}")
    if [ "${ACTUAL_SIZE}" -eq "${EXPECTED_SIZE}" ]; then
        echo "Weights file already exists and size matches (${EXPECTED_SIZE} bytes): ${TARGET_FILE}"
        exit 0
    else
        echo "Weights file exists but size (${ACTUAL_SIZE}) does not match expected (${EXPECTED_SIZE}). Re-downloading..."
    fi
fi

echo "Downloading Depth Anything V2 Small weights from Hugging Face..."
if command -v curl &>/dev/null; then
    curl -L -o "${TARGET_FILE}" "${URL}"
elif command -v wget &>/dev/null; then
    wget -O "${TARGET_FILE}" "${URL}"
else
    python3 -c "import urllib.request; urllib.request.urlretrieve('${URL}', '${TARGET_FILE}')"
fi

ACTUAL_SIZE=$(stat -c%s "${TARGET_FILE}" 2>/dev/null || stat -f%z "${TARGET_FILE}" 2>/dev/null || wc -c < "${TARGET_FILE}")
if [ "${ACTUAL_SIZE}" -eq "${EXPECTED_SIZE}" ]; then
    echo "Successfully downloaded ${TARGET_FILE} (${ACTUAL_SIZE} bytes)."
else
    echo "Warning: File downloaded but size is ${ACTUAL_SIZE} (expected ${EXPECTED_SIZE})."
fi
