# Rà soát toàn bộ logic vận hành — chấm điểm, vá chất lượng, kế hoạch tới khi bán được

**2026-08-22, 23:00.** Rà soát do chính tôi làm trên mã tôi vừa viết. Mọi kết luận
dưới đây **đo được hoặc chỉ được ra dòng mã**, không có nhận định cảm tính.

Cách chấm: **10 = có bằng chứng chạy thật + có test neo + đã nghĩ tới đường hỏng.**
Thiếu bằng chứng thật thì trần là 7, dù mã đẹp đến đâu.

---

## 1. Ba lỗi TÌM RA TRONG CHÍNH BUỔI RÀ SOÁT NÀY

Ghi trước, vì chúng là kết quả có giá trị nhất của việc rà soát.

### 🔴 L1 — `qwen38-vision` gần như KHÔNG BAO GIỜ gọi được

**Triệu chứng:** mọi yêu cầu tới hồ sơ vision trả **429** sau 18 giây.

**Nguyên nhân:** `api.py` hỏi *"đúng model NÀY đã nạp chưa?"*. Khi `qwen38-api`
đang chạy và giữ 19.973 MiB, câu trả lời là "chưa" ⇒ `don_dep` chạy ⇒ nó thấy VRAM
cao ⇒ **bảo ComfyUI nhả** (ComfyUI chẳng giữ gì) ⇒ chờ 18 giây ⇒ VRAM không đổi vì
**nó là của chính ta** ⇒ 429.

`llama-swap` vốn **tự đổi hồ sơ được**. Mã của tôi chặn nó trước.

**Đã sửa:** hỏi *"có model nào CỦA TA đang chạy không?"*. Có ⇒ để `llama-swap` lo.
**Kiểm thật sau khi sửa: 200 sau 21,6 giây** (gồm cả thời gian đổi model).
Neo bằng `test_doi_sang_ho_so_KHAC_cua_ta_KHONG_bi_chan`.

### 🔒 L2 — Ảnh `image_url` trỏ ra ngoài là một đường SSRF

Chuyển tiếp `image_url` nghĩa là **máy B** đi tải nó. Khách gửi
`http://127.0.0.1:8188/...` là bắt máy B gọi vào chính mạng nội bộ của nó — và
**ComfyUI ở cổng 8188 không có xác thực**.

Đo thật: llama-server hiện **từ chối** URL http (trả 400). Nhưng đó là **bảo đảm đi
mượn** — nó phụ thuộc hành vi thượng nguồn và có thể đổi ở một bản nâng cấp.

**Đã sửa:** `ngan_sach` chỉ nhận `data:` URL. Sau khi vá, đo thật: **413 trong
0,13 giây**, không chạm tới model. Neo bằng 6 test (ComfyUI, máy A, metadata IMDS,
`file://`, https ngoài).

### ⚠️ L3 — `/free` chỉ ĐẶT CỜ, và điều đó đổi cách nên dùng nó

Đọc `server.py` của ComfyUI:

```python
@routes.post("/free")
async def post_free(request):
    if unload_models: self.prompt_queue.set_flag("unload_models", True)
```

Nó **không nhả ngay** — nó đặt cờ, và hàng đợi xử lý cờ **giữa các prompt**.

- **Tin tốt:** gọi `/free` giữa một lượt video **không cắt ngang** lượt đó.
- **Tin phải xử lý:** nếu video đang chạy, cờ sẽ nổ **ngay sau khi video xong** —
  và nếu dự án video xếp nhiều lượt liên tiếp, ta vừa bắt họ nạp lại model.

**Chưa sửa** — xem V2 trong kế hoạch: hỏi `/queue` trước, đang chạy thì **đừng đặt
cờ**, trả 429 ngay (nhanh hơn 18 giây và không làm phiền hàng xóm).

---

## 2. Chấm điểm từng hạng mục

