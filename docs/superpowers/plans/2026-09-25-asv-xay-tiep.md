# Auto Scan Video — plan xây tiếp (25/09/2026)

> Lập **sau** một vòng khảo sát cộng đồng (R1 hệ thống · R2 tiếng · R3 chữ · R4 timeline)
> **và** một lượt kiểm kê app LTT. ⛔ Thay thế mọi thứ tự việc ghi ở nơi khác.
> Plan `2026-09-24-thang-cong-asv.md` giữ làm **sổ trạng thái + sổ cái N-xx**.

**Mục tiêu:** hoàn thiện lõi **voice → voice** của Auto Scan Video tới mức **ra sản phẩm**.
Hình ảnh / nội dung video: ⛔ chưa xử lý sâu, chỉ báo cáo.

---

## ⭐ BỐN LUẬT — áp cho MỌI làn, đọc trước mỗi phiên

### L1 · Cổng
- Trong phiên: **test NHẮM** cụm vừa sửa. Cần gate ⇒ **chỉ L1/L2**.
- ⛔ **KHÔNG L3 giữa các pha.** L3 chỉ chạy **khi kết thúc PHIÊN LÀM VIỆC**, **một lần**.
- 🔴 **Gate đọc cây chính ⇒ ⛔ KHÔNG ai được GHI vào cây chính** (gộp `main`, `pytest`).
  Ngày 24–25/09: hỏng **một** lượt gate, **suýt** hỏng lượt thứ hai. ⛔ Chưa có cơ chế ⇒
  **báo bằng lời** trước mỗi lượt gộp.
- ⭐ **Trước khi tin một cổng: chạy một HỆ HOÀN HẢO qua nó.**
  Hệ hoàn hảo ⛔ không đạt ⇒ cổng đang đo **chân lý nền của ta**, ⛔ không đo sản phẩm.
  **Phạm vi:** **áp** khi cổng đối chiếu **một phép đo khác** · ⛔ **không áp** khi cổng so
  với **một con số cố định** (trần = 1,00 theo định nghĩa) · cổng có **lựa chọn rời rạc**
  ⇒ phải đo thêm **SÀN MAY RỦI**.

### L2 · Agent
- Số làn = số việc **ĐỘC LẬP**. Mỗi làn **một worktree + một nhánh**. ⛔ Không hai làn một
  tệp. ⛔ Không làn nào làm việc trong cây chính.
- Việc cơ học ⇒ `sonnet`; gỡ lỗi khó / thiết kế ⇒ mặc định.
- ⭐ **Gọi máy B = chờ mạng ⇒ ⛔ KHÔNG giữ `cpu_nhieu`.** Lệnh **tính** nặng đi qua
  `chay_nang.py`, **nhả khoá NGAY khi lệnh tính xong** — đọc kết quả / sửa mã / commit làm
  **ngoài** khoá.
- ⭐ Mọi khẳng định phải **trích nguồn** (tệp + dòng, hoặc repo + issue/PR). Câu không nguồn
  ⇒ ⛔ không nhận. Tra không ra ⇒ **khai đã tra ở đâu, tìm gì, vì sao không dùng được**.
- 🔴 ⭐ **`main` KHÔNG phải nơi công việc đang diễn ra** (~100 worktree). Mỗi khẳng định phải
  nói rõ **đọc ở nhánh nào**. Hai làn đã kết luận sai vì đọc `main`.

### L3 · ⛔ KHÔNG dừng giữa các pha
Xong một pha ⇒ **làm tiếp pha kế**, ⛔ không xin phép. Hết **mọi** pha ⇒ L3 → gộp `main` →
deploy nếu cần → **báo**.
**Chỉ dừng khi:** gate đỏ · thao tác ⛔ không đảo được · thay đổi ⛔ không rõ của ai · rủi ro
bảo mật hoặc **pháp lý**. ⛔ Hộp thoại nâng quyền **không** phải điểm dừng.

### L4 · ⭐ ĐIỀU PHỐI (một LLM) LÀ NGƯỜI CHẤM khi bộ đo bị nghi ngờ
*Chủ dự án chốt 25/09.* Áp khi bộ đo **trượt cổng**, **chưa được xác thực**, hoặc **nghi cùng
họ** với thứ nó chấm.

- ⭐ **Vì sao có giá trị:** `qc_ai` chạy **cùng họ model** với bản dịch ⇒ nó có thể chỉ đang
  đo **độ giống nhau**. Điều phối thuộc **họ khác** ⇒ đồng ý hay bất đồng đều **mang tin**.
