# Kế hoạch xây dựng tiếp — chốt 2026-08-24

Viết sau khi D-057 đóng đường "dùng máy A sinh ảnh". Đây là **một danh sách duy
nhất, xếp theo thứ tự làm**, gộp việc còn treo của H37, H38, hạ tầng GPU và nợ kỹ
thuật — vì trước tài liệu này chúng nằm rải ở sáu chỗ và không ai đọc được thứ tự.

⚠️ **Cột "Ai" là phần quyết định đọc được hay không.** Ba việc cần chủ sản phẩm, và
chúng **chặn** phần còn lại — nên chúng ở trên cùng.

---

## 0. Trạng thái lúc chốt

| | |
|---|---|
| Ảnh (H37) | G4 · G5 · G9 **đóng**; L1–L7 **xong**; 4 cổng **mở trong mã**; cờ `image.ltt` **đã bật trong `app.env`** |
| Ảnh — còn | **chưa deploy**, nên chưa có job nào đi thật từ ngoài vào |
| LLM (H38) | **đang bán**, ba cửa chạy thật, tiền khớp từng credit |
| Card 3090 máy B | HiDream **và** Qwen vẫn dùng chung — 18.450 + 19.237 = **37.687 MB / 24.576 MB** |
| Card máy A | 2 × 5060 Ti, cả hai khoẻ, **card thứ hai nằm không** |
| Gate đầy đủ | vòng 3 đang chạy; vòng 2 được **14/15**, pytest **1 lỗi đã sửa** |

---

## 1. 🔴 Chặn — cần chủ sản phẩm

| # | Việc | Vì sao nó chặn |
|---|---|---|
| ~~**P1**~~ | ✅ **XONG 15:10 ngày 24/08** — `EXITCODE=0`, `status=ready environment=production`. | — |
| **P3** | Luật WAF Cloudflare cho `/api/v1/*` — **hạ xuống "nên có", không còn chặn** | Đo lại kỹ 24/08: **chỉ `urllib` mặc định** bị 403. `requests`, `openai`, `anthropic`, `curl`, `Go-http-client`, `node-fetch`, PowerShell 5.1/7 **đều lọt** (401 của ta). Nguyên nhân thật là **ví dụ của chính ta** — đã sửa, xem dưới. |

### 🔴 Tôi đã viết P3 nặng hơn sự thật, và số đo lật lại

Bản trước ghi *"khách dùng thư viện chuẩn sẽ dính"*. **Sai.** Đo từng `User-Agent`
vào `GET /api/v1/tools` (401 = ứng dụng ta trả lời, tức đã qua Cloudflare):

```
urllib mac dinh                     403   <== CLOUDFLARE CHAN
python-requests / openai / anthropic 401
curl / Go-http-client / node-fetch   401
PowerShell 5.1 / PowerShell 7        401
trinh duyet                          401
```

**Chỉ một cái bị chặn.** Nên luật WAF không phải là thứ đang chặn khách.

⛔ **Nhưng có một lỗi thật, và nó nặng hơn P3:** `examples.python_snippet()` —
ví dụ Python hiện trên cổng dev cho **mọi tool** — dùng `urllib` mà **không đặt
`User-Agent`**. Khách chép ví dụ của **chính ta** thì nhận 403 ngay dòng đầu, và
403 đó **không phải của ta** nên không có `request_id`, không tra được gì.

⭐ Điều làm nó thành một **lớp lỗi**: `python_chat_snippet()` **đã** đặt
`User-Agent`, kèm chú thích giải thích đúng lý do. Có người đã gặp, đã hiểu, đã
sửa — **ở đúng một chỗ**. Không có gì bắt chỗ thứ hai phải theo.

⚠️ Và vì sao test cũ không thấy: test hợp đồng kiểm ví dụ **cú pháp có đúng** và
**có khớp schema** — cả hai đều xanh, vì ví dụ hoàn toàn hợp lệ. Thứ sai nằm ở
tầng khác: nó hợp lệ nhưng **không đi qua được biên**. Loopback không có
Cloudflare. Đây chính là **quy tắc 5b** của dự án, ở dạng test.

✅ Đã sửa + chốt bằng `tests/test_281_vi_du_qua_cloudflare.py` (3 test), có kiểm
ngược: tái hiện bản lỗi thì test **đỏ** đúng như mong đợi.

⛔ **P1 phải xong trước mọi việc ở mục 2.**

