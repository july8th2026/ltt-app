# 00_BASELINE — trạng thái ĐO ĐƯỢC trước khi sửa một dòng nào

Mọi con số dưới đây lấy từ lệnh chạy thật lúc 09/09/2026 13:30–13:40 +0700,
trên cây `auto-scan-video-v4-mvp-7173d9`. Chỗ nào chưa đo được thì ghi
**CHƯA ĐO**, không ghi ước lượng.

---

## 1. Khoá git

| trường | giá trị |
|---|---|
| nhánh | `claude/ltt-voice-98-upgrade-9b586f` |
| SHA | `990179106f7e80a554f28c41c4745488fb17bbd8` |
| commit | `Nhat ky: dong lo trinh Workflow V2 — 23/23, gate cuoi 7 do deu la test_448` |
| `git status --porcelain` | **rỗng** (0 dòng) — cây sạch |
| nhánh đích của chương trình | `admin-mvp-v3` |
| SHA của `admin-mvp-v3` | `99017910` — **BẰNG** SHA trên |

⭐ Điểm này quan trọng cho hợp đồng của chương trình: yêu cầu nói *"audit
`admin-mvp-v3`, không audit `master` thay cho nó"*. Nhánh phiên này đang đứng
**trỏ vào đúng cùng một commit** với `admin-mvp-v3`, nên nội dung được audit
đúng là nội dung của nhánh đích. (`master` ở `9e73bf1f`, một commit KHÁC —
không audit nó.)

## 2. Thứ KHÔNG xác minh được ở Phase 0

Ghi ra để không ai tưởng phần này đã đóng:

- **SHA production đang chạy** — chưa hỏi `/health/version`. Chưa hỏi vì
  Phase 0 là chỉ-đọc-cục-bộ; sẽ hỏi trước bất kỳ kết luận nào về deploy drift.
- **Alembic head trên production** — chưa đọc.
- **`asset_ver` production** — chưa đọc.
- **GPU window** — chưa đo card có rảnh không. Mọi hạng mục cần GPU đang
  `BLOCKED_BY_GPU_WINDOW` cho tới khi đo.
- **Máy B** — chưa hỏi. Nhắc: `NODE_OFFLINE` ≠ máy tắt, và máy B chỉ có MỘT
  suất đồng thời.

## 3. Kiểm kê mã nguồn — đếm thật

| khối | tệp | dòng |
|---|---|---|
| `apps/ltt_voice/**.py` | 38 | **9.287** |
| `voice_sidecar/**.py` | 21 | **5.802** |
| `server/static/voice.js` | 1 | 105.041 **byte** |
| test giọng (`tests/*voice*`, `*giong*`) | **36** | **11.981** |
| hàm test giọng | — | **545** |
| template Voice | 14 | — |
| công cụ `tools/*voice*`/`*giong*` | 14 | — |
| kịch bản deploy Voice | 3 | — |

Tệp lớn nhất mỗi bên: `apps/ltt_voice/text_pipeline.py` (823),
`routes/_p_du_an.py` (653); `voice_sidecar/do_chat_luong.py` (782),
`noi_dai.py` (579).

⭐ Tỉ lệ test/sản phẩm ≈ **11.981 / 15.089 = 0,79**. Đây là một cơ sở test
DÀY, không phải một app trần trụi. Điều đó thay đổi hình dạng của chương trình:
phần lớn công việc sẽ **không** là viết thêm mã.

## 4. Bề mặt HTTP — đếm thật

### 4.1 Web (`apps/ltt_voice/routes/`)

**31 endpoint** trên 8 tệp route:

- `_p_tao.py` (7): `GET ""`, `GET "/"`, `POST /xem-truoc`, `GET /ket-qua/{job_id}`,
  `POST /tao`, `GET /tu-dien`, `POST /tu-dien/them`, `POST /tu-dien/{muc_id}/xoa`
- `_p_du_an.py` (13) · `_p_giong.py` (3) · `_p_lich_su.py` (2) ·
  `_p_nghe_thu.py` (1) · `_p_audio.py` (1) · `_p_chi_so.py` (1) · `_p_api.py` (1)

### 4.2 Public API (`manifest.MANIFEST.tools`)

**MỘT** ToolSpec: `speech.ltt` → `ltt_voice.synthesize`, `api_exposed=True`,
scope `jobs:create`, tham số `text` / `voice_id` / `preset`,
`admission_resource="vieneu_gpu"`, `admission_slots=1`.

⚠️ `job_types` khai **hai** loại: `ltt_voice.synthesize` **và**
`ltt_voice.enroll`. Chỉ loại thứ nhất có ToolSpec. Nghĩa là **ghi danh giọng
(cloning) KHÔNG mở qua Public API** — chỉ có đường web. Đây là một sự thật
cần chấm, chưa phải một lỗi.

### 4.3 Sidecar (`voice_sidecar/server.py`)