- **Giao thức bắt buộc:**
  1. **MÙ** — ⛔ không thấy nhánh/hệ nào sinh ra mục nào; thứ tự **xáo**.
  2. **Ghi phán quyết RA TỆP và COMMIT TRƯỚC**, rồi mới đối chiếu.
  3. Mỗi phán quyết kèm **đoạn trích** + **lý do**. ⛔ Không trích được ⇒ ⛔ không tính là lỗi.
  4. **Nghi ngờ ⇒ ghi "biên"**, ⛔ không ghi "lỗi" — sai về phía **bất lợi cho ta**.
  5. **Khai ngay cạnh con số**: *người chấm là một mô hình*. ⛔ Không giấu ở cuối.
- ⛔ **Giới hạn nói to:** mọi người chấm đều là máy. Đây là giới hạn **ghi ra được**, ⛔ không
  phải lỗ hổng bị giấu.

---

## Sự thật nền — ⛔ đừng đo lại

| | |
|---|---|
| ✅ **Đường dịch ổn định** | ghim `temperature` + **ép lược đồ** ⇒ lô hỏng **64,3 % → 0,0 %**, **+0 lượt gọi** |
| ✅ **Model dịch** | `ltt-3.5` — chủ dự án chốt, ⛔ không bàn lại |
| ✅ **App voice** | `ltt_voice` = **VieNeu, đã tối ưu**, **cả ba** trọng số sạch ⇒ ⛔ không tìm TTS khác |
| ✅ **ASV đã nối ba app của ta** | `autosubvideo.transcribe_file` · `ltt_voice.sidecar_client` · `ltt_llm.ngan_sach` — **giá 0** |
| 🔴 **Đường dịch KHÔNG TÁI LẬP** | seed **có** được chuyển; bất định là **cấu hình máy B** (`-np 3`, `--spec-type`) ⇒ **mọi số dịch kèm PHƯƠNG SAI**, ⛔ không một con số |
| 🔴 **Bộ chấm TRƯỢT** | quét 30 luật: ⛔ **không điểm nào** thoả cả hai cổng — hạ báo động giả **mua bằng chỗ mù thực thể** |
| 🔴 **Vòng sửa MÙ** | `y_canh` có tham số, có chỗ nhận, ⛔ **chưa ai truyền** ⇒ giải thích N-02 (85→85) |
| 🔴 **Aligner NC trên đường khách** | `nguyenvulebinh/…-vlsp2020` `cc-by-nc-4.0`, **mặc định**, ~5 credit/phút |
| ⚠️ **Đơn vị** | `3,5–4,5×` đo trên **ký tự**; công thức nắn chạy trên **âm tiết** |
| ⚠️ **107 ≠ 74** | 33 ranh giới thiếu là ranh giới **HIỂN THỊ** (trần ~16 ký tự/dòng), ⛔ không phải ranh giới **lời nói** |

---

## PHA A — đóng nợ chặn đường

- [ ] A1. Gộp nốt `phien/do-chuan` + phần dư hai nhánh làn → nhánh dàn dựng → `main`
- [ ] A2. `N-32` cửa lỗi khách (G-04) chưa ai nối — khai vào bánh cóc **kèm lý do**, ⛔ không miễn trừ trần
- [ ] A3. `thieu_khai` giữ **test-facing** (nối vào đường nạp module = tái tạo **N-08b**). ⭐ **Sửa PLAN**, ⛔ không sửa mã theo plan
- [ ] A4. `test_448` ×2 — chạy lại **nghiệm thu thật**, **một lần**, **sau** khi mọi nhánh về một chỗ

## PHA B — lõi dịch *(việc chính)*

- [ ] B1. ⭐ **Nối `y_canh`** — truyền **đoạn trích** lỗi, ⛔ không nhãn trần. Lời nhắc nói
      *"kiểm lại; đúng thì giữ nguyên"*, ⛔ **không** *"hãy sửa"* (bộ chấm còn 33 % báo động giả)
- [ ] B2. Đo A/B vòng sửa (có/không `y_canh`), ≥3 lượt mỗi nhánh, **đo CHIỀU**. ⭐ Điều phối chấm mù theo **L4**
- [ ] B3. Sinh bản dịch **FLORES zh→vi** (≥100 dòng, ≥3 lượt) ⇒ mở khoá **chrF++** — ⭐ tín hiệu **DUY NHẤT ngoài vòng tròn LLM**
- [ ] B4. Đo lại đường B (`57 %`/`0,63 %` đo ở nhiệt độ **chưa ghim**) trước khi thiết kế bảng từ
- [ ] B5. Bảng từ **B→D** (+`A` khách nạp đè). ⛔ Giới hạn: *model biết nó không biết **TỪ**; nó không biết nó hiểu sai **CÂU***

