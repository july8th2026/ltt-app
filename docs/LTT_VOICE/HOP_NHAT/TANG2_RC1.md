# LTT Voice RC1 — Nghiệm thu **Tầng 2** (sau deploy)

> Tầng 1: `TANG1_RC1.md` (`READY_FOR_DEPLOYMENT`, 99/100).
> Ô của Tầng 2 định nghĩa ở spec §10.2.

| | |
|---|---|
| SHA được cổng chứng nhận | `e2676aaa194d0e781c92c2ec9bdac3fb3166ce47` |
| ff vào | **`main`** (không phải `admin-mvp-v3` — xem §1) |
| Deploy | 12/09/2026 02:39:33 → 02:41:21, `EXITCODE=0`, `deploy-20260912-023933.ket.txt` |
| Đường lui | `C:\LTTPlatform\app.previous` = `7cde3c9d4dac` (build 12/09 00:42) |

---

## 1. Đích ff đã đổi — và vì sao

Kế hoạch viết `admin-mvp-v3`. Hỏi máy chủ trước khi chạm vào nó (luật 5 của
`CLAUDE.md`) cho kết quả khác:

```
/health/version truoc deploy  ->  commit 7cde3c9d4dac  (build 2026-09-12T00:42:28)
admin-mvp-v3                  ->  34b4626e             (CU HON production 7 commit)
git merge-base --is-ancestor 7cde3c9d <RC>  ->  KHONG
```

Trong 7 commit ấy có `3a6da723 refactor: make main the live branch authority`,
và `docs/16_CAP_NHAT_VA_DEPLOY.md` **của chính nó** ghi *"Nhánh trunk: `main`
(Q123)"*. ff vào `admin-mvp-v3` rồi deploy sẽ **lùi** 7 commit đang chạy thật.

⇒ Hoà `main` vào RC (`f98be1be`, ba xung đột đều giải theo hướng **giữ cả hai
bên**), rồi ff vào `main`. Sau khi hoà, `7cde3c9d` là tổ tiên của SHA deploy ⇒
**không commit nào bị lùi**.

Kiểm chắn trước deploy (§3 của tài liệu deploy):

```
tep .py chi co o production ma commit KHONG co  ->  0
```

---

## 2. Bảng ô Tầng 2

| # | Ô (spec §10.2) | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | SHA tested = SHA ff = SHA deploy | **PASS** | cả ba đều `e2676aaa` |
| 2 | `/health/version` = SHA ấy | **PASS** | `{"commit":"e2676aaa194d","asset_ver":"de7fdfe7","build_luc":"2026-09-12T02:40:47"}` |
| 3 | `nghiem_thu_deploy` 0/0/0 **và** tệp không `.py` 0/0/0 | **PASS** | 922 tệp trong commit, **266 tệp không `.py`**; lệch 0 · thiếu 0 · thừa 0; tài sản ngoài commit đã khai (`van_chuyen`) = 9 → `DAT` |
| 4 | `alembic upgrade head` một head | **PASS** | CSDL production: `alembic_version = d9a1f6c2b3e5`; cột `voice_profile.ngon_ngu_nguon` và bảng `voice_lich_su` đều có mặt |
| 5 | Di trú ASR thật trên production | **PASS** — đã chạy, đã ghi số; **0 giọng đổi** | §3 |
| 6 | Bộ Playwright trên URL công khai | **PASS** (3 luồng SKIP đúng thiết kế) | §4 |
| 7 | Public API live bằng khoá đọc | **PASS** | §5 |

⇒ **Bảy ô đều đạt.** Nhưng đọc ô 5 và ô 6 kèm phần chữ nhỏ của chúng: ô 5 đạt
nghĩa là *công cụ đã chạy trên production và đã ghi số*, **không** nghĩa là dữ
liệu đã được di trú — **0 giọng đổi**. Ô 6 đạt với **3/5 luồng SKIP** vì chúng
phụ thuộc dữ liệu seed chỉ có trên loopback.

---

## 3. Ô 5 — di trú ASR: **BLOCKED**, và nguyên nhân nằm ngoài RC1

