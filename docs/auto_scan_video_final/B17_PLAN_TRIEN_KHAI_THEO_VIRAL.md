# B17 — PLAN TRIỂN KHAI: dựng chuỗi bước ASV theo đúng cách Viral làm

> **Chủ của**: thứ tự bước và **cổng gọi kết nối** cấp triển khai.
> B16 là **thiết kế** (8 giai đoạn, vì sao). B17 là **lệnh thi công**: mỗi việc kèm
> neo dòng trong `localize.py` để agent ⛔ không phải suy diễn.
> Tham chiếu thô: `B17_THAM_CHIEU_VIRAL/W1_CHUOI_GOI.md` (432 hàng nguyên văn) ·
> `W2_CONG_KET_NOI.md` (kênh phụ) · `W3_MOT_LAN_ENCODE.md` (hợp đồng `burn_phude`).

⛔ **Nguồn chân lý là mã Viral, ⛔ không phải tệp này.** Mọi hàng đều có neo dòng;
đọc mã trước khi sửa. `D:\Viral` là **CHỈ ĐỌC**.

## Khai độ phủ (bằng số) — để ⛔ không ai tưởng plan này biết nhiều hơn thực tế

| Đại lượng | Số | Nguồn |
|---|---|---|
| Biên `localize.chay()` | `:15021`–`:20576` (5.556 dòng) | W1, đã kiểm 3 neo ngẫu nhiên khớp từng ký tự |
| Câu lệnh **cấp 1** đã trích nguyên văn | **150 / 150** = 100% | W1 |
| Câu lệnh cấp 2 (trong 69 khối) | 282 | W1 |
| Biên `burn_phude()` | `:6560`–`:8532` (1.973 dòng) | W3 |
| Đọc nguyên văn trong `burn_phude` | ~340 / 1.973 ≈ **17%** | W3 tự khai |
| ⛔ **CHƯA đọc** trong `burn_phude` | dựng dải che chi tiết `:6670-7263` (~590 dòng) + thân `khung_filter_parts` / `text_wm_parts` / `_srt_to_ass_pos` | W3 tự khai |

⚠️ ⇒ Việc nào **chạm vùng chưa đọc** thì trong §6 được đánh `[ĐỌC TRƯỚC]`: agent
phải đọc nguyên văn vùng đó **trước** khi sửa, ⛔ không dựa vào plan này.

---

## 0b. QUY TẮC VẬN HÀNH PLAN NÀY — chủ dự án chốt 28/09/2026

> *"Tiếp tục theo quy trình. ⛔ Không dừng lại giữa các pha."*

### Điều phối: ⛔ KHÔNG dừng giữa các pha

Làn xong ⇒ **gộp → chạy lưới → mở làn kế**, ⛔ không xin duyệt, ⛔ không tóm tắt tiến
độ rồi chờ. Hết **mọi** pha thì MỘT gate → gộp `main` → deploy (nếu cần) → **báo**.

⛔ **Dừng CHỈ khi**: gate đỏ · thao tác ⛔ không đảo được · thay đổi chưa commit ⛔ không
rõ của ai · rủi ro bảo mật. (Hợp đồng §10.)

⭐ **HỎI chỉ khi câu trả lời ⛔ không nằm trong mã, trong số đo, hay trong nguồn**: đánh
đổi **sản phẩm** · hai đường **đều đúng** mà dữ liệu ⛔ không chọn hộ · việc **chỉ chủ dự
án làm được** (bí mật, quyền, dashboard ngoài).

### Lưới sau mỗi lượt gộp — theo LOẠI lượt gộp, ⛔ không một cỡ cho tất cả

| Lượt gộp | Phải chạy |
|---|---|
| thuần `docs/` | `pre-commit run --all-files` (**9 giây**, nhóm *vừa*, ⛔ không cần khoá) |
| có **mã** | `scan_source_secrets` · `check_mypy` · `check_silent_except` (**< 45 giây**) **+** test nhắm **+** `pre-commit` |

🔑 Ba bộ kiểm hình dạng bắt loại lỗi **test nhắm ⛔ KHÔNG THỂ bắt**: mã **đúng hành vi,
sai bất biến toàn kho**.

⛔ **KHÔNG chạy `gate.py` trong phiên** — không L1, không L2, không L3. Gate **MỘT lần**
ở **cuối plan**, **MỘT cấp**. Hết một pha / một làn / một lượt gộp `main` ⛔ **không phải**
cuối plan.

### Một tệp một chủ — và `pipeline.py` là sổ đăng ký dùng chung

Mỗi làn MỘT worktree + MỘT nhánh. ⛔ Không hai làn sửa cùng tệp.
🔴 `apps/auto_scan_video/pipeline.py` có **chủ duy nhất** là làn `P1-0`. Làn khác cần
đổi `CHUOI`/`sau=` thì **báo điều phối**, ⛔ không tự sửa — mỗi lượt đổi `sau=` trả một
lần giá vân tay (§6).

### 🔴 Trước khi giao một dòng việc: va vào MÃ, ⛔ không chỉ vào plan trước

Một dòng trong bảng việc là một **MỆNH LỆNH** — agent ⛔ không cân nhắc, nó thi hành.
28/09 luật này sinh ra sau **hai** ca thật trong một buổi (`edit_plan`, gộp 3 QC): plan
ra lệnh đúng điều mà **mã cùng ngày đã cấm, kèm lý do**.

```bash
sed -n '1,30p' <tep chinh cua dong viec>      # docstring dau tep = noi cac phien
                                              # truoc ghi phan quyet
grep -rn "⛔ KHONG\|⛔ KHÔNG" --include=*.py <thu muc> | grep -i "<viec>"
```

⭐ Lượt quét ấy trả **cả hai chiều**: nó tìm ra lệnh **cấm** (bỏ `edit_plan`, gộp QC) và
cả **tiền lệ đồng thuận** (*"Pha 26 — Renderer fusion"* ở `phu_de.py:8-20`) để agent tra
thay vì thiết kế lại.

### 🔴 Làn tự khai NỢ ⇒ mở làn trả nợ NGAY

Một làn báo *"giá trị đã có nhưng chưa ai đọc"* / *"ngoài phạm vi sở hữu"* là một
**cần gạt chết**. Điều phối mở làn trả nợ trong **cùng pha**, ⛔ không đẩy vào *"sau
này"*. Tiền lệ: `P0-a` → `P0-a2`.

---

## 1. TRẬT TỰ VĨ MÔ THẬT của `localize.chay()` — 14 khối, đúng thứ tự thực thi

