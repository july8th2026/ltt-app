# LTT VOICE STUDIO — KẾ HOẠCH THI HÀNH GIAO DIỆN (prompt pack V1)

> ## ⛔ TỆP NÀY LÀ MỘT **KẾ HOẠCH ĐÃ THI HÀNH**, KHÔNG PHẢI HỢP ĐỒNG HIỆN HÀNH
>
> Lập **2026-08-31**. Từ đó tới nay hai thứ trong đây đã đổi, và đổi theo cách làm
> mọi câu nhắc tới "trần 1.500" ở dưới **sai nếu đọc như trần sản phẩm**:
>
> · 31/08 — `TRAN_KY_TU_CONG_KHAI` tách khỏi `TRAN_MOI_LUOT_SINH`;
> · 03/09 — trần yêu cầu của khách mở lên, đường tài liệu dài hấp thụ trần model.
>
> ⭐ 1.500 **vẫn đúng** — nhưng nó là trần của **một lượt sinh**, không phải thứ
> khách gõ được. Hai câu hỏi khác nhau dùng chung một con số chính là lỗi mà
> `docs/LTT_VOICE/03_TAI_LIEU_DAI.md` mô tả.
>
> ⇒ Câu hỏi nào đọc ở đâu: **`docs/LTT_VOICE/NGUON_CHAN_LY.md`**.
> Giữ tệp này nguyên văn làm hồ sơ *"lúc ấy ta nghĩ gì"* — đừng sửa số bên trong.



> Lập: **2026-08-31**. Nhánh `admin-mvp-v3`. Máy này **LÀ máy chủ** (`C:\LTTPlatform` có thật).
> Nguồn yêu cầu: `G:\My Drive\AI\A LTT AII\LTT_VOICE_UI_PROMPT_PACK_V1`
> (12 prompt · 6 ảnh tham chiếu · `specs/FEATURE_MATRIX.md` · `specs/VISUAL_REFERENCE_NOTES.md`).
>
> Đây là deliverable của **prompt 00 — MASTER UI ORCHESTRATOR**, và nó đã nuốt
> luôn phần lớn **prompt 01 — UI FORENSIC AUDIT** (mục 2–4 dưới đây), vì audit
> chỉ có nghĩa khi nó dẫn tới một quyết định.
>
> Nhãn: **[V]** đọc được từ mã (có đường dẫn) · **[S]** suy ra · **[Đ]** đề xuất.

---

## 0. Kết luận trước, lý lẽ sau

**Ba câu quan trọng nhất của tài liệu này:**

1. 🟢 **Ngôn ngữ thị giác trong 6 ảnh đã có sẵn trong `ltt.css`.** Không phải
   "gần giống" — cùng một bảng màu, cùng một triết lý. Không cần một dòng token
   mới. Phần khó không nằm ở visual.
2. 🔴 **Hai trong sáu trang không có backend nào cả.** Projects và Batch là **0
   bảng, 0 route, 0 job type**. Vẽ chúng bằng dữ liệu giả là cách nhanh nhất để
   biến pack này thành một bộ ảnh chụp màn hình thứ hai.
3. 🔴 **Ảnh tham chiếu chứa ít nhất 6 điều khiển mà backend cố ý KHÔNG hỗ trợ**
   — và một trong số đó (`Delivery Style` / tốc độ / phong cách) bị **Q119 cấm**
   phơi ra. Vẽ nó là đi ngược một quyết định đã có số đo đứng sau.

⇒ **Chiến lược chọn: B — vỏ dùng chung + component mới có chọn lọc.** Chi tiết §4.

---

## 1. Bản đồ thẩm quyền (authority map)

Khi hai nguồn mâu thuẫn, thứ tự này quyết định. Thấp hơn **không bao giờ** lật cao hơn.

| # | Nguồn | Ví dụ thứ nó quyết |
|---|---|---|
| 1 | **`docs/QUYET_DINH_NEN_TANG.md` + `DECISIONS.md`** | Q117–Q119: engine chạy máy A · không provider · **không phơi tham số sinh mẫu** |
| 2 | **Mã nguồn + runtime đang chạy** | `voice_sidecar/server.py` có `/v1/voices` nhưng app chưa gọi ⇒ "sample voices" là **việc phải làm**, không phải "đã có" |
| 3 | **`CLAUDE.md` + `AGENTS.md`** | route ≤ 900 dòng · nghiệp vụ ở `features.py` · **cache-bust static** · kiểm trên URL công khai |
| 4 | **`docs/LTT_VOICE/00_PHUONG_AN_VA_LO_TRINH.md`** | V6: "Jinja + `ltt.css`, **không React trừ khi chứng minh được cần**" |
| 5 | **`specs/FEATURE_MATRIX.md`** của pack | trang nào nên có năng lực gì |
| 6 | **6 ảnh tham chiếu** | tinh thần thị giác — **không phải wireframe** (chính pack nói vậy) |

🔴 **Xung đột đã tìm thấy giữa (1) và (6):** ảnh `01_STUDIO.png` vẽ ô
`DELIVERY STYLE` với thanh trượt *Tốc độ 1.00x* và ô chọn *Phong cách: Natural*.
`voice_sidecar/tham_so.py` mở đầu bằng đúng chữ: *"ĐÂY KHÔNG PHẢI NÚT VẶN CỦA
KHÁCH (Q119) … không lên giao diện"*, với **hai lý do độc lập** (cache CUDA graph
khoá theo `(B, temperature, top_k, top_p)`; và upstream #173 lệch tông giữa các
đoạn). ⇒ **Ảnh thua. Không vẽ ô đó.** Ghi vào phần deferred, không im lặng bỏ.

---

## 2. Audit — nền tảng đang có gì [V]

### 2.1 Kiến trúc giao diện

| Hạng mục | Thực tế |
|---|---|
| Kết xuất | **Jinja2** server-side (`server/templating.py`), `server/templates/base.html` |
| Tăng cường | Vanilla JS nhúng trang + `htmx.min.js` tự-host + vài `.js` rời ở `server/static/` |
| SPA | Có, nhưng **ngoại lệ**: 3 bó React/Vite (`frontend/agent-canvas`, `autosub-studio`, `prompt-ai-ommi`) gắn qua `platform_core/frontend_bundle.bundle_assets` |
| CSS | **Một** tệp: `server/static/ltt.css` (222 KB), tự-host, CSP chặn CDN ngoài |
| Cache-bust | `?v={{ asset_ver }}` — hash nội dung, `server/templating.py:ASSET_VER` |
| Theme | **Dark một chiều, có chủ ý** (`color-scheme:dark`, không có nhánh light) |
| i18n | `_()` / `N_()` bọc mọi chuỗi, có `/en` prefix + `hreflang` |

### 2.2 Token thiết kế — đối chiếu trực tiếp với 6 ảnh

`ltt.css:6-33`. Cột phải là thứ ảnh đòi:

| Token | Giá trị | Ảnh đòi | Khớp? |
|---|---|---|---|
| `--surface-canvas` | `#08090a` | nền black sâu | ✅ |
| `--surface-raised` / `--surface-overlay` | `#151111` / `#1b1413` | card charcoal | ✅ |
| `--border-subtle` / `--border-strong` | `#382422` / `#63332e` | border mảnh, ám đỏ | ✅ |
| `--brand-primary` | **`#ef3731`** | đỏ LTT | ✅ |
| `--brand-soft` / `--brand-border` | `#421511` / `#8f2c24` | nền chip đỏ + viền selected | ✅ |
| `--status-success/warning/danger` | `#62d889` / `#efb84f` / `#ff6b63` | Completed / Waiting / Error | ✅ |
| `--radius-lg/md/sm` | `12 / 8 / 6 px` | bo góc card | ✅ |
| `--mono` | Cascadia/Consolas | `vce_01K8f3a7…` | ✅ |

⭐ **Không có một token nào phải thêm.** Đây là phát hiện quan trọng nhất của
audit: pack và nền tảng được thiết kế từ cùng một gu, nên rủi ro "hệ UI song
song" là rủi ro **có thật và dễ mắc** — sẽ rất cám dỗ để viết một `voice.css`
khai lại đúng những màu này.

