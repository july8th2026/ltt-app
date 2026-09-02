# 01 — RÀ SOÁT HIỆN TRẠNG (đo, không tin báo cáo cũ)

Ngày 2026-09-02 · nhánh `claude/ltt-voice-autonomous-supervisor-1c3f95`
Gói yêu cầu: `LTT_VOICE_AUTONOMOUS_SUPERVISOR_PACK_V4`

---

## 0. Hai việc phải sửa trước khi đo được gì

### 0.1 Nhánh này KHÔNG có app — đã sửa

Worktree được tạo trên `master`. `apps/ltt_voice/` **không tồn tại ở đó**.
App sống trên `admin-mvp-v3` (nhánh của bản checkout chính), đi trước `master`
**466 commit**.

Nhánh này chưa có commit riêng nào (`HEAD == master`), nên đã `merge --ff-only
admin-mvp-v3`. Không mất gì, không viết lại lịch sử.

⚠️ Ghi lại vì nó sẽ tái diễn: **worktree mới mặc định mọc từ `master`, còn công
việc thật sống ở `admin-mvp-v3`.** Ai mở worktree tiếp theo cho app này phải
kiểm `git ls-tree --name-only HEAD apps/` trước khi tin rằng "app chưa được xây".

### 0.2 Không có engine thì không đo được gì — đã dựng đường đo riêng

`LTTStudioVoice` (production) giữ cổng 8120 và **GPU 0**; token của nó nằm trong
`C:\LTTPlatform\secrets\` mà tiến trình này không đọc được (ACL, đúng thiết kế).

Thay vì xin bí mật, đã dựng **một sidecar thứ hai của riêng cây làm việc**:

| | production | đường đo của phiên này |
|---|---|---|
| cổng | 8120 | **8121** |
| GPU | 0 (`CUDA_VISIBLE_DEVICES` mặc định) | **1** (`CUDA_VISIBLE_DEVICES=1`) |
| token | secrets/app.env | `dev-sidecar-token-v4` (tự đặt) |
| CSDL | PostgreSQL production | `D:\_lttvoice_dev\dev.db` (sqlite) |
| kho tệp | `C:\LTTPlatform\data` | `D:\_lttvoice_dev\store` |

Hai tiến trình **không dùng chung gì cả**. Model nạp 39,9 s, chiếm 342 MB trên
card 16.311 MB.

⇒ Không có HARD BLOCKER nào ở đây. Bí mật production **không cần thiết** cho
vòng này, và việc không xin nó là lựa chọn đúng chứ không phải né tránh.

---

## 1. Ba cái bẫy đã trả giá trong lúc dựng đường đo

Ghi lại vì cả ba đều **trông như lỗi sản phẩm** trong khi không phải.

### 1.1 `MAX_PATH` — lỗi ở bước GHI, sau khi engine đã sinh xong

Đặt kho tệp trong scratchpad làm job chết với

```
FileNotFoundError: [WinError 3] The system cannot find the path specified:
  ...\scratchpad\voice-dev\store\voice\out\<uid-36>\<job-36>
```

Thư mục cha **có tồn tại**. Thứ vượt trần là tổng đường dẫn: scratchpad ~150 ký
tự + khoá kho `voice/out/<uuid>/<uuid>/tieng.wav` ~85 ký tự > **260**.

⛔ Triệu chứng chỉ đến ở bước ghi, tức **sau** khi GPU đã chạy 12 giây và engine
đã trả về âm thanh — nên nó đọc như "kho hỏng" chứ không như "đường dẫn dài".
Đã chuyển kho về `D:\_lttvoice_dev`. Không phải lỗi production (`C:\LTTPlatform\data`
ngắn), nhưng là bẫy chắc chắn với mọi phiên chạy dev từ scratchpad.

### 1.2 Tiến trình nền chết theo shell

Sidecar khởi động bằng `&` trong một lượt gọi shell **chết khi lượt gọi kết
thúc**. Triệu chứng ở worker là `WinError 10061 connection refused` — đọc y hệt
"chưa cài dịch vụ". Phải chạy nền đúng cách (`run_in_background`).

### 1.3 🔴 Chip "Engine sẵn sàng" NÓI DỐI — đây là lỗi sản phẩm thật

```python
def san_sang() -> bool:
    return bool(_token())        # apps/ltt_voice/sidecar_client.py
