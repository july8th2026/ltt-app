# Prompt 06 — Reliability, Security, Observability, Deployment & Recovery

**31/08/2026 21:20 → 01/09 01:10.** Ownership: F01–F28.

⚠️ **Phase này CHƯA đóng** — nhưng phần còn nợ nay nhỏ, liệt kê ở §11.

Đã có số đo: hai `CHANGE` treo từ Prompt 03/04 (§1, §2) · tiêm lỗi thật trên máy
B (§5) · **phát hiện chính** là `/health` xanh giả (§6) · quét bí mật + advisory
(§8) · phong bì năng lực (§9) · soát quan sát (§10) · SSRF, ACL, và **diễn tập
rollback thật 18,9 s** (§3, §4, §11).

Còn nợ: diễn tập reboot máy A thật (§12).

🔴 **ĐỌC TÊN CÁC MỤC F NHƯ CÂU HỎI, KHÔNG NHƯ CHẨN ĐOÁN.** *"Tiêm lỗi CUDA"*,
*"máy A khởi động lại"* là **kịch bản cần dựng để thử**, không phải sự cố đang
xảy ra. Chủ dự án đã đọc nhầm **hai lần** vì tôi viết cụt (*"CUDA hỏng"*,
*"máy-A-restart"*) — một lần là lỗi diễn đạt, hai lần cùng kiểu là lỗi **đặt
tên**, nên các mục nay viết dạng câu hỏi.

Đo 01/09, **không máy nào hỏng**: máy A hai RTX 5060 Ti driver 596.21, năm dịch
vụ `Running/Automatic`; máy B RTX 3090 driver 610.88, `/health` khai
`tren_gpu: true`, VRAM 22.416 MiB khi model nạp.

⭐ **§7 đáng đọc ngay cả khi bạn bỏ qua phần còn lại.** Nó ghi **bốn** lần hỏng
dụng cụ trong một tối, và cả bốn đều đọc lên y hệt một kết quả thật — ba trong
bốn sai về phía sẽ khiến không ai đi tìm.

---

## 1. 🔴 CHANGE đã thi hành: trọng tài nhận nhầm tải của chính ta

### A/B, đo trên cùng bộ đề, cùng máy, cách nhau 40 phút

| | Bị 429 ở lần thử đầu | Chất lượng |
|---|---|---|
| **Trước** (bản cũ) | **9 / 12** | 12/12 |
| **Sau** (đã vá) | **0 / 12** | 12/12 |

Cộng cả bộ hiệu năng, con số trước bản vá là **14/20 = 70 %**.

⭐ Đúng thứ `OPERATING_CONTRACT §6` đòi: lợi ích **đo được**, và **không có hồi
quy chất lượng** — 12/12 cả trước lẫn sau.

### Sửa gì

`llm_gateway/trong_tai.py` — nhánh *"1 python trên card + tải ≥ 50 % ⇒ bận"* nay
hỏi thêm **"model của ta có đang chạy không"**. Nếu có, tải cao ấy là **của ta**.

Lý do chọn điều kiện này chứ không phải một ngưỡng khác: **chính thông điệp của
nhánh nói ra mục đích của nó** — *"nạp model bây giờ sẽ đè lên nhau"*. Nó bảo vệ
thao tác **NẠP**, không phải thao tác phục vụ. Model đã nạp rồi thì không có gì
để nạp.

⚠️ Cái giá, nói thẳng: model ta đã nạp **và** ComfyUI bắt đầu vẽ thật ⇒ ta không
còn từ chối. Chấp nhận được vì `--reserve-vram 3` đã có và VRAM của ta ổn định
22,4 GB. Nếu một ngày dự án video đổi cách dùng card thì **đọc lại chỗ này**.

`tests/test_368` — 8 phép kiểm, gồm một bánh cóc chốt rằng `api.py` **có nối
dây** tín hiệu: sửa `trong_tai.py` mà quên nối thì bản vá không chạy, và triệu
chứng là 70 % từ chối oan **vẫn nguyên, không dòng đỏ nào**.

---

## 2. CHANGE đã thi hành: deploy im lặng về cấu hình chưa có hiệu lực

**Bằng chứng gốc (Prompt 03 §5):**

```
llama-swap.yaml TREN DIA        "input public 65K"   ghi 18:37:35
tien trinh llama-swap           khoi dong           18:34:37
cau hinh DANG CHAY (/running)   "input public 90K"
```

Ba con số, hai sự thật khác nhau, không một dòng cảnh báo.

