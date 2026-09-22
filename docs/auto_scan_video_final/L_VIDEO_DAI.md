# Làn `video-dai` — giai đoạn dài của ASV thành lát cắt có điểm chốt

Nhánh `phien/asv-final-video-dai` · 22/09/2026 · test mới `tests/test_2050`, `tests/test_2051`.

## Vấn đề

`docs/auto_scan_video_v6/CHAN_DOAN_TEST_448.md` §10: ASV nhận video **120 phút**, nhưng
`content_process` chạy các lô dịch **tuần tự trong MỘT job** có trần 3.600 s. Ở 142 s/lô
(đo 10/09) chỉ ~25 lô lọt trần, tức **~20 phút video**. Vượt trần thì `job_runner._het_gio`
giết tiến trình với `retry=False` (`test_217`): lần chạy hỏng, khách phải tự bấm lại.

## Cách sửa (một cơ chế, dùng cho mọi giai đoạn có vòng lặp đơn vị)

`apps/auto_scan_video/lat_cat.py` — **nhường trước khi chạm trần, rồi nối tiếp bằng job mới**.

- Trước MỖI đơn vị (lô / cảnh / đoạn tiếng), giai đoạn hỏi
  `đã_trôi + dự_phòng(đơn vị tệ nhất) > 0,85 × trần_job` hoặc `đã_trôi ≥ 30 phút`.
  Nếu đúng và lượt này đã làm ≥ 1 đơn vị thì ném `TiepNoi`. Lượt nào cũng làm ít nhất một
  đơn vị, nên việc luôn tiến.
- `dự_phòng` lấy từ **chính các trần timeout của lớp gọi**, không gõ lại số:
  `ai.NGAN_SACH_RA`, hoặc giá trị mặc định của `dieu_phoi.goi(timeout_s)` và
  `sidecar_client.noi(timeout)`, đọc bằng `inspect`. Chừng nào lớp gọi còn giữ đúng
  timeout của nó thì job **không thể** chạm trần.
- `thi_hanh.chay_giai_doan` bắt `TiepNoi`, ghi con trỏ vào `AsvStage.outputs["tiep_noi"]`
  (`van_tay` của giai đoạn, `phien`, `luot`, `vi_tri`, `trang_thai`), rồi đưa giai đoạn về
  `pending`. Job kết thúc ở trạng thái `done`.
- `jobs._nop_giai_doan_san_sang` nộp lượt kế tiếp với khoá dedupe `a{attempt}:n{luot}` và
  **không tăng `attempt`**: nối tiếp không phải thử lại, nên không ăn vào
  `LAN_THU_GIAI_DOAN_TOI_DA`.
- Kết quả từng đơn vị vẫn đọc từ điểm chốt (`su_dung.danh_dau_xong`), đúng như một lần chạy
  lại. Con trỏ chỉ ghi "đã đi tới đâu": đơn vị đã hỏi rồi bỏ (cảnh mơ hồ, lô QC hỏng) nằm
  trước con trỏ, nên lượt sau **không hỏi lại**, giống hệt lần chạy một mạch.
- Chặn quay vô hạn: `TIEP_NOI_TOI_DA = 500` lượt. Vượt thì hỏng hẳn. `du_phong ≥ ngân sách`
  thì `lat_cat.mo` hỏng ngay, không để job chạy rồi bị giết.

### Giới hạn đồng thời LLM: dùng lại, không viết mới

Brief đề nghị ≤ 2 lượt `ltt-3.8` + ≤ 2 lượt `ltt-3.5` (`acquireModelSlot` của LTTCODE). Nền tảng
**đã có** giới hạn này, và nó chặt hơn: `pipeline.CHUOI` khai `tai_nguyen="llm_remote"`,
`tai_nguyen_suat=1` cho `edit_plan`/`content_process`/`qc_ai`. Admission của
`platform_core/jobs.py` chỉ cấp **một** suất `llm_remote` (`canonical._TAI_NGUYEN_MAC_DINH`).
Thêm vào đó, `apps/ltt_llm/ngan_sach.py` giữ `seq_cap` phía máy B.

Mỗi lượt nối tiếp là một job đi qua đúng admission ấy. Vì vậy lát cắt **không** thêm lượt gọi
đồng thời nào, và giữa hai lượt, run khác có thể chen vào suất. Chạy song song các lô trong một
job sẽ phải xin thêm suất mà máy B không có (`DONG_THOI_MAY_B=1`), nên tôi không làm.

⛔ Không sửa `platform_core/`. `credit.py`/`jobs.py`/`job_runner.py` giữ nguyên. Lát cắt chỉ
đọc trần từ `registry` và `job_runner.RUNTIME_LIMIT_DEFAULT_S`.

## Bảng giai đoạn

"Trần" là `max_runtime_s` của job (manifest). "Đơn vị tệ nhất" là dự phòng tính từ timeout,
đã cộng 60 s ngoài lượt gọi.