⛔ **Chạy đè với dự án video: BỎ khỏi quy trình** (chủ sản phẩm quyết 24/08).
Dự án video sẽ được xây lại theo đúng khuôn khoá-logic của LLM/ảnh, nên một
phép đo trên bản video **hiện tại** đo một thứ sắp không còn tồn tại. Chốt đó
quay lại cùng lúc với bản video mới, không sớm hơn.
⇒ **Đừng thêm nó lại vào danh sách này.** Nếu thấy Đợt B của H37 thiếu một chốt
thì đó là **cố ý**, không phải sót.

---

## 2. ✅ H37 ĐÃ ĐÓNG — nghiệm thu bằng tiền thật, 24/08

| # | Việc | Kết quả |
|---|---|---|
| **A1** | Job ảnh thật từ ngoài vào qua `https://app.lttstudios.com/api/v1` | ✅ 3 lượt, mỗi lượt `succeeded` sau ~120 giây |
| **A2** | Đối soát tay: báo giá → giữ chỗ → quyết toán | ✅ báo giá 3 = `held` 3 = `charged` 3 = số dư trừ 3. Số dư `30 → 27 → 24 → 21` |
| **A3** | Điền bằng chứng vào mục 4 của `APP_API_COVERAGE_FINAL.md` | ✅ đã điền, kèm số đo |
| **A4** | Thu hồi khoá nghiệm thu | ✅ `da thu hoi 1 khoa; con song: 0` (đọc lại CSDL để chắc) |

```
GET  /tools                  -> 200, thay ['image.ltt']
POST /quotes                 -> 200, credit = 3
POST /jobs                   -> 202
GET  /jobs/{id}              -> succeeded, credit {held: 3, charged: 3}
GET  /artifacts/{id}/content -> 200, 5.519.918 byte, dung chu ky PNG
```

### 🔴 Trước khi deploy, `image.ltt` **chưa hề mở** dù file nói là mở

`secrets/app.env` ghi `LTT_PUBLIC_API_TOOLS=text.chat,image.ltt`, nhưng nssm nướng
vào **cả hai** dịch vụ chỉ có `text.chat`. Đúng cái bẫy nssm đã cắn dự án hai lần
(D-058). Không có lỗi nào báo — chỉ là `GET /tools` trả về một danh sách thiếu.

⇒ **Sửa app.env rồi khởi động lại là chưa đủ.** Phải `nap_lai_env.ps1` hoặc deploy.

### 🔴 Bốn lỗi trong chính script nghiệm thu — ba chỉ lộ khi chạy thật

| | Lỗi | Vì sao test không thấy |
|---|---|---|
| ① | Gửi `params`/`id` trong khi hợp đồng là `input`/`quote` | tôi đoán tên trường từ **tên biến nội bộ** của handler, không đọc hợp đồng công khai. Trả 400 rất rõ — may, vì đoán sai ở một trường **không bắt buộc** thì im lặng |
| ② | **Thiếu hẳn bước tải ảnh về** | `succeeded` chỉ nói worker chạy xong. Khoá trỏ sai, presigned hết hạn, quyền đọc sai — cả ba cho ra **đúng một job xanh** với `outputs` trông đẹp. Khách trả tiền để **lấy được ảnh** |
| ③ | `print` ký tự ngoài ASCII ⇒ chết trên console cp1252 | chết **sau** khi đã tiêu tiền và job đã chạy, tức mất đúng phần đối soát là lý do của cả script |
| ④ | `don` gọi `revoke(db, key_id)` thay vì `revoke(db, row)` | một lệnh **thu hồi thất bại** để lại một khoá **tiêu được tiền thật**, trong khi báo cáo vẫn ghi "đã dọn" |

⚠️ Lỗi ② là cùng họ với lỗi nó đi kiểm: **tin vào một cờ trạng thái thay vì kiểm
thứ khách thật sự nhận.** Một phép nghiệm thu có cùng điểm mù với thứ nó nghiệm thu
thì không nghiệm thu được gì.

## 3. 🔴 Trọng tài VRAM — nay là việc BẮT BUỘC

D-057 đóng đường tách hai model ra hai máy. Nên chúng **vẫn dùng chung một card**,
và phép cộng vẫn vượt trần. Chi tiết + số đo ở
[`ANH_NOI_BO/CHIA_GPU_HAI_MODEL.md`](ANH_NOI_BO/CHIA_GPU_HAI_MODEL.md).