`deploy.ps1` nay **phát hiện và nói**: sau khi chép, nó hỏi thời điểm khởi động
của `llama-swap` trên máy B; nếu tiến trình cũ hơn tệp vừa chép thì in cảnh báo
kèm lệnh cần chạy.

⛔ Nó **không tự restart**. `llama-swap` restart là **unload model** — một quyết
định vận hành, không phải một bước phụ của deploy. Nhưng im lặng thì không chấp
nhận được.

---

## 3. Deploy & rollback — đã đi thật hai lần hôm nay

| | Máy A | Máy B |
|---|---|---|
| Đường | `setup/deploy_nang_quyen.ps1` → `2-cai-dat.ps1` | `llm_gateway/deploy/deploy.ps1` qua SSH |
| Đã chạy | 18:17 (`EXITCODE=0`) | 18:37 và 21:30 |
| Giữ cấu hình vận hành | `app.env` không đụng | `gateway.env` **migrate giữ token/model** |
| Kênh vào khi SSH tắt | — | **Nexus** (bật SSH tạm, đóng lại sau) |
| Rollback | `app.previous/` | `releases/auto-<mốc>`, **chụp mỗi lần deploy** |

🔴 **Rà soát 01/09 tìm ra đường rollback của máy B không được nuôi.** `releases/`
chỉ có hai bản, cả hai từ **27/08** — bốn lần deploy trong ngày không chụp bản
nào. Tức nó tồn tại *trên giấy*: nếu một lần deploy làm hỏng thì cách duy nhất
còn lại là `git revert` + deploy lại, đòi máy A sống **và** bật được `sshd`.
Máy A đã có `app.previous/` cho đúng việc này; máy B thì không.

Nay `deploy.ps1` chụp **trước khi đè** và **tự kiểm bản chụp**. Chụp thất bại thì
không dừng deploy — nhưng nói to, vì từ đó trở đi ta deploy **không có đường lui**.

**Diễn tập rollback THẬT (F26), không phải mô phỏng:**

```
làm hỏng một module  ->  dịch vụ Paused, health chết
xcopy ngược + restart ->  18,9 GIÂY  ->  Running, health sống, tệp đã về
```

⭐ **`gateway.env` migrate tại chỗ** (dòng 114–116 của `deploy.ps1`) — kiểm trước
khi deploy, vì nếu nó sinh token mới thì khoá máy A lưu sẽ lệch và toàn bộ dịch
vụ chết. Nó không sinh mới khi tệp đã tồn tại.

---

## 4. Bảo mật — quan sát trong lúc thi hành (chưa phải quét đầy đủ)

* `sshd` trên máy B trở lại `Disabled` sau mỗi lần dùng; đã đối chiếu cổng 22
  đóng **từ máy A** chứ không chỉ tin lệnh `Set-Service`.
* Máy B **không giữ bí mật nào của nền tảng** — `gateway.env` chỉ có bearer của
  chính nó (43 ký tự) + URL loopback + các trần.
* Cầu hẹp `setup/chay_voi_env.ps1` nạp `app.env` vào **riêng tiến trình**, chạy
  đúng bốn việc trong danh sách trắng, **không in giá trị nào**.
* ✅ **F19, F20 nay ĐÃ LÀM — xem §8.** (Dòng cũ ở đây ghi *"chưa làm"*; giữ
  nguyên nó sẽ thành hai câu ngược nhau trong một tệp, đúng lỗi mà `CLAUDE.md`
  đã dính hai lần với hàng Public API.)
* ✅ **F14 SSRF nay ĐÃ CHỐT** — `test_373`, 30 phép kiểm. Biện pháp **đã có sẵn
  trong mã** và giải thích rõ, nhưng `grep url_tu_xa tests/` trả về **rỗng**:
  một biện pháp bảo mật đang làm việc mà không phép kiểm nào giữ, tức cách một
  lần refactor thiện chí là mất — và mất **không tiếng động**.
* ✅ **F21 ACL nay ĐÃ SIẾT** — `gateway.env` cho `BUILTIN\Users` quyền đọc, tức
  **mọi tài khoản cục bộ trên máy B đọc được bearer token**. Không phải lo xa:
  máy B có **hai tài khoản sandbox Codex** đang bật (`CodexSandboxOffline`,
  `CodexSandboxOnline`) cộng `Guest` — đúng loại tài khoản sinh ra để chạy mã
  không tin cậy. So sánh: `app.env` trên máy A chỉ SYSTEM + Administrators, và
  chính báo cáo này đã ghi ACL đó *"LÀ ĐÚNG"*. Hai máy lẽ ra cùng một chuẩn.
  Nay đã siết, và **đặt lại ở mỗi lần deploy** — sửa tay là mất ở lần sau.
