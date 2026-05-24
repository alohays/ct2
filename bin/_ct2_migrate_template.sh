#!/usr/bin/env bash
# Template for future CT2 protocol migration helpers.

set -euo pipefail

FROM_VERSION="${FROM_VERSION:-0.0}"
TO_VERSION="${TO_VERSION:-0.0}"

echo "Copy this template to bin/ct2-migrate-${FROM_VERSION}-${TO_VERSION} and implement the migration in Python stdlib or bash."