| # | Việc | Trạng thái |
|---|---|---|
| **V1** | Gọi `llama-swap /unload` **trước** khi gửi prompt | ✅ **XONG, đã đo thật**: đuổi mất **4,0 giây** |
| **V2** | **Chờ và XÁC MINH** VRAM xuống dưới ngưỡng mới gửi | ✅ **XONG.** Không đọc được VRAM ⇒ **từ chối**, không chạy mù |
| **V3** | Sau job, chờ 60 giây rảnh rồi `POST ComfyUI /free` | ✅ **XONG, đã đo thật**: 17,5 GB → **811 MB** |
| **V4** | Số đo VRAM **và RAM** *trong lúc* job chạy | ✅ **XONG** — nằm trong `do_duoc` của kết quả job |
| **V5** | ~~Hạ `ttl` của Qwen 1.800 → 600~~ | 🔴 **BỊ BÁC (D-058)** — xem dưới |

**Đã xác minh trên máy B**, hai chu kỳ lặp lại được (D-058):

```
778 MB (rỗng) → 19.491 MB (Qwen giữ) → "da bao llm nha card, cho 4.0s"
             → 17.5xx MB (HiDream vẽ 111 s) → 60 s rảnh → 811 MB (trả card)
```

### 🔴 V5 bị bác, và chính việc xây xong cho thấy vì sao

`ttl` từng là **cơ chế duy nhất** trả card cho ảnh — nên nó phải ngắn. Nay cổng
render **chủ động đuổi** khi cần. Cho nên `ttl` chỉ còn quyết định *"Qwen giữ card
bao lâu khi KHÔNG ai cần"* — và khi không ai cần thì giữ **không tốn gì**.

Hạ `ttl` chỉ đổi được một thứ: khách LLM trả **18 giây nạp lại** thường xuyên hơn,
để đổi lấy một card rỗng mà không ai xin.

⇒ **Một cơ chế tốt hơn làm một cơ chế cũ thành vô nghĩa. Đừng làm cả hai.**

### Hai chỗ hỏng tìm được nhờ **chạy thật**, không nhờ test

| | Hỏng gì | Đã sửa |
|---|---|---|
| **①** | Đuổi **thành công** không để lại dấu vết nào trong log — hỏi *"vì sao phiên LLM của tôi chậm lúc 13:50"* thì không có gì chỉ ra | ✅ nay ghi `da bao llm nha card, cho 4.0s, VRAM con 778 MB` |
| **②** | Cổng **không đọc được** `gateway.env` mới: nssm nướng env lúc cài. Bẫy này đã cắn dự án **hai lần** | ✅ `main.nap_env()` — cổng tự đọc, không ghi đè biến cấp cao hơn |

⚠️ **Một bẫy về THỨ TỰ đã dính, ghi lại để không ai xếp lại như cũ.** Bản đầu đặt
`xin_card` **SAU** chốt bận. Chốt bận coi *"VRAM còn ít"* là bận, nên khi Qwen giữ
19 GB thì cổng trả 429 ngay và **không bao giờ đi bảo Qwen nhả** — trọng tài thành
mã chết. Thứ tự đúng: **giữ suất → xin card → hỏi bận**.

Và test đầu tiên cho nó **xanh vì lý do sai**: chạy 0,58 giây trong khi hạn chờ là
45 — bằng chứng `xin_card` chưa hề được gọi.

Số đo để cân chính sách (đo 24/08):

| | Nhả | Nạp lại |
|---|---|---|
| HiDream | 0,2 s | **0,8 s** (0,7 % một job) |
| Qwen | 0,7 s | **18 s** (card sạch) |

Bất đối xứng **22 lần** ⇒ chính sách **không đối xứng**: ảnh nhả sau mỗi job; LLM
giữ thường trú và chỉ bị đuổi khi có job ảnh.

---

## 4. GPU máy A — ✅ **G1–G4 ĐÃ XONG TỪ TRƯỚC**, G5 xong 2026-08-29

🔴 **Bảng dưới đây trước 29/08 là bảng CŨ, và nó suýt gây ra một thiệt hại thật.**
Nó liệt bốn chỗ "hỏng ngầm… tất cả còn nguyên". Rà từng dòng vào mã thật ngày
29/08 cho thấy **ba trong bốn đã được sửa**, và mục G4 — *"không có cơ chế giữ
chỗ GPU nào"* — mô tả một thứ **đã tồn tại đầy đủ**.

⛔ Nếu tin bảng thay vì đọc mã, việc tiếp theo sẽ là **viết một cơ chế giữ chỗ
GPU thứ hai** trên một máy đã có ba hộ tranh nhau card. Đó tệ hơn hẳn một buổi
mất công.