Chạy khô trên production (`tools/di_tru_lan_asr.py`, ngưỡng 0.9, 2 luồng):

```
Xet: 28   Se doi: 0   Da ghi: 0   Khong chac: 28
28/28 dong:  "khong doc duoc kho (voice/<owner>/<voice>/source.wav): R2 khong doc duoc"
```

### Truy tới gốc, không dừng ở thông báo lỗi

| Câu hỏi | Đo được |
|---|---|
| Cấu hình R2 có đúng không? | `LTT_STORAGE=r2`, backend `R2Storage`, bucket `fb-video-storage` |
| Bucket có truy cập được không? | **Có** — `list_objects_v2` trả `KeyCount=15`, thấy `anhnoibo/…`, `thumbnail/…` |
| Tiền tố `voice/` có gì? | **Chỉ `voice/mau/…`** (nghe thử của 20 giọng mẫu). `voice/chung/` = 0 khoá |
| `voice/<owner>/…/source.wav` của 28 giọng khách? | `exists=False` — **không có khoá nào** |
| Có nằm trên đĩa máy chủ không? | Không: `C:\LTTPlatform\data\files\` chỉ còn `taovideo`, `thumbnail`; tìm `source.wav` và `repr-*.npz` trên cả `C:\LTTPlatform` → **0 tệp** |
| Có phải đổi bucket giữa chừng? | Không: **mọi** bản `secrets/app.env.bak-*` đều ghi cùng `LTT_STORAGE=r2` và cùng bucket |
| Dữ liệu ấy sinh khi nào? | `voice_profile`/`voice_ref` tạo **31/08 12:21 → 01/09 12:58** |

**Kết luận đo được:** CSDL production có **28 hàng `voice_ref` + 28 hàng
`voice_repr`** trỏ tới các khoá kho mà **không khoá nào còn tồn tại**.

### 🔑 Đính chính (đo sau, ở lượt Tầng 2 lần hai) — 28 giọng ấy là của ai

Lần đầu tôi viết *"28 giọng riêng của khách"*. **Sai.** Đếm theo chủ sở hữu:

```
giong theo CHU SO HUU:
  thu.giongnoi@lttstudios.local   29