Rút từ 150 câu lệnh cấp 1. Cột **ta có?** so với `pipeline.CHUOI` hiện hành.

| # | Khối | Neo | Việc | Ta có? |
|---|---|---|---|---|
| 1 | Chuẩn hoá tham số + ENV | `15039`–`15236` | dựng `burn_kw`, gate `che_chu`+`zoom≥1.3`, chọn `_ocr_video` | một phần, rải rác |
| 2 | **RESET kênh phụ** | `15280`–`15288` | `_LAST_VIDEO_SLOW`, `_LAST_TIME_WARP`, `_LAST_DUB_ONSETS`, `_LAST_ASR_PARTIAL`, `_KET_ASR_HONG` | ⛔ KHÔNG — xem §4 |
| 3 | Chọn model ASR | `15250`–`15256` | `medium`+`ASR_TURBO` → turbo; chặn `large*` | có (`whisperx_runner`) |
| 4 | **Mở SỔ KẾ TOÁN CÂU** | `15312` `_sk_bat_dau(video)` | đếm câu vào/ra từng bước, in `◄── RƠI N CÂU Ở ĐÂY` | có, **khác chỗ**: `tools/asv_so_ke_toan_cau.py` chạy NGOÀI |
| 5 | Đo tài nguyên + giao thức tiến độ | `15332` `_ResMon`, `15358` `print("STAGE:batdau")` | mỗi stage một mốc CPU/GPU/RAM/VRAM | có (job_runner) |
| 6 | Phát hiện ngôn ngữ + ngắn mạch cùng-ngữ | `15361`–`15479` | `cung_ngon_ngu` → bỏ dịch | có |
| 7 | **KHỞI 4 LUỒNG NỀN** | `15611`, `15710`, `15783`, `15880` | xem §3 — **đây là khác biệt lớn nhất** | ⛔ KHÔNG |
| 8 | Băm video + dựng 4 KHOÁ CACHE | `15732` `_vhash`; `15943` scan, `15983` ocrbox, `16068` trans, `16111` srt | bốn khoá độc lập, mỗi khoá một lớp | một phần (`cache_chung.py`) |
| 9 | **NHÁNH LỚN: ASR + dịch** | `16235` `if srt_co_san:` / `16381` `else:` → `18110` | 1.729 dòng | có (`transcribe`+`content_process`) |
| 10 | Dựng `ket` + **thoát sớm `chi_dich`** | `18119`, `18123` | hợp đồng trả về duy nhất | ⛔ KHÔNG có chế độ chạy lẻ |
| 11 | Giải phóng model ASR | `18137`–`18139` | `phu_de._MODEL = None; gc.collect()` | ngầm (tiến trình chết) |
| 12 | Phân giọng (diarization) | `18154`–`18199` | `_segs_diar`, `doc_giong_json` | có |
| 13 | **CHE CHỮ** | `18204` `if che_chu:` → `18914` | 710 dòng: OCR + dải che | ⛔ KHÔNG (B16 định thêm `vung_che`) |
| 14 | **LỒNG TIẾNG ⊕ BURN — `if/elif` LOẠI TRỪ NHAU** | `19186` `if lam_long_tieng:` → `20464`; `20464` `elif burn:` → `20514` | dub tự burn bên trong | 🔴 ta tách `compose` + `render` NỐI TIẾP |
| — | Dọn + xong | `20514`–`20576` | `_dep_demucs`, `LOCALIZE_DONE`, `return ket` | có |

### 🔴 Phát hiện gánh cả plan: khối 14 là `if/elif`

`19186 if lam_long_tieng:` … `20464 elif burn:` — **loại trừ nhau**. Đường lồng
tiếng **tự burn phụ đề bên trong nó**, ⛔ không đi qua một bước burn riêng.

⇒ Chuỗi của ta có `compose` **rồi** `render` **nối tiếp** là một **hình dạng khác**,
⛔ không phải một thứ tự khác.

### 🔴 ĐÍNH CHÍNH LỚN NHẤT của tệp này — *"ta encode hai lần"* là SAI

Vòng một tôi viết câu ấy và suy nó ra từ **hình dạng chuỗi**, ⛔ không đo. Đo (28/09):

| Giai đoạn | Làm gì với ĐIỂM ẢNH | Bằng chứng |
|---|---|---|
| `compose` | ⛔ **không chạm** — dựng `ban_dung.json` + trộn `master.wav`, đo LUFS | `pipeline.py:365-384` |
| `render` | ⛔ **không chạm** — **`-c:v copy`**, nguyên văn *"Hình ⛔ không bị chạm tới"* | `ket_xuat.py:8,30-33` |
| `image_finish` | ✅ **lần encode hình DUY NHẤT** | `che_do_render.py:133-143` (một bộ codec, ⛔ không pass 2) |

⇒ 🔑 **Ta ĐÃ chỉ có MỘT lần encode hình.** Và việc tách hai giai đoạn chính là **để**
GĐ1 ⛔ không phải chạm điểm ảnh: `ket_xuat.py:30-33` ghi rõ hai hệ quả — **⛔ không dùng
GPU** (nên `RENDER` nằm làn `asv_media`, ⛔ không khai `tai_nguyen`) và **⛔ không mất chất
lượng** (*"hình của khách ra đúng bằng bit nó vào"*).

🔴 ⇒ **Gộp `compose`+`render` vào lượt encode là một BƯỚC LÙI**, ⛔ không phải tối ưu: nó
kéo một lượt CPU rẻ (`-c:v copy`, vài chục giây cho video 10 phút) vào bên trong một
lượt **giữ lease GPU**, và bắt việc trộn tiếng phải chờ card.

⇒ Việc thật của P2 **hẹp hơn nhiều**: ⛔ không phải *gộp ba giai đoạn*, mà là **sửa THỨ
TỰ NODE và thêm node còn thiếu bên TRONG lượt encode đã có một mình**. Đối chiếu sẵn ở
`W3_MOT_LAN_ENCODE.md` §2.5.

---

## 2. BỐN LUỒNG NỀN — khác biệt lớn nhất, và nó ⛔ không phải "tối ưu thêm"

Viral khởi **bốn** việc dài **trước** nhánh ASR rồi `join` ở **phút cuối cần dùng**.
Số đo (từ W1 + đọc trực tiếp bốn chỗ join):

