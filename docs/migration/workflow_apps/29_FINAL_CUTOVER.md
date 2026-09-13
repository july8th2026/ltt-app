# 29 — FINAL CUTOVER: trạng thái thật của bốn App

**Ngày:** 2026-09-11 · **Nhánh:** `claude/ltt-4bot-workflow-app-550cab` ·
**30 commit** · **238 phép kiểm** trong 14 tệp `test_1100`–`test_1113`

> ⛔ Đây là bản khai **trạng thái**, không phải một lời tuyên bố hoàn thành. Mọi
> ô "CHƯA" bên dưới là một phép đo chưa chạy được, không phải một chỗ để lấp
> bằng chữ.

---

## Tuyên bố cuối

```text
TRANSCRIPT:      NOT READY   (parity da dong; thieu E2E qua worker + URL cong khai)
AUDIO PAUSE:     NOT READY   (parity KHONG kiem duoc — bot khong de lai hien vat)
GEM:             NOT READY   (khong co parity theo thiet ke; thieu E2E)
VIDEO ASSEMBLY:  NOT READY   (thieu E2E; `vram_min_mb` chua do that)

WORKFLOW CORE:   READY FOR THESE APPS   (qua executor Agent/M1, khong qua V2)
AGENT:           NO CHANGE
FAST_BUILD GOVERNANCE: ACTIVE
AUTO-BOT:        OUT OF SCOPE
```

⭐ **Bốn `NOT READY` không phải bốn thất bại** — chúng là bốn lần từ chối nói
"xong" khi thứ chứng minh nó chưa chạy. Chặn chung của cả bốn là **một**: chưa
có lượt E2E thật qua worker trên phần cứng thật.

---

## Ma trận theo App

| | `transcript` | `audio_pause` | `prompt_canh` | `video_assembly` |
|---|---|---|---|---|
| **Source** SHA đóng băng | ✅ | ✅ | ✅ | ✅ |
| engine chuyển | 19 tệp / 3.966 dòng | 6 / 1.111 | viết lại | 29 / 7.208 |
| **Manifest** hợp lệ · group Workflow | ✅ | ✅ | ✅ | ✅ |
| `gpu_vram_mb` khai đúng chỗ runner đọc | ✅ 5000 | ✅ 5000 | — (không GPU) | ✅ 8000 |
| **Parity** | ✅ **95,50 %** vs **95,76 %** của chính engine gốc | ⛔ **không kiểm được** | 🔶 không áp dụng | ✅ tầng khớp clip + phụ đề |
| golden trong kho | 5 cặp job thật | — | — | 4 bộ job thật |
| **Macro Node** chạy được | ✅ | ✅ | ✅ | ✅ |
| typed I/O qua `validate_plan` | ✅ | ✅ | ✅ | ✅ |
| huỷ hợp tác | ✅ ~20 s | ✅ ~20 s | ✅ mỗi lượt model | ✅ ~64 s (đã vá từ ~300 s) |
| **E2E** qua worker, phần cứng thật | ⛔ | ⛔ | ⛔ | ⛔ |
| kiểm trên URL công khai | ⛔ | ⛔ | ⛔ | ⛔ |
| palette khách | 🔒 đóng có chủ đích | 🔒 | 🔒 | 🔒 |

---

## Parity — con số, và vì sao ba App còn lại không có con số ấy

**`transcript`** là App duy nhất đo được parity thật, vì bot legacy để lại
**1.932 cặp** vào/ra trên đĩa:

```
engine GOC  so voi dau ra CUA CHINH NO : 1850/1932 = 95,76 %
ban CHUYEN  so voi cung dau ra do      : 1845/1932 = 95,50 %
bon luot rut: goc 95,19-95,76 % · chuyen 94,93-95,70 %
```

⭐ Cột "engine GỐC" mới là phần đắt nhất. `make_timeline_v2` gọi `random.uniform`
**có chủ đích** (cắt B-ROLL cho đỡ đều), nên *"trùng khớp từng byte"* là mục tiêu
**bất khả về nguyên tắc** — chính bot chạy lại cũng không tái hiện được đầu ra
của nó. Không có cột đối chứng, 95,50 % đọc thành *"thiếu 4,5 %"* và sẽ có người
đi sửa một thứ không hỏng.

**`audio_pause`**: `workdir_bot` **rỗng** — bot tải lên Drive rồi xoá cục bộ.
3.099 chu kỳ, 1.398 lượt `job_done`, nhưng bản ghi chỉ có `elapsed_s` và một liên
kết Drive. ⇒ Mệnh đề *"kết quả như bot đã giao"* **không kiểm được**, và sẽ vẫn
thế trừ khi lấy lại tệp từ Drive. Thứ kiểm được là **bốn quyết định** của thuật
toán, đối chiếu từng dòng với `bot/worker.py:999-1043`.

