# NHỊP SONG SONG — chạy nhiều việc cùng lúc trên một máy 10 lõi

> **Đề xuất**, không phải luật đã chốt. Viết 2026-09-12 từ các phép đo trong
> phiên `ltt-llm-dual`. Nó **không thay** luật nào đang có: `CLAUDE.md` (trần
> `-n 6`, `cua_so_yen` trước lệnh nặng), `tools/gate.py::loi_cho_bo_test`,
> `tools/tai_may.py`, `docs/QUY_TAC_CHAY_LENH_NANG.md` vẫn là nguồn. Tệp này chỉ
> trả lời một câu chưa ai trả lời: **một phiên có thể chạy bao nhiêu việc cùng
> lúc mà không làm hỏng việc của chính nó.**

---

## 0. Số đo, không phải cảm giác (máy A, 2026-09-12)

| | |
|---|---|
| Lõi | **10 vật lý / 20 logic** |
| RAM | 31,9 GB tổng · **9,2–11,1 GB trống** (đo bốn lần trong hai giờ) |
| 20 tiến trình `claude.exe` | **3,75 GB** |
| 18 tiến trình `python.exe` (dịch vụ + bot) | 1,53 GB |
| ~40 tiến trình `node.exe` (MCP) | ~1,6 GB |
| Máy B | 3090 **184 MiB**, 5060 Ti **54 MiB** — cả hai rảnh |

### 🔴 CPU đo tại một thời điểm là một con số VÔ NGHĨA để ra quyết định

Bốn lần đọc trong cùng một giờ, cùng khối lượng việc: **27 % → 49 % → 78 % →
91 %**. Rồi lấy mẫu **3 giây theo từng tiến trình** ngay sau lần đọc 91 %: tiến
trình ngốn nhất là **Defender 6,6 %**, không có tiến trình nào của ta trên 0,5 %.

Vì sao: việc của agent **bùng theo nhịp** — vài giây `pytest` rồi vài phút model
nghĩ. Một lát cắt trúng lúc bùng đọc ra 91 %; trúng lúc nghĩ đọc ra 27 %.

⭐ `tools/tai_may.py` **đã** phát biểu đúng điều này trong docstring của nó và
   phán quyết theo **RAM**. Tệp này chỉ nối dài: RAM là thước, CPU là ngữ cảnh.

### 🔴 Và đây là hệ quả đắt nhất, đo được

`gate.loi_cho_bo_test()` có một vế **đo tải CPU** (`loi_dang_ban`). Đo hôm nay:

```
lúc 4 agent đang chạy   ->  loi_cho_bo_test = 1      (nó thấy "6 lõi đang bị chiếm")
lúc máy rảnh            ->  loi_cho_bo_test = 6
```

⇒ **Chạy gate trong lúc agent còn sống là tự hạ gate xuống `-n 1`.** L3 trung vị
`-n 6` là **11,4 phút** (43 lượt); `-n 1` không phải "chậm hơn một chút". Đây là
lý do **thứ hai, độc lập** với lý do đúng/sai (`test_145` chụp cả cây nên bất kỳ
ai ghi cũng làm nó đỏ) để bắt gate chạy một mình.

---

## 1. Bảy quy tắc

### R-S1 · Ngân sách có MỘT nguồn. Đừng đặt số thứ hai.

```
python tools\tai_may.py            # phán quyết RAM: RANH / BAN / QUA TAI
python tools\cua_so_yen.py trang-thai
```

Số worker do `gate.loi_cho_bo_test()` trả, không do người gọi đoán. Ba chỗ đã
từng cùng trả lời một câu hỏi và lệch nhau — `gate.py` đã gom về một hàm, đừng mở
lại.

### R-S2 · Song song bị chặn bởi **QUYỀN SỞ HỮU TỆP**, không bởi số lõi

Đây là ràng buộc thật, và nó không phải ràng buộc phần cứng. Bằng chứng trong
chính phiên này:

* Task 5.4 phải đợi 4.3 vì **cùng sửa `llm_gateway/api.py`**.
* Commit của Task 4.2 bị pre-commit từ chối vì `ruff` đỏ do **tệp đang viết dở
  của Task 5.3** — hai việc không liên quan, một hàng rào chung.
* Một commit tài liệu của tôi **quét theo 12 tệp** của agent khác: `git commit`
  lấy **cả index**, không chỉ tệp mình `git add`.

⇒ **Điều phối viên giữ một BẢNG LÀN** và mỗi agent nhận một tập tệp **rời nhau**.
Hai việc cần cùng một tệp thì hoặc **tách theo hàm**, hoặc xếp nối tiếp — quyết
định trước khi dispatch, không phát hiện lúc merge.

⭐ Và khi hai việc chỉ dính nhau qua **một giao diện**, hãy cắt ở đó: Task 5.4
   (server máy B) và 5.5 (trọng tài máy A) chạy song song được vì hợp đồng HTTP
   nằm trong plan, nên mỗi bên code theo **hợp đồng** chứ không theo tệp của bên
   kia.

⇒ Mọi commit trong cây nhiều phiên: **`git commit -- <đường dẫn>`**, và xem
  `git diff --cached --name-only` trước.