| Luồng | `start` | `join` | Chồng lấn | Hạn (ENV) | ⭐ QUÁ HẠN thì sao |
|---|---|---|---|---|---|
| `_ct_som_th` che-tính-sớm | `15880` | `18289` | ~2.400 dòng | `CHE_TINH_SOM_JOIN=180` | `_r=None` → dò **đồng bộ** như cũ |
| `_cdd_th` che-động (OCR nền) | `15783` | `18839` | ~3.050 dòng | `CHE_DONG_JOIN_TO` | `_segs=None` → lùi **blur TĨNH** |
| `_tn_th` tách-nhạc (demucs) | `15710` | `20016` | ~4.300 dòng | `DEMUCS_TIMEOUT=2400` | ba nhánh, xem 🔴 dưới |
| `_xn_th` xoá-nhạc (demucs) | `15611` | `20478` | ~4.867 dòng | `DEMUCS_TIMEOUT=2400` | tách lại tuần tự, **tiền tố tạm khác** |

🔑 **Mỗi luồng có một ĐƯỜNG LUI ĐỒNG BỘ đầy đủ.** Luồng nền ⛔ không phải nguồn
duy nhất của dữ liệu ấy — nó chỉ là đường **nhanh hơn**. ⇒ Quá hạn **⛔ không** làm
hỏng lượt chạy, chỉ mất phần đã chồng lấn.

### 🔴 `:20478` — "BỎ CHỜ ≠ DỪNG ĐƯỢC" (bài học ta sẽ gặp Y HỆT)

Nguyên văn lý do trong mã: luồng nền là **daemon, ⛔ KHÔNG có cờ dừng**. Hết hạn
`join` ta **thôi chờ**, nhưng nó **vẫn đang chạy và vẫn đang ghi file**. Vì
`_audio_xoa_nhac` dùng đường dẫn tạm **CỐ ĐỊNH** `<ten><ptmp>_xnhac_goc.wav`:

- nhánh tuần tự bên dưới **ghi đè đúng file luồng nền đang đọc**;
- `finally` của bên này **xoá file của bên kia**;
- trên Windows còn **khoá file** ⇒ `TachNhacThatBai` ⇒ mất cả giọng.

⇒ Cách chữa của họ: **đổi tiền tố tạm** cho nhánh lui (`_ptmp + "_l2"`). Hai bên
⛔ không bao giờ chạm cùng một file.

### 🔴 `:20016` — ca đã từng rơi vào IM LẶNG, họ vá 30/08/2026

Quá hạn mà luồng nền **còn sống**: trước đây ⛔ không nhánh nào log, rồi tách lại
ngay bên dưới ⇒ **HAI demucs cùng lúc**. Nay là nhánh `else` tường minh.

⚠️ Cùng họ [[hai-trang-thai-gop-thanh-mot-gia-tri]]: *"⛔ không có kết quả"* và
*"chưa xong"* là **hai** trạng thái; gộp chúng làm một thì mất đúng khả năng phân biệt
cần để chọn đường lui.

### Trong mô hình của TA điều này thành gì

Mỗi giai đoạn của ta là **một tiến trình riêng** ⇒ luồng khởi ở giai đoạn 1 ⛔ không
`join` được ở giai đoạn 6. Bốn luồng phải thành **bốn JOB song song**, và:

| Của Viral | Của ta |
|---|---|
| `threading.Thread(daemon=True)` | job trong hàng đợi, `parent_run_id` |
| `_xn_kq[0]` (holder trong bộ nhớ) | **artifact** trên đĩa + trường `outputs` |
| `th.join(timeout=T)` | vòng chờ job với hạn `T`, rồi đi đường lui |
| `th.is_alive()` | trạng thái job ≠ `SUCCEEDED`/`FAILED` |
| đổi tiền tố tạm `_ptmp+"_l2"` | 🔴 **đường lui phải có `run_id` riêng trong tên tệp tạm** |

🔴 **Bắt buộc**: job bị bỏ chờ **vẫn chiếm GPU/CPU và vẫn ghi đĩa**. Ta có
`gpu_lease.py` — đường lui ⛔ không được xin lease khi lease cũ chưa hết, nếu ⛔ không
sẽ **hai demucs** đúng như ca 30/08 của họ, nhưng tệ hơn vì ta có lease thật.

---

## 3. 🔴 CHẶN KIẾN TRÚC: hai trong bốn luồng nền ta ⛔ KHÔNG copy được nguyên dạng

Đây là thứ phải quyết **trước** khi agent nào động vào chuỗi.

**Viral**: ⛔ **không có khoá GPU nào** (`grep Lock()` trong `localize.py`: 12 khoá,
⛔ không một khoá nào cho GPU). demucs chạy **cuda** (`_demucs_worker.py:50`) **song
song** whisper **trên cùng một card**, dựa vào biên VRAM. Thứ họ chia khẩu phần là
**CPU** (`_asr_cpu_slot`) — và demucs khi đã ở GPU thì **bỏ qua** khe CPU
(`_xn_gpu = (phu_de._whisper_device_nhe()[0] == "cuda")`).

**Ta**: `platform_core/gpu_lease.py:293-300` — `UNIQUE(host, gpu_uuid)`,
`exclusive=True`, nguyên văn chú thích: *"một job chiếm TRỌN card… Bên kia chia phần
theo VRAM nên nếu ⛔ không nói rõ, họ sẽ nhét thêm job vào card của ta"*. Máy A có
**một** 5060 Ti (`docs/HAI_MAY_A_VA_B.md`).

⇒ **Hai luồng demucs (`_xn_th`, `_tn_th`) ⛔ KHÔNG thể thành hai JOB song song** —
job thứ hai sẽ ⛔ không bao giờ giành được lease, và `acquire` trả `None` ⇒ nó **xếp
hàng**, ⛔ không phải chồng lấn. Copy nguyên dạng sẽ cho một chuỗi **trông song song
mà chạy tuần tự**, và ⛔ không phép đo nào của ta hiện bắt được điều đó.

### Quyết (và cái giá nếu sai)

| Luồng | GPU? | Làm gì | Vì sao |
|---|---|---|---|
| `_cdd_th` che-động (OCR) | ⛔ không (RapidOCR, đã chặn 6 lõi) | ✅ **JOB song song** | ⛔ không xin lease ⇒ chồng lấn thật |
| `_ct_som_th` che-tính-sớm | ⛔ không | ✅ **JOB song song** | như trên |
| `_xn_th` xoá-nhạc (demucs) | ✅ | 🔑 **CÙNG MỘT JOB với ASR** | một lease, hai luồng trong một tiến trình — **đúng hình dạng Viral** |
| `_tn_th` tách-nhạc (demucs) | ✅ | 🔑 **CÙNG MỘT JOB với ASR** | như trên |