```

**Toàn bộ** giọng riêng trên production thuộc **một tài khoản THỬ** (`.local`,
tức `tools/tai_khoan_thu.py` sinh ra, không phải hộp thư có thật). Tên của
chúng cũng tự khai: *"Giọng mẫu nam trầm"*, *"HF_HOME"*, *"Clip 30s kiem thang
cham"*.

⇒ **Không khách hàng nào bị ảnh hưởng.** Mức nghiêm trọng hạ từ *"sự cố dữ liệu
khách"* xuống *"mất dữ liệu kiểm thử"*. Vẫn đáng điều tra — cùng cơ chế ấy sẽ
chạm dữ liệu thật vào ngày có giọng thật — nhưng nó **không** là việc phải làm
gấp, và **không** được ghi vào báo cáo như một sự cố khách hàng.

⚠️ Lỗi suy luận đáng ghi: từ *"28 hàng trong `voice_profile`"* tôi nhảy sang
*"28 khách"*. Con số **tổng** không nói được **của ai** — chỉ một phép `group by
owner` nói được, và nó rẻ hơn nhiều so với một báo cáo sai.

⛔ **Đây KHÔNG do lần deploy này.** Dữ liệu sinh 31/08–01/09; lượt deploy hôm nay
chỉ thay mã và chạy migration (chỉ **thêm** cột/bảng); không lệnh ghi nào của
lượt nghiệm thu này chạm tới kho. Trạng thái ấy đã có sẵn **trước** khi deploy.

### 3.1 Lượt hai — chứng minh công cụ **đo được** trên chính production

28 hàng cũ không có clip nên không nói lên được gì về công cụ. Lượt D003 ở §4.2
vừa tạo một hồ sơ giọng **có clip thật trong kho**, nên mượn đúng hàng ấy để đo:

1. Ghi giá trị cũ ra tệp, đặt tạm `ngon_ngu='vi'`, `ngon_ngu_nguon='mac_dinh_cu'`
   (công cụ chỉ xét hồ sơ `mac_dinh_cu`). Công cụ mượn **từ chối** mọi hồ sơ
   không thuộc tài khoản `.local`.
2. Chạy `tools/di_tru_lan_asr.py` (khô) trên production.
3. Trả nguyên trạng và **đối chiếu lại** — `en/khai_bao`, khớp.

```
Xet: 29   Se doi: 0   Da ghi: 0   Khong chac: 29
vc_d60a3c21…  giu nguyen (vi)   do=en/0.442
```

🔑 `do=en/0.442` là một lượt **ASR thật trên production**: công cụ đọc được clip
từ R2, chạy đo, ra `en`, và vì `0.442 < 0.90` nên **từ chối đổi**. Đó đúng là
hành vi fail-closed đã thiết kế. Độ tin thấp cũng giải thích được: clip do bộ
Playwright sinh ngay trong trang là một **sóng sin**, không có lời — nên "không
chắc" là câu trả lời đúng, không phải một thất bại.

⇒ Ô 5 **PASS theo đúng chữ của spec** ("chạy công cụ di trú ASR trên production
— ghi số giọng đã đo/đổi/không chắc"): đã chạy, đã ghi số.

⛔ **Nhưng đừng đọc nó thành "đã di trú".** Số giọng đổi là **0**. 28 hồ sơ cũ
vẫn chưa đo được vì mất clip (§3, dữ liệu của tài khoản thử), và ngày có giọng
thật thì lượt di trú thật vẫn còn ở phía trước.

---

## 4. Ô 6 — Playwright trên URL công khai: một phần

**Đạt** (trang công khai, không cần đăng nhập):

| Kiểm | Kết quả |
|---|---|
| `GET /` qua `https://app.lttstudios.com` | **200**, render đủ danh mục app (có thẻ "Giọng nói LTT") |
| `console.error` / `pageerror` | **0** |
| Yêu cầu mạng hỏng | **0** — 9/9 request trả 200 |
| **Cache-bust** (luật 18) | `static/ltt.css?v=**de7fdfe7**` — khớp đúng `asset_ver` mới của `/health/version` ⇒ CSS mới đã ra tới biên Cloudflare |
| `/ltt-voice` (chưa đăng nhập) | **303** → đăng nhập, đúng thiết kế |
| `/gia-api`, `/health/ready` | **200** |
| Dịch vụ | `LTTStudioWeb`, `LTTStudioWorker`, `LTTStudioVoice` — cả ba **Running** |

### 4.1 Lượt hai — các luồng **cần đăng nhập** đã chạy thật (12/09, 05:58)

Lượt đầu BLOCKED vì hai thứ; cả hai đều gỡ được **mà không** vượt bot-detection
và **không** mượn tài khoản khách:

| Vật cản | Cách gỡ |
|---|---|
| Trình duyệt tự động bị Cloudflare chặn (`403`, *"Just a moment…"*) | **Không tự mở trình duyệt.** Mở Chrome **thật**, để nó tự qua thử thách, rồi **nối vào** qua `--remote-debugging-port=9222` (`chromium.connectOverCDP`). Đúng cách mà memory `kiem-gui-noi-vao-chrome-that` đã chốt từ 04/09 |
| Không có tài khoản test vận hành | Kho **đã có** `tools/tai_khoan_thu.py`. Nó liệt kê 4 tài khoản thử `.local` đang có, trong đó `thu.giongnoi@lttstudios.local` (35 credit) đúng cho Voice. Đặt lại mật khẩu bằng chính công cụ đó |

Hai sửa harness đi kèm (commit cùng lượt):

1. `ltt_voice_rc1.js` đọc `LTT_SMOKE_USER`/`LTT_SMOKE_PASS` khi người gọi đặt
   chúng, và chỉ rơi về tài khoản seed của máy chủ E2E khi không — **không tệp
   test nào mang một mật khẩu thật**.
