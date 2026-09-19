> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: `docs/NHAT_KY.md` (bàn giao một lần cho kho `D:\FULL AUTO VIDEO`). Chỉ đọc để hiểu lịch sử.

# BÀN GIAO — cửa tải cho bot `D:\FULL AUTO VIDEO`

Viết 2026-09-03 bởi phiên `auto-scan-video-v4-mvp` (làm việc ở `D:\LTTSTUDIOSAPP`).
Người đọc: một phiên Claude/Codex mở **trên chính `D:\FULL AUTO VIDEO`**.

Tôi không sửa tiếp được vì mọi thao tác Bash vào `D:\FULL AUTO VIDEO` bị chặn từ phía tôi —
đó là ranh giới đúng cho một kho tham chiếu, không phải một sự cố. Nên phần còn lại là của bạn.

---

## 1. Chuyện đã xảy ra

Máy production (20 lõi logic / 10 vật lý, 32 GiB) **bị reset vì quá tải** lúc ~13:52 ngày
03/09. Trên máy này chạy đồng thời:

| Hệ thống | Ghi chú |
|---|---|
| `C:\LTTPlatform` | 4 dịch vụ đang phục vụ khách (Web, Worker, Voice, Codex) |
| `D:\FULL AUTO VIDEO` | 8 tiến trình — `start_gui.bat`, `run_master_g*`, `pythonw` |
| `D:\BOT GEMINI` | 22 tiến trình, bot production cổng 8000 |
| `D:\LTTSTUDIOSAPP` | gate/pytest của 4 phiên Claude |

Nhật ký `DUNGVIDEO-FULL/logs/dungvideo_debug.log` cho thấy **lúc reset bot đang NGỦ**:

```
13:46:37  NO JOB (no row matched conditions across all tabs)
13:46:37  SLEEP 300s (không job)
13:48:37  💤 SLEEP 300s — còn 180s      ← log dừng, máy reset ~13:52
```

⇒ **Bot không phải thủ phạm lần này.** Nhưng nó *có thể là* lần sau, và lý do ở §2.

---

## 2. Phát hiện: cơ chế bảo vệ tồn tại nhưng không được dùng, và ngưỡng đã bị nới

**`bot_coordination.py` có sẵn `ResourceGuard`:**

```python
bot_coordination.py:429   cpu = psutil.cpu_percent(interval=0.1)
bot_coordination.py:436   free_gb = psutil.virtual_memory().available / 1024**3
```

**Nhưng worker không gọi nó.** `DUNGVIDEO-FULL/bot/worker.py:41` chỉ import
`GpuSlot, VramBudget`; dòng 1099 thêm `PhaseRegistry`. `ResourceGuard` **vắng mặt** —
tức bot hỏi về **CARD**, không hỏi về **MÁY**. Một job render chạy đúng lúc máy đã bão hoà
thì card rảnh không cứu được gì.

**Và ngưỡng đã bị nới tới mức gần như vô hiệu:**

```python
bot_coordination.py:40   CPU_MAX_PERCENT = 98
#   [Phase F3] 92→98: ngưỡng cũ chặn job khi DEMUCS/Whisper burst CPU >92%
#   (DUNGVIDEO chỉ chạy được 2 job/4h). 98% vẫn để 2% slack.
bot_coordination.py:39   RAM_MIN_FREE_GB = 2.0    # máy 32 GiB
```

⚠️ **Đây là bài học quan trọng nhất của cả tài liệu này.** Một cửa chặn quá chặt thì người ta
không gỡ nó — họ **nới ngưỡng** cho tới khi nó không còn chặn gì. 92 → 98 không phải tinh
chỉnh, đó là vô hiệu hoá bằng một con số. Bất kỳ ngưỡng mới nào cũng sẽ gặp lại đúng áp lực
đó, nên **đừng đặt một con số rồi hy vọng**; hãy làm cho việc bị chặn ít đau đến mức không ai
muốn nới nó.

---

## 3. Việc TÔI ĐÃ LÀM (cần bạn xác minh)

Chèn cửa tải vào `DUNGVIDEO-FULL/bot/worker.py` **dòng 1197**, ngay sau
`log(f"📋 PA3: Scan xong …")` và trước khối PREFETCH:

```python
    try:
        from bot_coordination import ResourceGuard
        _tai_ok, _tai_ly_do = ResourceGuard.check_cpu_ram()
    except Exception as _e:  # noqa: BLE001
        _tai_ok, _tai_ly_do = True, f"OK (không kiểm được: {_e})"
    if not _tai_ok:
        log(f"⏸️  HOÃN batch — {_tai_ly_do}. "
            f"{len(jobs)} job vẫn còn trên sheet, thử lại vòng sau.")
        cleanup_old(cfg)
        return (0, 0)
```

**Sao lưu:** `DUNGVIDEO-FULL/bot/worker.py.bak-truoc-cua-tai-20260903_141249`

### ⛔ VIỆC ĐẦU TIÊN CỦA BẠN — tôi chưa chứng minh được file còn hợp lệ

```bash
python -c "import ast;ast.parse(open(r'D:\FULL AUTO VIDEO\DUNGVIDEO-FULL\bot\worker.py',encoding='utf-8').read());print('OK')"
```