| # | Hạng mục | Điểm | Căn cứ |
|---|---|---:|---|
| 1 | **Ngăn xếp phục vụ máy B** (llama.cpp · llama-swap · dịch vụ · tường lửa) | **9,5** | Nghiệm thu 19/19 trên phần cứng thật. Số đo đầy đủ. Tường lửa đã kiểm từ máy A: 8299 mở, 8280/8281/8282/8188 **đóng**. Trừ 0,5: chưa qua một lần reboot thật |
| 2 | **Trọng tài VRAM** (`don_dep` + `trong_tai`) | **8,0** | Bắt được lỗi tràn im lặng 3,5× và neo bằng test. Vừa sửa L1. Trừ 2,0: L3 chưa xử, và chưa phân biệt "ComfyUI rảnh mà ôm" với "ComfyUI đang render" |
| 3 | **Cổng VLM** (`llm_gateway`) | **9,0** | 36 test. Ba giao thức. Fail-closed. SSE chuyển tiếp nguyên byte. Vừa vá SSRF. Trừ 1,0: chưa có giới hạn tần suất của riêng cổng |
| 4 | **Adapter + điều phối** (`cong_vlm` · `dieu_phoi`) | **9,0** | 34 test. Bận≠lỗi neo bằng test. Đã bắt lỗi `base_url` lấy sai chỗ. Trừ 1,0: **chưa có đường streaming** |
| 5 | **Giá + quyết toán** (`gia_token` · `thanh_toan`) | **8,5** | 32 test, số nguyên toàn phần, nhãn phiên bản giá, "không đo được thì không thu". Trừ 1,5: **chưa nối vào bất kỳ đường chạy thật nào** — mới chỉ có test |
| 6 | **App `ltt_llm` + hợp đồng công khai** | **8,0** | 22 test. Một khai báo, hai cửa. Lớp alias đã đúng sau khi `test_212` bắt lỗi. Trừ 2,0: **cửa đồng bộ chưa có**, và `LTT_PUBLIC_API_TOOLS` chưa bật |
| 7 | **Bảo mật** | **8,5** | Token mã hoá, không log. Tường lửa một IP. `llama-server`/ComfyUI chỉ loopback. SSRF đã bịt. Trừ 1,5: `/health` đòi bearer nên máy giám sát không thăm dò được; chưa có giới hạn tần suất ở cổng |
| 8 | **Tài liệu + truy vết quyết định** | **9,0** | 8 tài liệu, mọi con số có nguồn, **mọi lần tôi sai đều ghi lại kèm số đo bác bỏ**. Trừ 1,0: chưa có tài liệu cho **khách** |
| 9 | **Quan sát được** (observability) | **4,0** | 🔴 Yếu nhất. `/health` có số, nhưng **không ai gọi nó**: không cảnh báo khi máy B chết, không đo tần suất 429, không biết tỉ lệ cache thật. Hỏng lúc 2 giờ sáng thì sáng ra mới biết |
| 10 | **Bán được cho khách ngoài** | **3,0** | Cửa job **đã sống về mặt catalog** nhưng chưa bật công tắc, chưa qua Cloudflare, chưa có tài liệu, chưa có khoá khách, chưa có sandbox |

**Trung bình có trọng số: ≈ 7,7/10.**
Hai điểm kéo xuống — **quan sát được** và **bán được** — đều là *"chưa làm"*, không
phải *"làm sai"*. Đó là tin tốt hơn ngược lại.

---

## 3. Nghiên cứu: ba việc nâng chất lượng có bằng chứng

### N1 — `--jinja` + `--reasoning-format deepseek` đang đúng, nhưng `reasoning_effort` chưa được đo

Template cộng đồng đặt mặc định `medium`. Nhưng con số IFBench **78,3** mà cộng đồng
công bố được đo ở **`xhigh`**. Ta đang phục vụ ở `medium` và **chưa đo** chênh lệch.

⇒ **V6**: chạy bộ 10 prompt vận hành ở cả `medium` và `xhigh`, đo cả chất lượng lẫn
số token ra. Nếu `xhigh` tốt hơn đáng kể thì đó là một **lựa chọn của khách** có
giá khác nhau, không phải một mặc định ta tự chọn hộ.

### N2 — `--parallel 1` đang bỏ phí thông lượng khi có nhiều khách

Cộng đồng đo: lợi thế speculative **biến mất ở `--parallel 4`**. Ta đặt `1` vì đó là
cấu hình họ dùng để **đo**, và một người dùng thì đúng là nhanh nhất.

Nhưng khi bán ra ngoài, hai khách gọi cùng lúc sẽ **xếp hàng**. Với `--parallel 1`,
khách thứ hai chờ trọn lượt của khách thứ nhất.

⇒ **V7**: đo `--parallel 1` với `2` và `4` ở **tải nhiều luồng** (khác hẳn cách đo
một luồng của cộng đồng). Chọn theo tổng thông lượng, không theo tốc độ một lượt.

### N3 — Cửa sổ 64K đang phí VRAM khi phần lớn lượt gọi ngắn

Đo được: prefill 1.050–1.190 tok/s; cửa sổ 64K tốn ~2 GB KV ở `q8_0`. Nhưng lượt
gọi bot điển hình chỉ 2.000 token vào.

⇒ **V8**: cân nhắc hồ sơ thứ tư `ltt_llm_fast` (16K, KV f16) cho lưu lượng ngắn —
KV f16 **chất lượng cao hơn** q8_0 và vẫn còn thừa VRAM. Chỉ làm **sau khi** có số
liệu thật về phân bố độ dài prompt của khách. **Chưa có khách thì chưa có số.**

---

## 4. Hạng mục còn lại — 14 việc