🔑 Gộp demucs + whisper vào **một job GPU** ⛔ không phải sáng kiến mới: `apps/asv_gpu/jobs.py:3`
đã khai *"Hai giai đoạn thực sự cần GPU: tách nguồn tiếng (demucs) và chép lời (whisper)"*.
Ta chỉ đang **làm đúng** điều tệp ấy đã nói.

**Cái giá nếu quyết sai**: hai model cùng card có thể vượt VRAM ⇒ OOM giữa lượt.
`apps/asv_gpu/manifest.py:27` đã đo: *"VRAM là thứ KHÔNG tăng theo độ dài"*, demucs
RSS phẳng ~2,6 GiB. ⇒ Rủi ro thật là **RAM hệ thống**, ⛔ không phải VRAM. Phép đo
chốt: VRAM đỉnh + RSS đỉnh khi cả hai cùng chạy — **đo một lượt ở §7**, ⛔ đừng đoán.

⛔ **KHÔNG đổi `gpu_lease` sang chia-theo-VRAM.** Nó phục vụ lưu lượng thật và đứng
cạnh sổ sách (`CLAUDE.md` luật về `gpu_lease.py`). Đổi mô hình lease để tiện một app
là đánh đổi sai chiều.

### ⚠️ Thu hẹp: "JOB song song" ở bảng trên nói về **LEASE**, ⛔ không nói về **THỨ TỰ**

Hai hàng `_cdd_th` / `_ct_som_th` chỉ khai một điều: chúng ⛔ không xin lease GPU nên
**được phép** chồng lấn. Chúng ⛔ **không** khai rằng mọi phần của che-chữ chồng lấn
được với `transcribe`.

🔴 `W2_CONG_KET_NOI.md` §2.2 đã đo ra điều ngược lại cho **một nửa** của che-chữ:
phần **bám hộp OCR** đọc `_ocr_boxes` (sinh ở `:16630`, lưu `.ocrbox.json` `:16669`)
⇒ **buộc sau** `transcribe`. Chỉ phần **dò dải TĨNH** (`detect_blur_band`, đọc **video**
thuần) mới song song thật — Viral đã gỡ `srt=` khỏi `_band_key` ngày 29/08 kèm bằng
chứng AST (`:15808-15812`).

⇒ **`vung_che` ở ta là HAI giai đoạn**, ⛔ không phải một:

| Giai đoạn | `sau=` | Đọc | Song song với `transcribe`? |
|---|---|---|---|
| `vung_che_tinh` | `(MEDIA_PREPARE,)` | chỉ **video** | ✅ có |
| `vung_che_bam` | `(TRANSCRIBE, VUNG_CHE_TINH)` | `hop_ocr.json` | ⛔ không |

🔴 **Vì sao đây là lỗi nguy nhất trong cả plan nếu làm sai**: gộp một giai đoạn rồi
khai `🔀 || transcribe` thì nhánh bám-hộp chạy với `_ocr_boxes = []`, và ca ấy
⛔ **KHÔNG NỔ** — `:16376` ghi rõ khối nới dải + net an toàn chống lộ chữ **bị tắt im
lặng**. Kết quả: **chữ Trung lộ trên bản giao khách**, log báo `✔ Xong`.
⇒ Đúng họ [[phep-kiem-xanh-tren-thu-da-hong]] và [[ma-phong-thu-cho-ca-khong-the-xay-ra]] đảo chiều.

---

## 4. CỔNG KẾT NỐI — ba ĐƯỜNG NGƯỢC CHUỖI, và luật cứng cho mỗi cái

Bảng đủ 68 hàng ở `W2_CONG_KET_NOI.md`. Đây là ba hàng **quyết định plan**.
⭐ Mẫu số đúng, để ⛔ không ai sợ sai chỗ: Viral **đọc 401** tên biến môi trường nhưng
chỉ **GHI 15** ⇒ 386 cái là **cấu hình một chiều**, ⛔ **không** phải đường truyền.

### 4.1 🔴🔴 `DUB_WPS` / `DUB_FIT_LEN` / `DUB_NEN` — bản DỊCH phụ thuộc TỐC ĐỌC của GIỌNG

```
Viral GHI  :15101, :15102, :15136        (đầu chay() = GĐ1 của ta)
Viral ĐỌC  dich_gemini_web:147, 2132, 2141   (GĐ5 content_process của ta)
Nội dung   thuộc tính của GIỌNG mà GĐ6 voice_synthesis mới dùng
```

Trong DAG B16 đây là **chu trình**: `5 → 6` theo `sau=`, mà `5` cần một đại lượng của `6`.

⭐ **Cách giải của Viral là cách DUY NHẤT đúng cho ta**: họ ⛔ **không đo giọng lúc
chạy**. `_wps_giong_that:1946` **tra bảng đã đo trước** (`:15109` —
`id 1,56× · en 1,51× · es 1,36× · vi 1,35× · pt 1,33× · ko 1,29× · fr 1,25×`) ⇒ nó là
**hàm thuần của `settings.voice` + hằng số trong mã** ⇒ tính được ở **dòng đầu**.

| Luật cứng | |
|---|---|
| ✅ LÀM | `settings` **dẫn xuất**, tính ở GĐ1, đi vào **vân tay GĐ5** |
| ⛔ KHÔNG | *"GĐ6 đo giọng rồi báo lại GĐ5"* — DAG vỡ và ⛔ **không ai thấy nó vỡ**: `settings.giong_id` vẫn có giá trị nên GĐ5 vẫn chạy, chỉ **neo sai** |
| ⚠️ COPY CẢ | `min()` **một chiều** (`:15112-15117`, nguyên văn *"CHỈ SIẾT, KHÔNG NỚI"*). Cài hai chiều ⇒ giọng nhanh **nới** neo ⇒ bản dịch dài hơn ⇒ nén nặng hơn ⇒ **ngược ý** |

🔑 Đây là mảnh còn thiếu của cả chuỗi *"nói dồn"* anh đặt ra: ngân sách thời gian phải
vào **bản dịch** (GĐ5), ⛔ không chỉ vào bậc thang nắn (GĐ7). Nắn là **cứu chữa**;
neo đúng ở GĐ5 là **phòng bệnh**.

### 4.2 🔴🔴 `_ocr_boxes` — đã xử ở §3, tách `vung_che_tinh` / `vung_che_bam`