* ⚠️ **Chấp nhận có ý, không phải bỏ sót:** dịch vụ chạy bằng `LocalSystem` —
  nhiều quyền hơn cần, nhưng đổi nó chạm quyền truy cập GPU. `Guest` đang bật
  trên máy B là chính sách máy, ngoài phạm vi audit này.
* ✅ **Chuỗi cung ứng nay ĐÃ SOÁT.** Nexus (thứ duy nhất phát tới máy **bên thứ ba**) ký Ed25519 và tự kiểm trước khi ghi — đúng chỗ cần ký. Nền tảng và cổng thì tin **cây nguồn cục bộ** + khoá SSH; đó là ranh giới tin cậy hợp lý, không phải lỗ.
  🔴 Nhưng tìm ra một **bất đối xứng**: `render_gateway/deploy` có 15 dòng đối chiếu hash, `llm_gateway/deploy` có **0**. Hai cổng cùng một máy, một cái kiểm một cái không. Nay đã có, và chạy thật: **34/34 tệp khớp — máy B không bị sửa tay**. Đó là lần đầu ta *biết* điều đó thay vì giả định.

---

## 5. §1 Tiêm lỗi thật trên máy B (F01–F10, một phần)

**01/09, 23:30–00:20.** Chủ dự án xác nhận **chưa có khách ngoài** (log cổng: 537
yêu cầu từ 192.168.2.17 đều là lưu lượng thử của phiên này), nên bán kính bằng 0.

### Chuỗi phải sống để `ltt_llm` phục vụ một yêu cầu

```
Windows boot → LTTLlamaSwap (8280)  Automatic, không phụ thuộc ai
             → LTTLlmGateway (8299) Automatic, DependsOn LTTLlamaSwap
             → request đầu → llama-swap sinh llama-server, nạp GGUF 15,33 GiB
             → sau ttl 1800s → nhả, VRAM 22.420 → 886 MiB
```

⭐ **Kích hoạt là theo Windows, không phải máy A gọi mở.** `grep Start-Service`
trong `platform_core/`, `server/`, `apps/` trả về **rỗng** — máy A không bao giờ
bật dịch vụ trên B; nó chỉ gọi, hỏng thì `KhongMoDuocLuong`, bận thì cascade sang
Gemini. Thứ *duy nhất* nạp theo yêu cầu là **model**, và đó là thiết kế đúng: giữ
15,9 GB VRAM thường trú sẽ chặn hai hộ kia dùng chung card (D-037).

### Bảng `failure → detect → recovery`

| Hỏng | Phát hiện | Ai dựng dậy | Đo được | Khách thấy |
|---|---|---|---|---|
| luồng bị cắt giữa chừng (RST) | — | 2 tầng nhả suất | `dang_chay=0`, `da_thu_hoi=0` | không gì |
| `llama-server.exe` chết | request kế tiếp | llama-swap | **17,7 s** | một request chậm |
| tiến trình con python chết | NSSM | `AppExit=Restart`, delay 15 s | PID đổi thật | ~15 s lỗi |
| **vỏ bọc `nssm.exe` chết** | **KHÔNG AI THẤY** | **không ai** | **99 s health xanh giả** | không gì → rồi sập |
| mất điện / reboot | — | `StartType=Automatic` cả hai | *suy ra từ cấu hình* | boot xong là xong |

### F01 luồng treo — thử hồi quy cho sự cố rò suất 31/08

Cắt 3 luồng bằng `SO_LINGER(1,0)` → **RST**, tức khách *rút mạng* chứ không phải
đóng tab tử tế. Ba mốc **0,3 s / 1,5 s / 4 s**; mốc 0,3 s cắt *trước khi generator
kịp chạy dòng đầu*, đúng đường rò cũ.

```
dang_chay=0/1 suốt cả 3 lần và suốt 30 s theo dõi
da_thu_hoi=0
```

⭐ `da_thu_hoi=0` mới là phần đáng kể: **chặn cuối (hạn giữ 1200 s) không phải
đỡ**. Hai tầng trên tự nhả suất trước khi đến lượt nó. Nếu nó `>0` thì suất vẫn
về 0 nhưng bằng một đường khác — một tin xấu đội lốt tin tốt.