```

Nó chỉ kiểm **biến môi trường có được đặt hay không**, không kiểm cổng có trả
lời hay không. Đo được trong phiên này: chip hiện **"Engine sẵn sàng"** màu xanh
trong khi sidecar đã chết, và mọi lượt bấm Tạo đều hỏng với *"Máy tạo tiếng nói
chưa sẵn sàng"*.

⇒ Hai câu trên cùng một trang mâu thuẫn nhau, và câu **to hơn, xanh hơn** là câu
sai. Đây đúng loại lỗi mà gói V4 gọi là *functional truth* — xếp **P1**, sửa ở
Phase 03.

---

## 2. Hiện trạng đo được — không phải đọc từ tài liệu

### 2.1 Bề mặt điều hướng

Manifest khai **5 tab**, và đó đúng là thứ trình duyệt hiện:

`Tạo tiếng nói` · `Giọng của tôi` · `Dự án` · `Lịch sử` · `API`

✅ **Batch đã biến mất khỏi bề mặt sản phẩm** — không tab, không route
(`routes/__init__.py` không còn `_p_lo.py`). Dư lượng còn lại chỉ là nhãn
`"lo": N_('Chạy lô')` trong `NHAN_NGUON` (`_chung.py:46`) và vài dòng chú thích.

⛔ **Nhãn đó phải GIỮ**, không phải dọn: hàng lịch sử cũ vẫn mang `nguon="lo"`,
xoá nhãn là để khách nhìn thấy chuỗi thô `lo`. Đây là dư lượng *đúng*.

### 2.2 29 route thật

| mảng | route |
|---|---|
| Tạo | `GET ""`, `GET "/"`, `POST /xem-truoc`, `GET /ket-qua/{job}`, `POST /tao`, `GET /tu-dien`, `POST /tu-dien/them`, `POST /tu-dien/{id}/xoa` |
| Giọng | `GET /giong`, `POST /giong/tao`, `POST /giong/{id}/tat` |
| Dự án | `GET /du-an`, `POST /du-an/tao`, `POST /du-an/{id}/xoa`, `GET /du-an/{id}`, `POST …/sua`, `POST …/khoi/them`, `POST …/khoi/{b}/sua`, `POST …/khoi/{b}/xoa`, `POST …/nhap`, `POST …/khoi/{b}/doc`, `POST …/doc-tat-ca`, `GET …/trang-thai`, `POST /du-an/luu-tu-studio`, `GET …/khoi/{b}/phien-ban` |
| Lịch sử | `GET /lich-su`, `POST /lich-su/{job}/doc-lai` |
| API | `GET /api` |
| Audio | `GET /audio/{key:path}` |

### 2.3 Chuỗi đầu-cuối ĐÃ CHẠY THẬT

Bấm nút trên trình duyệt thật, không phải test:

```
web(8131) → job → worker → GPU 1 → sidecar(8121) → WAV 775.724 byte
12,0 giây · thời lượng 8,08 s · credit 5.000 → 4.998
```

Tiền khớp: 2 credit, đúng như `credit_cost` handler báo về.

### 2.4 Điểm mạnh sẵn có (đừng xây lại)

- DNA thị giác **đã là nền tối + nhấn đỏ**, đồng hướng với ảnh tham chiếu.
- Studio có: bộ chọn giọng có lọc (nguồn/làn), tìm giọng, tốc độ 6 nấc, từ điển
  phát âm, xem trước cách đọc, nhập TXT, đếm ký tự, **sóng âm + trình phát**,
  tải WAV/MP3, thời lượng, credit đã tính, danh sách "Gần đây".
- 20 giọng dựng sẵn có thật, kèm mã giọng + nút chép.
- Dự án có mô hình khối đầy đủ (thêm/sửa/xoá/đọc từng khối/đọc tất cả/phiên bản).
- **0 lỗi console** trên cả 5 trang.
- Giá tính theo **giây tiếng thật**, không theo ký tự — và màn API cố ý không in
  giá, có test chốt.

---

## 3. Bảng chênh lệch với ảnh tham chiếu

### 3.0 ⛔ Bộ ảnh tham chiếu có hai tệp đặt sai tên

| tệp | nội dung thật |
|---|---|
| `01_STUDIO.png` | Studio ✔ |
| `02_VOICES.png` | Voices ✔ |
| `03_PROJECTS.png` | **History** ✘ |
| `04_HISTORY.png` | **Batch** ✘ |
| `05_API.png` | API ✔ |

⇒ **Không có ảnh nào cho Projects**, và ảnh Batch duy nhất lại mô tả màn mà
`START_HERE.md` nói là **đã loại**.

Phân giải theo chính thứ tự nguồn chân lý của gói (mục 3 của contract: prompt
đứng trên ảnh; `AUTONOMOUS_UI_GATE`: *"Reference image is a direction, not a
ceiling"*):

- **Bỏ ảnh Batch.** Không dựng lại Batch.
- **Projects xây không có ảnh**, theo `07_PROJECTS_AUTONOMOUS.md` và theo DNA
  thị giác của bốn màn còn lại.
- Ảnh `03` dùng làm tham chiếu cho **History**.

Không phải HARD BLOCKER: mâu thuẫn tự phân giải được bằng quy tắc của chính gói.

### 3.1 Studio (ref `01_STUDIO.png`)

| # | Chênh lệch | Mức |
|---|---|---|
| S1 | Bố cục lãng phí bề ngang: cột phải chỉ ~330 px, dưới nó là **~600 px trống**; cột giữa hết nội dung ở nửa trang | P1 |
| S2 | ~~Thiếu bộ chọn ngôn ngữ đầu ra (Auto/VI/EN)~~ → **BỎ, xem §3.1b** | *bỏ* |
| S3 | Không **nghe thử giọng** trước khi tạo (ảnh có nút play trên từng giọng) | P1 |
| S4 | Không **chép mã giọng** ngay trong bộ chọn của Studio (Voices có, Studio không) | P2 |
| S5 | Không có **VERSIONS / phiên bản** của cùng một đoạn văn bản | P2 |
| S6 | Không có bảng **CHI TIẾT** (độ trễ, tần số mẫu, định dạng, request id) | P2 |
| S7 | Không có **Lưu vào dự án** từ Studio (backend `POST /du-an/luu-tu-studio` **đã có** — chỉ thiếu nút) | P1 |
| S8 | Không đánh số bước 1–6 như ảnh; thứ tự thị giác yếu | P2 |
| S9 | MODE Fast/Quality và DELIVERY STYLE trong ảnh **không có backend thật** | *bỏ* |
| S10 | Ảnh ghi 5000 ký tự; thật là **1500** (trần chất lượng Q118, có lý do) | *giữ 1500* |

### 3.1b ⛔ S2 bị BỎ — một bộ chọn ngôn ngữ đầu ra sẽ là NÚT GIẢ

Ảnh `01_STUDIO.png` vẽ một nhóm `Auto / VI / EN` ở bước 2. Nó không có gì ở
dưới để nối vào.

`lan_ngon_ngu.py` đã chốt điều này bằng số đo, 01/09/2026: VieNeu-TTS v3 Turbo
**song ngữ thật** — model card khai `language: ["vi","en"]`, train trên ~10.000
giờ Anh–Việt, và có code-switching trong cùng một câu. Đo trên engine thật, ASR
nghe lại đúng từng chữ. Engine **không nhận tham số ngôn ngữ nào cả**; nó đọc
thứ nó thấy.

⇒ Ba nút ấy sẽ không điều khiển gì. Dựng chúng là vi phạm thẳng mục 8 của hợp
đồng gói: *"Không tạo control không hoạt động chỉ để giống ảnh."*

⭐ Và thứ **đã có** lại đúng hơn thứ ảnh vẽ: `Mọi làn / Tiếng Việt / Tiếng Anh`
là bộ lọc **danh sách giọng**, hiện thực một chốt **chất lượng** (clip nguồn
tiếng Việt phục vụ văn bản tiếng Việt) chứ không phải một giới hạn kỹ thuật.
Nó có tác dụng thật, đúng chỗ: chọn đúng giọng từ đầu thì không bao giờ chạm
tới cảnh báo lệch ngôn ngữ.

### 3.2 Voices (ref `02_VOICES.png`)

| # | Chênh lệch | Mức |
|---|---|---|
| V1 | **Không nghe thử được giọng nào** — không route preview, không nút play. Đây là thiếu sót lớn nhất của trang | P0 |
| V2 | ~~Panel chi tiết là khung rỗng~~ → **SAI, đã sửa bên dưới** | ~~P0~~ → P1 |
| V3 | Không có "Dùng trong Studio" / "Mở API" từ thẻ giọng | P1 |
| V4 | Biểu mẫu tạo giọng là một khối dài ở **đáy trang**, không phải một luồng | P1 |
| V5 | Không sắp xếp, không đổi lưới/danh sách, không phân trang | P2 |
| V6 | Không sửa tên giọng (chỉ có tắt) | P2 |
| V7 | Thanh **Quality/Similarity %** trong ảnh — chỉ làm nếu đo thật được, không bịa số | *xét ở P03* |

### 3.3 Projects (không có ảnh)

| # | Chênh lệch | Mức |
|---|---|---|
| P1 | Trang rỗng hoàn toàn khi chưa có dự án — chưa đánh giá được màn thật | — |
| P2 | Cần dựng dữ liệu thật rồi mới chấm | — |

### 3.4 History (ref `03_PROJECTS.png`)

| # | Chênh lệch | Mức |
|---|---|---|
| H1 | Lọc chỉ có trạng thái + thời gian. Ảnh có **giọng · ngôn ngữ · nguồn** | P1 |
| H2 | Không có panel **chi tiết mục được chọn** | P1 |
| H3 | Không có sóng âm/trình phát trong từng hàng | P1 |
| H4 | Không **dùng lại thiết lập** (chỉ có `doc-lai` = đọc lại nguyên si) | P1 |
| H5 | Không phân trang, không đổi số dòng/trang | P2 |

### 3.5 API (ref `05_API.png`)

| # | Chênh lệch | Mức |
|---|---|---|
| A1 | Không có **Try API** tương tác | P1 |
| A2 | Không có ví dụ cURL/Python/JS *(cố ý: chỉ hiện khi cửa thật mở — `test_364` chốt)* | *đúng như thiết kế* |
| A3 | Khoá/usage/logs trỏ sang `/developers` *(cố ý, tránh bản sao thứ hai của sự thật)* | *giữ* |
| A4 | Không liệt kê **giọng dựng sẵn kèm mã dùng cho API** ở dạng bảng chép được | P2 |

---

### 3.2b 🔴 SỬA MỘT KẾT LUẬN SAI CỦA CHÍNH BẢN RÀ SOÁT NÀY

Mục `V2` ở trên viết panel chi tiết là *"khung rỗng, không có gì làm nó đầy"*,
và xếp **P0**. **Sai.**

Panel chạy đầy đủ. Bấm một thẻ giọng thì `voice.js::moChiTiet` điền tên · nhãn
loại · ba tính chất · mã dùng khi gọi kèm nút chép · trạng thái · nút *"Dùng
giọng này"*; với giọng nhân bản còn thêm số lượt, số phút, lần dùng cuối, danh
sách clip gốc phát được, và biểu mẫu tắt giọng. `chi_tiet_cho_trang()` nạp sẵn
toàn bộ số liệu ấy vào trang nên một cú bấm **không gọi mạng**.

⛔ **Vì sao tôi kết luận sai, và đó mới là điều đáng ghi.** Tôi không bấm. Tôi
đọc `document.body.innerText` rồi tìm chuỗi *"Chọn một giọng để xem chi tiết"*,
thấy có, và kết luận panel rỗng. Phép đo ấy sai: chuỗi đó nằm trong một nút
`[hidden]` vẫn còn trong DOM.

⭐ Đúng cái lớp lỗi mà chính gói V4 dựng lên để bắt — *"Audit đọc mã trả lời được
component nào dùng lại được; nó không trả lời được thứ này có thực sự làm điều
nó trông như đang làm không"* (`VOICE_UI_EXECUTION_PLAN.md` §15). Tôi đã thay
một trình duyệt bằng một phép tìm chuỗi, và nhận đúng thứ một phép tìm chuỗi
cho: một câu trả lời tự tin về một thứ nó không đo.

**Điều còn đúng sau khi bấm thật:** panel **mỏng** so với ảnh tham chiếu — thiếu
trình nghe thử, thiếu bảng metadata, thiếu hàng thao tác (Mở API · Sửa · Lưu
trữ), và với giọng mẫu thì chỉ có năm dòng. Đó là **P1 làm dày**, không phải P0
dựng mới.

---

## 4. P0 / P1 / P2 gom lại

**P0 — chặn cổng phát hành**
1. `V1` Voices không nghe thử được giọng → cần route preview + phát.

**P1**
2. `1.3` Chip "Engine sẵn sàng" nói dối — phải hỏi cổng thật.
3. `S1` Bố cục Studio lãng phí bề ngang.
4. `S3`/`S7` Nghe thử giọng trong Studio; nút Lưu vào dự án (backend đã có).
5. `V3`/`V4` Dùng-trong-Studio, luồng tạo giọng.
6. `H1`–`H4` Lọc, chi tiết, trình phát, dùng lại thiết lập ở History.
7. `A1` Try API.

**P2** — S4·S5·S6·S8 · V5·V6 · H5 · A4.

**Bỏ có chủ ý** — MODE Fast/Quality, DELIVERY STYLE slider, bộ chọn ngôn ngữ đầu ra (§3.1b), trần 5000 ký tự,
Batch, `temperature/top_k/top_p` ra giao diện (Q119).

---

## 5. Bản đồ phụ thuộc → thứ tự thi hành

```
P03 backend  ──► preview giọng (route + kho mẫu)      ─┐
             ──► san_sang() hỏi cổng thật              │
             ──► ngôn ngữ đầu ra (nếu engine đỡ được)  ├─► P05 Studio
             ──► metadata chi tiết cho một lượt        │
             └─► dùng lại thiết lập từ một lượt cũ    ─┴─► P08 History
                                                        └─► P06 Voices
P04 shared UI ──► trình phát + sóng âm dùng chung  ────► cả 5 màn
                                                        └─► P07 Projects
                                                        └─► P09 API
```

⇒ Thứ tự: **03 → 04 → 06 (Voices, có P0) → 05 (Studio) → 08 → 07 → 09 → 10.**

Đảo 05/06 so với số thứ tự của gói vì hai P0 duy nhất đều nằm ở Voices, và
Studio dùng lại chính bộ chọn giọng + trình phát mà Voices sẽ dựng.

---

## 6. Điều kiện dừng đã kiểm

| điều kiện HARD BLOCKER | có? |
|---|---|
| thiếu bí mật/token | không — đã dựng đường đo riêng, không cần secret production |
| quyền tài khoản ngoài | không |
| quyết định pháp lý/thương mại | không |
| nguy cơ mất dữ liệu thật | không — sqlite riêng, kho riêng, GPU riêng |
| mâu thuẫn yêu cầu không tự giải được | không — mâu thuẫn ảnh Batch/Projects giải được bằng quy tắc của chính gói (§3.0) |
| thiếu phần cứng | không — GPU 1 rảnh, model nạp được |

⇒ **Chạy tiếp, không dừng.**
