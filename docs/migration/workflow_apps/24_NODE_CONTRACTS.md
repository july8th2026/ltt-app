# 24 — HỢP ĐỒNG MACRO NODE (đóng băng)

Đóng băng 2026-09-09 trên hợp đồng tool v2 hiện hành
(`platform_core/registry.py::_validate_hop_dong_v2` @ `05464239`).

## Ràng buộc của nền tảng — kiểm lúc NẠP, không lúc chạy

```python
_TOOL_NAME_RE     = ^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$
type_version      int >= 1
side_effect       {"none", "external", "irreversible"}
idempotency       {"key_fields": (...)}  — mỗi tên phải CÓ trong params_schema
resource          {"class", "vram_min_mb", "slots", "est_duration_s"}
TOOL_PARAM_TYPES  string int number bool enum model_ref
                  text image image[] video video[] audio json json[]
TOOL_PORT_TYPES   text image image[] video video[] audio json json[] model_ref
```

⭐ Vì sao bốn trường ấy bị kiểm nghiêm: chúng chạm **tiền** và **khôi phục sau
sự cố**. Một khai báo sai chỉ lộ ra lúc chạy thì chỗ nó lộ ra là sổ credit.

⚠️ `image` **không** thuộc `MEASURABLE_TYPES` — một tấm ảnh không có thời lượng,
và khai như thế là lỗi hợp đồng, không phải một phép đo trả 0.

---

## `transcript.run`

```
job_type      transcript.run          type_version  1
side_effect   none                    idempotency   key_fields=("audio", "min_s", "max_s")
resource      class=gpu  vram_min_mb=5000  slots=1  est_duration_s=<đo>
```

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `audio` | `audio` | ✅ | |
| ~~`ho_so_stt`~~ | — | | **BỎ**: hồ sơ là hằng số của App (`HO_SO_STT` trong service), không phải tham số của khách |
| `language` | `string` | | rỗng = tự dò |
| `min_s` / `max_s` | `number` | | legacy 3.0 / 6.0 |
| `include_silence` | `bool` | | |
| `sua_van_ban` | `bool` | | `comprehensive_fixer_v5` |

`returns` = `{"transcript": "json"}` — mảng đoạn theo schema đã bị
`_validate_output_segments_strict` cưỡng chế trong legacy.

⭐ **`ho_so_stt` bị bỏ khỏi `params_schema` khi build thật, và đó là bản sửa
đúng.** Hồ sơ quyết định *đầu ra*, không phải *sở thích*: mở nó ra cho khách là
mời họ đổi một thứ mà parity đang neo vào. Nó thành hằng số `HO_SO_STT` trong
`services/phien_am.py`. Khoá luỹ đẳng đổi theo: `("audio", "min_s", "max_s")` —
`language` **không** nằm trong khoá, vì để trống nghĩa là tự dò và hai lần tự dò
trên cùng tệp cho cùng kết quả.

⛔ **Không** khai tham số cho `gemini_corrector`: `DEFER` theo audit `03`. Thêm
một tham số rồi bỏ trống dễ hơn nhiều so với gỡ một tham số đã công bố.

---

## `audio_pause.run`

```
job_type      audio_pause.run         type_version  1
side_effect   none                    idempotency   key_fields=("audio", "pause_plan")
resource      class=gpu  vram_min_mb=5000  slots=1
```

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `audio` | `audio` | ✅ | |
| `pause_plan` | `json` | ✅ | `[{id, anchor_text, pause_ms, pause_type, reason}]` |
| ~~`ho_so_stt`~~ | — | | **BỎ** — như `transcript.run` |
| `min_pause_ms` / `max_pause_ms` | `int` | | clamp |
| `min_gap_s` | `number` | | legacy 0.8 |
| `nguong_khop` | `number` | | ngưỡng khớp mờ |

`returns` = `{"audio": "audio", "transcript": "json"}` — **hai** đầu ra, và cả
hai đều P0: transcript đã dịch mốc là thứ bước sau tiêu thụ.

---

## `gem.run`

⚠️ **Khối này đã SỬA 2026-09-09** sau quyết định bỏ lái trình duyệt. Bản đầy đủ
kèm lý do: `09_QUYET_DINH_GEM_BO_TRINH_DUYET.md`.