| # | Việc | Vì sao cần | Ước |
|---|---|---|---:|
| ~~**V1**~~ | ~~Nối `thanh_toan` vào một đường chạy thật~~ | ✅ **XONG 23/08** — và tìm ra một lỗi tiền thật, xem §8 | 0,5 ngày |
| **V2** | `don_dep` hỏi `/queue` trước khi đặt cờ `/free` | L3 — nhanh hơn 18 giây, không làm phiền hàng xóm | 0,5 ngày |
| ~~**V3**~~ | ~~Route `POST /api/v1/chat/completions`~~ | ✅ **XONG 23/08** — cần **Q106** (chế độ `SYNC_BILLED`) chứ không chỉ cần mã; xem §9 | 1,5 → 2,75 ngày |
| **V4** | Streaming SSE + tính tiền khi khách ngắt giữa chừng | 🔺 **ƯU TIÊN LẠI 23/08 — nay là ĐƯỜNG CHÍNH.** Chủ sản phẩm bỏ đường LAN, chốt một cửa qua API; mà **cả ba client CLI đều bắt buộc streaming**. Chi tiết: `LO_TRINH_API_CLI.md` | 1,0 ngày |
| **V5** | 🔴 **Giám sát + cảnh báo** | Điểm 4/10. Máy B chết lúc 2h sáng thì phải biết | 1,0 ngày |
| **V6** | Đo `reasoning_effort` medium vs xhigh | N1 — đang chọn hộ khách mà chưa đo | 0,5 ngày |
| **V7** | Đo `--parallel` ở tải nhiều luồng | N2 — bán ra ngoài thì không còn một luồng | 0,5 ngày |
| **V8** | Hồ sơ `fast` 16K KV f16 | N3 — **hoãn tới khi có số thật của khách** | — |
| ~~**V9**~~ | ~~Giới hạn của riêng cổng VLM~~ | ✅ **XONG 23/08** — đồng thời + tần suất, đo thật trên máy B | 0,5 ngày |
| **V10** | `/health` cho phép thăm dò không cần bearer | Máy giám sát không mang được bí mật | 0,25 ngày |
| **V11** | Bật `LTT_PUBLIC_API_TOOLS=text.chat` + kiểm **qua Cloudflare thật** | Quy tắc 5b: loopback đẹp không chứng minh gì | 0,5 ngày |
| **V12** | Khoá API cho khách + sandbox | Chưa có khách nào gọi được | 0,5 ngày |
| ~~**V13**~~ | ~~Tài liệu API + ví dụ cho khách~~ | ✅ **XONG 23/08** — và nó lộ ra hai lỗi thật; xem §10 | 1,0 ngày |
| **V14** | Nghiệm thu sống qua một lần **reboot thật** máy B | Chưa ai chứng minh | 0,25 ngày |

**Tổng: ~8,5 ngày công.**

---

## 5. Thứ tự thi hành — vì sao thứ tự này

**Đợt A — bịt lỗ đang chảy (1 ngày).** V2 · V5 · V10.
Làm trước vì chúng là **rủi ro đang tồn tại**, không phải tính năng thiếu. Một hệ
thống không quan sát được thì mọi thứ xây thêm lên nó đều là xây trong bóng tối.

**Đợt B — đóng vòng tiền (1,5 ngày).** ✅ **XONG 23/08.** V1 · V9.
Trước khi mở cho khách, phải chắc **một lượt gọi bị tính đúng một lần**.

**Đợt C — mở cửa đồng bộ.** ✅ **V3 XONG 23/08** · **V4 nay là đường chính** (`LO_TRINH_API_CLI.md`).
Đây là thứ khách cần để trỏ SDK vào. V3 hoá ra không phải việc thêm mã mà là việc
thêm **hợp đồng** — xem §9.

**Đợt D — đo để chốt (1 ngày).** V6 · V7.
Làm **sau** khi có cửa đồng bộ, vì lúc đó mới đo được đúng hình dạng tải thật.

**Đợt E — mở bán (2,25 ngày).** V11 · V12 · V13 · V14.

**Đợt F — sau khi có khách.** V8, và mọi thứ đo được từ lưu lượng thật.

---

## 6. QUY TẮC VẬN HÀNH — hiệu lực từ bây giờ tới khi bán được

Đây là phần chủ dự án yêu cầu bổ sung. Chúng **ràng buộc chính tôi** ở mọi phiên sau.

### QT-1. Không con số nào vào mã mà chưa đo trên máy B

Trần ngữ cảnh, trần token, ngưỡng VRAM, giá — mỗi con số phải chỉ được ra một phép
đo, kèm ngày. Mượn số của cộng đồng thì **ghi rõ là mượn** và đặt nó thành việc đo.
*(Đã có tiền lệ: mốc 200K của cộng đồng đo với prompt 400 token — một con số cấp
phát, không phải con số dùng được.)*

### QT-2. Bận ≠ hỏng, và ranh giới đó không được mờ

`429` cho bận, `502` cho hỏng, `413` cho quá to. **Không bao giờ** gọi
`danh_dau_loi()` cho một cái 429. Mọi lớp mới phải có test neo điều này — mất nó là
model nhà **tự tắt vĩnh viễn** sau 5 lần hàng xóm bận.

### QT-3. Không dựng động cơ thứ hai

Một bảng giá (`gia_token`), một danh mục (manifest), một đường gọi model
(`dieu_phoi`), một phép đo bận (`render_gateway.busy`). Thấy mình sắp viết cái thứ
hai thì **dừng lại và nói vì sao**, đừng viết.

### QT-4. Thất bại phải ồn ào