| # | Kế hoạch nói | Mã thật (đo 29/08) |
|---|---|---|
| **G1** | `autotune.py` dùng `splitlines()[0]` ⇒ chỉ thấy GPU 0 | ✅ **đã sửa** — `query_vram(gpu_uuid)` tra đúng card qua `list_gpus()`; `_TOTAL_MB_FALLBACK` nay chỉ là đường lùi khi không đọc được card nào |
| **G2** | `whisperx_runner.py` `device="cuda"` ⇒ luôn `cuda:0` | ✅ **đã sửa** — `transcription.py` truyền `env=_env_ghim_gpu(gpu_uuid)` → `gpu.env_for()` đặt `CUDA_VISIBLE_DEVICES`. `device="cuda"` trong runner nay **đúng**: tiến trình con chỉ thấy một card. Ghim bằng biến môi trường chứ không `torch.cuda.set_device`, vì việc nặng chạy trong tiến trình con mà ta không sửa được mã bên trong |
| **G3** | một tiến trình ⇒ một job một lúc ⇒ GPU 2 nằm không | ✅ **đã có** — `LTT_WORKER_POOLS` (`job_worker.py`, H36) |
| **G4** | *"không có cơ chế giữ chỗ GPU nào"* | ✅ **đã có** — `platform_core/gpu_lease.py`: `acquire` / `busy_uuids` / `reclaim_orphans` / heartbeat, xung đột bắt bằng `IntegrityError`. Đúng khuôn `claim → đập nhịp → reclaim` mà chính mục này mô tả |
| **G5** | chốt `nvidia-smi -L` phải thấy 2 GPU | ✅ **XONG 29/08** — xem dưới |

### G5 — đếm card trong vòng bảo trì

**Vì sao nó cần tồn tại.** Liên kết driver của card thứ hai mong manh
(`oem3.inf` không liệt kê nó). Khi nó rụng thì **không có gì hỏng**: job vẫn
chạy, chỉ là tất cả dồn vào một card. Năng lực giảm một nửa và mọi tín hiệu vẫn
xanh — không ngoại lệ, không job đỏ, không cảnh báo. Cách duy nhất để biết là đi
**đếm card**, đúng thứ không ai làm vào một ngày bình thường.

⭐ Đây là một lỗi **im lặng**, và lỗi im lặng chỉ bắt được bằng một phép đếm chủ
động. Không phải một phép kiểm sức khoẻ — máy **vẫn khoẻ** khi thiếu card, và đó
mới chính là vấn đề.

**Đã làm:**
- `job_runner._quet_so_gpu()`, gọi trong `_mot_luot_bao_tri` ⇒ chạy dưới lease
  `bao_tri`, tức **đúng một lần trên toàn cụm**. Đặt trong vòng job thì mỗi
  worker gửi một thư về cùng một card (đúng lớp lỗi H36 đã sửa).
- Kind mới `notifications.GPU_MISSING`, nghỉ **1 ngày**.
- Khoá khử trùng lặp mang **con số**: `gpu:1/2` và `gpu:0/2` là **hai** sự việc.
  Nếu khoá chỉ là `gpu` thì card thứ hai rụng sẽ im suốt chu kỳ nghỉ, chỉ vì
  card thứ nhất vừa được báo — đúng lúc tệ nhất.
- **Không** vào `EMAIL_KINDS`. Nó là *fact* chứ không phải ước lượng, nhưng một
  card rụng lúc 03:00 không cần đánh thức ai lúc 03:00 — nó cần **được thấy vào
  buổi sáng**. Thứ làm lỗi này vô hình chưa bao giờ là giờ gửi thư; là việc
  **không ai đếm card cả**.
- Thân thư nói rõ **không có job nào hỏng vì việc này** và chỉ ra `nvidia-smi -L`.
  Người đọc sẽ đi tìm job đỏ và không thấy cái nào; không nói trước thì cảnh báo
  bị đọc thành báo động giả.

🔴 **Số card kỳ vọng KHÔNG tự suy được.** Khai ở `LTT_GPU_MONG_DOI`; **không
khai = tắt phép kiểm**. Hai cách "thông minh" đều sai và đều hỏng im lặng:

| Cách | Hỏng thế nào |
|---|---|
| đọc số card lúc khởi động | máy khởi động lại khi card **đã** rụng sẽ chốt mức thấp đó thành "bình thường", cảnh báo im vĩnh viễn |
| nhớ mức cao nhất từng thấy | một lần cắm thử card thứ ba làm máy báo thiếu **mãi mãi** |