**Đối chứng** (bắt buộc, xem §7): đọc đồng hồ *trong lúc* một luồng chạy thật →
`[1,1,1,1,1,1,0]`, đỉnh = 1. Không có bước này thì một đồng hồ **chết** cũng cho
ra dãy 0 y hệt.

---

## 6. 🔴 §2 PHÁT HIỆN CHÍNH: `/health` xanh giả, và nó giả **theo cấu trúc**

Prompt 06 §2 yêu cầu *"prove health isn't accidentally green for a state violating
SLO."* Ở ta **nó xanh giả**. Đo thật, dừng vỏ bọc `nssm.exe`:

```
+ 0.0s   /health=200  Get-Service=Stopped   cong8299=26528
+62.9s   /health=200  Get-Service=Paused    cong8299=26528
+99.0s   /health=200  Get-Service=Paused    cong8299=26528
```

Tiến trình con **sống sót mồ côi**, giữ cổng, trả 200 — suốt 99 giây, trong khi
dịch vụ đã chết và **không có ai dựng nó dậy nữa**.

`/health` **không nói dối** — nó thành thật báo cáo về một tiến trình **thật sự
khoẻ**, chỉ là tiến trình đó lẽ ra không nên đang chạy. Cái sai nằm ở câu hỏi,
không ở câu trả lời: *"anh có khoẻ không"* là câu hỏi sai, câu đúng là *"anh có
nên đang chạy không"*.

### ✏️ SỬA MỘT CÂU TÔI ĐÃ VIẾT QUÁ MẠNH

Bản đầu của mục này viết: *"không sửa được bằng cách làm `/health` thông minh
hơn — một endpoint sức khoẻ được phục vụ bởi thứ cần kiểm tra thì **vĩnh viễn**
không nói được «tôi là tiến trình không nên tồn tại»."*

**Câu đó sai.** Con mồ côi biết một sự thật về *thế giới bên ngoài nó*: cha nó đã
chết. Đo trên máy B 01/09:

```
PPID cua tien trinh phuc vu van la 13672,
va tien trinh do bay gio: <KHONG CON TON TAI>
```

⇒ Thông tin **có sẵn**. Một bản sửa **một nguồn** là khả thi: cổng chụp
`(PPID, tên cha, giờ sinh cha)` lúc khởi động, rồi định kỳ kiểm — cha chết thì
tự khai `mo_coi: true` (hoặc tự thoát để NSSM/SCM dựng lại sạch).

⚠️ Phải so **cả ba**, không chỉ PPID: Windows tái sử dụng PID sau một thời gian,
nên "PPID vẫn tồn tại" là một phép kiểm sẽ im lặng đúng lúc nó cần nói.

⚠️ Và cây tiến trình **sâu hơn tôi tưởng** — `nssm → python → python`. Dừng ở
tầng giữa thì con lá **chết theo**; chỉ dừng ở tầng SCM biết mới sinh mồ côi. Nên
bản sửa một nguồn phải neo vào **đúng tổ tiên là `nssm.exe`**, không phải "cha
trực tiếp".

**Vì sao vẫn giữ chốt hai nguồn** dù bản một nguồn khả thi:

* nó **đã chạy được ngay**, không cần deploy sang máy B (deploy là ranh giới giữ lại);
* nó bắt cả những lệch **khác** hướng — dịch vụ `Running` mà `/health` chết;
* bản một nguồn đòi cổng tự-thoát-đúng-cách, và một tiến trình tự sát sai lúc là
  một lớp lỗi mới. Nó nên đến **sau** khi có người quan sát, không phải thay.

⇒ Bài học không phải *"phải luôn hai nguồn"*. Là: **tôi đã đóng khung một hạn chế
kỹ thuật thành một điều bất khả**, và một câu như thế trong tài liệu sẽ khiến
phiên sau không thử bản sửa rẻ hơn. Sáu giờ sau khi viết nó tôi tự kiểm và nó
sai.

### Ba việc, và một kết quả âm đáng ghi

1. ✅ `sc failure` cả hai dịch vụ (reset 86400; restart 15 s/60 s/120 s).
   🔴 **CẦN NHƯNG KHÔNG ĐỦ** — đo lại: SCM *có* kích hoạt (Stopped → Paused ở
   62,9 s) nhưng bản mới **không giành được cổng** vì mồ côi giữ. Tôi đã suýt
   báo "đã sửa" sau bước này.
