# LTT-CMC normalization baseline

Đo ngày 2026-09-12 trên `main` tại
`7cde3c9d4dac05858bb8cf1806a6f5b190521d66`. Đây là baseline source trước
khi nhận hai handoff Voice/LLM; không phải bằng chứng deploy production.

## Phép kiểm độc lập

Preflight ngay trước lượt chạy:

```text
python tools\tai_may.py
CPU 9% tren 20 loi | RAM trong 17.5 GiB
RESULT: RANH - du bo nho cho mot luot day du

python tools\cua_so_yen.py trang-thai
RANH - khong tai nguyen nao dang bi giu.
```

Lệnh đã chạy:

```powershell
python -m pytest tests/test_103_autosub_projects.py::test_platform_migrations_have_a_single_head tests/test_223_nexus_devices.py::test_khong_co_hai_migration_trung_revision_id tests/test_223_nexus_devices.py::test_do_thi_migration_chi_co_MOT_head tests/test_60_app_registry.py tests/test_148_frontend_bundle.py -q
```

Kết quả thật: **48 passed, 1 warning in 3.28s**. Cảnh báo duy nhất là
`StarletteDeprecationWarning` của `fastapi.testclient`/`httpx`; không có test
skip hoặc fail.

## Migration graph

- Alembic heads: đúng một head — `e26c9a41d8b5`.
- Không có revision ID trùng.
- Toàn bộ revision graph phân giải về đúng một head.

Nếu ghép thẳng canonical + Voice + LLM theo ancestry lịch sử, graph giả định
sẽ có **ba head**: một head canonical, một head Voice và một head LLM. Revision
ID/schema intent không trùng, nhưng ancestry chưa chuẩn hóa. Khi nhận handoff,
phải đọc applied revision trước; sau đó port Voice rồi LLM tuần tự trên head
canonical bằng forward/merge migration, không tự ý đổi `down_revision` của
migration từng được apply.

## Registry identities và bảng

Đo từ `platform_core.registry.discover()`, `load_app_tables()` và
`Base.metadata.tables`:

| Đại lượng | Số đo |
|---|---:|
| AppManifest đã nạp | 20 |
| ToolSpec | 15 |
| Job type | 40 |
| Bảng ORM | 98 |

Năm app có `tables.py` được registry nạp là `auto_scan_video`, `chatltt`,
`ltt_voice`, `prompt_ai_ommi` và `vps`. Bộ `test_60_app_registry.py` chốt slug,
route prefix, ToolSpec name, job type, table prefix và table ownership không
trùng; mọi app đều nạp không lỗi.

Các số trên chỉ mô tả baseline hiện hành. Việc hợp nhất provider/model, retry,
ToolSpec V2 và GPU authority vẫn thuộc handoff LLM, chưa được tuyên bố hoàn tất.

## Frontend/generated freshness

`git diff --name-only 34b4626e..HEAD -- frontend` không trả dòng nào, nên không
rebuild để tạo churn. Bốn SHA-256 nguồn được tính lại bằng các hàm của
`tools.build_release` và đều trùng `server/static/<bundle>/build-meta.json`:

| Bundle | Source SHA-256 |
|---|---|
| `agent-canvas` | `5aeb859509485f4b382d50e3e6e6f7638683daa14789c5c4e730b3790fd678fe` |
| `autosub-studio` | `1b4b0ce79454e20ed0ecd647835614a1f5b4227603992d082f15586c8b9282fd` |
| `prompt-ai-ommi` | `01535b51462d66bf137821a08b6d2a9280c3515a618c58b2c6bccbdaac47901b` |
| `chatltt` | `428820c1cfc0566611896d112fdb44f711bcc7ab290b646ce57adc54e20b388b` |

`tests/test_148_frontend_bundle.py` còn xác nhận ba bundle đang được app phục
vụ đều giải ra asset thật và không có app tự neo gốc repo bằng số cấp thư mục.