⇒ Nó là một **tuyên bố về phần cứng**, nên phải do người khai. Khai sai kiểu thì
tắt **và ghi log** — im lặng ở đây đúng là lỗi mà phép kiểm này sinh ra để chặn.

⚠️ **Còn một bước để nó thật sự chạy:** thêm `LTT_GPU_MONG_DOI=2` vào
`C:\LTTPlatform\secrets\app.env` rồi `setup\nap_lai_env.ps1`. Chưa làm thì mã đã
có nhưng phép kiểm **đang tắt** — và dòng này tồn tại để không ai đọc "G5 xong"
thành "máy đang được canh".

Chốt: `tests/test_329_chot_so_gpu.py` (13 phép kiểm). Kiểm-có-răng: tháo khoá
khử trùng lặp, tháo câu "không có job nào hỏng", và bắt nó báo cả khi đủ card —
cả ba đều làm **đúng** test tương ứng đỏ.

⚠️ Mục này **không chặn** H37 và H38. Nó là năng lực đang bỏ không, không phải
một sự cố.

---

## 5. H38 — việc còn nợ, chủ sản phẩm đã hoãn có chủ ý

| # | Việc | Ghi chú |
|---|---|---|
| **L1a** | ✅ **XONG 24/08** — nửa API, bằng tài khoản test `autosub-test` (`role=user`, **không** phải admin) | Cả **ba cửa** đều 200 và thu tiền thật, xem dưới |
| **L1b** | ⛔ **KHÔNG tự động hoá được** — nửa GUI (đăng ký → xác thực email → đăng nhập → tạo khoá trên trang) | Trang `/login` nằm sau **thử thách bot của Cloudflare**. Playwright nhận `403 "Performing security verification"`. **Không vượt CAPTCHA** ⇒ đây vốn dĩ là việc của người thật |
| **L2a** | ✅ **XONG 24/08** — Codex CLI + Claude Code CLI, trên **hai máy độc lập** | xem dưới |
| **L2b** | ⛔ **Claude Desktop — chủ sản phẩm từ chối quyền điều khiển máy.** Và kể cả được phép, **ô "Gateway API key" tôi không được tự điền** (luật an toàn: không nhập khoá/token vào bất kỳ ô nào). | Việc của người thật. Tôi làm được mọi bước còn lại, chừa đúng một ô |
| **L3** | **Điều khoản sử dụng** cho API | chủ sản phẩm quyết nội dung; tôi soạn nháp |
| **L4** | Thu tường lửa máy B về **một** IP | thiết lập bảo mật |
| **L5** | Xoay khoá provider | đã có quy trình, chưa chạy định kỳ |

---

## 5b. ⭐ Công cụ tự cắm CLI (C15) — việc đáng làm nhất còn lại

**Trạng thái hôm nay:** trang `/developers/cli` **đã có** (C14 xong). Nó sinh sẵn
`config.toml`, `settings.json`, biến môi trường cho Codex + Claude Code + Claude
Desktop, và nói rõ hai base URL lệch nhau bốn ký tự.

**Vẫn còn thiếu:** thứ *ghi hộ* cấu hình. `api.nghimmo.com` phát `ClaudeKeyTool`
và `CodexKeyTool` — và bài học rút ra ở `LO_TRINH_API_CLI.md` §1 vẫn đúng: **thứ
khách vấp không phải giao thức, mà là điền cấu hình.**

### ⛔ Nhưng chép nguyên cách làm của họ là sai ở bốn chỗ

**① Đóng gói `.exe` là phần đắt nhất, và nó KHÔNG phải phần có giá trị.**
Một `.exe` nhỏ, không ký số, ghi vào thư mục cấu hình của người dùng — đó **đúng
mô tả hành vi của malware**. Hệ quả thật: SmartScreen chặn, diệt virus báo động
giả, và phải nuôi ba bản dựng (Windows/macOS/Linux). Chứng chỉ ký số thì tốn tiền
hằng năm.

Mà phần lõi chỉ là **vài chục dòng ghi tệp**. Trả một chứng chỉ ký số để giao vài
chục dòng là sai tỉ lệ.