2. ✅ `llm_gateway/main.py` từ chối khởi động khi 8299 đã có người giữ, in PID thủ
   phạm + hai dòng xử lý. Nó **không** sửa cái xanh giả; nó biến một `Paused` câm
   thành một dòng log chẩn đoán được. Dò bằng **connect** chứ không bind — bind
   rồi đóng để nhường cho uvicorn là một cuộc đua.
3. ✅ `tools/soi_cong_llm.py` — chốt hai nguồn, **lấy trong một lượt gọi** để
   chúng nói về cùng một khoảnh khắc (hai lượt cách nhau vài giây là hai ảnh chụp
   khác nhau, và đúng cái lệch ta đang săn có thể lọt qua khe giữa chúng).

**Chứng minh đầu-tới-cuối trên máy thật:** LÀNH → tạo mồ côi → công cụ kêu `LỆCH`
và gọi đúng `pid 14244` → khôi phục bằng **đúng hai dòng nó in ra** → LÀNH.
`test_370` chốt phán xử bằng dữ liệu tổng hợp (11 phép, chạy offline).

### Bề mặt không xác thực (đo)

```
/live      200 không cần token   {"ok":true,"version":"0.1.0"}
/health    401      /v1/models  401      /metrics 404      /  404
```

✅ Đúng hướng: liveness mở và tối thiểu, chỉ số vận hành chi tiết thì đóng. Bộ
chăm sóc dịch vụ không cầm token vẫn phân biệt được *chết* với *sống nhưng từ
chối ta*. ⚠️ Nhưng `/live` **cũng do con mồ côi phục vụ** — nó nằm trong đúng
phạm vi mù ở trên.

---

## 7. ⚠️ Chất lượng phép đo: **bốn** lần hỏng dụng cụ trong một tối

Ghi ra vì cả bốn **đọc lên y hệt một kết quả thật**, và ba trong bốn sai về phía
sẽ khiến không ai đi tìm.

| # | Cơ chế | Nó nói gì | Sự thật |
|---|---|---|---|
| 1 | đọc sai tên trường → `.get()` → `None` | *"RO SUAT quay lai"* | hệ thống lành lặn |
| 2 | đồng hồ có thể chết mà vẫn cho dãy 0 | *"không rò"* | chưa biết — phải đối chứng |
| 3 | `curl -w` qua Nexus trả **chuỗi rỗng** | *"chết từ giây 0"* | dịch vụ vẫn chạy |
| 4 | Nexus cắt ở **120 s cứng** bất kể `timeout_ms` | mất sạch phép đo 150 s | NSSM *đã* dựng dậy |

⇒ Hai thói quen, không phải hai bước thêm:

* **Kiểm dụng cụ ở dòng đầu.** Bộ đo cuối từ chối chạy nếu `/health` không 200 và
  `Get-Service` không Running — và nói rõ *"không đo được"*, khác *"không đạt"*.
* **Ghi xuống tệp từng bước.** Một lần đứt vận chuyển không được xoá phép đo.
  Cùng bài học với lô đo ảnh ghi kết quả sau mỗi ảnh.

⭐ Và một điều về hình dạng: lỗi #1 (`h["dang_giu"]` → `None`) cùng lớp với
`_ban_va()` gộp *"chưa có bản vá"* vào *"không hỏi được"* — **một giá trị trông
hợp lý thay cho sự vắng mặt**. Đó là lớp lỗi mà bánh cóc `check_silent_except`
sinh ra để chặn, và nó xuất hiện hai lần trong một buổi ở hai tầng khác nhau.

---

## 8. §5 Bảo mật — quét đầy đủ (F19, F20)

**F19 quét bí mật trong nguồn:** `tools/scan_source_secrets.py` →
**0 phát hiện / 2.123 tệp**, `RESULT: PASS`.

**F20 phụ thuộc & advisory:** `tools/check_phu_thuoc_advisory.py` hỏi OSV.dev về
19 gói chạm dữ liệu không tin cậy hoặc giữ bí mật. **5/19 có advisory.** Đã sửa
**hai cái nằm trong ghim sẵn có**, tức không phải quyết định kiến trúc:

| Gói | Từ → đến | Vì sao ưu tiên |
|---|---|---|
| `python-multipart` | 0.0.29 → **≥0.0.31** | **chạm được**: `server/api/uploads.py:139` nhận `UploadFile` trên bề mặt **công khai** `/api/v1`; 3 advisory `AV:N/PR:N`. Sau khi nâng: **sạch** |
| `cryptography` | 46.0.6 → **≥46.0.7** | 9 → 7 advisory |

