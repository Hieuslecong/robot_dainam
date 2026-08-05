# Deployment

## Localhost

```bash
cp .env.example .env
uv sync --frozen
npm ci --prefix clients/browser
npm run build --prefix clients/browser
uv run python -m app.main --host 127.0.0.1 --port 8000 --profile mock
```

## Cloud voice localhost

```bash
uv run python scripts/check_cloud_profile.py --profile google_vi
uv run python -m app.main --host 127.0.0.1 --port 8000 --profile google_vi
```

## Docker

```bash
docker build --no-cache -t robot-ai-host:fixed .
docker run --rm -p 8000:8000 --env-file .env robot-ai-host:fixed
curl -f http://127.0.0.1:8000/health
```

Google credential JSON phải mount read-only và `.env` dùng path trong container. Không copy credential vào image.

## LAN

- `HOST=0.0.0.0`.
- Thay provisioning/JWT secrets bằng chuỗi mạnh tối thiểu 32 byte.
- HTTPS là bắt buộc để browser máy khác được cấp microphone.
- Cấu hình CORS đúng origin.
- Thêm STUN/TURN khi NAT/topology yêu cầu.
- Chỉ mở firewall trong LAN tin cậy.

## Giới hạn deployment

SmallWebRTC ở đây được nghiệm thu cho localhost/LAN và tối đa bốn phiên. Chưa có bằng chứng cho multi-node hoặc người dùng phân tán địa lý.

## Hybrid deployment

Use `HYBRID_DEPLOYMENT.md` for native macOS/Linux instructions. A Linux CPU Docker baseline is provided through `Dockerfile.hybrid`, `docker/piper/Dockerfile` and `docker-compose.hybrid.yml`. Apple Silicon should run the host natively to use MLX.
