#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="${PROJECT_ROOT}/storage/certs"
KEY_PATH="${CERT_DIR}/localhost-key.pem"
CERT_PATH="${CERT_DIR}/localhost-cert.pem"

mkdir -p "${CERT_DIR}"

openssl req \
  -x509 \
  -nodes \
  -days 365 \
  -newkey rsa:2048 \
  -keyout "${KEY_PATH}" \
  -out "${CERT_PATH}" \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

printf 'Wrote %s\n' "${KEY_PATH}"
printf 'Wrote %s\n' "${CERT_PATH}"