Xác minh: **437 passed / 3 skipped** trên các đường upload + token + mã hoá.

**Còn nợ, đều đòi NỚI TRẦN GHIM** ⇒ không tự quyết:
`pillow` 34 advisory (cần 12.3.0, ghim `<12` — chạm mọi app ảnh) ·
`aiohttp` 28 (cần 3.14.1, phụ thuộc gián tiếp) · `cryptography` 7 còn lại (cần ≥48) ·
`urllib3` 4 (vá ở 2.7.0).

⛔ Công cụ **không vào gate** và **luôn trả 0**: nó gọi mạng (gate phải tất định +
chạy offline) và kết quả **đổi mà mã không đổi** — một advisory công bố hôm nay
làm đỏ một cây không ai chạm tuần này. Đó là **bản tin**, không phải **phán quyết
về một thay đổi**. Mất mạng thì trả 2 và nói *"KHÔNG KẾT LUẬN ĐƯỢC"*, không bao
giờ nói thành *"sạch"*.

⚠️ **Cái giá đã ghi ra, không phải để đổi ý:** một công cụ ngoài gate là một công
cụ **sẽ không ai chạy** (`check_multiproc` đã phải vào gate mới được chạy đều).
⇒ Nó cần một chỗ **buộc chạy theo lịch**, không phải "chạy khi nhớ".

---

## 9. §7 Phong bì năng lực đang bền vững

Dựng từ số đo Prompt 04. **Không đề xuất phần cứng/topology mới** — ngoài phạm vi
chương trình này.

### Ràng buộc cứng, theo thứ tự cắn trước

| # | Ràng buộc | Con số | Cắn khi nào |
|---|---|---:|---|
| 1 | **`max_dong_thoi = 1`** | 1 luồng | **ngay lập tức** — khách thứ hai bị 429 |
| 2 | `rpm` | 120 | ~2 req/s, xa hơn #1 nhiều |
| 3 | VRAM khi model nạp | 22,4 / 24,6 GiB (**91 %**) | khi hàng xóm cần card |
| 4 | Cloudflare chờ phản hồi | 100 s | cửa đồng bộ, không phải cửa luồng |
| 5 | Trần token vào | 96.256 | theo yêu cầu, không theo tải |

⭐ **Ràng buộc #1 quyết định mọi thứ khác.** Ở `max_dong_thoi = 1`, năng lực
**không** là một đường cong tải — nó là một hàng đợi một chỗ. Ba ràng buộc dưới
không bao giờ được chạm tới trước nó.

### Phong bì suy ra

```
1 luồng  ×  63,3 tok/s  =  63,3 tok/s cho TOÀN HỆ, không phải cho mỗi khách
```

| Hình dạng yêu cầu | Thời gian một lượt | Thông lượng bền vững |
|---|---:|---:|
| ngắn (200 token ra) | 4,36 s | **~13,8 req/phút** |
| dài (900 token ra) | 17,20 s | **~3,5 req/phút** |
| ngữ cảnh lớn (52K vào) | ~77 s | **~0,8 req/phút** |

⚠️ Đây là **trần lý thuyết ở tải hoàn hảo**. Khách thứ hai đến giữa một lượt 77 s
sẽ **chờ trọn 77 giây** hoặc bị 429 — không có mức suy giảm ở giữa.

### Ngưỡng biện minh cho việc mở rộng

| Ngưỡng | Đo bằng gì | Nghĩa |
|---|---|---|
| tỉ lệ 429 > 5 % trong một giờ | `metrics.CAPACITY_REFUSED` | hàng đợi một chỗ đã thành nút cổ chai thật |
| chờ hàng đợi > 30 s | `admission_delay_ms` — **đã có**, xem ✏️ dưới | đang tiến tới trần |
| VRAM đỉnh > 23,5 GiB | `nvidia-smi` trong `/health` | hết biên cho hàng xóm |

### ✏️ SỬA LẦN HAI — cùng hình dạng với lần trước

Bản đầu mục này viết: *"ngưỡng thứ hai **chưa đo được** — chưa có metric thời
gian chờ hàng đợi."* **Sai.** `platform_core/public_api/metrics.py:66` có sẵn:

```python
LATENCY_ADMISSION = "admission_delay_ms"
```

