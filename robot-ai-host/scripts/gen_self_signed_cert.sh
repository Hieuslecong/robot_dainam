#!/usr/bin/env bash
# Self-signed cert for LAN HTTPS (phone mic/WebRTC needs a secure context).
# Includes the Mac's current LAN IP in the SAN so browsers accept it for
# https://<ip>:8000 after the user taps "proceed anyway".
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="$ROOT_DIR/certs"
mkdir -p "$CERT_DIR"

IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo 192.168.1.2)"
echo "LAN IP: $IP"

openssl req -x509 -newkey rsa:2048 -sha256 -days 825 -nodes \
  -keyout "$CERT_DIR/dev-key.pem" -out "$CERT_DIR/dev-cert.pem" \
  -subj "/CN=robot-ai-host-dev" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:$IP"

echo ""
echo "OK: $CERT_DIR/dev-cert.pem + dev-key.pem (SAN: localhost, 127.0.0.1, $IP)"
echo "Thêm vào .env rồi restart server:"
echo "  SSL_CERTFILE=certs/dev-cert.pem"
echo "  SSL_KEYFILE=certs/dev-key.pem"
echo "Điện thoại mở: https://$IP:8000/robot/  (chấp nhận cảnh báo chứng chỉ)"