| Giai đoạn | Trần job | Timeout/lượt gọi | Đơn vị tệ nhất | Điểm chốt trước | Trước (120 phút) | Sau |
|---|---|---|---|---|---|---|
| `content_process` (lô 12 đoạn) | 3.600 | 300 s (`NGAN_SACH_RA`) | 360 s | có, theo đoạn | 150 lô × 142 s = 21.300 s → **bị giết ở ~lô 25**, `retry=False` | nhường sau ≤ 13 lô/lượt (mềm 30 phút); ~12 lượt × ≤ 1.846 s |
| `edit_plan` (VLM mỗi cảnh) | **chưa khai** → 1.800 mặc định lớp `api`; nay khai 1.800 | 120 s (`dieu_phoi`) + 2 khung × 120 s ffmpeg | 420 s | có, theo cảnh; **cảnh hỏng không chốt → chạy lại hỏi lại** | N cảnh × (VLM + rút khung) trong 1 job; tách cảnh lại mỗi lần chạy | nhường theo ngân sách; chỉ mục cảnh lưu trong con trỏ (không tách cảnh lại); cảnh hỏng không hỏi lại |
| `voice_synthesis` (TTS mỗi đoạn) | 5.400 | 900 s TTS × 3 + 120 s × 2 viết lại | 3.000 s | có (tệp + đơn vị) nhưng **đoạn đã nắn** tìm theo vân tay câu gốc nên bị sinh lại | ~1.800 đoạn × vài giây trong 1 job | nhường khi `đã_trôi > 1.590 s`; bản ghi `lat` (câu đã nắn, số vòng, bản kê) dùng lại y nguyên |
| `qc_ai` (lô 10 đoạn, mặc định TẮT) | 1.800 | 300 s | 360 s | **không có** | 180 lô × ~142 s → bị giết, mất hết phán quyết | chốt theo lô (cùng `phien`); nhường sau 9 lô/lượt |
| `audio_prepare` (demucs) | 3.600 | tiến trình con **5.400 s** | — (một lần, không chia) | — | timeout con > trần job ⇒ job bị giết trước, **demucs mồ côi giữ GPU** | timeout con = min(5.400, ngân sách còn lại) (`lat_cat.han_tien_trinh_con`) |
| `render` (ffmpeg) | 3.600 | `TIMEOUT_RENDER` **3.600 s** | — | — | bằng trần ⇒ cùng rủi ro mồ côi | kẹp như trên |
| `transcribe` (ASR) | 3.600 | trong tiến trình | — | — | chưa đo trên 120 phút | không đổi (xem "còn lại") |
| `media_prepare`, `timing_align`, `compose`, `qc` | 900–1.800 | ffmpeg | — | — | ffmpeg `-c copy`/đo, tuyến tính theo thời lượng | không đổi |

Vì sao demucs/ASR/render **không** chia lát: chia âm thanh ở biên ngoài đổi kết quả tại biên
(demucs chồng đoạn bên trong, ASR mất ngữ cảnh), tức đổi ngữ nghĩa bản ra. Brief cấm đổi ngữ
nghĩa. Ở ba giai đoạn này tôi chỉ sửa chỗ timeout con **dài hơn** trần job.

## Bằng chứng

### Test (dữ liệu tổng hợp, model giả, đồng hồ giả)

`tests/test_2050_asv_lat_cat_120_phut.py` dùng 1.800 đoạn (15 đoạn/phút × 120 phút), mỗi lượt
gọi model "tốn" 142 s:

- **Đối chứng**: 150 lô × 142 s > 5 × trần. Chạy một mạch (tắt lát cắt) thì một lượt dài hơn
  trần thật.
- **(a)** Mọi lượt ≤ 0,85 × 3.600 s, có ≥ 6 lượt, tổng thời gian = 150 × 142 s (không làm thừa
  lô nào). Khoá sổ cái `lo_000…lo_149` duy nhất.
- **(b)** Giết worker ở lần gọi thứ 50 (một `BaseException`, không nhánh `except` nào nuốt
  được), rồi chạy tiếp: mỗi đoạn gửi **đúng một lần** trên cả hai lần chạy. Bản ra đủ 1.800 mục.
- **(c)** Lát cắt so với một mạch: cùng dãy lô gửi đi, `content.json` **giống từng byte**,
  `tom_tat` giống nhau.
- `qc_ai`: 180 lô, cứ 7 lô có 1 lô hỏng. Mỗi lô hỏi đúng một lần qua các lượt (lô hỏng không
  hỏi lại), báo cáo giống từng byte so với một mạch.
- Cấu hình thật: đơn vị tệ nhất của 4 giai đoạn đều lọt ngân sách manifest. Timeout của demucs
  và render bị kẹp dưới ngân sách còn lại.

`tests/test_2051_asv_lat_cat_hang_doi.py` chạy **qua hàng đợi thật** (`claim` → handler →
`advance` → dedupe → admission), ép trần nhỏ để mỗi đơn vị là một lượt:

- run về `done`; `content_process` 6 job, `edit_plan` 3 job, `voice_synthesis` 6 job, tất cả
  `done`, dedupe khác nhau, `attempt == 1`, không còn con trỏ;
- cảnh 2 hỏng ở lượt 2 và **không** được hỏi lại ở lượt 3;
- artifact JSON của `edit_plan`/`content_process`/`voice_synthesis` giống lần chạy một mạch
  (sau khi bỏ run_id/owner khỏi khoá kho).

Kiểm đột biến: đổi khoá lô về `lo_{i}` → (a) đỏ. Bỏ con trỏ QC → test QC đỏ. Bỏ phép bỏ qua cảnh
trước con trỏ → test hàng đợi đỏ.

### Đo thật: giây/lô trên máy B

22/09 ~21:25 (giờ máy A). Lời nhắc **thật của ASV**: `long_tieng.loi_nhac`, 3 lô × 12 đoạn
hội thoại tiếng Anh, đích `vi`. Thân request giống cái `dieu_phoi.goi` gửi: `qwen38-api`,
`max_tokens` 16.384, không stream, không khai effort (máy chủ tự chèn `medium`), timeout 300 s.
Script chạy **trên máy B** qua SSH, gọi `127.0.0.1:8299`; token đọc từ `gateway.env` ngay trên
máy B, không in ra, không rời máy. Không giữ khoá `eval_may_b`: máy B có thể đang phục vụ lượt
khác. Script: `scratchpad/dung_loi_nhac.py`, `do_lo_b.py`, không commit.

| lô | giây | finish | token vào | token ra | đoạn trả về |
|---|---:|---|---:|---:|---:|
| 0 | 92,0 | stop | 1.731 | 5.106 | 12/12 |
| 1 | 80,0 | stop | 1.774 | 5.155 | 12/12 |
| 2 | 83,6 | stop | 1.733 | 5.264 | 12/12 |

**p50 83,6 s/lô**, thấp hơn 142 s đo 10/09. Chênh ấy có thể đến từ budget suy nghĩ do máy chủ
đặt (L-33, sau 10/09) và từ hội thoại ngắn. Với 150 lô, tổng là ~12.540 s ≈ **3,5 giờ trong
một job 1 giờ**: không có lát cắt thì vẫn chỉ ~36 lô (~29 phút video) lọt trần. Có lát cắt thì
mỗi lượt nhường sau khoảng 21 lô (mốc mềm 30 phút), tức ~7–8 lượt.

⚠️ Đây là đường 8299 trực tiếp, **chưa** qua `goi_tinh_tien` → pool → `secretbox` của nền tảng.
Đo đường ấy phải chạm CSDL/khoá production nên tôi không làm. Chênh lệch dự kiến chỉ là
overhead HTTP, cỡ mili-giây.

## Lỗi đã tìm thấy trên đường đi

1. **Khoá sổ cái của lô trùng khi chạy lại** (`giai_doan_noi_dung`, đã có từ trước lát cắt):
   `item_key=f"lo_{i:03d}"` đánh số theo `con_lai`, nên một lần chạy lại sau hỏng bắt đầu lại từ
   `lo_000`. `UNIQUE(run_id, ma_dispatch)` nuốt dòng thứ hai (`DaGhiRoi`), và một lượt gọi
   **đã giao** biến mất khỏi sổ cái. Nay khoá đánh số theo vị trí trong `doan_giu`.
2. **`qc_ai` không có điểm chốt nào.** Job bị giết là mất toàn bộ phán quyết đã trả tiền.
3. **Demucs 5.400 s > trần 3.600 s; render 3.600 s = trần.** `_het_gio` gọi `os._exit`, mà trên
   Windows tiến trình con không chết theo cha.
4. **`edit_plan` không khai trần** và ăn mặc định 1.800 s của lớp `api`. Nay khai tường minh
   (cùng giá trị).

## Còn lại (điều phối cần biết)

- **ASR và demucs trên 120 phút chưa đo.** Không chia được mà giữ nguyên ngữ nghĩa. Nếu
  large-v3 trên GPU không xong trong 3.060 s thì cần nâng trần `asv_gpu.*`; đó là quyết định
  tài nguyên, không phải lát cắt.
- Timeout demucs quá hạn ném `MediaError("quá hạn")`. `loi.py` xếp nó vào nhóm người dùng, tức
  hỏng hẳn. Như vậy vẫn tốt hơn một job bị giết kèm GPU mồ côi, nhưng khách vẫn nhận một lần
  chạy hỏng.
- `httpx.Timeout(300)` là timeout **mỗi thao tác** (đọc giữa hai gói), không phải tổng. Với
  phản hồi không stream thì hai thứ gần bằng nhau. Một cổng nhỏ giọt từng byte có thể vượt;
  chuyện này nằm ở `platform_core/llm/dieu_phoi.py` (không sửa).
- Giữa hai lượt, giai đoạn hiện `pending` vài giây trên màn khách. Tôi chưa kiểm trên giao diện.
- Chưa chạy gate (điều phối lo).