**12 cửa**: `/live` · `/health` · `GET /v1/capabilities` · `POST /v1/speech` ·
`/v1/batch` · `/v1/speech-dai` · `/v1/lo-ra-tep` · `/v1/ghep-tep` ·
`/v1/stream` · `/v1/enroll-kho` · `/v1/enroll` · `GET /v1/voices`

### 4.4 Đối chiếu cửa ↔ người gọi — ĐO, không suy

Đếm bằng tham chiếu **có định danh module** (`sidecar_client.<tên>`), sau khi
bỏ phép đếm theo tên trần vì nó khớp nhầm (`noi(`, `song(` là từ thường trong
mã tiếng Việt):

| hàm bọc | số lần được gọi (có định danh) |
|---|---|
| `noi` | 31 |
| `san_sang` | 18 |
| `trang_thai` | 5 |
| `lo_ra_tep` | 4 |
| `song`, `giong_dung_san`, `ghi_danh`, `ghep_tep` | 2 mỗi hàm |
| `noi_lo`, `noi_dai`, `ghi_danh_kho` | 1 mỗi hàm |

⇒ **Không có hàm bọc chết.** Mọi hàm trong `sidecar_client` đều có ít nhất
một người gọi thật.

🔴 **`/v1/stream` là bề mặt sidecar DUY NHẤT không có người gọi.** Toàn kho
không có `sidecar_client` nào bọc nó. Và điều này **đã được ghim bằng test**:

```
tests/test_504_ltt_voice_be_mat_sidecar.py:159
    assert "/v1/stream" in sv,  "sidecar khong con cua /v1/stream?"
    assert "/v1/stream" not in sc, "... da co client cho /v1/stream — go phep kiem nay"
```

⇒ Đây **không phải** một bề mặt chết bị bỏ quên. Nó là một bề mặt **cố ý để
sẵn**, có phép kiểm canh cả hai chiều. Phân loại đúng: `EXISTS` ở sidecar,
`NOT_WIRED` ở sản phẩm — tức đúng nội dung của U-07.

⚠️ Đính chính một phép đo của chính tôi: lượt grep đầu tiên của tôi tìm
"stream" trong `apps/ltt_voice` + `voice_sidecar` rồi lọc qua `grep -v "^.*#"`.
Mẫu ấy loại **mọi dòng có ký tự `#` ở bất kỳ đâu**, nên nó đã âm thầm giấu
`@app.post("/v1/stream")`. Tôi suýt báo "streaming không tồn tại". Con số
đúng chỉ ra khi đếm lại không lọc.

## 5. Dữ liệu — trạng thái thật của hai tệp then chốt

### 5.1 `apps/ltt_voice/ho_so_giong.json` — **RỖNG**

608 byte, và phần dữ liệu là:

```json
"phien_ban": "",
"engine_tham_so": "",
"giong": {}
```

Chính tệp tự khai: *"Map `giong` rỗng nghĩa là CHƯA CHẠY phép đo lần nào. Mọi
giọng sẽ lùi về hai hằng số chung trong `gia.py` (1,5 giây khởi động + 18 ký
tự/giây). Đó là hành vi đúng, không phải một khoảng trống cho lấp."*

⚠️ Câu cuối là một **lời khai của tài liệu**, và luật §4 nói code + runtime
thắng tài liệu. Nó đúng ở chỗ *hệ thống không sập khi rỗng*. Nó **chưa trả
lời** câu mà điểm số phụ thuộc vào: một hằng số 18 ký tự/giây dùng chung cho
mọi giọng làm **giá giữ chỗ** và **ETA** lệch bao nhiêu so với đo thật.
Đó là một phép đo, chưa ai chạy. ⇒ `DATA_GAP`, không phải `CODE_GAP`.

### 5.2 `voice_sidecar/baseline_chat_luong.json` — CÓ, nhưng hẹp

```
phien_ban_tham_so : ltt-voice-2026-08-30a
so_vong           : 3
so_cau            : 6          ← SÁU câu
cer.tb            : 0,1249     (lệch 0,0067; n = 18)
cer.lech_giua_cau : 0,1044
```

⇒ Có phân bố σ, có 3 vòng — tốt. Nhưng corpus là **6 câu**, trong khi đặc tả
của chương trình này đòi 30 VI + 30 EN + 15 mixed. Và `lech_giua_cau` (0,1044)
lớn gần bằng chính `cer.tb` (0,1249): **phương sai giữa các câu áp đảo phương
sai giữa các vòng**, tức 6 câu là quá ít để con số trung bình có nghĩa.

`baseline_lech.json`: 8 giọng × 3 câu, n = 24.

## 6. Bộ xếp lịch — đã có gì, thiếu gì

`platform_core/jobs.py:claim()` xếp thứ tự:

```python
.order_by(aged_first, never_served_first, last_account_claim,
          Job.created_at, Job.id)
```

⇒ **Đã có** aging + fair-share **theo tài khoản** + FIFO ổn định trong tài
khoản. Đây nhiều hơn hẳn "FIFO trần" mà U-20 giả định.