Bằng chứng cơ học W2 đưa thêm: `:18216` dùng `locals().get("_ocr_boxes")` — tức chính
Viral cũng ⛔ không bảo đảm tên ấy tồn tại. Ca thiếu **im lặng**.

### 4.3 🔴 `.dubsync.vi.srt` — GĐ7 sinh thứ đóng CÙNG VAI với đầu ra GĐ5

```
GĐ5 content_process -> <ten>.vi.srt           (:15507, ghi :17940)
GĐ7 timing_align    -> <ten>.dubsync.vi.srt   (:20327)
GĐ8 render          -> cần CẢ HAI: :20357-20360 (0 cue -> lùi bản gốc)
                                   :20387-20391 (burn dubsync lỗi -> burn gốc)
```

⛔ không ngược theo **thứ tự**, nhưng ngược theo **quyền sở hữu**.

| Luật cứng | |
|---|---|
| ✅ LÀM | GĐ7 xuất artifact **khoá riêng** `phu_de_canh_giong.srt`; GĐ8 ghi `outputs["phu_de_da_dung"] ∈ {canh_giong, goc}` |
| ⛔ KHÔNG | ghi đè khoá của GĐ5 — vân tay GĐ5 giữ nguyên trong khi nội dung đã đổi ⇒ **vân tay NÓI DỐI**, lượt chạy lại GĐ8 với cache dùng bản sai |
| ⚠️ CÙNG HÌNH DẠNG | `_ln.wav` · `_af.wav` · `_nhac_warp.wav` — mỗi cái **một khoá**, ⛔ không ghi đè |

### 4.4 Hai chỗ Viral tự ghi là CÒN NỢ — ⛔ đừng copy cái nợ

| Chỗ | Nội dung | Ta làm gì |
|---|---|---|
| chú thích `:15221-15225` | **SAI**: `burn_phude` chỉ **ĐỌC** `CHE_BLUR_FIT_X`/`CHE_BAND_FIT`, ⛔ không ghi | ⛔ đừng thiết kế đường ngược ⛔ không tồn tại |
| `.boxes.json` `:18699` | **HAI bộ sinh khác nghĩa ghi CHUNG một khoá**; họ tự ghi *"còn nợ, cần đổi CẤU TRÚC"* | ta tách **hai khoá** từ đầu — rẻ hơn nợ |

⚠️ Cùng họ [[luat-thieu-ve-ngoai-le-nhan-theo-so-nguoi-doc]]: một chú thích sai trong
mã nguồn tham chiếu **nằm chờ**, và bán kính của nó = số agent đọc nó.

---

## 5. MỘT LẦN ENCODE — thứ tự filter THẬT là 10 node, ⛔ không phải 4

Hợp đồng đầy đủ (32 tham số, ⛔ không phải 25 như brief tôi giao — chính chú thích gốc
thừa nhận số này tăng theo thời gian): `W3_MOT_LAN_ENCODE.md`.

🔴 **Dòng tóm tắt `:7264` trong mã Viral ⛔ KHÔNG ĐỦ.** Nó ghi
`[biến đổi hình] → [watermark] → [che+burn sub] → [setpts]` và chỉ đúng cho nhánh
⛔ **không** có `co_khung`/`co_reframe`. Thứ tự thật, đọc từ `:7264-8425`:

| # | Node | Neo | Bật khi |
|---|---|---|---|
| 0 | `format=yuv420p` (ép chuẩn màu khi hwaccel GPU bật) | `:7271-7275` | `_hw_vf` |
| 1 | `extra_vf` (hflip/eq…) | `:7276-7277` | `extra_vf` |
| 2 | watermark **ẢNH**: `scale=` + `overlay` | `:7278-7282` | `co_wm` |
| 3 | lật toạ độ che theo x (**⛔ không chèn filter, chỉ tính lại số**) | `:7284-7292` | `mirror`/`hflip` |
| 4 | **`blur_boxes` ô XOÁ — TRƯỚC mọi node che** | `:7304-7315` | `blur_boxes` |
| 5 | che chữ (`blur_band`/`blur_segs`) **+** `subtitles=` burn phụ đề | `:7320-8202` | `co_blur`; `vi_srt and not _sub_sau_khung` |
| 6 | `khung_filter_parts`: logo / ô xoá còn lại / banner | `:8244-8262` | `co_khung` |
| **7** | **`setpts` tốc độ** — đơn hoặc piecewise `_emit_speed` | `:8210-8267` | `co_speed`/`_has_warp` |
| **8** | **reframe tỉ lệ**: nền mờ + `overlay` giữa khung | `:8276-8360` | `co_reframe` |
| **9** | **`text_wm` watermark CHỮ** | `:8370-8375` | `co_text_wm` |
| — | (nhánh audio, ⛔ không cùng chuỗi) `atempo` → `amix` nhạc nền → `alimiter` | `:8376-8425` | — |

### 🔑 Điều này SỬA cách B16 phát biểu nguyên tắc trục

B16 viết *"trục thời gian và cả hai trục khung đổi CUỐI CÙNG"*. Đúng, nhưng thiếu
**thứ tự giữa chúng**, và thứ tự ấy là bắt buộc:

> ⭐ **trục THỜI GIAN (node 7) trước trục KHUNG (node 8-9).**

Lý do nguyên văn của họ (`:6846-6852`, `:8208`): node che/overlay nối **TRƯỚC**
`setpts`, nên `t` mà ffmpeg dùng để đánh giá `enable=between(t,a,b)` **vẫn là timeline
GỐC** — đúng nguyên tắc *"bake mốc GỐC"*. Đặt `setpts` sớm hơn thì **mọi** mốc che và
mốc phụ đề lệch, và ⛔ **không** phép kiểm nào của ta hiện bắt được (ảnh vẫn ra, chữ vẫn
có, chỉ **sai chỗ**).

### Hai luật cứng nữa, đều đã trả giá bằng bug thật

| Luật | Neo | Bằng chứng của họ |
|---|---|---|
| **XOÁ trước, CHE sau** (node 4 trước node 5) | `:7293-7303` | chốt 04/09: che chạy trước làm watermark **bị chép xuống bản sao**, đo thật `y≈500 → y≈620` |
| **phụ đề / text_wm vẽ SAU reframe** | `:7103-7146`, `:8198`, `:8257` | reframe sau burn ⇒ cỡ chữ tính theo `W,H` **GỐC** rồi bị co theo hệ số reframe ⇒ chữ nhỏ đi. Có hàm bù `_wh_bu_reframe` (`:7109`) cho nhánh ⛔ không hoãn được |