Số đo 22/08: card bẩn cho 18,2 tok/s, card sạch cho 63,3 — `/health` **xanh cả
hai**. Mọi cơ chế mới phải trả lời được: *"nếu nó hỏng, ai biết, và biết bằng cách
nào?"* Không trả lời được thì chưa xong.

### QT-5. Kiểm trên đường mà khách thật sự đi

Loopback không chứng minh gì cho LAN; LAN không chứng minh gì cho Cloudflare.
`kiem_tra.ps1` chạy từ **máy A**, không phải từ máy B, đúng vì lý do này. Bước V11
phải chạy qua **Cloudflare thật**.

### QT-6. Máy B là máy dùng chung — đụng vào thì phải hỏi

ComfyUI, cổng 8188 và `E:\AI\tools\` thuộc dự án ảnh và dự án video. Đổi cách khởi
động, đổi cờ, hay dừng tiến trình của họ là **quyết định của chủ dự án**, không phải
của tôi. Đã áp dụng: việc ComfyUI tự khởi động vẫn đang chờ, dù script đã sẵn sàng.

### QT-7. Việc dài kết thúc trước 01:00 — ⏳ **quy tắc TẠM, chờ gỡ tận gốc**

**Mốc này không phải do ai nghĩ ra, nó là một số đọc được trên máy B:**

```
HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings
  ActiveHoursStart = 0x7   (07:00)
  ActiveHoursEnd   = 0x1   (01:00)
```

Ngoài khung đó Windows được phép tự cài bản vá rồi khởi động lại. Đã xảy ra
**một lần, 22/08 lúc 01:29:31** — `MoUsoCoreWorker.exe` trên danh nghĩa `SYSTEM`,
lý do *"Operating System: Service pack (Planned)"*, cuốn theo một lô ảnh đang
chạy dở.

⚠️ **ĐÍNH CHÍNH 23/08.** Tôi từng quy cả sự cố CUDA ngày 23/08 cho quy tắc này.
**Sai.** Sự kiện `1074` lúc 13:16:37 hôm đó là `StartMenuExperienceHost.exe`
trên danh nghĩa `lengo`, *"power off, Other (Unplanned)"* — **một người bấm tắt
máy**, không phải Windows Update. Quy tắc này chỉ có **một** sự kiện thật đứng
sau nó, không phải hai.

🔴 **Cách đúng là gỡ NGUYÊN NHÂN, không phải sống chung với triệu chứng.** Bắt
việc dài kết thúc trước 01:00 là để nguyên cái bẫy rồi đi vòng quanh nó, và cái
vòng đó tính vào **mọi phiên sau**. Cách gỡ (cần Administrator trên máy B):

```
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" /v NoAutoUpdate /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" /v AUOptions /t REG_DWORD /d 3 /f
```

`AUOptions = 3` = **tải về nhưng KHÔNG cài nếu chưa có người bấm**. Không cài thì
không khởi động lại. Máy B là Windows 11 **Pro** nên chính sách này có hiệu lực
(bản Home bỏ qua).

⚖️ **Đánh đổi, nói thẳng:** bản vá bảo mật từ đó cần một người bấm. Máy B chỉ
nghe LAN sau tường lửa và không giữ bí mật nào của nền tảng, nên đổi này chấp
nhận được — nhưng nó là đổi thật, và nó cần một thói quen mới: **rà cập nhật
bằng tay theo lịch**.

✅ **Khi đã áp dụng và xác nhận, XOÁ hẳn quy tắc này** thay vì để nó nằm lại làm
một điều kiêng kỵ không ai còn nhớ vì sao.

### QT-8. Ghi lại mọi lần tôi sai, kèm số đo bác bỏ

Phiên này đã sai 6 lần: *"buộc phải dùng vLLM"*, *"cấm mốc 200K"*, *"llama.cpp báo
lỗi to khi GPU chưa sạch"*, ngưỡng bận `>0` thay vì `≥2`, alias trùng id nội bộ, và
L1 ở trên. **Mỗi lần đều do một phép đo hoặc một test bác bỏ, không phải do tôi
nghĩ lại.** Đó là lý do phải đo và phải có test — và là lý do phải ghi lại.

### QT-9. Không tự báo xanh khi chưa có bằng chứng

Đã vi phạm một lần trong phiên này: tôi báo *"suite nền 36 %, chưa lỗi nào"* trong
khi tiến trình **đã chết từ 19:54**. Từ nay: chưa thấy dòng tổng kết thì nói là
**chưa có kết quả**, không nói là đang xanh.

### QT-10. Fail-closed ở mọi cổng mới

Bật một cờ không bao giờ được mở thêm năng lực. `LTT_LLM_MODELS` rỗng ⇒ không model
nào. `LTT_PUBLIC_API_TOOLS` rỗng ⇒ không tool nào. Ba cổng độc lập của Q92 —
`api_exposed`, `surface`, công tắc người vận hành — giữ nguyên cả ba.

### QT-11. Test chỉ xanh lúc cô lập thì chưa phải bằng chứng

Chạy một file test riêng là **kiểm tra khi viết**, không phải bằng chứng. Bằng
chứng là nó xanh **trong lượt chạy đầy đủ**, cùng mọi test khác, theo thứ tự
pytest tự chọn.

Đã dính 23/08: 34 test của H38 xanh khi chạy lẻ và **đỏ khi chạy cùng cả rổ**. Gốc
là một kỹ thuật giả lập sai — xem QT-12.

Kèm theo: **một test xanh mà không nói được nó bác bỏ điều gì thì chưa phải bằng
chứng.** Tôi viết một test HTTP tưởng chứng minh "suất còn giữ giữa luồng SSE";
nó xanh, nhưng `TestClient` hút cạn thân phản hồi trước khi trả `status_code`, nên
nó đo "sau luồng". Cách chữa không phải sửa test cho khéo hơn — mà là **tách phần
cần đo ra chỗ đo thẳng được** (`gioi_han.boc_luong`).

### QT-13. Giữ nguyên kiểu kết thúc dòng của file

Repo này lưu **CRLF**. `pathlib.read_text` chuẩn hoá về `
`, nên ghi lại bằng
`write_text(..., newline="")` **đổi dòng cả file**: `git diff` phình từ 9 dòng
thành 137, thay đổi thật bị chôn, và hai phiên làm cùng repo đụng nhau nặng.

Đọc/ghi bằng **bytes**, hoặc khôi phục kiểu dòng gốc sau khi ghi. Kiểm bằng
`git diff --numstat` — số dòng phải khớp với thay đổi thật.

### QT-14. Tài liệu phải được chạy thử, không chỉ được đọc lại

Một ví dụ không chạy được còn tệ hơn không có ví dụ: người đọc tin nó, mất một
buổi chiều, rồi kết luận **API hỏng** chứ không kết luận ví dụ sai.

Trước khi in một lời gọi cho khách, **chạy nó bằng đúng công cụ khách sẽ dùng**.
Ngày 23/08 việc này bắt được hai lỗi mà toàn bộ bộ test không thấy: SDK OpenAI
gọi trần trả `400` (L4), và cửa job của `text.chat` từ chối mọi input hợp lệ
(L5). Cả hai đều nằm ngay ở dòng lệnh đầu tiên của tài liệu.

### QT-12. Giả lập bằng cách vá HÀM, không vá `sys.modules`

Mã trong dự án này gần như luôn viết `from platform_core import api_pool` chứ không
`import platform_core.api_pool`. Dạng đó lấy **thuộc tính của gói cha** khi gói cha
đã nằm trong `sys.modules` — nên `monkeypatch.setitem(sys.modules, ...)` chỉ ăn khi
chưa ai import thật, tức là **chỉ khi chạy file test đó một mình**.

```python
# SAI — phu thuoc thu tu chay
monkeypatch.setitem(sys.modules, "platform_core.api_pool", gia)