⇒ **Phát một tệp `.py` duy nhất.** Ai cài được Codex hay Claude Code thì đã có
terminal. Không ký số, không diệt virus, không đa bản dựng — và **khách đọc được
nó trước khi chạy**, điều đó quan trọng vì nó đang ghi vào cấu hình của họ.
⛔ **Không** dạy kiểu `curl ... | python`. Đó là dạy khách chạy mã không đọc.

**② Rủi ro thật không phải "ghi tệp" mà là "phá tệp đang có".**
`~/.codex/config.toml` và `~/.claude/settings.json` là **của khách**, không phải
của ta. Ghi đè là xoá cấu hình họ đang dùng — và hỏng theo kiểu tệ nhất: **nó vẫn
chạy**, chỉ là thiết lập riêng của họ biến mất.

⇒ Bắt buộc: **hợp nhất chứ không ghi đè**, **sao lưu trước**, và **chạy hai lần
bằng chạy một lần**.

**③ `ANTHROPIC_BASE_URL` trong `settings.json` là TOÀN CỤC — và trang của ta đang
gọi nó là "bền hơn" mà không nói điều đó.**
Đặt nó ở đó thì **mọi** phiên Claude Code của khách đi qua ta, kể cả việc họ làm
với tài khoản Anthropic thật. Codex có `--profile ltt` nên phạm vi gọn; Claude Code
**không có** thứ tương đương.

⇒ Với Claude Code, mặc định phải là **đoạn lệnh đặt biến môi trường cho một phiên**;
chỉ ghi `settings.json` khi khách nói rõ (`--toan-cuc`). Và sửa lại chữ trên trang
`/developers/cli`: "bền hơn" phải kèm "và áp cho **tất cả** dự án".

**④ Khoá không được nằm trong tệp.**
Luật đã có trong mã: *"No snippet ever contains a key."* Nhưng
`claude_code_settings()` hiện bảo khách đặt `ANTHROPIC_AUTH_TOKEN` **vào
`settings.json`** — một tệp văn bản thường mà nhiều người đồng bộ hoặc commit vào
kho dotfiles. Codex đã làm đúng (`env_key = "LTT_API_KEY"`, chỉ **tham chiếu** biến).

⇒ Công cụ đặt biến môi trường (`setx` trên Windows), **không** ghi khoá vào tệp
nào. Và sửa `claude_code_settings()` cho khớp luật của chính nó.

### ⭐ Và phần mọi người bỏ qua: công cụ phải TỰ KIỂM

Một công cụ ghi xong tệp rồi báo "đã cấu hình" có **đúng điểm mù** với script
nghiệm thu ảnh của tôi hôm nay: nó tin vào việc mình vừa làm, thay vì kiểm thứ
khách thật sự nhận.

⇒ Bước cuối bắt buộc: **gọi thật một lượt** (`GET /api/v1/tools` rồi một lượt chat
ngắn), in ra số dư còn lại. "Đã ghi tệp" và "cắm được rồi" là hai câu khác nhau.

### Bảng việc

| # | Việc | Đạt khi |
|---|---|---|
| **C15a** | `tools/cam_cli.py` — một tệp, không phụ thuộc ngoài chuẩn | chạy trên Python 3.9+ sạch |
| **C15b** | Hợp nhất + sao lưu + chạy lại không đổi kết quả | có cấu hình cũ ⇒ giữ nguyên, chỉ thêm khối của ta |
| **C15c** | Khoá **chỉ** vào biến môi trường | không tệp nào chứa khoá sau khi chạy |
| **C15d** | Tự kiểm bằng một lượt gọi thật | in `tools` thấy được + số dư |
| **C15e** | Sửa `claude_code_settings()` + chữ "bền hơn" trên `/developers/cli` | khớp luật *no snippet contains a key* |
| **C15f** | Cho tải từ `/developers/cli` | một nút, kèm hướng dẫn đọc trước khi chạy |

⚠️ **C15 không chặn gì và không ai đang chờ nó.** Nó là thứ biến "khách đọc hết
tài liệu thì cắm được" thành "khách cắm được". Làm sau L1.

---

### ✅ L1a — ba cửa chat, tiền thật, 24/08

Tài khoản `autosub-test@lttstudios.com` (`role=user`), khoá mới tạo, `allowed_tools=['text.chat']`:

```
GET  /tools              -> 200, thay ['text.chat']
POST /chat/completions   -> 200  SYNC_BILLED  noi dung 'Xin chao'
                                 usage {prompt 19, completion 48, total 67}   thu 1
POST /messages           -> 200  STREAM  7.015 byte SSE, co `usage`           thu 1
POST /responses          -> 200  STREAM  9.025 byte SSE (Codex)               thu 1
so du 459 -> 458 -> 457 -> 456
```