### 2.3 Component có sẵn dùng lại được ngay

| Component | Ở đâu | Trang nào cần |
|---|---|---|
| `.apptabs` — **thanh tab ngang của app** | `ltt.css:318` + `base.html`, dữ liệu từ `MANIFEST.nav` | **Cả 6 trang** — đây chính là thanh Studio/Voices/… |
| `.badge` `.b-ok/.b-warn/.b-err/.b-grey` | `ltt.css:88` | Completed / Generating / Error |
| `.chip` (+ `.i .v .m`) | `ltt.css:96` | `Sample` · `My Voice` · `VI` · `EN` |
| `.btn` `.ghost` `.sm` `.danger` | `ltt.css:74` | mọi nút |
| `.ui-card` · `.field` · `.inp` · `.pill` · `.health` | `ltt.css:102-120` | card giọng · form · thanh % |
| `_job_progress.html` + `/jobs/{id}/progress` + `/api/jobs/{id}` | `server/routes/jobs.py:197,240` | trạng thái sinh |
| `sao_chep.js` (nút chép) | `server/static/sao_chep.js` | **copy `voice_id`** ở 4 trang |
| `_o_chon_tep.html` + `chon_tep.js` | `server/templates/` | tải clip mẫu khi ghi danh |
| `_cam_chon.html` + `cam_chon.js` | `server/templates/` | segmented control |
| `job_history.list_owned(...)` | `platform_core/job_history.py:26` | History (đã có lọc status/date/cursor) |
| Khu `/developers` **đầy đủ** | `server/routes/developer/` + 16 template `dev_*.html` | **trang API** — keys, usage, logs, playground, webhooks đã xong |

### 2.4 Backend của app hôm nay

| | |
|---|---|
| Route | 7 (`""`, `/tao`, `/giong`, `/giong/tao`, `/giong/{id}/tat`, `/lich-su`, `/audio/{key}`) — **307 dòng**, còn xa trần 900 |
| Template | 3, tổng **245 dòng** — sơ khai đúng nghĩa: 1 `<textarea>`, 1 `<select>`, 2 `<table>` |
| Bảng | 4: `voice_profile` · `voice_ref` · `voice_repr` · `voice_consent` |
| Job type | 2: `ltt_voice.synthesize` · `ltt_voice.enroll` |
| Nghiệp vụ | `features.py` (đúng chỗ) · `text_pipeline.py` (chuẩn hoá + **chia đoạn + ghép đã chạy**) · `gia.py` · `tu_dien.py` |
| Cổng engine | `127.0.0.1:8120` — `/live` `/health` `/v1/capabilities` `/v1/speech` `/v1/batch` `/v1/speech-dai` `/v1/stream` `/v1/enroll` `/v1/voices` |

---

## 3. 🔴 Bảng đối chiếu ẢNH ⇄ NĂNG LỰC THẬT

Đây là phần có giá trị nhất của tài liệu. Cột **Phán quyết** là hợp đồng.

### 3.1 Ảnh 01 — STUDIO

| Thành phần trong ảnh | Backend hôm nay | Phán quyết |
|---|---|---|
| Ô văn bản + đếm ký tự | ✅ `/tao`, trần 1.500 | **DÙNG LẠI**, dựng lại vỏ |
| Chọn giọng: tab `Sample` / `My Voices` | ⚠️ `/v1/voices` **có ở cổng, app chưa gọi** | **MỚI — nối dây** (§7.1, có bẫy) |
| `vce_…` + nút chép trên từng dòng | ✅ `public_id` + `sao_chep.js` | **DÙNG LẠI** |
| `+ Tạo giọng của tôi` | ✅ `/giong/tao` | dùng lại, đưa vào modal |
| **`LANGUAGE` Auto / VI / EN** | ❌ không tham số nào; engine tự xử VI/EN lẫn lộn | **BỎ điều khiển.** Hiện *"tự nhận tiếng Việt + tiếng Anh lẫn nhau"* như một câu, không phải ba nút giả |
| **`MODE` Fast / Quality** | ❌ không tồn tại | **BỎ** |
| **`DELIVERY STYLE` tốc độ + phong cách** | ⛔ **Q119 CẤM** (`voice_sidecar/tham_so.py`) | **BỎ.** Ghi rõ ở §9 |
| `PRONUNCIATION → Dictionary` | ✅ `tu_dien.py` chạy thật (bảng chung) + `tu_dien_rieng=` cho từ riêng | **MỚI — mở phần "Từ riêng của tôi"** ở P4 |
| `Normalize Preview` | ✅ `text_pipeline.chuan_hoa` — thuần regex, vài chục µs | ⭐ **MỚI, rẻ, giá trị cao nhất cả pack** (§7.2) |
| `OUTPUT` WAV / MP3 / 48 kHz | ⚠️ cổng chỉ trả WAV; sample rate cố định | Hiện là **sự thật hiển thị** (`WAV · 48 kHz`), **không phải nút bấm**. MP3 → deferred |
| Trình phát + waveform kết quả | ⚠️ chỉ có `<audio>` trần | **MỚI** — canvas waveform từ Web Audio, 0 thư viện (§7.3) |
| `VERSIONS V1/V2/V3` | ❌ không có mô hình phiên bản | **HOÃN** tới P5 (phiên bản là khái niệm của **block**, không phải của một lượt lẻ) |
| `GẦN ĐÂY (3 câu)` | ✅ suy từ `job_history` | **MỚI**, rẻ |
| `CHI TIẾT`: latency / sample rate / request id | ✅ có trong `job.result` + `job.id` | **MỚI**, rẻ |
| `Save to Project` | ❌ chưa có Projects | nút xuất hiện ở **P5**, không sớm hơn |
| Chip header `Engine Online` | ✅ `sidecar_client.san_sang()` + `/live` | **MỚI**, rẻ |
| Chip header `Queue 2` | ✅ đếm được từ bảng job | **MỚI**, rẻ |
| Chip header `Storage 256 GB / 1 TB` | ❌ **không có hạn mức dung lượng cho khách** | **BỎ** — một con số bịa trong header là một lời hứa bịa |

### 3.2 Ảnh 02 — VOICES

| Trong ảnh | Thật | Phán quyết |
|---|---|---|
| Lưới thẻ giọng, lọc All/Sample/My | ⚠️ dữ liệu có, UI là `<table>` 4 cột | **DỰNG LẠI** thành lưới thẻ |
| Ô tìm + sắp xếp | ✅ lọc phía máy chủ được | **MỚI**, rẻ |
| `Voice ID` + chép | ✅ | dùng lại |
| Panel chi tiết bên phải | ✅ dữ liệu từ `voice_profile` + `voice_ref` | **MỚI** |
| `Reference Audio (2)` + nghe thử | ✅ `voice_ref.storage_key` đã lưu | **MỚI** — cần mở thêm tiền tố ở `/audio/` (§7.4) |
| **`Similarity 92%` · `Pronunciation 94%` · `Stability 90%`** | ❌ **không đo gì cả** — đó là cổng **V10** | ⛔ **BỎ HẲN.** Bịa ba con số phần trăm là cách nhanh nhất phá lòng tin, và chúng sẽ không bao giờ xoá được |
| `Generations 1.248` · `Audio Minutes 86h` · `Last Used` | ✅ đếm được từ job | **MỚI**, rẻ |
| `Voice Family: LTT Family` | ❌ không có khái niệm | **BỎ** |
| `Create Voice – Quick Guide` 5 bước | ⚠️ luồng thật chỉ 3 bước (thông tin → tệp → cam kết) | **DỰNG LẠI theo luồng thật** — đừng vẽ 5 bước cho một luồng 3 bước |
| `Archive` | ✅ `trang_thai = disabled` (có chủ ý không xoá) | dùng lại, đổi chữ thành **"Tắt"** |

### 3.3 Ảnh 03 — PROJECTS · 3.4 Ảnh 04 — BATCH

🔴 **Cả hai: 0 bảng, 0 route, 0 job type.** `grep -r "voice_project|voice_batch|voice_block"` ⇒ **không có gì**.