Sắc thái đúng, và nó nhỏ hơn nhiều: metric **có**, nhưng nó gom
`count / total_ms / max_ms` ⇒ cho **trung bình và cực đại**, không cho **p95**.
Mà `max_ms` là một cận trên bảo thủ — dùng được ngay để đặt ngưỡng, chỉ là nó
nhạy với một lượt lẻ bất thường.

⇒ Không phải *"phải xây metric"*. Là *"phải đọc metric đang có, và biết nó nói
`max` chứ không nói `p95`."*

⚠️ Đây là **lần thứ hai trong một đêm** tôi tuyên bố một thứ **không tồn tại**
trong khi nó có sẵn — lần trước là *"không thể sửa bằng một nguồn"* ở §6. Cùng
một hình dạng: một câu khẳng định rộng hơn thứ tôi đã thực sự tra. Và cả hai lần
đều tự bắt được **chỉ vì đi tra tiếp**, không phải vì có phép kiểm nào đỏ.

---

## 10. §3 Quan sát — soát nhu cầu, cardinality, riêng tư (F11–F16)

### Đã có, và đủ dùng

`platform_core/public_api/metrics.py` — 20+ bộ đếm phủ đủ vòng đời:

| Nhóm | Metric |
|---|---|
| Yêu cầu | `requests` · `auth_success` · `auth_failure` · `rate_limited` |
| Từ chối | `capacity_refused` · `kill_switch_refused` |
| Idempotency | `idempotency_replay` · `idempotency_conflict` |
| **Tiền** | `credit_held` · `credit_settled` · `credit_refunded` · `credit_exhausted` |
| Việc | `jobs_created` · `jobs_cancelled` |
| Webhook | `webhook_delivered` · `webhook_failed` |
| **Suất** | `admission_acquired` · `rejected` · `released` · **`expired`** |
| Trễ | `request_ms` · `queue_pickup_ms` · `admission_delay_ms` |

⭐ Bốn metric `admission_*` là bộ duy nhất nhìn ra được sự cố 31/08: `acquired`
trừ `released` là số suất **đang treo**, và `expired` đếm số lần chặn cuối phải
đỡ. Trên máy B đã có bản tương đương ở `/health` (`da_thu_hoi`).

### Cardinality — **không có rủi ro**, và lý do là kiến trúc

```python
def increment(name: str, amount: int = 1) -> None:
```

**Không có nhãn.** Không `user_id`, không `key_id`, không `model`. Nghĩa là số
chuỗi thời gian bị chặn cứng bởi số hằng đã khai — nó **không thể** nổ theo số
khách hay số khoá.

Cái giá đã trả: không cắt lát được *"khách nào đang bị 429"*. Bù lại bằng
`public_api_requests` (có `request_id`, tra qua `/admin/api-trace`) — tức chi
tiết nằm ở **log có cấu trúc**, còn metric giữ vai trò tổng hợp. Đó là một sự
phân vai đúng, không phải một thiếu sót.

### Riêng tư — sạch, **do hệ quả** của điều trên

Không nhãn ⇒ không có dữ liệu cá nhân nào lọt vào metric. Không cần thêm luật
che, vì không có gì để che.

### Không đề xuất thêm metric nào

Prompt 06 §3 nói *"only add metrics that answer an operational question."* Mọi
câu hỏi vận hành đã nêu trong báo cáo này — *có rò suất không · có đang chạm trần
không · khách có bị thu tiền oan không · máy B có xanh giả không* — đều trả lời
được bằng thứ **đang có**. Thêm nữa là thêm việc phải nuôi.

### Rủi ro P2 đã ghi, nay có số

`max_dong_thoi = 1` ⇒ **một sự cố suất = 100 % ngừng dịch vụ**. Sự cố 31/08 chính
là hình dạng đó: một suất rò, và vì chỉ có một suất, hệ **mất hoàn toàn 6 giờ**.
Nay đã có ba tầng nhả + hạn giữ 1200 s, nhưng **hình dạng rủi ro không đổi** —
chỉ xác suất giảm. Hệ vẫn không có mức suy giảm ở giữa.

---

## 12. §1 F05 — *"nếu máy A khởi động lại thì sao?"*

Đo 01/09. **Máy A không có lỗi nào** — mục này hỏi một giả định.

| Dịch vụ | Trạng thái | Khởi động | NSSM `AppExit` | SCM failure-actions |
|---|---|---|---|---|
| `LTTStudioWeb` | Running | Automatic | **Restart** | ❌ **không có** |
| `LTTStudioWorker` | Running | Automatic | **Restart** | ❌ |
| `LTTStudioVoice` | Running | Automatic | **Restart** | ❌ |
| `LTTStudioCodex` | Running | Automatic | — | ❌ |
| `cloudflared` | Running | Automatic | — | ❌ |