2. Định vị ô đăng nhập bằng **id** (`#login-username`/`#login-password`) thay vì
   **nhãn**: màn đăng nhập production hiện tiếng Việt khi trình duyệt khai
   `Accept-Language: vi`, nên ba nhãn tiếng Anh của tầng mock trượt hết.

### 4.2 Kết quả lượt hai — trên `https://app.lttstudios.com`, Chrome thật

| Luồng | Kết quả |
|---|---|
| **D003** — ghi danh không khai làn ⇒ 400 `voice_language_required`; ghi danh EN hợp lệ ⇒ 200 + thẻ hiện đúng làn | **PASS** |
| **D002** — khai VI + văn bản EN chắc ⇒ 400 `voice_language_mismatch`, giao diện hiện lỗi | **PASS** |
| 6 khung hình × 4 màn (tràn ngang) | **PASS 24/24** |
| 4 lớp bắt lỗi | **0 vấn đề** ngoài hai 400 kỳ vọng đã cho phép theo bước |
| D004 · T-08 · D005 | **SKIP có lý do in ra** — cả ba phụ thuộc dữ liệu seed `_seed_rc1` chỉ tồn tại trên máy chủ E2E loopback |

```
RC1 OK (tang-2) — 6 khung hinh x 4 man, D003, D002: 2/5 luong dat;
D004, T-08, D005 SKIP (phu thuoc du lieu seed _seed_rc1 chi co tren loopback)
```

🔑 **Bằng chứng mạnh nhất không nằm trong dòng PASS**: lượt D003 tạo một job
`ltt_voice.enroll` thật trên production và nó chạy tới **`done`**, sinh một hồ
sơ giọng mới `ngon_ngu='en'`, `ngon_ngu_nguon='khai_bao'`, `trang_thai='active'`
(`vc_d60a3c21…`, 05:58:51). Tức **toàn bộ đường ghi danh** — cửa web → hàng đợi
job → worker → cổng giọng thật → kho → CSDL — hoạt động trên bản vừa deploy, và
cột `ngon_ngu_nguon` của D003 được ghi đúng ở đường thật.

⚠️ Dấu vết để lại: một hồ sơ giọng thử trên tài khoản `.local`. Giữ lại làm bằng
chứng; mỗi lượt chạy lại sẽ thêm một hồ sơ nữa, nên đừng chạy lặp mà không dọn.

---

## 5. Ô 7 — Public API live: PASS

`tools/api_prod_canary.py trang-thai --token-file …` (khoá chỉ đọc, scope
`tools:read` + `jobs:read`; token ghi thẳng ra tệp, **không in ra**):

```
/health/ready 200 · / 200 · /vps 200 · /gia-api 200 · /developers 303
KHU API /api/v1 — 5 tool dang mo:
  image.ltt · speech.ltt · text.chat · video.subtitle · video.upscale
```

`speech.ltt` — cửa Public API của Voice — **đang mở và trả lời thật**.

### 5.1 Hook kiểm-trước D007 — đã thử trên production (12/09, 09:00)

Lượt đầu không thử được vì khoá canary chỉ có scope đọc. Lượt này phát một khoá
**tạm** (`tools:read` + `jobs:create`) cho chính tài khoản canary, chỉ gọi
`/api/v1/quotes` — **không** gọi `/jobs`, nên không job nào chạy và không credit
nào bị tiêu — rồi **thu hồi khoá ngay trong khối `finally`**.

| Ca | Kết quả |
|---|---|
| **Lệch làn** — preset VI `Adam` + văn bản tiếng Anh chắc | **HTTP 400** |
| **Đối chứng** — cùng preset VI + văn bản tiếng Việt | **HTTP 200**, `credit: 1`, `balance: 100` |

Thân lỗi của ca lệch làn, nguyên văn từ production:

```json
{"type": "/errors/invalid_request", "title": "Invalid request", "status": 400,
 "code": "invalid_request",
 "detail": "Giọng này thuộc làn Tiếng Việt, nhưng văn bản là Tiếng Anh. …",
 "instance": "/api/v1/quotes", "retry": "never",
 "reason": "voice_language_mismatch"}
```