Không in `OK` ⇒ khôi phục từ bản `.bak` rồi làm lại. File dùng **CRLF**, giữ nguyên.

### Ba quyết định trong đoạn đó, để bạn khỏi đoán

1. **Vị trí sau scan, trước render.** Scan là I/O mạng (~8 phút, nhẹ CPU) — chặn nó không
   được gì. Render mới ăn CPU/RAM.
2. **HOÃN chứ không BỎ.** Job vẫn nằm trên sheet, vòng sau lấy lại. Một bot làm *mất* job vì
   máy bận sẽ bị gỡ cửa này ra trong một tuần.
3. **Fail-open.** Đo không được thì **chạy**. Cùng nguyên tắc `check_cpu_ram` tự tuyên bố
   (*"KHÔNG BAO GIỜ raise"*) — một công cụ đo hỏng không được biến thành một cái chặn.

---

## 4. Việc CÒN LẠI — của bạn

### 4a. Ba worker khác cũng import `bot_coordination` nhưng chưa rõ có gọi `ResourceGuard`

```
Bot_PausePipeline/bot/worker.py
BOT_TRANSCRIPT/Bot_Whisper_FULL/bot/worker.py
CUT CLIP SHORT/bot/worker.py
```

⚠️ **Đừng kết luận từ một lượt `grep` hẹp.** Tôi đã mắc đúng lỗi đó: quét 3 thư mục, thấy
trống, kết luận *"không một dòng nào"* — rồi lượt quét rộng tìm ra `bot_coordination.py`.
**Một kết quả rỗng từ phép quét hẹp không phải bằng chứng vắng mặt.**

### 4b. Đo lại hai ngưỡng — ĐO, đừng đoán

`CPU_MAX_PERCENT = 98` và `RAM_MIN_FREE_GB = 2.0` cần dữ liệu thật:

- Nền CPU máy này **biến động ~10 lần trong ngày**: đo được 27% lúc 13h, 3% lúc 21h, 37% ngay
  sau reset. Một ngưỡng CPU cố định sẽ ngoan buổi tối và cấm cửa buổi chiều.
- ⇒ Cân nhắc **RAM làm phán quyết chính** (ổn định hơn nhiều), CPU chỉ để ghi log. Đó là kết
  luận tôi rút ra sau khi một phiên khác phá thiết kế cũ của tôi bằng đúng số đo trên.
- Nếu vẫn dùng CPU: đo **delta so với nền vừa lấy mẫu**, không so với hằng số.

### 4c. Câu hỏi thiết kế lớn hơn, nếu bạn có thời gian

Bốn hệ thống trên cùng một máy, **không cái nào biết cái kia tồn tại**. `LTTSTUDIOSAPP` có
`tools/cua_so_yen.py` — một khoá cấp máy đặt ở `%TEMP%\ltt_cua_so_yen*.json`, không phụ thuộc
kho nào. Bot có thể đọc/ghi cùng khoá đó để bốn hệ thống xếp hàng thay vì tranh nhau.

⚠️ Nhưng đó là quyết định kiến trúc liên hệ thống — **hỏi chủ dự án trước**, đừng tự nối.

---

## 5. Nguyên tắc rút ra, áp cho mọi thay đổi tiếp theo

1. **Một ngân sách là giới hạn TRÊN, không phải phép gán.** Luôn `min(ngân_sách_ta,
   câu_trả_lời_của_chính_công_cụ)`. Tôi vừa sửa một lỗi cùng loại ở `gate.py`: nó tính trên
   lõi **logic** (20) rồi truyền `-n 11`, trong khi `pytest -n auto` chỉ mở **10** (lõi vật
   lý) — một cơ chế sinh ra để *giảm* tải đang *tăng* nó.
2. **Không bao giờ từ chối chạy hẳn.** Cổng bị chặn sẽ đẻ ra một cờ `--bỏ-qua`, hoặc một
   ngưỡng bị nới. `CPU_MAX_PERCENT` 92→98 là bằng chứng.
3. **Fail-CLOSED khi thiếu thông tin về tài nguyên, fail-OPEN khi hỏng công cụ đo.** Hai thứ
   khác nhau: "không khai" ≠ "không dùng"; nhưng "không đo được" thì đừng chặn.
4. **Không đợi một điều kiện mình không kết thúc được, trong lúc đang giữ khoá.** Mọi phép đo
   tải đặt **trước** khi xin khoá.
5. **Một kết quả dễ chịu là kết quả ít bị kiểm nhất.** Khi công cụ đo trả về "0 lỗi" hay "bạn
   sai", đó là lúc phải đối chiếu, không phải lúc đi tiếp.

---

## 6. Ranh giới

- `D:\FULL AUTO VIDEO` và `D:\BOT GEMINI` **đang phục vụ khách thật**. Sửa tối thiểu, cộng
  thêm, luôn sao lưu trước.
- Bot đang chạy giữ bản cũ trong RAM; thay đổi có hiệu lực **từ lần khởi động sau**.
- Đừng sửa `D:\LTTSTUDIOSAPP` từ phiên đó — nó có 4 phiên khác đang làm việc.