### Ba câu W3 trả lời — vẫn dùng được, nhưng đọc lại với đính chính §1

⚠️ Brief tôi giao W3 hỏi *"gộp `render`+`image_finish`"*. §1 đã cho thấy câu hỏi ấy
**sai tiền đề** (`render` ⛔ không chạm điểm ảnh). Ba câu trả lời của nó **vẫn đúng và
vẫn cần** — chúng nói về `burn_phude`, tức về **lượt encode duy nhất** của ta.

| Câu | Trả lời (W3, đọc trực tiếp) |
|---|---|
| Cắt cuối nằm trong hàm? | **Có**, nhưng là trần `-t` **toàn cục**, ⛔ không phải node filter ⇒ ⛔ **không** áp thẳng được cho `ke_cat.py` của ta (ta cắt **nhiều đoạn rời**) |
| Kiểm lộ chữ sau render? | `_kiem_lo_sau_render` gọi ở **dòng áp chót**, SAU khi ffmpeg thành công. 🔴 Nhưng **giá trị trả về bị bỏ qua** và nó **mặc định TẮT** (`CHE_RESIDUAL_CHECK=0`) ⇒ ⛔ đừng tính nó là một cổng |
| Hợp đồng trả về? | `bool`; caller đọc **trực tiếp** làm điều kiện rẽ (`if burn_phude(...)`, `ok_lt = burn_phude(...)`) |

### ⚠️ `VC_WARP_MAX_DOAN` — brief tôi giao đã SAI, ghi lại cho đúng

Nó **⛔ không thuộc `burn_phude`**. Nó sống trong `_ghep_track_khop` (`:8965-9835`, nhánh
**audio**), mặc định hiện hành **1200** (`:9451`), ⛔ không phải 150. Con số `400→150` ở
`:9289` là **chú thích lịch sử**. Ai thiết kế theo 150 sẽ chặn ở 1/8 độ phủ thật.

---

## 6. CHUỖI MỚI — vẫn **13** giai đoạn, và cái thắng ⛔ KHÔNG phải số bước

🔴 **B16 đuổi theo một con số sai.** Nó khai *"8 giai đoạn"*, tôi sửa thành 9. Soát
28/09 cho thấy **gần như mọi giai đoạn của ta đều có lý do đã đo**, nên phép trừ ra:

| Đổi | Δ | Vì sao được / ⛔ không được |
|---|---|---|
| `audio_prepare` + `transcribe` → `gpu_asr` | **−1** | một lease GPU, hai luồng trong một tiến trình (§3) |
| + `vung_che_tinh`, `vung_che_bam` | **+2** | W2 §2.2 buộc tách, ⛔ không gộp được |
| − `edit_plan` | **−1** | W4 đo: giá có biên, tự lành — và **đi kèm miễn phí** với lượt đổi `sau=` |
| ~~gộp `compose`+`render`+`image_finish`~~ | **0** | 🔴 **⛔ KHÔNG** — `render` đã `-c:v copy`, xem đính chính §1 |
| ~~gộp 3 QC~~ | **0** | 🔴 **⛔ KHÔNG** — xem 🔴 dưới |
| | **= 13** | |

⇒ ⭐ **Cái ta thắng là BA thứ khác, ⛔ không phải bước ngắn hơn:**
**(a)** song song thật qua DAG (§2-3) · **(b)** thứ tự node đúng trong lượt encode đã có
(§5) · **(c)** ba đường ngược chuỗi được nối đúng (§4).

### 🔴 ⛔ KHÔNG gộp 3 QC — quyết định đã ghi, kèm lý do

`tests/test_402_asv_mach_doc_gia.py:247-251`, nguyên văn:

> `qc_ai` được thêm SAU `qc`, ⛔ không thay `qc`: QC kỹ thuật là một cổng **PHÁT HÀNH
> tất định** — đo được, chạy lại cho cùng kết quả — còn QC bằng AI hỏi một bên **CHỦ
> QUAN và TRẢ TIỀN**. Gộp hai thứ vào một giai đoạn là làm một lần chạy hỏng vì một
> phán quyết chủ quan **trước khi ai kịp xem phép đo tất định nói gì**.

Và `qc_do_luong` (`:258-260`) thiếu venv đo thì **vẫn `succeeded`** với mọi bộ đo
`khong_kha_dung` — một cổng hạ cấp có chủ đích. ⇒ **Làn P1-c bị BỎ.**

### Chuỗi đích

```
1 media_prepare ─┬─> 2 gpu_asr ───────┬─> 4 content_process ─> 6 voice_synthesis ─> 7 timing_align
                 │                    │                                                 │
                 └─> 3 vung_che_tinh ──┴─> 5 vung_che_bam ──┐                            v
                     (🔀 song song 2)                        │                  8 compose (audio)
                                                             │                            v
                                                             └────────────> 10 image_finish <── 9 render (-c:v copy)
                                                                                 │
                                                                                 v
                                                                    11 qc -> 12 qc_do_luong -> 13 qc_ai
```

| # | Giai đoạn | `sau=` | Đổi gì | Chạm điểm ảnh? |
|---|---|---|---|---|
| 1 | `media_prepare` | — | + `toc_doc_giong` ✅, + **cắt đầu**, + 4 khoá cache | ⛔ |
| 2 | `gpu_asr` | `(1,)` | **gộp** `audio_prepare`+`transcribe` | ⛔ |
| 3 | `vung_che_tinh` | `(1,)` | **mới** — chỉ đọc video | ⛔ |
| 4 | `content_process` | `(2,)` | neo bằng `toc_doc_giong` của GĐ1 | ⛔ |
| 5 | `vung_che_bam` | `(2, 3)` | **mới** — đọc `hop_ocr.json` | ⛔ |
| 6 | `voice_synthesis` | `(4,)` | **giữ nguyên** (TTS của ta) | ⛔ |
| 7 | `timing_align` | `(6, 2)` | bậc thang nắn + `phu_de_canh_giong.srt` | ⛔ |
| 8 | `compose` | `(7,)` | giữ — dựng bản dựng + `master.wav` | ⛔ |
| 9 | `render` | `(8,)` | giữ — **`-c:v copy`**, CPU, ⛔ không lease | ⛔ |
| 10 | `image_finish` | `(9, 5)` | 🔑 **10 node đúng thứ tự §5** + cắt cuối `-t` | ✅ **DUY NHẤT** |
| 11-13 | `qc` → `qc_do_luong` → `qc_ai` | nối tiếp | **giữ cả ba** | ⛔ |