Nhưng nền móng thì có, và đó là lý do chúng khả thi chứ không phải viễn tưởng:

| Mảnh cần | Đã có sẵn |
|---|---|
| chia văn bản thành khối | `text_pipeline.chia_doan()` **đã chạy thật** |
| sinh nhiều đoạn rồi ghép liền mạch | `features.goi_cong_dai` → `/v1/speech-dai` **đã chạy thật** |
| sinh cả lô | cổng `/v1/batch` **đã có** |
| xếp hàng, thử lại, tiến độ, huỷ | hàng đợi job của nền tảng — **miễn phí** |
| một GPU một việc | `admission_resource="vieneu_gpu"` **đã khai** ⇒ batch tự tuần tự, không cần cơ chế riêng |
| việc định kỳ (dọn tệp lô) | `AppManifest.bao_tri` (tiền lệ `apps/vps/`) |

⇒ **Không hoãn, nhưng không vẽ trước.** Xây backend tối thiểu ở P5/P6 rồi mới
dựng UI. Cắt phạm vi có chủ ý:
- Projects: **bỏ `Chapters`** ở bản đầu (project → block là đủ; chương là một
  tầng lồng làm đôi mọi màn hình để đổi lấy rất ít).
- Batch: **CSV + dán danh sách**, bỏ `Destination` ghi thẳng ổ đĩa máy chủ
  (`D:\LTT_Studio\Batch_Output` trong ảnh là khái niệm của một app desktop —
  ở SaaS nó là **tải về / zip**).

### 3.5 Ảnh 05 — HISTORY

| Trong ảnh | Thật | Phán quyết |
|---|---|---|
| Danh sách + phát + tải + chạy lại + xoá | ✅ `job_history` + `/audio/` | **DỰNG LẠI** |
| Lọc theo Voice / Language / **Source** / Date | ⚠️ status+date có sẵn; **`Source` chưa được ghi** | thêm `nguon` vào `params` khi nộp (§7.5) — 1 dòng ở mỗi cửa |
| Thẻ nguồn `Studio` `Project` `Batch` `API` | ⚠️ như trên | **MỚI**, rẻ |
| `TÓM TẮT HOẠT ĐỘNG` / `THỐNG KÊ NHANH` | ✅ đếm được | **MỚI**, rẻ |
| `ĐANG XỬ LÝ (2)` + % | ✅ `job.progress` | **MỚI**, dùng `/api/jobs` |
| Panel chi tiết + `Request ID` | ✅ | **MỚI**, rẻ |

### 3.6 Ảnh 06 — API

🔴 **Trang này gần như đã tồn tại — ở chỗ khác.** `/developers` có: quickstart ·
tools · keys · usage · logs · playground · webhooks · pricing · docs (16 template).

⛔ Dựng lại chúng bên trong Voice Studio là **vi phạm trực tiếp nguyên tắc 5 và 6
của pack** (không tạo hệ song song, không chép markup).

⇒ Tab `API` của Voice Studio là một trang **mỏng, chuyên biệt cho giọng**:
`voice_id` nào gọi được · ví dụ cURL/Python/JS cho **đúng** `speech.ltt` · trạng
thái mở/đóng của tool · và **liên kết sâu** sang `/developers/keys`,
`/developers/usage`, `/developers/logs`. Không sinh hay hiện khoá API nào ở đây.

⚠️ **`speech.ltt` CHƯA mở ra ngoài.** Ngày 30/08 `LTT_PUBLIC_API_TOOLS` có đúng
bốn tool: `text.chat` · `image.ltt` · `video.upscale` · `video.subtitle`.
Trang API phải **đọc trạng thái thật** và nói *"sắp mở"* nếu chưa — đừng dạy
khách một lời gọi trả 403. Cách kiểm (đừng tin tài liệu, hỏi máy chủ):

```bash
curl -s https://app.lttstudios.com/api/v1/tools -H "Authorization: Bearer $LTT_API_KEY" -H "User-Agent: ltt/1.0"
```

---

## 4. Ba chiến lược đã cân, và vì sao chọn B

| | A — dùng lại tối đa | **B — vỏ chung + component chọn lọc** | C — dựng lại ranh giới UI bằng React |
|---|---|---|---|
| Cách làm | Giữ 3 template, thêm CSS | Jinja + `ltt.css`, thêm **một** bộ partial `_voice_*.html` + **một** `voice.js` | Bó Vite thứ tư như `autosub-studio` |
| Đạt được ảnh? | ❌ không — 245 dòng template không đỡ nổi lưới thẻ + panel chi tiết | ✅ đủ tinh thần | ✅ |
| Rủi ro hệ song song | thấp | thấp — **tái dùng token, không khai lại** | 🔴 cao: một `studio.css` thứ hai, một bảng màu thứ hai |
| Tốc độ tới MVP | nhanh nhưng không tới đích | trung bình | chậm — thêm build, thêm CI, thêm test frontend |
| Hợp `docs/…/00_PHUONG_AN` V6? | có | ✅ **có** ("không React trừ khi chứng minh được cần") | ❌ chưa chứng minh được |
| Cache-bust | có sẵn | có sẵn (`asset_ver`) | thêm một cơ chế nữa |
| Chỗ React thật sự thắng | — | — | chỉ khi có **timeline kéo–thả** như `autosub-studio` |

**Chọn B.** Lý do quyết định, nói thẳng: thứ 6 ảnh này đòi là **lưới, panel,
bảng, thẻ trạng thái, và một trình phát** — không có một thao tác kéo–thả liên
tục nào. Đó chính xác là loại giao diện Jinja + một ít JS làm tốt, và là loại mà
một SPA chỉ thêm một hệ thống build để bảo trì.

🔎 **Điều kiện lật lại quyết định này** (viết ra để nó không thành giáo điều): nếu
Projects ở P5 phát sinh **sắp xếp lại khối bằng kéo–thả** hoặc chỉnh sóng âm theo
thời gian, mở lại lựa chọn C **chỉ cho riêng trang Projects** — đúng khuôn
`bundle_assets` đã có, không phải cho cả app.

---

## 5. Bản kiểm kê component sẽ tạo

Tất cả nằm trong `apps/ltt_voice/templates/_*.html` + **một** tệp JS
(vị trí chốt ở P1 sau khi đọc cách `apps/vps` phục vụ static của nó).

| Partial | Việc | Ảnh |
|---|---|---|
| `_voice_the.html` | thẻ một giọng: avatar sóng · chip Sample/My · `voice_id`+chép · Dùng/Nghe thử | 02 |
| `_voice_chon.html` | bộ chọn giọng hai tab (Sample / My) — **dùng ở Studio, Projects, Batch** | 01·03·04 |
| `_voice_ma.html` | `voice_id` mono + nút chép (bọc `sao_chep.js`) | 01·02·04·05·06 |
| `_voice_phat.html` | trình phát + waveform canvas + tải WAV | 01·02·05 |
| `_voice_trangthai.html` | badge trạng thái sinh, ánh xạ job status → `.b-ok/.b-warn/.b-err` | mọi trang |
| `_voice_dong_lichsu.html` | một dòng lịch sử (dùng lại ở History **và** ở "Gần đây" của Studio) | 01·05 |
| `_voice_rong.html` | empty state có hướng dẫn bước kế | mọi trang |

`voice.js` (một tệp, vanilla, `?v={{ asset_ver }}`): đếm ký tự · nộp + **poll
`/api/jobs/{id}` tại chỗ** · vẽ waveform · lọc phía client cho lưới giọng ·
xem trước chuẩn hoá (gọi máy chủ).

⛔ **Không thêm token CSS.** Nếu thấy cần một màu chưa có, đó là dấu hiệu đang vẽ
một thứ ảnh có mà sản phẩm không có — quay lại §3.

---

## 6. Phụ thuộc giữa các trang

```
P1 vo + 6 tab  --+--> P2 Studio ---+--> P5 Projects --+
                 |                 |                  |
                 +--> P3 Voices ---+                  +--> P7 danh bong + ma tran trang thai
                 |                                    |
                 +--> P4 Lich su ---------------------+
                 |                                    |
                 +--> P6 Batch -----------------------+
                        (P6 can bo chon giong cua P3)

P8 API — doc lap, nhung chi co nghia sau khi speech.ltt mo
```