# DUNG — va thang vao mo dun that
from platform_core import api_pool
monkeypatch.setattr(api_pool, "chon_key", gia_chon_key)
```

Triệu chứng khi làm sai rất dễ đọc nhầm: test đỏ hàng loạt trong lượt đầy đủ, xanh
hết khi chạy lại từng file — trông y như "lỗi ngẫu nhiên của CI".

---

## 7. Trạng thái test lúc rà soát

| | |
|---|---|
| Test của hạng mục H38 | **125 xanh** (`test_250` 36 · `251` 20 · `252` 18 · `253` 14 · `254` 11 · `255` 14 · `256` 22) |
| `tools\gate.py --quick` | **12/12 PASS** |
| Nghiệm thu máy B | **19/19** |
| Kiểm toàn tuyến máy A → máy B | **9/9** |
| **Suite đầy đủ** | ⏳ **đang chạy, 31 %, có 2 F** — chưa biết là test nào. **Chưa được coi là xanh** (QT-9) |


---

## 8. Đợt B — thi hành 23/08/2026

### V1 — nối tiền vào đường chạy thật, và một lỗi tiền im lặng

Việc này bắt đầu như một việc nối dây, và kết thúc bằng việc tìm ra một **lỗi
tiền thật đang nằm sẵn trong mã**.

`platform_core/job_runner.py:537` quyết toán như sau:

```python
actual = result.get("credit_cost")
if actual is None:
    actual = credit.so_da_giu(db, job.id)      # <- dung dung PHAN DA GIU