## PHA C — bộ chấm: đổi thiết kế theo giao thức đã công bố

⭐ Khảo sát R3: **mọi thứ ta tự nghĩ ra đều đã có tên — 5/7 dùng được.**

- [ ] C1. Chân lý nền neo **MQM** + thống kê **`mt-metrics-eval`** (Apache-2.0)
- [ ] C2. **ESA** thay MQM đầy đủ (WMT25 dùng cho 14/16 cặp — ⛔ không cần chuyên gia đắt)
- [ ] C3. **DEMETR** (MIT, có nguồn tiếng Trung) thay bộ tiêm lỗi tự viết
- [ ] C4. **Sentinel metrics** — đối chứng ta **chưa hề có**
- [ ] C5. ⛔ Không có chuẩn zh→vi được công nhận. **`ALT Parallel Corpus`** là kho **duy nhất** vừa người dịch vừa CC BY 4.0 (⚠️ treebank cùng dự án **NC-SA** — bẫy hai giấy phép)

## PHA D — timeline & nắn thời lượng

- [ ] D1. ⭐ Đổi thước sang **SubER** + **CPS/CPL/LPB** (Apache). Nhánh CPS/CPL/LPB ⛔ **không đọc chân lý nền** ⇒ lưới, bias, 107-vs-74 **biến mất**. ⛔ Khai rõ **ĐỔI CÂU HỎI**
- [ ] D2. Giữ **độ chính xác chỗ ngắt** làm cổng; ⛔ **bỏ** độ nhạy so với **107 dòng hiển thị**
- [ ] D3. Nắn thời lượng — ba cần gạt **theo thứ tự**: rút gọn lời dịch → phân phối lại thời gian → giãn/nén giọng. Mượn **đặc tả**, ⛔ không runtime. ⚠️ **Đếm âm tiết trước**
- [ ] D4. `vad.py` — kênh **onset độc lập với whisper**. ⛔ `silence.py` loại · ⛔ `SENT_SPLIT_RE` loại (**N-30**)

## PHA E — pháp lý *(⛔ ngoài ASV nhưng CHẶN sản phẩm)*

- [ ] E1. ⭐ **Ghim `model_name` ở `whisperx_runner.py:25`** — whisperX **cho ghim** (`alignment.py:80-86`); ghim **đóng luôn cửa thứ tư**, tên trọng số hiện trong mã ta. **Ứng viên sạch DUY NHẤT**: `anuragshas/wav2vec2-large-xlsr-53-vietnamese` (apache-2.0, dữ liệu **CC0**)
- [ ] E2. ⭐ Đo **rẻ nhất**: chênh lệch mốc `forced-align` vs `DTW` — **cả hai đã cùng chạy trong sản xuất**. Bỏ căn chữ ⛔ **không** mất mốc từ (`transcription.py:232`), chỉ giảm độ chính xác
- [ ] E3. Sửa chú thích sai `ban_ghi.py:120-122` (*"faster-whisper thì không căn từng từ"* — **sai**)
- [ ] E4. ⭐ **Cửa kiểm thứ BA** (giấy phép **dữ liệu huấn luyện**) + **thứ TƯ** (**thư viện tự tải gì hộ ta**) vào danh mục. Ca thật: `dragonSwing/` thẻ `apache-2.0` nhưng học trên **VLSP** — thẻ sạch ⛔ **không gột** được ràng buộc dữ liệu

## PHA F — mở rộng rẻ *(đã có sẵn, chưa nối)*

- [ ] F1. ⭐ **`video_crawler`** — ASV chỉ nhận upload; crawler đã có (`enabled=False`). Đường rẻ nhất: **0 dòng mã** — khách cào → tệp vào kho → ASV nhận `source_key`
- [ ] F2. Lớp **trung gian sửa được** + dựng lại **chỉ phần đã đổi** (ý `Softcatala/open-dubbing`, Apache-2.0) ⇒ khách sửa một câu thì **chỉ trả tiền cho câu đó**

---

## ⛔ Ngoài phạm vi

Hình ảnh/nội dung sâu · khớp môi (**`MuseTalk`** là ứng viên sạch **duy nhất**, để dành) ·
đổi TTS (**đã có VieNeu**) · đổi model dịch (**đã chốt 3.5**) · đổi cấu hình máy B để lấy
tính tái lập (**giá = thông lượng cả máy B** — quyết định của chủ dự án).