`_voice_chon.html` (P3) là **nút thắt**: Studio, Projects, Batch đều dùng. Làm nó
đúng một lần, ở P3, trước P5/P6.

---

## 7. Bẫy đã tìm thấy trước khi viết mã

### 7.1 🔴 `/v1/voices` **nạp model** — đừng gọi nó lúc dựng trang
`voice_sidecar/server.py:272` gọi `c.nap()`, và `engine.py:142` nạp VieNeu —
**19,4 giây khi nguội** (số đo `docs/LTT_VOICE/do_v1.json`). Một trang liệt kê
giọng mẫu gọi thẳng vào đó sẽ treo 19 giây ở lượt đầu mỗi sáng, và trông y hệt
một trang chết.
⇒ **Giọng mẫu khai tĩnh** trong `apps/ltt_voice/giong_mau.py` (id + nhãn + mô tả
+ khoá clip nghe thử), và **một test đối chiếu** danh sách đó với `/v1/voices`
thật — đúng khuôn `tham_so_cong_khai.py` + `test_331` đã dùng cho trần ký tự.
*Hai bản sao không có phép kiểm là hai bản sao sẽ lệch; hai bản sao **có** phép
kiểm là một hợp đồng.*

### 7.2 Xem trước chuẩn hoá là tính năng **có thật**, không phải trang trí
`text_pipeline.chuan_hoa` quyết định **cả tiền lẫn âm thanh**: `manifest._gia()`
đếm ký tự **sau** chuẩn hoá, nên "1.250.000 đồng" (14 ký tự) tính tiền như "một
triệu hai trăm năm mươi nghìn đồng" (~40). Hôm nay khách không có cách nào thấy
điều đó trước khi bấm. Ô `Normalize Preview` trong ảnh 01 biến một sự bất ngờ về
hoá đơn thành một thứ nhìn thấy được.
⇒ Route mới `POST /ltt-voice/xem-truoc` → `{da_chuan_hoa, so_ky_tu, uoc_credit}`.
Thuần regex, không chạm mạng/CSDL. **Tỉ lệ giá trị/công cao nhất trong cả pack.**

### 7.3 Waveform không cần thư viện
`AudioContext.decodeAudioData` → gộp đỉnh → vẽ `<canvas>`. CSP tự-host không cản.
Waveform **tĩnh** trong ảnh 02/04 chỉ là hình trang trí ⇒ chấp nhận một SVG dựng
sẵn, đừng giải mã cả tệp cho một hình nhỏ trong danh sách 20 dòng.

### 7.4 `/audio/{key}` chỉ mở cho `voice/out/{uid}/`
`apps/ltt_voice/routes.py` chặn theo tiền tố. Nghe thử **clip nguồn** (ảnh 02,
`Reference Audio`) nằm ở tiền tố khác. ⇒ mở thêm đúng một tiền tố, **giữ nguyên
khuôn kiểm bằng hình dạng khoá** — đừng thay bằng một phép tra CSDL, vì một phép
kiểm rẻ và không thể quên là thứ đang giữ an toàn cho đường này.

🔴 **SỬA 31/08 sau đính chính của phiên `lttstudiosapp-9e` — bản đầu định mở một
tiền tố MỚI `voice/src/{uid}/`, và đó là sai.** `tham_chieu.khoa_nguon()` đã có
sẵn khuôn `voice/{owner}/{public_id}/source.<đuôi>`; dùng lại nó thay vì đẻ ra
tiền tố thứ hai, để ngày khách xoá một giọng chỉ có **một** chỗ phải dọn.

⭐ Và biết vì sao clip nguồn **cố ý không** có `job_id` trong khoá: nó nằm ngoài
tầm dọn của `platform_core/job_content.py`, tức nó **không** chết theo hạn 30
ngày của tệp kết quả. Đó là đúng — điều khoản hứa giữ nguyên bản clip để dựng
lại giọng khi nâng engine, nên nó phải sống theo **vòng đời của hồ sơ giọng**.

⚠️ `tests/test_343` có một phép quét TĨNH trên `apps/*/jobs.py`: cấm đặt job id
ngay trước một dấu chấm. Handler mới nào cũng phải theo khuôn
`{app}/{owner}/{job_id}/<tên tệp>`.

### 7.5 `Source` chưa được ghi ⇒ History không truy vết được
Thêm `nguon` (`studio|project|batch|api`) vào `params` **tại mỗi cửa nộp job**.
Rẻ nếu làm ở P1; đắt nếu làm sau P6, vì khi ấy đã có bốn cửa và dữ liệu cũ khuyết.
⇒ **Làm ở P1.**

### 7.6 Tab đang mở **không sáng lên** — lỗi thật, đang sống
`base.html` so `nav == entry.nav_key`, nhưng `apps/ltt_voice/routes.py::_ngu_canh`
**không đặt `nav`**. Các app khác có (`apps/autosubvideo/routes.py:75`, …). Hệ
quả: cả ba tab của Voice đều xám. Sửa một dòng ở P1.

### 7.7 Nút Tạo **rời khỏi trang**
`ltt_voice_studio.html` làm `window.location.href = '/jobs/' + id`. Ảnh 01 (và
lẽ thường) muốn kết quả hiện **tại chỗ**. `/api/jobs/{id}` đã trả JSON ⇒ poll tại
chỗ, giữ văn bản, cho sinh lại ngay. Vẫn giữ liên kết "mở trang việc" cho ai cần.

### 7.8 Static mới **phải** cache-bust
`voice.js` là tài sản tĩnh **mới** ⇒ `?v={{ asset_ver }}`, không thì Cloudflare
phục vụ bản cũ tới 4 giờ (CLAUDE.md quy tắc 6 — đã dính một lần với `ltt.css`).

### 7.9 `.ps1` thuần ASCII · ghi cấu hình không BOM
Nếu phần nào chạm script cài (thêm làn worker, thêm biến), theo quy tắc 1–3.

---

## 8. Thứ tự thi hành

Đổi so với thứ tự đề xuất của pack ở **hai chỗ**, và pack cho phép đổi nếu giải
thích (`START_HERE.md`):

1. **History lên trước Projects/Batch** (P4 trước P5/P6; pack xếp History thứ 07).
   Lý do: History chỉ cần dữ liệu đã có, nó là nơi **chứng minh** ba trang đầu
   chạy thật, và nó không phụ thuộc gì. Làm sớm để có bằng chứng sớm.
2. **API có điều kiện** (P8): nó chỉ có nghĩa sau khi `speech.ltt` thực sự nằm
   trong `LTT_PUBLIC_API_TOOLS`. Trước đó nó là một trang dạy cách nhận 403.

| # | Prompt pack | Việc | Backend mới? | Ước |
|---|---|---|---|---|
| **P1** | 02 | **Vỏ + hệ thiết kế**: 6 `NavEntry` (3 thật, 3 `built=False` ⇒ nền tảng tự gắn badge *"đang xây"*) · sửa `nav` (§7.6) · chip Engine/Queue · bộ partial · `voice.js` · ghi `nguon` (§7.5) | không | 1 ng |
| **P2** | 03 | **Studio**: bố cục 3 cột · bộ chọn giọng · xem trước chuẩn hoá (§7.2) · kết quả tại chỗ + waveform (§7.3, §7.7) · Gần đây · Chi tiết | `POST /xem-truoc` | 1,5 ng |
| **P3** | 04 | **Voices**: lưới thẻ · lọc/tìm/sắp xếp · panel chi tiết · nghe clip nguồn (§7.4) · tạo giọng 3 bước trong modal · **giọng mẫu** (§7.1) | `giong_mau.py` · `/audio` mở tiền tố · `/giong/{id}` JSON | 1,5 ng |
| **P4** | 07 | **History**: lọc · thẻ nguồn · tóm tắt · đang xử lý · panel chi tiết · tải/chạy lại | route lọc mỏng | 1 ng |
| **P5** | 05 | **Projects**: `voice_project` + `voice_block` (+ `voice_block_version`) · CRUD · sinh theo khối · xuất ghép | 🔴 **có** | 3 ng |
| **P6** | 06 | **Batch**: `voice_batch` + `voice_batch_item` · CSV/dán · **kiểm hợp lệ trước khi thu tiền** · toả job · thử lại · zip | 🔴 **có** | 3 ng |
| **P7** | 09+10 | **Responsive · a11y · ma trận trạng thái**: empty/loading/error/disabled/success cho **mọi** trang · bàn phím · `aria-live` · điểm gãy 820/1200 | không | 1 ng |
| **P8** | 08 | **API**: quick start theo giọng · bảng `voice_id` · ví dụ 3 ngôn ngữ · liên kết sâu `/developers` · **đọc trạng thái tool thật** | không | 0,5 ng |
| **P9** | 11 | **Tổng kiểm + bàn giao**: gate đầy đủ · kiểm trên `https://app.lttstudios.com` bằng Playwright · cập nhật `NHAT_KY` + `ho_so_he_thong` | — | 0,5 ng |