### Bảng việc — mỗi làn MỘT worktree, MỘT nhánh, ⛔ không hai làn sửa cùng tệp

| Làn | Việc | Tệp (chủ duy nhất) | Model | Chặn bởi |
|---|---|---|---|---|
| ~~P0-a~~ | ✅ **XONG** `toc_doc_giong` — hàm thuần, siết một chiều, đường lui tường minh | `cai_dat.py`, `ho_so_dich.py` | sonnet | — |
| ~~P0-b~~ | ✅ **XONG** — đã ĐO, ⛔ không sửa mã → `W4_...md` | — | sonnet | — |
| ~~P0-a2~~ | ✅ **XONG** — `ngan_sach_do_dai(..., toc_doc_giong=)` siết một chiều; `long_tieng.py:300` gọi **trong vòng `for` từng đoạn** | `long_tieng.py`, `ngon_ngu.py` | opus | — |
| **P0-a3** | **Nợ của P0-a2**: nối chỗ gọi còn lại `dich_thuat.py:374` (`min` của `min` — chỉ được SIẾT) | `dich_thuat.py` | sonnet | P0-a2 ✅ |
| ~~P0-c~~ | 🔴 **⛔ KHÔNG LÀM** — đo ra một bản giao SAI mà QC **đồng thuận**; 28 phép đo giữ lại làm bẫy | `tests/test_4973..4977` | opus | — |
| 🔑 **P1-0** | **MỘT lượt đổi `CHUOI`**: gộp `audio_prepare`+`transcribe` · khai `vung_che_*` · bỏ `edit_plan` · nối lại **mọi** `sau=` | `pipeline.py` (**chủ DUY NHẤT**) + `tests/test_402*` | **opus** | W4 ✅ |
| **P1-a** | **THÂN** job `gpu_asr` (một lease, hai luồng) | `apps/asv_gpu/jobs.py`, `manifest.py` — ⛔ không chạm `pipeline.py` | **opus** | P1-0 |
| **P1-b** | **THÂN** hai module `vung_che_tinh` / `vung_che_bam` | `apps/auto_scan_video/vung_che_*.py` (mới) — ⛔ không chạm `pipeline.py` | **opus** | P1-0 |
| ~~P1-c~~ | 🔴 **BỎ LÀN** — `test_402:247-251` cấm gộp QC tất định với QC chủ quan trả tiền | — | — | — |
| **P2** | 🔑 Sửa **THỨ TỰ NODE** + thêm node thiếu **bên trong** lượt encode đã có một mình | `che_do_render.py` | **opus** | P1-0, P1-b |
| **P3** | `phu_de_canh_giong.srt` khoá riêng + `outputs["phu_de_da_dung"]` | `giai_doan_thoi_gian.py` | sonnet | P0-a ✅ |
| **P4** | Chế độ chạy lẻ `chi_asr`/`chi_dich`/`chi_dub` | `tools/asv_chay_tai_cho.py` | sonnet | P1-0 |

✅ **Chuỗi `toc_doc_giong` — ba làn, mỗi làn tự khai nợ cho làn sau.** `P0-a` tạo giá trị
(hàm thuần; bảng đo riêng **rỗng** hôm nay ⇒ rơi về `ngon_ngu.NHIP`, ⛔ không bao giờ trả
`0`). `P0-a2` nối vào `do_dai_toi_da`. `P0-a3` nối chỗ gọi cuối.

⭐ **Ba điều `P0-a2` làm đúng — lấy làm khuôn cho mọi làn sau:**
1. Bài ranh giới AST của `P0-a` đỏ vì một dòng **docstring**, ⛔ không vì chỗ gọi ⇒ nó
   **viết lại bài để đo bằng AST** (đọc ở đâu · đúng một lời gọi · nằm trong vòng `for`
   từng đoạn), ⛔ không đếm chuỗi. Đó là [[banh-coc-do-cach-go-thay-vi-do-tinh-chat]]
   được chữa đúng chỗ.
2. **Ba phép tiêm nghịch tiêm vào MÃ THẬT**, ⛔ không vào test: `min` thành hai chiều ·
   bỏ tham số ở chỗ gọi · kéo lời gọi ra ngoài vòng `for`. Mỗi cái có bài đỏ tương ứng.
   ⇒ *"đã nối dây"* giờ là một **phép đo**, ⛔ không phải một lời khai.
3. **⛔ Không tăng `PHIEN_BAN_LONG_TIENG`** vì hành vi hôm nay ⛔ không đổi một đơn vị, và
   ghi **nghĩa vụ tăng ngay tại hằng số** cho lần thêm dòng đầu vào bảng đo.

🔴 **`P0-c` — dời cửa sổ cắt đầu/đuôi: ĐO RỒI, và câu trả lời là ⛔ KHÔNG.**

Chủ dự án chốt 28/09: *"cắt đầu đuôi họ làm đầu là đúng nếu chỉ 1 lần render"*. Tiền đề
ấy **đúng** (§1: ta đã chỉ có một lần encode). Nhưng cái chặn nằm ở chỗ khác, và nó là một
**luật của chính module** — `cat_dau_cuoi.py:10-13`, luật **L1**:

> Toạ độ là **PHÂN SỐ 0..1 của THỜI LƯỢNG, ⛔ không bao giờ giây**… Đổi sang giây xảy ra
> đúng **MỘT chỗ** — nơi biết thời lượng thật.

⇒ Đặt lần áp thứ hai ở `media_prepare` là **phân số nhân hai lần**: khai `[0,05; 0,95]`
thành **0,81** thay vì **0,90**. Khách mất thêm **24,751 s** đã yêu cầu GIỮ.

🔴 **Và đây là lý do thật để dừng, ⛔ không phải con số trên:** hai người áp
(`giai_doan_hinh_anh.py:369` cắt thật · `giai_doan_qc.py:272` dựng lại để biết độ dài
mong đợi) **vẫn ĐỒNG Ý với nhau trên một bản giao SAI**. `_thoi_luong_mong_doi` trả đúng
độ dài của tệp đã bị cắt **hai lần** ⇒ **T2 lệch 0 giây**. Tức **QC XANH trên một bản giao
sai**, và ⛔ không một cổng nào của ta phát hiện.
⇒ Đúng họ [[hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop]]: hai chỗ cùng dẫn xuất từ một
**trục sai** thì phép đối soát giữa chúng ⛔ không còn nói gì.