```
job_type      gem.run                 type_version  1
requires      ("api",)                       <- was ("browser",)
side_effect   none                           <- was "external"
idempotency   key_fields=("kich_ban", "so_canh")   <- was {} (co y de rong)
resource      khong tu khai — admission cua `text.chat` lo
```

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `kich_ban` | `text` | ✅ | đầu vào bước 1 |
| `so_canh` | `int` | | |
| `batch_step2` / `batch_step3` | `int` | | mặc định **10 / 5** — giữ từ legacy |
| `model` | `model_ref` | | category `text`, `hidden`, **phải có `default`** |

`returns` = `{"ket_qua": "json"}`.

🔑 **`side_effect` đổi `external` → `none` là thay đổi có thật.** Bản cũ khai
`external` vì mỗi lượt tiêu một suất trong hạn mức phiên của một tài khoản người
thật, và chạy lại không miễn phí — khai `key_fields` khi ấy là hứa một tính luỹ
đẳng mà runtime không giữ được. Qua `runtime_noi_bo`, mỗi lượt là một lời gọi có
kế toán riêng, nên `key_fields` khai được **thật**.

⛔ Sáu hằng số nhịp của legacy (`8s` · `+3s/lô` · cap `60s` · nghỉ `45s`/`12` lô
· hội thoại mới mỗi `25` lô) **bị bỏ**: chúng là nhịp chống throttle của một
**phiên web**, và chiến trường ấy không còn. Nhưng `HISTORY_SCENES_COUNT = 5`
thì **giữ** — nó nói về ngữ cảnh của mô hình (*"chỉ giữ 2 scene cuối → qua 100+
scenes drift character/style"*), không về trình duyệt. Phân biệt hai loại hằng
số ấy là phần khó của quyết định này.

⛔ Ba template `data/prompts/step*.txt` là **tài sản, không phải mã** — giữ
nguyên từng ký tự.


## `video_assembly.run`

```
job_type      video_assembly.run      type_version  1
side_effect   none                    idempotency   key_fields=("clips", "music", "cau_hinh")
resource      class=gpu  vram_min_mb=8000  slots=1  est_duration_s=<đo>
requires      ("gpu", "ffmpeg")
```

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `clips` | `video[]` | ✅ | |
| `music` | `audio` | | |
| `cau_hinh` | `json` | | ngưỡng lọc · style phụ đề · chuyển cảnh |
| ~~`ho_so_stt`~~ | — | | **BỎ** — như `transcript.run` |
| `bat_demucs` / `bat_phu_de` / `bat_cham_diem` | `bool` | | giai đoạn 8 / 11 / 12 |

`returns` = `{"video": "video", "transcript": "json"}`.

⚠️ `vram_min_mb=8000` là **ước tính chưa đo** — bốn model trong một job
(whisper · YOLO · CLIP · Demucs). Phải đo thật ở Phase 11 rồi sửa lại. Và
`admission_slots` phải khai, vì ngân sách `-n` **không đếm tiến trình cháu**:
ngày 03/09 đo được 12 tiến trình `demucs` mỗi cái 460–984% CPU.

---

## Bất biến kiểm được, cho cả bốn

| # | Mệnh đề | Kiểm thế nào |
|---|---|---|
| N1 | Node và GUI gọi **cùng** hàm service | phép kiểm hợp đồng: `routes.py` và `jobs.py` cùng import một `services/<domain>` |
| N2 | Node và GUI tạo **cùng** `job_type` | so `ToolSpec.job_type` với `AppManifest.job_types` |
| N3 | `routes.py` không chứa nghiệp vụ | `tools/lint_app_contract.py` (900 dòng / 30 handler) |
| N4 | Không App nào import App khác | `test_147` (phân tầng) đã cưỡng chế |
| N5 | Nền tảng không biết tên App | `test_60`: không slug nào hardcode trong `server/`/`platform_core/` |
| N6 | `idempotency.key_fields` trỏ tới tham số có thật | nền tảng kiểm lúc nạp |

⛔ **Không tách atomic node ở V1.** Bốn Macro Node, hết. Tách sau khi parity và
E2E đóng — MASTER-GUARDRAILS #7.