**`prompt_canh`**: chủ dự án chốt bỏ hẳn lái trình duyệt (S2), nên đầu ra là LLM
— không tất định và **không có** một "đầu ra đúng" để so. Chuẩn nghiệm thu của nó
là **hợp đồng đầu ra**, không phải parity.

**`video_assembly`**: tầng khớp clip và tầng phụ đề đo được (tất định). Tầng dựng
video cần ffmpeg + GPU.

---

## Thay đổi ở Workflow/Core, tất cả từ bằng chứng

| | Chỗ | Vì sao |
|---|---|---|
| R1 | `platform_core/workflow/foreach.py` | giành phần tử bằng SQL, không bằng một bản đọc |
| P13 | `platform_core/registry.py::vram_for` | **hai** chỗ khai VRAM, chỉ một chỗ được đọc |
| — | `tools/gate.py --tu` · `tools/ho_so_cay.py` | governance FAST_BUILD |
| — | `tests/test_394` · `test_361` · `tools/cua_so_yen.py` | bộ test **tự tháo khoá đồng thời của cả máy** |

⚠️ Ba thay đổi cuối **đã lên trunk và đã theo deploy `3b22503c` ra production**.

---

## Ba sai lệch CỐ Ý so với bản gốc — khai ở đây vì chúng là quyết định

1. **`sequential_timeline`: sắp xếp đầu vào.** Đầu ra bot phụ thuộc thứ tự thư
   mục hệ tệp — đo trên `row196`: **115/125 cảnh đổi clip** khi đổi thứ tự. Mã
   **đã có** cơ chế `suffix` kèm chú thích nêu ý định, nhưng nó chết với tên có
   tiền tố (chính là tên production dùng). Sửa cho nó làm đúng điều nó đã viết.
2. **`error_context.MOC_NGOAI`.** `video_assembly` có 3 mốc trên 900 giây ⇒ huỷ
   chờ ~5 phút trong khi giữ 8 GB VRAM. Móc vào 14 `start_stage` ⇒ ~64 giây.
3. **`gpu_vram_mb` khai thêm ở ba App.** Không phải sai lệch với bot mà là sửa
   một khai báo **sai chỗ** của chính tôi.

⇒ Sai lệch 1 và 2 nằm trong engine "chuyển nguyên vẹn". Cả hai **khai tại chỗ**
  trong docstring, và cả hai có đối chứng chạy được.

---

## Residual gaps — xếp theo thứ ai gỡ được

### Cần phần cứng / dữ liệu (tôi không gỡ được)

* **E2E thật qua worker** cho cả bốn App — cần GPU + tệp media thật.
* **`vram_min_mb` của `video_assembly`** — con số 8000 là **ước**, chưa đo.
* **Kiểm trên URL công khai** `app.lttstudios.com` — cần deploy.
* **`audio_pause` parity** — vĩnh viễn không kiểm được nếu không lấy lại tệp Drive.

### Cần quyết định của chủ dự án

* **Tầng workflow V2 không có bộ thi hành.** `platform_core/workflow/` định
  nghĩa · băm · báo giá · ghi trạng thái được, nhưng **không tệp nào tạo một
  `Job`**. Đường sống là executor Agent (M1). Ba lựa chọn: chấp nhận M1 là đường
  chính thức · viết bộ thi hành cho V2 (sửa `platform_core/`, một chương trình
  riêng) · hợp nhất hai tầng.
* **Connector Drive/Sheets.** Phase 12 nói rõ **không** nhét vào 4 App. Muốn thay
  hẳn bot thì phải có App/Tool connector riêng — chưa audit.
* **Mở lại palette khách** sau khi E2E xong.

### Còn nợ trong Phase 13

Chưa quét hết các nhóm bằng chứng (`artifact limits` · `observability` ·
`version pinning` · `wait/resume`). Đã quét: `credit` · `error routing` ·
`job dispatch` · `resource admission` · `cancellation` · `ForEach/Join`.

---

## Cutover — chưa bắt đầu, và có lý do

Kịch bản của Phase 15 là *App canary → so đầu ra → giữ legacy fallback → promote
→ retire*. Bước đầu tiên đòi **một lượt chạy thật**, mà đó chính là chặn chung.

⛔ **Không** xoá kho legacy, **không** dọn dẹp phá huỷ. Bốn bot ở
`D:\FULL AUTO VIDEO` vẫn là oracle nguồn và vẫn đang chạy thật.