🔴 Nhưng nó **không** giải bài của U-20. Ba lỗ đo được:

1. Công bằng ở đây là công bằng **giữa các tài khoản**, không phải giữa
   **việc ngắn và việc dài**. Hai job của **cùng một khách** — một 100.000 ký
   tự, một 200 ký tự — vẫn thuần FIFO.
2. Xếp thứ tự chỉ chạm job **chưa bắt đầu**. `admission_slots=1` nghĩa là job
   dài đang chạy **giữ nguyên suất GPU tới lúc xong**. Không có điểm nhả
   giữa chừng, dù `text_pipeline` đã chia đoạn.
3. `Job.priority` **tồn tại** (`models.py:723`, mặc định 100) và **không xuất
   hiện trong `order_by`**. Đo toàn `platform_core/`: mọi lần dùng `.priority`
   đều là của `ApiKey`, không phải `Job`. ⇒ một cột đang mang giá trị mà
   không ai đọc.

## 7. Đường lùi giọng — kiến trúc đúng, kho rỗng

`lui_giong.py` có bậc thang bốn nấc, **cấm** nới giới tính và nới làn, và bắt
mọi lượt lùi phải sinh cảnh báo cho khách. Chính tệp ghi lý do: hệ `D:\Viral`
đã lùi nam → nữ và khách báo lỗi ngày 26/08/2026.

Giới hạn tự khai, và tôi xác nhận nó khớp mã: ứng viên lùi hiện **chỉ là 20
giọng mẫu của engine, cả 20 đều làn `vi`**.

⇒ `lan en` → **không lùi được**. `gioi = ""` → **không lùi được**.
Phân loại: `DATA_GAP` ở kho giọng, **không** phải lỗi thuật toán. Tệp đã nói
đúng cách sửa: đưa giọng `en` có giới đã khai vào danh sách ứng viên, không
sửa bậc thang.

## 8. Nguồn nghiên cứu ngoài — trạng thái thật

### 8.1 `D:\Viral`

**Không phải** kho mã TTS như tên gọi gợi ý. Nó là **thư mục cài đặt của một
app Electron đã đóng gói**: `ViralCrawl.exe` 180 MB + chromium runtime.

Mã đọc được **có**, ở `D:\Viral\resources\app-src\` (backend Python).
Tệp liên quan giọng nói:

```
capcut_tts.py  capcut_asr.py        TTS/ASR qua CapCut
omnivoice_synth.py  giong_piper.py  tổng hợp giọng
diarize_pitch.py                    tách người nói + cao độ
giong_mau/ giong_11labs/ giong_tuyen/ long_tieng/   giọng mẫu .mp3
```

🔴 **Ràng buộc bản quyền đọc được ngay từ `README.md` của kho ấy:**

- `MediaCrawler/` là fork của NanmiCoder/MediaCrawler — giấy phép **phi
  thương mại**.
- Phần còn lại: **UNLICENSED / private**.
- `giong_11labs/` — tài sản ElevenLabs. `capcut_tts.py` — endpoint dịch
  ngược.

⇒ Cả hai rơi đúng vào luật cứng của chương trình: **NGHIÊN CỨU THÔI**, không
import, không biến thành dependency. Không có ngoại lệ nào cần xin ở đây vì
LTT không cần chúng: ta có engine riêng.

### 8.2 `D:\LTT_VOICE_RESEARCH`

**Chưa tồn tại** lúc bắt đầu. Đã tạo scaffold lúc 13:36 (7 thư mục con).
`RESEARCH_SOURCES.lock.json` sẽ ghi khi có nguồn thật đầu tiên — chưa ghi một
tệp rỗng để trông như đã làm.

## 9. Hồ sơ đã có từ các lượt trước — ĐỌC SAU, và không kế thừa điểm

Tồn tại từ trước trong `docs/LTT_VOICE/`:

```
AUTONOMOUS_AUDIT/   00_RUNTIME_TRUTH … 08_LENH_TRIEN_KHAI  (9 tệp)
AUTONOMOUS_RUN/     01_RA_SOAT_HIEN_TRANG · 10_BENCHMARK_AM_THANH · FINAL_REPORT
VIRAL_VOICE_AUDIT_2026-09-07.md   ← nguồn của bảng U-01…U-20
KHO_GIONG/  DECISIONS.md  NGUON_CHAN_LY.md
```

⛔ Chương trình này **không tái sử dụng điểm** của các tệp đó. Chúng được đọc
**sau** mã nguồn, và chỉ để hiểu Ý ĐỊNH. Một dòng "DONE" ở đó không nâng điểm
ở đây; chỉ bằng chứng đo lại mới nâng.

Bản `VIRAL_VOICE_AUDIT_2026-09-07.md` tự nó đã có một mục **ĐÍNH CHÍNH**
(§19.0): nó thừa nhận U-06 là *"một PHÁT HIỆN SAI"* — việc ấy đã xong từ
trước khi bản audit được viết. Đó là một lý do cụ thể để không tin bảng U-
theo mặt chữ.