### R-S3 · Gate chạy MỘT MÌNH, trong cửa sổ cấm ghi

Hai lý do độc lập, cả hai đo được: verdict sai (`test_145`) và `-n` tụt về 1.
Trình tự: mọi agent **dừng hẳn** → không ai commit → `tai_may.py` nói `RANH` →
mới chạy. Một verdict gate chạy khi còn người ghi là verdict **vô hiệu**, không
phải verdict đỏ.

### R-S4 · Hai hạng lệnh, hai luật

| hạng | ví dụ | luật |
|---|---|---|
| **nhẹ** | ≤ 2 tệp test, `grep`, `ruff` một tệp, đọc/ghi tệp | chạy tự do, không xin khoá |
| **nặng** | `gate.py` (mọi chế độ), `test_nhanh.py`, ≥ 3 tệp test, benchmark, `build_system_profile.py` | `tai_may.py` + `cua_so_yen` trước, và **nối tiếp**: mỗi lúc chỉ một |

⛔ Đừng chạy lệnh nặng để **dò** lỗi. Gate ra **phán quyết**; chẩn đoán bằng
`grep`/`read_bytes`/một tệp test.

### R-S5 · Trần agent đồng thời tính theo RAM, và máy B là làn thứ hai

Đo: một `claude.exe` ≈ **100–700 MB** (trung bình ~190 MB, 20 tiến trình =
3,75 GB). Đề xuất:

| RAM trống | agent đồng thời |
|---|---|
| > 8 GiB | **4** |
| 4–8 GiB | 2 |
| < 4 GiB | 1, và không dispatch thêm |

⭐ **Máy B là một làn gần như miễn phí.** Việc ở đó tốn của máy A đúng một
   `ssh`. Và **RTX 5060 Ti không phục vụ sản xuất** (LTT-3.5 chưa deploy,
   ComfyUI ghim 3090) ⇒ mọi thí nghiệm GPU **không chạm 3090** là rủi ro bằng
   không. Hôm nay điều đó trả lời được một câu đã ghi `[INFERRED]` suốt nửa ngày
   (`GET /unload` nhả một hay nhả hết) bằng một thí nghiệm 60 giây chạy **song
   song** với bốn agent, không làm chậm gì cả.

⚠️ Nhưng "máy B rảnh" phải **đo trước mỗi lần**, không nhớ: nó phục vụ khách
   thật. `nvidia-smi --query-gpu=uuid,memory.used` và `/running` của llama-swap.

### R-S6 · Trước khi gom một lô, tra bảng giá

| việc | thời gian | chiếm |
|---|---|---|
| 2 tệp test không DB | 0,3–3 s | 1 lõi |
| 2 tệp test có DB/TestClient | 3–35 s | 1–2 lõi |
| `gate.py --doi` (L1) | vài phút | `loi_cho_bo_test` lõi |
| `gate.py` đầy đủ (L3) | **11,4 phút** trung vị, 43 lượt | 6 lõi + ~4 GB |
| một agent | 19–54 phút **đồng hồ**, phần lớn là model nghĩ | ~190 MB + bùng CPU vài giây |
| một lượt đo trên máy B | vài giây tới vài phút | **0** của máy A |

⇒ Bốn agent × 40 phút chạy **song song** = 40 phút. Chạy nối tiếp = hơn hai
tiếng rưỡi. Đó là toàn bộ phần thắng, và nó đến từ R-S2 chứ không từ phần cứng.

### R-S7 · Việc dài khởi động TRƯỚC

`gate.py` đã dùng đúng lịch này cho các bước của nó (`NHOM = (cong, nang, tinh,
…)`, việc dài chạy trước để mọi thứ khác nấp vào bóng nó). Cùng luật ở tầng
phiên: dispatch agent (dài) trước, rồi mới làm việc tay ngắn trong lúc chờ.

---

## 2. Cái KHÔNG được đổi

1. ⛔ Trần `-n 6` và `cua_so_yen` — luật của `CLAUDE.md`, không nới bằng tệp này.
2. ⛔ `tai_may.py` **chỉ đọc**, không chặn ai. Một cửa bị chặn sẽ đẻ ra cờ
   `--bo-qua`, và từ đó cửa ấy không còn tồn tại.
3. ⛔ Không thêm một cửa CPU thứ hai trước `bo test`: `gate.py` đã có ngân sách
   lõi **và** `BELOW_NORMAL_PRIORITY_CLASS` — lớp thứ hai mạnh hơn mọi ngưỡng
   đoán từ bên ngoài.

---

## 3. Việc còn để mở

* ~40 tiến trình `node.exe` của MCP (~1,6 GB) trông như **bản sao thừa** của các
  phiên đã đóng (playwright ×10, episodic-memory ×4, chrome ×3). Chưa đụng: giết
  nhầm là gãy công cụ của chính phiên đang chạy. Cần một cách **nhận diện tiến
  trình mồ côi** trước khi dọn — chủ dự án quyết.
* Bảng giá ở R-S6 lấy từ quan sát trong lúc làm việc, không từ một lượt đo có
  đối chứng. Đủ để xếp lịch, **chưa đủ** để làm ngưỡng cho một cổng tự động.