```

`apps/ltt_llm/jobs.py::handle` trả `usage` nhưng **không** trả `credit_cost`. Mà
phần đã giữ là **trần ước cao** — cố ý cao, để khách không tiêu quá số dư. Hệ quả:

> Khách xin `max_tokens=4096`, model chỉ sinh 200 token, **khách vẫn trả đủ 4096.**

Không lỗi, không log, không ai biết. Chỉ hoá đơn sai — và sai về phía khách.

**Sửa:** `KetQua.gia_that_credit()` tính lại giá từ token **đã đo**, và
`as_result()` báo nó qua `credit_cost`. Hai luật đi kèm:

- **Không bao giờ vượt trần.** `credit.quyet_toan` đã kẹp ở phần đã giữ, nhưng
  `test_gia_that_KHONG_BAO_GIO_vuot_tran` quét mọi kết cục để bắt trường hợp công
  thức ước trần bị sai chứ không phải trường hợp lẻ.
- **Không đo được thì không thu** (`dang_tin=False` ⇒ **0**, không phải phần đã
  giữ). Thu tiền mà không có bằng chứng còn tệ hơn mất một ít tiền — cùng luật
  với `thanh_toan.quyet_toan_hoac_hoan`.

### V9 — hàng rào của riêng cổng

`llm_gateway/gioi_han.py`. **Chốt chính là ĐỒNG THỜI, không phải tần suất** — ngược
với một API web thường. Một lượt LLM kéo dài hàng chục giây, nên "20 lượt mỗi phút"
gần như không chặn gì, còn "2 lượt cùng lúc" thì chặn đúng thứ cần chặn. Và vì
`llama-server` chạy `--parallel 1`, 50 yêu cầu đồng thời **không** thành 50 lượt
song song — chúng thành 50 kết nối treo và một hàng đợi không ai nhìn thấy.

Đặt **sau** ngân sách (413 phải dứt khoát) và **trước** việc dọn (`bao_dam_sach()`
chờ tới 18 giây — chỗ tốn thời gian mới là chỗ phải chặn).

Số đo thật trên máy B, 23/08 lúc 00:2x — 5 lượt bắn cùng lúc, `max_dong_thoi=2`:

| lượt | mã |
|---|---|
| 1, 2 | `200` |
| 3, 4, 5 | `429`, `retry-after: 15` |

### Ba lỗi của chính tôi trong đợt này (QT-8)

**S-1 — trả suất hai lần.** Bản đầu để `gh.xong()` trần: `finally` trong hàm chạy
trả một lần, rồi `except` ở hàm gọi trả tiếp. Bộ đếm tụt **dưới** số thật ⇒ cổng
nhận nhiều lượt hơn hạn mức ⇒ chốt lặng lẽ **ngừng chốt**, không ném lỗi nào.
Sửa: `Suat` là một thẻ **một-lần**, tính đúng nằm trong kiểu dữ liệu chứ không
phụ thuộc vào việc đọc kỹ luồng điều khiển.

**S-2 — một test xanh vì lý do sai.** Tôi viết một test HTTP tưởng là chứng minh
"suất còn giữ giữa luồng SSE". Nó xanh. Nhưng `TestClient` của Starlette **hút cạn
thân phản hồi trước cả khi trả `status_code`** — nhãn ghi "giữa luồng", thứ nó đo
là "sau luồng". Sửa: tách bộ bọc thành `gioi_han.boc_luong()` và đo thẳng
generator đó (giữ tới miếng cuối · `close()` giữa chừng · thượng nguồn nổ).
*Bài học: một test xanh mà không nói được nó bác bỏ điều gì thì chưa phải bằng chứng.*

**S-3 — chẩn đoán vội "mã mới làm chết dịch vụ".** Xem ngay dưới.

### 🔴 Bẫy hạ tầng: `AppThrottle` lớn hơn thời gian chờ của SCM

Sau khi deploy, `net stop LTTLlmGateway & net start LTTLlmGateway` báo *"could not
be started"* và **cổng VLM nằm im ở trạng thái STOPPED**. Trông hệt như mã mới vỡ.

Nó không phải. Log ứng dụng ghi `Uvicorn running on http://0.0.0.0:8299` — app
**lên được**. Nhật ký sự kiện Windows mới nói ra nguyên nhân:

```
The minimum number of milliseconds which must pass before service LTTLlmGateway
is considered to have been started successfully is set to 90000.  ...  NSSM will
wait a maximum of 20000 milliseconds before reporting the service's state.
```

`AppThrottle = 90000` **lớn hơn thời gian chờ của SCM (~30 giây)**. SCM chờ hết
giờ → tuyên bố khởi động thất bại → gửi STOP → dịch vụ chết hẳn.

**Sửa:** `AppThrottle 5000` cho cả hai dịch vụ, trong
`llm_gateway/deploy/cai_dat_dich_vu.ps1` và trên máy B đang chạy. 5 giây vẫn chặn
được vòng lặp crash, mà không bao giờ đụng vào trần chờ của SCM. Đã chứng minh:
đúng lệnh `net stop` + `net start` đó giờ chạy sạch.

⚠️ **Bẫy này áp cho MỌI dịch vụ NSSM của dự án**, không riêng cổng VLM.
`render_gateway/deploy/cai_dat_dich_vu.ps1` cần soát cùng một chỗ.


---

## 9. Đợt C/V3 — thi hành 23/08/2026

### Nó không phải việc thêm mã

V3 vấp chốt của chính nền tảng ngay dòng đầu tiên: mọi route phải khai một
`execution_mode`, và **không chế độ nào đang dùng mô tả được một lượt chat**.
`SYNC` cấm cả ba thứ nó cần — cấm thu tiền, cấm gọi GPU, cấm quá 5 giây — và
`check_mode_rules` **chặn thẳng**, không phải chỉ khuyên.