🔑 Ba thứ cùng lúc, và cả ba đều là hợp đồng chứ không phải trang trí:

1. **Chặn tại `/quotes`** — tức **trước khi tiền động**. Đó chính là điều D007
   sinh ra để làm: trước RC1, lượt gọi đã được báo giá, giữ credit và xếp job
   rồi mới hỏng ở worker.
2. **`reason: "voice_language_mismatch"`** — mã máy đọc được, đúng tên mà
   `lan_ngon_ngu` dùng ở mọi cửa khác. Một `detail` tiếng Việt không thay thế
   được nó.
3. **Ca đối chứng vẫn ra giá** — rào chặn đúng thứ nó phải chặn, không chặn
   thừa. Một rào chỉ được chứng minh bằng **hai** ca.

⚠️ Cloudflare trả `1010 Access denied` cho `urllib`; công cụ của kho
(`tools/api_prod_canary.py`) dùng `httpx` với `User-Agent` riêng và đi qua bình
thường. Đó là chữ ký client, không phải lỗi ứng dụng — đừng đọc `1010` thành
"API chặn".

✅ Sau lượt đo: `developer_api_keys` không còn khoá nào mang tên
`D007 tier-2 probe (tam)` với `revoked_at IS NULL`.

---

## 6. Một điều Tầng 1 đã chứng minh mà bảng trên không thể hiện

Cổng giọng dùng cho lượt "tổng hợp THẬT" của Tầng 1 là `127.0.0.1:8120` —
**chính là dịch vụ `LTTStudioVoice` của production**. Nên engine giọng đang
phục vụ khách đã được chứng minh, trong chính phiên này, là tổng hợp được **cả
hai làn**: VI qua preset và EN qua một giọng ghi danh từ clip tiếng Anh thật.

---

## 7. Phán quyết Tầng 2 — **`RELEASED`**

Bảy ô của spec §10.2 đều đạt, trên đúng `e2676aaa` đang chạy thật.

### ⛔ Bốn điều chữ `RELEASED` này KHÔNG nói

| Nó **không** nói | Sự thật |
|---|---|
| "dữ liệu đã di trú xong" | **0 giọng đổi làn.** Ô 5 chỉ chứng minh công cụ chạy được và ghi số |
| "cả năm luồng Voice đã chạy trên production" | **2/5**. D004 · T-08 · D005 SKIP vì phụ thuộc dữ liệu seed cố ý không đưa lên production |
| "kho Voice lành lặn" | 28 hồ sơ của tài khoản thử vẫn trỏ tới khoá R2 không tồn tại; cơ chế gây mất **chưa biết** |
| "hook D007 đã chạy trên production" | Chưa — khoá canary chỉ có scope đọc |

⭐ Bốn dòng trên là lý do bảng ô ở §2 có cột "Bằng chứng" chứ không chỉ cột "Kết
quả": một chữ PASS không mang theo phạm vi của chính nó.

---

## 8. Việc còn nợ

| Việc | Mức |
|---|---|
| ~~Điều tra mất tệp kho Voice~~ → **ĐÃ TRUY RA**: kho không giữ object quá **~7 ngày**, cơ chế nằm **ngoài ứng dụng** (gần như chắc chắn là lifecycle rule của bucket). Toàn văn: `MAT_TEP_KHO_R2.md` | 🔴 việc còn lại là của **chủ dự án**: đọc luật thật trong dashboard Cloudflare R2, rồi chốt nới luật hay hạ hằng số trong mã (mã đang khai **30 ngày**) |
| Lấy `LTT_SMOKE_USER`/`LTT_SMOKE_PASS` để chạy bộ Playwright đầy đủ trên URL công khai | trung bình |
| ~~Thử hook D007 trên production~~ → **XONG** (§5.1): chặn 400 + `reason=voice_language_mismatch` tại `/quotes`, ca đối chứng vẫn ra giá | — |
| `tools/restore_drill_schema.py` còn giữ tên ràng buộc của bảng đã xoá 24/08 (`uq_vps_port_map_cong`); `test_155` chỉ kiểm một chiều | thấp, thuộc hệ VPS |
