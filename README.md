# LTT AI Studio

Nền tảng nhiều app tự động hoá, mỗi app một đường dẫn dưới
`app.lttstudios.com`.

**→ Bắt đầu đọc từ [`docs/00_BAT_DAU_TU_DAY.md`](docs/00_BAT_DAU_TU_DAY.md)**

---

## App đang có

| App | Đường dẫn | Trạng thái |
|---|---|---|
| Đăng bài Facebook + TikTok | `/facebook`, `/sheet/...`, `/manual/...` | chạy production |
| Demo — nghiệm thu hạ tầng | `/demo` | dùng để kiểm tra, tốn 0 đồng |

## Thêm app mới

Thêm một thư mục vào `apps/`. Không sửa file nào của nền tảng.
Xem [`docs/03_THEM_APP_MOI.md`](docs/03_THEM_APP_MOI.md).

## Chạy nhanh

```powershell
python -m pip install -r requirements.txt -r requirements-server.txt
python -m pytest -q
python -m uvicorn server.run:app --host 127.0.0.1 --port 8100
```

## Tài liệu

| File | Nội dung |
|---|---|
| `docs/00_BAT_DAU_TU_DAY.md` | bố cục, nguyên tắc, trạng thái |
| `docs/01_COPY_LEN_SERVER.md` | đưa code lên VPS |
| `docs/02_LENH_CHO_CLAUDE.md` | câu lệnh mẫu cho Claude |
| `docs/03_THEM_APP_MOI.md` | thêm app |
| `docs/04_CLOUDFLARE_TUNNEL.md` | dựng Tunnel |
| `docs/_luutru/PROJECT_MEMORY.md` | nhật ký thay đổi |
| `docs/_luutru/WEB_PARITY_PLAN.md` | lịch sử chuyển từ desktop sang web |

## Không bao giờ commit

`data/config.json`, `data/*.enc`, `secrets/`, `cloudflare/config.yml`,
`cloudflare/*.json`.

Chạy `python tools/scan_source_secrets.py` trước khi chia sẻ bất cứ thứ gì.