Lách được, và đó là cái bẫy: khai `SYNC` với `chargeable=False` **qua được** cửa,
rồi để lại một lượt đốt GPU mà không ai bị tính tiền. Chủ sản phẩm chọn **B** —
khai đúng thứ đang xảy ra.

**Q106: `SYNC_BILLED`.** Trả lời trong request, **có thu tiền**, **bắt buộc
`Idempotency-Key`**, **không có quote**, **không đẩy vào hàng đợi**, trần 90 giây.

Ba nhánh mới trong `check_mode_rules`, và mỗi nhánh là một cách hỏng đã lường:

| chặn | vì sao |
|---|---|
| `chargeable=False` | Miễn phí mà trả trong request thì là `SYNC`, và `SYNC` khắt khe hơn. Để nó nằm đây là lặng lẽ mua cho nó ngân sách 90 giây mà nó chưa bao giờ biện minh. |
| thiếu `Idempotency-Key` | Không có quote thì đây là thứ **duy nhất** chặn một lần thử lại vì mạng mua hàng hai lần. |
| có `requires_quote` | Quote là giá **ký trước khi chạy**. Giá token không biết trước được — đòi quote là buộc ta ký một con số không giữ nổi. |

### Trần 90 giây dẫn ra từ đâu

```
ngân sách chế độ                        90 s   (100 s của Cloudflare trừ biên)
− trường hợp xấu nhất: llama-swap đổi model   −25 s
= còn lại để sinh chữ                    65 s
× tốc độ đã đo trên máy B (card sạch)   × 63 tok/s
                                      ≈ 4.095 token
```

Xin nhiều hơn thì **từ chối bằng 400 và chỉ sang cửa job**, đừng nhận rồi để
Cloudflare cắt bằng một cái 524 không phân biệt được "hỏng" với "xong rồi nhưng
mất kết nối".

### Một khiếm khuyết tôi tự tạo ra rồi tự bắt: giao dịch trùm lên lượt gọi

Bản đầu để nguyên một giao dịch chạy suốt từ lúc giữ chỗ tới lúc quyết toán —
tức là **suốt 90 giây gọi model**. Ba thứ hỏng:

1. `idempotency.begin` lấy `pg_advisory_xact_lock`, và khoá đó sống hết giao
   dịch ⇒ một yêu cầu trùng khoá **treo 90 giây** thay vì nhận ngay câu trả lời
   đúng ("đang xử lý").
2. Một kết nối CSDL bị giữ suốt lượt gọi ⇒ N lượt đồng thời là hết pool, và thứ
   chết trước là **những trang không liên quan gì** — đăng nhập, nạp tiền.
3. Tiến trình chết giữa chừng thì cuộn ngược xoá **cả** phần giữ chỗ **lẫn** bản
   ghi idempotency ⇒ lần thử lại đốt GPU thêm một lần nữa.

Sửa: `db.commit()` ngay sau khi giữ chỗ. Hai test neo nó, và **cả hai đã được
kiểm là đỏ khi gỡ dòng commit** — theo đúng QT-11.

### 429 hay 503 khi máy B bận — ranh giới không được mờ

Tôi viết 429 lúc đầu, quen luật của `llm_gateway` nơi *máy A đọc máy B*. Ở bề mặt
khách thì `error_registry` đã chốt khác: **429 = "bạn đang gọi quá nhanh"**,
**503 = "máy không phục vụ được lúc này"**. Máy B bận là vế sau — khách không có
lỗi gì, và bảo họ chậm lại cũng không giúp. `_refuse_if_no_capacity` ở cửa job
trả lời đúng như vậy, và hai cửa phải nói cùng một ngôn ngữ.

### Đã dọn những đâu

`protocol.py` · `server/api/inventory.py` · `server/api/chat.py` (mới) ·
`server/api/__init__.py` · SDK Python (`chat()`) · SDK TypeScript (`chat()`) ·
bộ sưu tập Postman · `test_178` (khu vực `chat` vào `/capabilities`) ·
`QUYET_DINH_NEN_TANG.md` (Q106) · `NHAT_KY.md`.


---

## 10. V13 — tài liệu, và hai lỗi nó lôi ra

Viết tài liệu là việc **đọc lại lời hứa của mình bằng mắt người lạ**, nên nó bắt
lỗi theo một kiểu mà test không bắt được. Đợt này lôi ra hai cái, cái thứ hai
nghiêm trọng.

### 🔴 L4 — lời hứa "cắm SDK OpenAI vào là chạy" KHÔNG đúng như đã xây

Q106 biện minh cho cả chế độ `SYNC_BILLED` bằng câu *"SDK OpenAI chạy được ngay,
không sửa gì"*. Trước khi in câu đó cho khách, tôi chạy thử bằng **chính SDK
thật** (`openai` 2.30.0):

```
OpenAI(base_url=".../api/v1").chat.completions.create(...)          -> 400
... create(..., extra_headers={"Idempotency-Key": uuid4().hex})     -> 200
```

**Vì sao.** SDK của OpenAI **tự sinh** một khoá idempotency cho mỗi lượt POST và
dùng lại nó qua các lần thử lại của chính nó — nhưng chỉ **gửi** khi
`_idempotency_header` được đặt, và với client OpenAI thì nó là `None`. Khoá được
sinh ra rồi vứt đi.