**Cái được, cũng đã đo**: vật liệu ASR giảm đúng **10 %**. ⇒ Đánh đổi rõ ràng: 10 % thời
gian ASR, đổi lấy một đường mà lỗi của nó **vô hình với QC**. ⛔ Không đáng, và nó
⛔ **không** nằm trên đường then chốt (`P1-0 → P1-a/b → P2`).

⭐ **Điều kiện tiên quyết sẽ ĐỔI câu trả lời này** (ghi để lần sau ⛔ không ai đo lại):
đổi cửa sổ từ **phân số** sang **giây tại một điểm duy nhất** (nên nó ⛔ không thể nhân
hai lần), **và** làm các chỗ đọc `run.source_key` biết bù `dau_cat`. Lúc ấy mở một làn
sở hữu `giai_doan_hinh_anh.py` + `giai_doan_qc.py` + `giai_doan_chep_loi.py`.

⚠️ **Một mong manh tiềm ẩn P0-c bắt được nhân thể**, đã chốt bằng `test_4976`:
`giai_doan_chep_loi.py:104-107` chọn bản tiếng theo **đuôi `.wav`** ⇒ đảo thứ tự
`khoa_asset` cho **hai trục khác nhau, cùng mã, ⛔ không lỗi nào**.

⚠️ **Và một bài học về chính BÁO CÁO của agent.** `P0-a2` khai nợ ở `nan_cho_vua.py:338`.
Tôi đếm lại: `grep -rn "ngan_sach_do_dai" apps/` cho chỗ gọi thật là **`dich_thuat.py:374`**;
`nan_cho_vua.py:338` là `mau_so_co_gian`, một hàm khác. ⇒ **Neo dòng trong báo cáo agent
phải ĐẾM LẠI trước khi thành mệnh lệnh cho làn sau** — cùng luật §0b, chỉ khác nguồn: lần
này lời khai lệch đến từ một **làn**, ⛔ không từ plan cũ.

✅ **P2 đi CÙNG chiều một quyết định đã chốt, ⛔ không ngược** — soát 28/09:
`apps/auto_scan_video/phu_de.py:8-20` gọi việc này bằng tên nội bộ **"Pha 26 —
Renderer fusion"**, nguyên văn *"tồn tại để gộp mọi biến đổi điểm ảnh vào MỘT lần
encode"*, và nó đã **từ chối** gọi `burn.burn()` vì *"nó chạy một lượt ffmpeg ĐẦY ĐỦ của
riêng nó, tức video bị mã hoá lại hai lần"*. ⇒ Agent làm P2 **tra "Pha 26" / "Renderer
fusion"** trước khi thiết kế — phần việc này đã có tiền lệ và có người đã nghĩ về nó.

⚠️ Cùng tệp, `:22` mở một khối tiêu đề **`🔴 TRỤC THỜI GIAN — chỗ dễ sai nhất, và nó đã
có một tiền lệ`** (`che_do_render.loc_cat_noi` CẮT rồi NỐI ⇒ mốc dịch). **Đọc khối đó
nguyên văn**, nó nói đúng về trục mà §5 của tệp này nói.

🔴 **Đã đo (28/09)**: mọi chỗ của ta truyền filtergraph bằng `-filter_complex` **trên
DÒNG LỆNH** (`am_master.py:537,752,1033,1081`), ⛔ không qua `-filter_complex_script`.
⇒ Gộp 10 node vào một lượt **làm dài chuỗi ấy**, và trần 32.767 ký tự của Windows là
trần **thật**, ⛔ không phải trần giả thiết. Thuốc rẻ: `-filter_complex_script <tệp>`.
⛔ Đừng để P2 phát hiện điều này lúc ffmpeg đã báo lỗi khó đọc.

🔑 **Vì sao hợp nhất 3 QC là P1-c, ⛔ không P0** (quyết 28/09): `QC_DO_LUONG` khai
`job_type="asv_gpu"` ⇒ nó **xin lease GPU**. Gộp nó vào một bước ⛔ không-GPU là đúng lớp
lỗi ở §3 — đổi nền đồng thời dưới chân một việc mà ⛔ không phép đo nào đỏ. Phải đi cùng
P1-a (nơi ta đang sắp xếp lại ai giữ lease).

⚠️ **`[ĐỌC TRƯỚC]` cho P2**: W3 chỉ đọc **17%** thân `burn_phude`. Vùng
`:6670-7263` (dựng dải che chi tiết) và thân `khung_filter_parts` / `text_wm_parts` /
`_srt_to_ass_pos` **chưa ai đọc nguyên văn**. Agent làm P2 phải đọc vùng đó **trước**,
⛔ không dựa vào §5 của tệp này.

---

## 7. ❓ CHƯA BIẾT — và phép đo để biết (⛔ đừng đoán, ⛔ đừng bỏ qua)

| Câu hỏi | Phép đo | Chặn việc nào |
|---|---|---|
| demucs + whisper cùng card: VRAM đỉnh và **RSS đỉnh**? | một lượt `gpu_asr` thử, ghi cả hai cột | P1-a |
| Một encode 10 node có vượt **trần dòng lệnh Windows** (32.767 ký tự)? | dựng `fc` **khô**, đếm ký tự, ⛔ chưa chạy ffmpeg | P2 |
| Có vượt trần **N=99 `if()` lồng** của ffmpeg (⇒ chunk ≤60)? | đếm số dải che động sau `vung_che_bam` | P2 |
| Ba nhánh song song có vượt `tai_nguyen_suat` máy A? | `tai_may.py` trước/sau một lượt thật | P1-b |
| `gop_khe` có lệch phụ đề thật ⛔ không, lệch bao nhiêu ms? | so `.vi.srt` với `.dubsync.vi.srt` theo từng cue | P3 |
| Đại lượng onset trong `_ghep_track_khop` là gì? | đọc `localize.py:9600-9790` nguyên văn | P3 |
| Bỏ một phần tử khỏi `CHUOI` làm gãy gì (`ha_nguon_cua` · vân tay · lineage · `giai_doan_lech_van_tay`)? | làn W4 — **đếm**, ⛔ không suy | mọi việc đổi `CHUOI` |

⭐ **Phép đo cuối cùng, MỘT lượt** (theo đúng chốt của chủ dự án: *"những gì viral đã
đo rồi thì ta dùng, ⛔ không đo lại; về cuối đo một lượt luôn"*): `T1a-ter` trên worker
thật + kiểm frame. Mọi con số Viral đã đo (bảng wps, `MAXSLOW`, 1.25/1.40, chunk ≤60,
`DUB_TRIM_SIL`) ta **dùng lại**, ⛔ không đo lại.