Mỗi lượt thu **1 credit** — khớp luật đã công bố ở `/gia-api`: *làm tròn LÊN
credit nguyên, tối thiểu 1*. 67 token thì dưới một credit, nên trả sàn.

Khoá đã thu hồi (`con song: 0`).

### ⛔ L1b không phải việc bỏ quên — nó không tự động hoá được

`/developers/cli` chuyển đúng về `/login?next=...` (cổng đăng nhập làm đúng
việc), nhưng Cloudflare trả **403 + Turnstile** cho trình duyệt tự động. Vượt
CAPTCHA là việc **không được làm**, nên nửa GUI cần **người thật bấm**.

⇒ Ghi rõ ở đây để phiên sau không đi tìm cách tự động hoá nó lần nữa. Việc cần
người: đăng ký một tài khoản mới → xác thực email → đăng nhập → `/developers/keys`
tạo khoá → `/developers/cli` chép cấu hình.

### 🔴 Hai lỗi trong script nghiệm thu, cùng một gốc với lỗi hôm nay

| | Lỗi | Gốc |
|---|---|---|
| ① | Đọc `resp["tools"]` trong khi hợp đồng trả `resp["items"]` | **đoán hình dạng phản hồi từ tên endpoint** thay vì đọc `server/api/`. Triệu chứng là một danh sách **rỗng** — giống hệt *"tool chưa được mở"*, tức một lỗi đọc sai **giả trang** thành một lỗi cấu hình. Tôi đã đi kiểm cờ, nssm và catalog trước khi nhìn lại chính mình |
| ② | `devkeys.create(...)` — hàm tên là `issue`, và trả `(key, token)` theo thứ tự đó | đảo hai giá trị thì token ghi ra tệp là một đối tượng ORM: **không lỗi nào báo**, chỉ là tệp token vô dụng ở bước sau |

⚠️ Lỗi ① là **lần thứ hai trong ngày** tôi đoán tên trường thay vì đọc hợp đồng
(lần đầu: `params`/`id` thay vì `input`/`quote`). Cả hai lần đều mất thời gian đi
tìm ở chỗ khác trước khi nhìn lại mã của mình.

---

### ✅ L2a — hai CLI, hai máy, 24/08

| Công cụ | Máy A (máy chủ nền tảng) | Máy B (GPU, độc lập) |
|---|---|---|
| **Codex CLI** | ✅ `2+2` → `4`, 12.306 token | — chưa cài `codex` ở đó |
| **Claude Code CLI** | ✅ `2+2 = 4` | ✅ `7×6` → **42**, 69,7 s |

Cả hai dùng **đúng cấu hình `/developers/cli` sinh ra**, không sửa gì thêm — nên
đó cũng là phép thử cho chính tài liệu của ta.

⭐ **Vì sao chạy trên máy B mới có nghĩa:** máy A **là** máy chủ nền tảng. Một
phép thử chỉ chạy ở đó không loại trừ được giả thuyết *"nó chạy vì đang ở nhà"*.
Máy B là một máy khác, đi ra internet rồi vòng lại qua Cloudflare — nên nó chứng
minh cấu hình đứng độc lập.

⛔ **Không cài `codex` lên máy B.** Nó sẽ đo lại đúng thứ máy A đã đo, trong khi
máy B là máy chạy GPU sản xuất. Cài thêm phần mềm lên đó để lấy một số đo trùng
là cái giá không đáng.

### 🔴 Ba cái bẫy khi cắm client thật, ghi lại để không dính lần nữa

**① `ANTHROPIC_BASE_URL` đã có sẵn trong môi trường của phiên đang chạy.** Một
tiến trình con kế thừa nó sẽ trỏ nhầm và ta không hề biết. Phải chạy trong môi
trường **sạch** — gỡ hết `CLAUDE_*`/`ANTHROPIC_*` rồi đặt lại đúng cái cần.

**② Tuyệt đối không ghi `~/.claude/settings.json`.** Nó **toàn cục**: đặt
`ANTHROPIC_BASE_URL` ở đó là chuyển hướng **mọi** phiên Claude Code trên máy, kể
cả phiên đang làm việc. Cách kiểm: băm md5 tệp đó trước và sau mỗi lượt chạy.
*(Đây đúng là điểm ③ của phần phân tích C15 — nay không còn là lý thuyết.)*