**Đã làm gì.** Không giấu, không nới hợp đồng. Tài liệu nói thẳng chỗ phải thêm,
**thông báo lỗi 400 dạy luôn cách sửa** (đó là trang tài liệu duy nhất chắc chắn
được đọc), và `test_259` neo cả hai hành vi bằng SDK thật chứ không giả lập nó.

⚠️ **Còn một quyết định để ngỏ:** giữ `Idempotency-Key` bắt buộc (an toàn tiền,
mất tính "cắm vào là chạy") hay suy ra một khoá mặc định khi khách không gửi
(được tính "cắm vào là chạy", nhưng hai lượt gọi giống hệt nhau trong cùng cửa sổ
sẽ bị gộp làm một — hỏng đúng cách lấy mẫu best-of-N). **Chưa tự quyết.**

Cái bẫy đi kèm, đã đo: đặt khoá cố định ở `default_headers` hỏng theo **hai**
kiểu — prompt khác thì `409` (ồn ào, nhìn thấy được), prompt **giống hệt** thì
nhận lại **câu trả lời cũ** không dấu hiệu gì (im lặng, nguy hiểm hơn nhiều).

### 🔴 L5 — cửa JOB của `text.chat` chưa bao giờ dùng được

`test_199` đối chiếu **ví dụ đã công bố** với **bộ kiểm thật** và đỏ:

```
POST /api/v1/jobs  {"tool":"text.chat","input":{"messages":[...]}}
-> 400 invalid_request: messages must be an object.
```

Nghĩa là cửa bất đồng bộ của tool này **từ chối mọi input hợp lệ** kể từ lúc
dựng — kể cả đúng ví dụ trang tài liệu in ra. Và V1 của Đợt B đã đi nối phần
quyết toán tiền cho **một cánh cửa không ai qua được**.

**Gốc rễ.** Bảng kiểu của `ToolSpec` không có cách nào nói *"một mảng JSON"*: chỉ
có `json`, mà `json` phơi công khai thành `object`, rồi `_validate_value` đòi một
`dict`. `messages` là một **list**.

**Sửa.** Thêm kiểu `json[]` vào bảng (`registry.py` + `catalog.py`), khai lại
`messages`/`tools`/`tool_calls`. **Không** nới lỏng `object` cho nhận cả list —
nới lỏng là làm yếu bộ kiểm của **mọi** tool khác để chiều một tool. Ghi vào
`CHANGELOG.md` và chạy `check_api_compat --accept`.

*Bài học, và nó thuộc về QT-11: bộ test cũ chỉ hỏi "tool này khai gì". Không ai
hỏi "khách dán đúng ví dụ ta in ra thì có chạy không". Nay `test_199` và
`test_256` hỏi câu đó.*

### Đã làm những gì

| | |
|---|---|
| `examples.py` | 6 ví dụ cửa chat (SDK OpenAI Python/TS · cURL · Python trần · PowerShell · HTTP thô) + `CHAT_DIFFERENCES` — sáu chỗ cửa chat khác cửa job |
| `DEVELOPER_GUIDE.md` §1b | chương riêng: bảng so hai cửa, tiền giữ-trần-thu-đo, trần thời gian, bận-503, chế độ thử |
| Cổng lập trình viên | mục mới ở `/developers/quickstart`, **chỉ hiện khi `text.chat` thật sự đang mở** (fail-closed của Q92 phải nhìn thấy được ở tài liệu) |
| Thông báo lỗi 400 | dạy luôn `extra_headers=...` và cảnh báo `default_headers` |
| Bản dịch | 7 chuỗi mới vào `locale/en` — cổng này dành cho lập trình viên nước ngoài |
| Test | `test_259` mục 9–10 (SDK thật + trang portal), `test_256` mục 8 (ví dụ qua được bộ kiểm) |

### Kiểm bằng trình duyệt thật

Bản dev riêng ở cổng 8137 (CSDL tạm — **không chạm bản chạy thật**), đăng nhập
thật, xem `/developers/quickstart`: **0 lỗi console**, 4/4 yêu cầu mạng
`200`/`302`, mục chat hiện đủ 6 ví dụ và 6 khác biệt, cả bản `en` lẫn bản `vi`.

### ⚠️ Một lỗi quy trình của tôi, đáng ghi

Tôi sửa file bằng `pathlib.write_text(..., newline="")`. Repo này lưu **CRLF**,
`read_text` chuẩn hoá về `
`, nên mỗi lần ghi lại là **đổi dòng cả file** —
`git diff` phình thành 137 dòng cho một thay đổi 9 dòng, và đụng nặng với phiên
khác đang làm cùng repo. Đã phục hồi CRLF cho các file của phiên này.

⇒ **QT-13**: đọc/ghi file trong repo này bằng **bytes**, hoặc giữ nguyên kiểu
kết thúc dòng của file gốc. Kiểm bằng `git diff --numstat` sau khi sửa: số dòng
phải khớp với thay đổi thật.