**Vạch MVP giao diện = sau P4.** Bốn trang thật, chạy thật, không một ô giả.
P5/P6 là **sản phẩm mới**, không phải đánh bóng giao diện — chúng thêm 4 bảng và
một loại job, nên nên được chốt riêng.

---

## 9. Đã bỏ có chủ ý (không phải quên)

| Thứ trong ảnh | Vì sao bỏ | Mở lại khi nào |
|---|---|---|
| Tốc độ · Phong cách · Fast/Quality | ⛔ **Q119** — cache CUDA graph + lệch tông (#173) | chỉ sau cổng V10, và phải là một quyết định mới |
| Similarity / Pronunciation / Stability % | không đo gì cả; đó là V10 | khi V10 sinh ra số thật |
| Chip `Storage 256 GB / 1 TB` | không có hạn mức dung lượng cho khách | khi có hạn mức thật |
| Voice Family | không có khái niệm | nếu sản phẩm cần gom nhóm |
| Nút chọn Language VI/EN/Auto | engine tự xử; ba nút giả tệ hơn một câu thật | nếu engine nhận tham số ngôn ngữ |
| MP3 / chọn sample rate | cổng chỉ trả WAV một sample rate | khi thêm bước chuyển mã |
| Chapters trong Projects | một tầng lồng đổi lấy rất ít ở bản đầu | sau khi Projects chạy thật |
| `Destination D:\…` của Batch | khái niệm app desktop; ở SaaS là tải về | không bao giờ |
| Versions V1/V2/V3 ở Studio | phiên bản là khái niệm của **block** | ở P5 |

---

## 10. Sổ rủi ro

| # | Rủi ro | Mức | Cách chặn |
|---|---|---|---|
| R1 | Vẽ điều khiển backend không có ⇒ khách bấm, không gì xảy ra | 🔴 cao | §3 là hợp đồng; P7 rà lại từng điều khiển |
| R2 | Khai lại token màu trong một `voice.css` | 🟠 vừa | Không tạo tệp CSS mới. Style riêng đi vào một khối trong `ltt.css` hoặc `<style>` trang, **chỉ dùng `var(--…)`** |
| R3 | `routes.py` phình | 🟠 vừa | Trần 900 dòng / 30 handler, `tools/lint_app_contract.py` canh. P5/P6 đưa nghiệp vụ vào `services/` |
| R4 | Static mới không cache-bust | 🟠 vừa | §7.8; chốt trên URL công khai chứ không loopback (quy tắc 5b) |
| R5 | Projects/Batch nở thành DAW | 🟠 vừa | Đã cắt: bỏ chapters, bỏ ghi ổ đĩa. Pack cũng nói *"không biến thành DAW"* |
| R6 | Batch làm cạn credit khách vì lỗi ánh xạ | 🔴 cao | **Kiểm hợp lệ toàn bộ trước khi giữ đồng nào** (ảnh 04 đã vẽ đúng: `5/5 rows valid`) |
| R7 | Trang API dạy một lời gọi trả 403 | 🟠 vừa | Đọc trạng thái tool thật; hiện "sắp mở" nếu chưa |
| R8 | **Hai phiên cùng sửa `apps/ltt_voice/`** | 🔴 cao | §11 |
| R9 | Nạp model 19,4 s làm trang treo | 🟠 vừa | §7.1 — không gọi `/v1/voices` lúc dựng trang |
| R10 | Job nằm `queued` mãi vì thiếu làn `voice` | 🔴 cao | `LTT_WORKER_POOLS` phải có `voice`; `4-nghiem-thu.ps1` có chốt. Kiểm **trước** mỗi lần deploy |

---

## 11. 🔴 Giao ước file — có phiên khác đang sửa đúng app này

`git status` lúc lập kế hoạch (2026-08-31):

```
 M apps/ltt_voice/jobs.py        <- phien khac
 M apps/ltt_voice/routes.py      <- phien khac
 M apps/ltt_voice/dieu_khoan.py  <- phien khac
?? tests/test_343_khoa_kho_don_duoc.py
```

Nội dung: đổi hình dạng khoá kho sang `voice/out/{owner}/{job}/tieng.wav` để
`platform_core/job_content.py` dọn được. **Chồng trực tiếp lên §7.4 của tôi.**

⇒ Trước khi viết dòng mã đầu tiên của P1:
1. Hỏi 4 phiên `interactive` đang mở (`lttstudiosapp-80/7b/9e/a5`) phiên nào giữ `apps/ltt_voice/`.
2. Chốt ranh giới: **giao diện lấy `templates/` + static + `giong_mau.py`**;
   `routes.py` sửa bằng **Edit từng chỗ, không Write đè**; `jobs.py` ·
   `features.py` · `dieu_khoan.py` **không đụng** ở P1–P4.
3. Nếu họ vẫn đang chạy, đợi đợt của họ commit xong rồi mới bắt đầu.

*(Khuôn này đã chạy: bộ nhớ dự án ghi "Hai phiên cùng cây — giao ước file … 0 lần đè nhau".)*

---

## 12. Cách nghiệm thu — mỗi P phải qua

1. **Cadence chạy cổng: xem `docs/00_LTT_OPERATING_CONTRACT.md` §4.** Không
   chép lại tên cờ hay số giây vào đây.

   🔴 Hai dòng cũ ở đúng chỗ này đã sai **cả hai vế**, và chúng sai một cách
   không ai phát hiện được từ trong tệp này:

   | dòng cũ | thực tế 08/09/2026 |
   |---|---|
   | `gate.py --vong-lap` sau **mỗi** lần sửa | vòng lặp nay là `gate.py --doi`; `--vong-lap` trước 08/09 **luôn tự hạ cấp** xuống chạy đầy đủ |
   | gate đầy đủ "~5 phút" | **11,4 phút** trung vị, đo trên 43 bản ghi |

   ⭐ Đó là toàn bộ lý do dòng này nay là một **con trỏ**. Một con số chép tay
   không có cách nào tự biết nó đã cũ — và một cadence chép tay còn tệ hơn một
   bảng chép tay, vì nó không chỉ mô tả sai mà còn **bảo người ta làm sai**.

2. `python tools\gate.py` **một lần** khi mọi pha xong (hợp đồng §4.2) — không phải
   sau mỗi lần sửa hay mỗi pha.
   ⛔ Đừng dùng gate để dò lỗi: nó là công cụ ra **phán quyết**.
3. **Kiểm bằng trình duyệt thật** (Playwright), theo quy tắc 5b: soi nhanh ở
   `127.0.0.1:8100`, **chốt ở `https://app.lttstudios.com`** — Cloudflare có
   cache/CSP/minify riêng, và trang đẹp ở loopback vẫn có thể vỡ với khách thật.
4. Mỗi trang: **0 lỗi console · 0 request hỏng**.
5. Điểm dừng bàn phím + `aria-live` cho vùng đổi bất đồng bộ.
6. Test hồi quy render cho mỗi trang mới (khuôn `tests/test_340_ltt_voice_trang_render.py`).
7. Báo cáo theo khuôn của pack: **VERIFIED · DECISIONS · REUSED · CHANGED ·
   TESTED · RISKS/DEFERRED · NEXT READY**.

---

## 13. Ba câu hỏi cần chủ sản phẩm trả lời (không chặn P1–P4)

| # | Câu hỏi | Vì sao cần |
|---|---|---|
| Q-A | **Projects và Batch có nằm trong đợt này không?** Chúng là +4 bảng, +1 loại job, ~6 ngày — một sản phẩm mới, không phải một lớp sơn | quyết P5/P6 |
| Q-B | **Mở `speech.ltt` ra `/api/v1` khi nào?** Cần chạy `setup\cong_tac_tool_api.ps1` **rồi mới** deploy — sai thứ tự thì cờ vô tác dụng | quyết P8 |
| Q-C | **Giọng mẫu công bố những giọng nào?** Cần danh sách chốt + một câu mô tả mỗi giọng + clip nghe thử | chặn phần "Sample Voices" của P3 |

---

## 14. Nhật ký thi hành

Ghi **thứ đã đo được**, không ghi ý định. Mỗi mục nói rõ cái gì đã đổi so với kế
hoạch và **vì sao** — một kế hoạch không ghi lại chỗ nó sai là một kế hoạch sẽ bị
phiên sau đọc như sự thật.

### P1 — Vỏ + hệ thiết kế · ✅ 2026-08-31 · gate đầy đủ PASS (25/25)

Làm: 6 `NavEntry` (3 thật + 3 `built=False` có route thật) · `vo.py` với
`nav_key` bắt buộc · chip Engine/Hàng đợi · 4 partial · `voice.js` · ghi `nguon`
· `tests/test_344` (17 phép kiểm).

**Ba lỗi đang sống mà audit §2 KHÔNG thấy — cả ba chỉ lộ ra khi mở trình duyệt:**

1. 🔴 **Chín lớp CSS mà template dùng chưa từng tồn tại.** `.lv-form` `.lv-field`
   `.lv-bang` `.lv-dem` `.lv-actions` `.lv-ket-qua` `.lv-gia` `.lv-dk` `.lv-man`
   — app phát hành 31/08 với form và bảng **không có một dòng style nào**. Ba
   trang vẫn render, vẫn 200, vẫn xanh trong toàn bộ 69 phép kiểm.
   ⇒ Audit đọc mã tìm được "component nào dùng lại được"; nó **không** tìm được
   "component nào được gọi mà không tồn tại". Đó là hai câu hỏi khác nhau, và
   chỉ câu thứ hai cần một trình duyệt.
2. 🔴 **Thanh tab ra tiếng Việt trên bản EN.** `base.html` in `{{ entry.label }}`
   trần thay vì `{{ _(entry.label) }}` — và ba nhãn của Voice **đã có bản dịch
   sẵn trong catalog**, tức bản dịch nằm đó không ai đọc tới. Lỗi thuộc nền
   tảng, ảnh hưởng **mọi** app có tab.
3. Dấu `*` bắt buộc rơi xuống dòng dưới nhãn (text node trần cạnh `<strong>`
   trong flex-column).

**Hai lần bánh cóc bắt đúng:**
- `ltt.css` vốn **CRLF**; heredoc nối LF ⇒ `check_xuong_dong.py` đỏ. Ghi lại
  đúng kiểu HEAD ⇒ diff về đúng số dòng thêm, 0 dòng nhiễu.
- 31 chuỗi mới đẩy mốc dịch 343 → 374. **Dịch cả 31** rồi thêm tay vào `.po`.
  ⛔ Không chạy `i18n.py trich`: `msgmerge` đoán bản dịch và gắn `#, fuzzy`, mà
  `msgfmt` **bỏ qua** fuzzy — bản dịch đó không bao giờ tới mắt người dùng, nó
  chỉ *trông như* đã làm xong.

### P3 — Màn Giọng · ✅ 2026-08-31 (làm TRƯỚC P2)

🔄 **ĐỔI THỨ TỰ so với §8, và đây là lý do.** Kế hoạch xếp P2 (Studio) trước P3
(Giọng), nhưng chính §6 lại nói `_voice_chon.html` là **nút thắt** dùng chung ba
màn. Hai câu đó mâu thuẫn nhau. Giải: dữ liệu giọng mẫu (`giong_mau.py`) là một
**hợp đồng có phép kiểm đối chiếu engine** — chốt nó trước thì Studio tiêu thụ
một thứ đã đúng, thay vì dựng một bộ chọn chỉ có "giọng của tôi" rồi dựng lại.

✅ **Q-C đã tự trả lời được, không cần chặn chủ sản phẩm.** Engine có **hai mươi**
giọng dựng sẵn, đọc thẳng từ `vieneu/assets/voices_v3_turbo.json` — không cần
token, không nạp model, không gọi `/v1/voices`.

⭐ **Và dữ liệu thật cho ba mặt lọc TỐT HƠN thứ ảnh vẽ.** Ảnh 02 lọc
`VI / EN / Bilingual` + `All Families`; nền tảng không có hai khái niệm đó. Mỗi
preset lại mang sẵn **giới tính · vùng miền (Bắc/Trung/Nam) · phong cách
(tin tức/tự nhiên/kể chuyện)** — đúng ba câu người chọn giọng thực sự hỏi.
⇒ Ở đây ảnh không bị "cắt bớt", nó được **thay bằng thứ đúng hơn**. Đó là hình
dạng tốt nhất mà một mâu thuẫn ảnh-⇄-backend có thể có.

⚠️ `phong_cach` là **nhãn mô tả, không phải nút vặn** — `v3turbo.py`: *"Style is
deprecated on v3 Turbo … Kept only as voice metadata."*

**🔴 Một lỗ tôi tự tạo rồi tự bắt được — đáng ghi vì nó sẽ lặp lại.**

Để nghe lại clip gốc (ảnh 02 `Reference Audio`), tôi mở thêm tiền tố
`voice/{uid}/` ở cửa `/audio/`. Nghe thì đúng — thư mục của chính khách đó.
Nhưng `tham_chieu.khoa_bieu_dien()` ghi `voice/{uid}/{pid}/repr-<vân tay>.npz`
vào **cùng thư mục ấy**, và tệp đó chứa `speaker_emb`. `tables.py` nói thẳng:
*"KHÔNG BAO GIỜ ra ngoài."*

⇒ Cửa nay mở theo **TÊN TỆP** (`source.*`), không theo thư mục.
⇒ `tests/test_346` chốt bằng cách đặt một tệp `repr-*.npz` **có thật** vào kho
rồi đòi 404 — nới cửa ra là đỏ ngay, không phải một phép kiểm chỉ xanh vì tệp
không tồn tại.

⭐ Bài học tổng quát: **"thư mục của khách" không phải một ranh giới quyền.**
Nó là một ranh giới *sở hữu*. Hai thứ đó trùng nhau cho tới ngày có tệp nội bộ
nằm trong đó — và ngày đó đã đến từ trước, chỉ chưa ai mở cửa.

**Cũng đã đóng trong P3:** `preset` trước đây **không được kiểm ở đâu cả**. Một
tên bịa đi tới worker rồi SDK ném `ValueError` — mà `ValueError` không phải
`LoiNguoiGoi`, nên job **bị thử lại ba lần**. Phép kiểm đặt trong
`features.chuan_hoa`, **không** trong route: Public API đi thẳng xuống job.

### Còn lại

P2 (Studio) · P4 (Lịch sử) → **vạch MVP**. Rồi P5/P6 (cần chốt Q-A), P7, P8, P9.

⚠️ **Chưa deploy.** Production (`C:\LTTPlatform\app`) vẫn là bản cũ, nên chưa
chốt được trên `https://app.lttstudios.com` như quy tắc 5b đòi. Deploy cần chủ
sản phẩm bấm UAC ⇒ gộp **một lần** ở vạch MVP, không deploy sau mỗi pha.

### P2 — Màn Studio · ✅ 2026-08-31

Ba cột · bộ chọn giọng dùng chung (`_voice_chon.html`) · xem trước cách đọc ·
kết quả **tại chỗ** với sóng âm thật · Gần đây · chi tiết kỹ thuật.

Hai cửa mới: `POST /xem-truoc` (thuần tính toán) và `GET /ket-qua/{job_id}`.
Cửa thứ hai cần thiết vì `job_history.customer_payload` **cố tình không** trả
`result` lẫn `error` — nó là gói dùng chung cho mọi app.

**Kiểm thật đầu-tới-cuối, không mô phỏng:** nộp → poll → job hoàn tất → sóng âm
vẽ **12.448 pixel** từ giải mã WAV bằng Web Audio, 0 thư viện.

🔴 **MỘT LỖ BẢO MẬT ĐANG SỐNG, do một phép kiểm thủ tục bắt được.**

Tôi viết `test_xem_truoc_doi_csrf` như một thủ tục lấy lệ. Nó đỏ:
`assert 200 >= 400`.

`verify_csrf_token` **trả `bool`, nó không ném**. Và app này gọi nó rồi vứt kết
quả đi ở **cả bốn** cửa POST — `ltt_voice` là **app duy nhất trong kho** làm vậy;
mọi app khác đều `if not verify_csrf_token(...)`. Nên CSRF chưa bao giờ được thi
hành ở đây kể từ ngày phát hành, trên ba cửa có hậu quả: `/tao` tiêu credit,
`/giong/tao` ghi **cam kết pháp lý**, `/giong/{id}/tat` vô hiệu hoá giọng.

⭐ Vì sao nó sống sót: dòng gọi **trông đúng**, và chú thích đầu tệp còn ghi
*"kiểm quyền/CSRF"*. Đọc lướt thì mọi thứ ở đúng chỗ. Nó chỉ lộ ra khi có ai gửi
một token sai và **đòi** một mã lỗi.

⚠️ Mức nguy hiểm thật, nói cho đúng: cookie phiên đặt `same_site="lax"`, nên
trình duyệt đã chặn phần lớn đường khai thác. Phòng thủ nhiều lớp hụt một lớp,
không phải cửa mở toang.

⇒ Sửa cả bốn + **hai lớp bánh cóc**: phép kiểm HTTP từng cửa, và một máy quét
**AST** bắt hình dạng `verify_csrf_token(...)` đứng một mình. Đã chứng minh nó
đỏ với mã xấu và xanh với mã tốt.
*(Bản đầu của máy quét đọc từng dòng và tự bắt chính docstring của mình. Một
bánh cóc báo động vì văn xuôi là một bánh cóc sẽ bị tắt đi.)*

**Và một chỗ tôi tự nói quá, đã sửa.** Tôi viết rằng `1.250.000 đồng` bị tính
tiền như *"một triệu hai trăm năm mươi nghìn đồng"*. Đo thật: nó thành
`1250000` — **ngắn đi**. `doc_so_tran` đang **tắt có chủ ý** chờ đo ở V1. Đã sửa
chú thích ở ba chỗ; §7.2 của tài liệu này cũng nói quá theo cùng cách.

### P4 — Màn Lịch sử · ✅ 2026-08-31 → 🏁 **VẠCH MVP GIAO DIỆN**

Lọc trạng thái · nguồn · giọng, **phía máy chủ** bằng form GET.
🔄 Khác màn Giọng (lọc phía trình duyệt), và có lý do: lịch sử đọc theo trần,
nên lọc phía trình duyệt sẽ lọc trên một tập **đã bị cắt** — trả ra ít hơn sự
thật mà không nói gì. Đổi lại được URL chia sẻ được, và chạy khi không có JS.

Hai chỗ cố ý làm khác cách dễ:

- **Tỉ lệ lỗi tính trên lượt ĐÃ KẾT THÚC**, không trên tổng. Dùng tổng làm mẫu
  số khiến tỉ lệ lỗi tụt xuống mỗi khi nhiều việc xếp hàng — tức nó đẹp nhất
  đúng lúc hệ thống tắc nhất.
- **Trần 500 lượt được NÓI RA.** Test hạ trần xuống 5, gieo 6, đòi câu giải
  thích xuất hiện — và đòi nó **không** xuất hiện khi chưa cắt gì.

Job cũ hơn P1 không có `nguon` ⇒ hiện rỗng, **không đoán**.

---

### P7 — Đáp ứng · tiếp cận · ma trận trạng thái ✅ 2026-08-31

**Rà soát trước, sửa sau.** Đo trên trình duyệt thật ở **375 · 768 · 1280 px**,
cả sáu màn cộng hai màn chi tiết.

**Điều KHÔNG hỏng** (ghi lại để phiên sau khỏi đo lại): không màn nào tràn ngang
ở bất kỳ điểm gãy nào; không nút/liên kết nào thiếu tên; hai nút biểu tượng
(`×`, `⧉`) đã có `aria-label` từ trước; mọi ô nhập đều có nhãn; không `tabindex`
dương; viền focus bàn phím hiện rõ (1,6 px, có offset); `html lang` đúng.

⚠️ Và một cái **suýt** thành phát hiện sai: bộ dò đầu tiên của tôi báo "không nút
nào thiếu tên" — vì nó đọc `textContent`, mà `×` thì **có** nội dung. Nút biểu
tượng qua được một phép đo không hỏi đúng câu. Phải hỏi lại bằng `aria-label`
mới thấy chúng vốn đã ổn; nếu chúng **không** ổn thì phép đo đầu đã cho tôi một
lời trấn an sai.

**Ba thứ đã sửa:**

1. **`aria-pressed` cho bốn nhóm lọc** (Studio, Giọng ×4 nhóm, Chạy lô). Trước
   đó trạng thái "đang bật" chỉ tồn tại bằng lớp CSS `on` — con mắt thấy, trình
   đọc màn hình không. Màn Lịch sử dùng **`aria-current`** thay vì `aria-pressed`
   vì nút ở đó là `submit` làm **tải lại trang**, không phải công tắc.

   ⭐ Và nó được sửa bằng **một hàm** `batNut()` chứ không phải ba chỗ vá: ba
   vòng lặp riêng đang làm cùng một việc là ba chỗ để quên đồng bộ nút thứ tư.
   Đây là đúng bài học của lỗi `[hidden]` ở P4 — *đặt một luật trên cả lớp, đừng
   liệt kê đường hỏng*.

2. **Vùng `role="status"` cho hai màn chi tiết.** Studio có từ đầu; Dự án và
   Chạy lô thì không — nên tiến độ ở hai màn đó chỉ tồn tại bằng mắt. Thêm một
   `<p class="sr-only" role="status" aria-live="polite">` và một hàm `baoTin()`
   nói **một câu**, và chỉ khi câu ấy **đổi**.

   ⛔ Không đặt `aria-live` lên chính lưới con số: mỗi luợt hỏi ghi lại cả bốn ô,
   nên trình đọc màn hình sẽ đọc lại cả bốn **mỗi vài giây**.

   Đo thật: `Read 0 of 3 blocks.` → `Read 1 of 3 blocks.` → `Finished reading all
   3 blocks.`; lô: `Batch finished: 2 rows done, 1 failed.`

3. **Cỡ vùng chạm ≥ 24 px** cho `.lv-chon-them` (15 px) và link quay lại (17 px).
   ⚠️ Nói cho đúng: cả hai **gần như chắc chắn lọt ngoại lệ khoảng cách** của
   WCAG 2.5.8 vì chúng đứng một mình — nên đây **không** phải một vi phạm đã
   chứng minh, mà là một chỗ khó bấm bằng ngón tay. Sửa vì `min-height` không
   tốn gì, không vì một điều khoản.

**Và một lỗi thật, tìm ra ngoài phạm vi P7.** `python tools/gate.py --vong-lap`
đỏ ở `test_211`: hai bảng `voice_project` / `voice_block` chưa khai hạn giữ.
Khai xong thì lộ ra hệ quả:

🔴 **`voice_block.audio_key` sống mãi cùng dự án; tệp nó trỏ tới sống 30 ngày.**
`jobs` là CONTENT/30, nên `job_content.purge_expired` xoá tệp và đặt
`content_expired_at` — còn khối vẫn quảng cáo là có tiếng. Khách mở dự án cũ,
thấy một trình phát trông bình thường, bấm, **không có gì xảy ra**.

Nó có **hạn**: đúng 30 ngày sau lượt đọc đầu tiên của khách đầu tiên. Hôm nay
chưa ai dính, nên rất dễ ghi một dòng TODO rồi quên.

Sửa bằng **một thẩm quyền duy nhất** `du_an.duong_tieng()` — một truy vấn cho cả
danh sách, trả `id khối → URL`, và khối có job hết hạn thì **không có URL**.
Trước đó **năm** chỗ tự dựng URL bằng `if k.audio_key` (hai ở Dự án, ba ở Chạy
lô, kể cả nút ZIP): sửa đúng nghĩa là phải nhớ đủ năm. Có test cấm chỗ thứ sáu.

⭐ Và ô trống **được nói ra**: khối `xong` mà không còn tệp hiện câu *"Tệp tiếng
đã hết hạn sau 30 ngày. Đọc lại để có tệp mới."* Một ô trống ở chỗ đáng lẽ có
trình phát trông y hệt một lỗi hiển thị — tức tôi đã dời cái hỏng im lặng chứ
chưa gỡ nó, nếu dừng ở bước trước.

**Chốt:** `tests/test_352_ltt_voice_tiep_can.py`, 19 phép kiểm. Đã **thử lùi ba
sửa đổi** để chắc test bắt được — cả ba đều đỏ đúng chỗ.


### P8 — Màn API ✅ 2026-08-31

**Màn thứ sáu, và nó cố tình mỏng.** Khu `/developers` đã có khoá · hạn mức ·
giá · nhật ký · playground · tài liệu, cho **mọi** công cụ. Chép bất kỳ thứ nào
về đây là tạo bản thứ hai của một sự thật, và bản thứ hai sẽ trôi.

Chỉ giữ thứ **chỉ đúng với giọng nói**: mã giọng của chính khách · 20 tên giọng
dựng sẵn · trần 1.500 ký tự **kèm lý do** (trần chất lượng, không phải trần kỹ
thuật — Q118) · một ví dụ đúng cho đúng công cụ. Bốn thứ còn lại là **đường dẫn**
sang khu Lập trình viên, không phải bản sao.

⭐ Và tôi suýt vi phạm quy tắc ấy trong **chính lượt viết nó**: bản nháp đầu của
`_p_api.py` truyền một hằng số giá xuống khuôn mẫu. Giá của Voice tính theo
**giây tiếng ra**, không theo ký tự vào — nên mọi cách viết nó ở một trang hướng
dẫn đều là một phép ước, và một phép ước in cạnh một lệnh `curl` sẽ được đọc là
một lời hứa. Đã gỡ, và có `test_364::test_man_api_khong_in_gia` giữ chỗ trống ấy.

**🔴 Chốt quan trọng nhất: ví dụ chỉ hiện khi cửa THẬT SỰ mở.**

`speech.ltt` khai `api_exposed=True` — điều đó **không** nghĩa là nó đang mở.
Cổng thật là `LTT_PUBLIC_API_TOOLS`, và hôm nay công cụ này không có trong đó.
Màn đọc cấu hình **đang chạy** mỗi lần dựng trang, không hằng số, không cache.

Hai chiều sai, cả hai đều có tiền lệ đắt:

- *Nói ĐÓNG khi đang MỞ* — `CLAUDE.md` đã dính **hai lần**, cùng một hàng, cùng
  một hướng.
- *Nói MỞ khi đang ĐÓNG* — chưa xảy ra nhưng đắt hơn, vì nạn nhân là **khách**:
  một `curl` nằm sẵn sẽ được chép bất kể câu chữ quanh nó, rồi trả 404 từ
  Cloudflare hoặc từ cổng — không `request_id`, không dòng nào trong
  `public_api_requests`, không tra được. Khách đọc thành "khoá của tôi sai", tạo
  khoá mới, vẫn 404, và **phía ta không thấy gì cả**.

⇒ Nên chốt không phải *"có một câu cảnh báo"* mà là **không có lệnh chép được**.
`test_364` chạy cả bốn tổ hợp, gồm cả *"một công cụ KHÁC đang mở"* — nếu màn chỉ
hỏi `LTT_PUBLIC_API` thay vì hỏi đúng công cụ, nó đã báo MỞ suốt trên production
(bốn công cụ đang mở ở đó).

**Cơ chế giữ chỗ đã gỡ.** `vo.CHUA_XAY` + `routes/_p_chua_xay.py` không còn phục
vụ ai khi màn cuối được xây. `test_344` **đổi việc** thay vì bị xoá: nó nay canh
"không tab nào còn `built=False`", vì rủi ro đã đổi chiều — ai thêm
`built=False` bây giờ sẽ tạo ra một tab dẫn tới 404.

**⚠️ Và việc gỡ đó làm gãy hai đường 404**, phát hiện bởi hai phép kiểm **không
thuộc màn API**:

🔴 `ltt_voice_chua_xay.html` **không chỉ** là trang giữ chỗ. Hai cửa 404 của Dự
án và Chạy lô đã mượn nó làm trang thông báo chung từ P5/P6 — nhưng **cái tên
không nói điều đó**. Tôi đọc cái tên, tin cái tên, xoá tệp, và hai đường gãy.

⭐ Bài học đáng giữ hơn cái tên: **một tệp được dùng lại cho việc thứ hai mà
không được đổi tên là một cái bẫy đã cài sẵn** cho người dọn dẹp sau. Nay nó tên
`ltt_voice_thongbao.html` — theo việc nó **làm**, không theo việc nó **từng
làm** — và badge "đang xây" đã bỏ, vì badge ấy bảo khách chờ một thứ sẽ không
bao giờ tới trong khi sự thật là họ gõ nhầm địa chỉ.

**Và một lỗi im lặng nữa, chỉ trình duyệt thấy.** Bản đầu của khuôn API **quên
`{% block scripts %}`**. Mọi phép kiểm HTTP đều xanh, vì HTML **đúng** — chỉ
hành vi sai: nút chép hiện đầy đủ, bấm được, có con trỏ tay, và **không làm gì
cả**. Tệ hơn một nút không có, vì không có nút thì người ta đi bôi đen. Bắt được
khi bấm thật trong trình duyệt (`dataset.ganChep` là `undefined`). Chốt lại bằng
một phép kiểm bắc cầu hai tệp: khuôn trang nào có nút chép — kể cả **gián tiếp**
qua `_voice_ma.html` — thì khuôn ấy phải nạp `voice.js`.

**Chốt:** `tests/test_364_ltt_voice_man_api.py`, 8 phép kiểm; `test_344` cập nhật.
Đã soi cả hai nhánh trên trình duyệt thật (nhánh "mở" bằng một tệp đánh dấu
trong scratchpad, đã tắt sau khi soi) và xác nhận nút chép lấy đúng 6 dòng lệnh
thật từ khối mã, không từ một bản sao trong thuộc tính.


## 15. Điều rút ra sau bốn pha

**Năm lỗi đang sống, và không lỗi nào bị bộ test cũ bắt.** Ba lỗi chỉ thấy được
bằng trình duyệt; một lỗi chỉ thấy khi viết một phép kiểm thủ tục; một lỗi do
chính bánh cóc của kho bắt.

⭐ Mẫu chung đáng ghi: **cả năm đều là mã "trông đúng".** Không cái nào là một
dòng sai rõ ràng. `verify_csrf_token(...)` trông như đang kiểm. `class="lv-form"`
trông như có style. `{{ entry.label }}` trông như đã dịch. `skipif` trông như
một sự thận trọng. `voice/{uid}/` trông như thư mục của chính khách.

⇒ Audit đọc mã trả lời được *"component nào dùng lại được"*. Nó **không** trả
lời được *"thứ này có thực sự làm điều nó trông như đang làm không"*. Câu thứ
hai cần một trình duyệt, hoặc một phép kiểm **đòi** một kết quả cụ thể.