### Trả lời từng chế độ hỏng

| Hỏng | Chuyện gì xảy ra |
|---|---|
| **máy reboot** (mất điện, Windows Update) | ✅ cả 5 `Automatic` ⇒ tự lên lại. Job dở dang được nhận lại qua lease hết hạn (`test_215`), khoản giữ treo được tự hoàn (H41.3) |
| **tiến trình con chết** | ✅ NSSM `AppExit=Restart` dựng dậy |
| **vỏ bọc `nssm.exe` chết** | ❌ **không ai dựng dậy** — SCM không có failure-actions |

🔴 **Hàng thứ ba là đúng cái lỗ đã bịt trên máy B đêm nay** — và ở đây nó nằm
trên máy **đang phục vụ khách thật**. Nếu vỏ bọc chết, tiến trình con sống sót
mồ côi vẫn giữ cổng, trang web **vẫn trả lời**, còn `Get-Service` nói `Stopped`
và không có gì dựng nó dậy nữa.

⏳ **Cần Administrator** (ranh giới UAC ta giữ). Lệnh đã soạn sẵn ở phần trả lời
cho chủ dự án; nó chỉ đặt **chính sách cho lần hỏng sau**, không khởi động lại
gì, nên chạy được lúc đang phục vụ.

⚠️ **Chưa diễn tập reboot thật.** Máy A là production **và** đang chạy phiên
làm việc này, nên một lần reboot cắt luôn tay đang gõ. Bảng trên suy từ cấu
hình đã đo, không phải từ một lần reboot quan sát được — và phải đọc đúng phạm
vi đó.

---

## 11. Còn nợ của phase này

| Mục | Trạng thái |
|---|---|
| F01 luồng treo · F08 llama-server chết · F09 vỏ bọc chết · F10 mất điện | ✅ **ĐO XONG** |
| F02 DB chập chờn · F03 worker restart · F04 lease cũ | ✅ **ĐÃ PHỦ** — `pool_pre_ping` + `test_215` ("chủ chết thì lease hết hạn", "worker chết giữa lúc gửi") |
| F06 máy B không với tới được | ✅ **XONG** — `test_372`, 6 phép kiểm gồm một đối chứng |
| F07 CUDA hỏng / CPU fallback | ✅ **PHỦ Ở MỨC PHÁT HIỆN** — `test_270` (10 phép, có ca thật 23/08) + `test_378` chốt **mắt xích giữa** mà trước đây không ai kiểm. Không tiêm được lỗi CUDA an toàn, **và không cần**: thứ thật sự hỏng ngày 23/08 không phải CUDA mà là **hơn một giờ không ai biết** |
| F05 kịch bản *“nếu máy A khởi động lại”* | **MỘT PHẦN** — xem §12. Đã đo cấu hình; chưa diễn tập reboot thật |
| F11–F16 mô hình health + bảng quan sát | ✅ **XONG** — §6 mô hình health, §10 soát metric/cardinality/riêng tư. Kết luận: **không thêm metric nào** |
| F19 quét bí mật · F20 advisory | ✅ **XONG** |
| F14 SSRF hồ sơ vision | ✅ **XONG** — `test_373`, 30 phép kiểm, 3 giao thức × 6 đích thật + 7 biến thể lách |
| F21 ACL / đặc quyền tối thiểu | ✅ **XONG** — siết `gateway.env`, và đặt lại ở **mỗi lần deploy** |
| F22–F27 deploy/rollback + diễn tập | ✅ **XONG** — deploy nay **chụp bản trước**, và diễn tập rollback thật: hỏng → **18,9 s** → lành |
| F28 phong bì năng lực / SLO | ✅ **XONG** (§9) — nhưng thiếu metric *thời gian chờ hàng đợi*, nên nói được trần ở đâu mà **không** nói được ta cách trần bao xa |

⛔ **Không đánh dấu phase này `PASS`.** Phần đã làm thì có số đo và tái hiện được;
phần còn lại là một nửa phase chưa chạy.

⏸️ **`llm_gateway/main.py` CHƯA DEPLOY sang máy B** — deploy là một trong ba ranh
giới giữ lại. `tools/soi_cong_llm.py` chạy từ máy A nên **đã dùng được ngay**.