**③ Truyền khoá qua chuỗi `ssh → cmd → powershell` bị nuốt.** Tham số tới nơi là
`$null`, `ANTHROPIC_AUTH_TOKEN` rỗng, Claude Code **thử lại liên tục** rồi chạm
rate limit. Triệu chứng là `429 "too many failed authentication attempts"` —
trông y hệt một vấn đề ở **máy chủ**, trong khi lỗi nằm ở **cách gọi**.
⇒ Truyền dạng **hex** (chỉ `0-9a-f`, không còn chỗ cho dấu nháy), và **kiểm độ
dài ở đầu bên kia** trước khi dùng.

⛔ Và **không ghi khoá xuống đĩa máy B** — CLAUDE.md: máy B không giữ bí mật nào
của nền tảng. Khoá chỉ sống trong biến môi trường của tiến trình, và đã thu hồi
ngay sau khi đo xong.

---

## 6. Nợ kỹ thuật — trả khi đi ngang qua, không lập đợt riêng

| # | Việc | Vì sao chưa làm ngay |
|---|---|---|
| **N1** | Đổi tên `apps/ltt_llm` → `apps/chatnoibo` (đối xứng với `anhnoibo`) | Đó là **migration**, không phải rename: slug nằm trong `job_type` **đã lưu**, và app **đang bán**. Hiện đang được miễn trừ trong `test_60` với lý do viết rõ. |
| **N2** | `apps/vps`: xếp loại lưu trữ 5 bảng là **TẠM**, chủ H39 phải xác nhận | Hạn của `vps_ip` có **hệ quả pháp lý** — lịch sử "IP nào, của ai, lúc nào" là thứ duy nhất trả lời được yêu cầu về lạm dụng. |
| **N3** | `test_221` trên một bucket R2 vứt đi | Chặn bởi một quyết định hạ tầng, không bởi code. |
| **N4** | G5b (chuỗi nâng chất ảnh: upscale/restore + VLM tự loại) | Chỉ làm khi có khách và có phàn nàn cụ thể. |
| **N5** | G11 (giám sát chất lượng ảnh thường trực) | Sau khi có khách thật. |

---

## 7. ⛔ Cái KHÔNG làm, và lý do

| Không làm | Vì sao |
|---|---|
| Tải bản model thấp hơn (FP8/GGUF) cho ảnh | **D-057.** Chủ sản phẩm quyết không hạ độ chính xác. |
| Chuyển sinh ảnh sang máy A | **D-057.** `bf16` không vừa 16 GB, và Llama-3.1-8B trong bộ mã hoá đã lấp kín một card. Mở lại cần **phần cứng ≥ 24 GB**, không phải một cách xếp encoder khác. |
| Chuyển Qwen sang máy A | 3090 nhanh gấp ~2 lần (băng thông 936 so với 448 GB/s), và 64K đã vừa trên 3090. Trả một nửa tốc độ cho thứ không cần. |
| Chạy thêm lô đấu Gemini | **D-046.** Không còn lựa chọn nào để đổi ⇒ điểm số không mua được gì. |
| Mở lại phép so 36 bước | **D-054.** Muốn mở lại phải là **phép kiểm tương đương**, không phải chạy lại phép cũ. |
| Cascade sang đám mây khi máy B bận | **D-010.** Khách trả tiền cho `image.ltt` mà nhận Gemini là bán sai hàng. |
| Đưa việc có chữ tiếng Việt sang `image.ltt` | **D-048.** Ngoài phạm vi, đã chấp nhận. |

---

## 8. Thứ tự làm, một dòng

```
V1..V4 trọng tài VRAM  ✅ XONG (D-058)
        ↓
P1 deploy (chủ sản phẩm)  →  A1..A4 nghiệm thu ảnh thật
        ↓
G1..G5 (GPU máy A)  ✅ XONG (29/08)  ·  L1..L5 (H38)  ← còn lại
```

**P3 (WAF)** làm được bất cứ lúc nào, nhưng **không còn gấp**. ⚠️ Dòng cũ ở đây
viết *"nó đang chặn khách dùng thư viện chuẩn"* — câu đó mâu thuẫn với chính §1
của tài liệu này, nơi số đo cho thấy **chỉ `urllib` mặc định** bị 403 còn
`requests`/`openai`/`anthropic`/`curl`/`node-fetch`/PowerShell đều lọt. Nguyên nhân
thật là **ví dụ của chính ta** thiếu `User-Agent`, và nó **đã sửa** (`test_281`).
