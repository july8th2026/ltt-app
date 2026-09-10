# QUYẾT ĐỊNH CỦA CHƯƠNG TRÌNH LTT VIDEO AI

> Khuôn theo `docs/ANH_NOI_BO/DECISIONS.md` (tiền lệ H37). Đây là sổ quyết định
> **cấp chương trình**. Quyết định **cấp nền tảng** (một model chạy GPU thuê ngoài
> đặt ở đâu trong kiến trúc) sẽ vào `docs/QUYET_DINH_NEN_TANG.md` dưới số **Q121**
> — **chỉ sau khi ADR-3 được duyệt**, vì đó chính là nội dung của nó.
>
> ⛔ Không sửa đè lên dòng cũ. Đổi thì đánh dấu `~~ĐÃ THAY~~`, ghi thay bởi ai và
> ngày nào, rồi thêm dòng mới (`AGENTS.md` §6).

| Trạng thái | Nghĩa |
|---|---|
| ✅ **CHỐT** | chủ dự án đã quyết |
| 🟡 **ĐỀ XUẤT** | P00 đề xuất, chờ chủ dự án |
| ⏳ **CHỜ ĐO** | không quyết được cho tới khi có số |

---

## V-001 ✅ CHỐT (2026-09-04) — Vì sao cần C-CLOUD (đáp **ADR-0**)

**Chủ dự án là nhà sản xuất video AI. C-CLOUD phục vụ *công ty dùng trước*, bán
phần dư. Mục tiêu xuyên suốt: *tối giản chi phí đầu tư lâu dài*.**

Trong bốn lý do P00 nêu, đây là **A (biên lợi nhuận / chi phí)** — nhưng ở một
dạng mà P00 đã **không** liệt kê ra, và nó đổi khá nhiều thứ:

> 🔴 **Khách hàng đầu tiên là chính nền tảng.**

Bốn hệ quả, tất cả đều có thể kiểm được:

1. **Tiêu chí chấp nhận của P08 đổi.** Không phải *"đẹp hơn Seedance"* mà là
   *"đủ để công ty xuất bản, ở mức chi phí thấp hơn đi mua"*. Phép so mù vẫn cần
   — nhưng để trả lời **có dùng được không**, không phải để trao huy chương.
   Tiền lệ: model ảnh nhà **thua Gemini 24–4** (D-045) và vẫn đáng mở, vì nó rẻ
   hơn và không bị chính sách nội dung của hãng khác chi phối.
2. **Giờ Pod nhàn rỗi là kẻ thù chính**, không phải chất lượng khung hình. Với
   GPU thuê, thứ giết biên lợi nhuận là thời gian **bật mà không có việc**.
3. ⭐ **Và chính "nội bộ trước" là thứ làm cho mô hình giá chạy được.** Việc của
   công ty do **chính chủ xếp lịch** ⇒ gộp lô là khả thi thật, không phải một lời
   hứa vận hành. Mỗi phiên Pod có sẵn một đáy tải để phân bổ chi phí khởi động
   — điều mà một sản phẩm thuần bán-lẻ **không** có ở giai đoạn đầu.
4. **Phạm vi V1 không co lại** (D03 giữ đủ 4 mode), nhưng **thứ tự mở bán** thì
   có — xem V-004.

---

## V-002 ✅ CHỐT (2026-09-04) — App mới `lttvideo` (đáp **ADR-1**)

**Tạo app mới, không mở rộng `apps/taovideo`.** Đúng tiền lệ `apps/anhnoibo`:
model nhà là một năng lực riêng, và bán nó cần một `ToolSpec` — mà ToolSpec chỉ
khai được trong manifest của một app. Thêm vào app đang phục vụ khách là đụng vào
doanh thu đang chạy; thêm một thư mục vào `apps/` thì không đụng ai.

### Định danh — chốt luôn, vì đặt sai tên là một món nợ không gỡ được

| Trường | Giá trị | Vì sao |
|---|---|---|
| `slug` | **`lttvideo`** | hợp lệ (`^[A-Za-z0-9_]+$`), chưa ai dùng |
| `display_name` | **LTT Video** | |
| `route_prefix` | **`/lttvideo`** | trùng slug ⇒ không có ánh xạ nào phải nhớ; chưa ai dùng |
| `job_types` | `lttvideo.t2v` · `lttvideo.i2v` · `lttvideo.character` · `lttvideo.v2v` | duy nhất toàn kho (`test_60`) |
| tên tool | **`video.ltt`** | ⭐ khớp gia đình model nhà đang có: `image.ltt` (anhnoibo) · `speech.ltt` (ltt_voice). `video.generate` đã là của `taovideo` |
| `requires` | **`("api",)`** | handler chỉ gọi HTTP tới C-CLOUD, **không** đụng GPU máy A |
| `table_prefix` | `lttvideo` nếu cần bảng riêng | |

### 🔴 Và tên này vô tình tránh đúng cái bẫy mà `ltt_llm` đã sập

`tests/test_60_app_registry.py:396` cấm tên app xuất hiện trong `platform_core/`.
Ba app **đã phải xin miễn trừ**: `agent`, `nexus`, `ltt_llm`. Chính phép kiểm đó
viết ra vì sao đấy là một cái giá, chứ không phải một sự tiện lợi:

> *"Adding a name here is not free: it blinds this check to that string, so a
> genuine hardcoded reference to that app would slip through."*
>
> *"⚠️ The naming is still backwards… the image side got this right (provider
> `ltt_image` + app `anhnoibo`), so its provider id is NOT an app slug and this
> check stays sharp for it."*

⇒ Nếu ADR-3 chốt có một provider, id của nó là **`ltt_video`** (có gạch dưới),
còn slug app là **`lttvideo`** (không gạch dưới). **Hai chuỗi khác nhau**, nên
`"lttvideo"` không xuất hiện trong `platform_core/` và phép kiểm **giữ nguyên độ
sắc** — không cần miễn trừ thứ tư.

⛔ **Đừng "cho gọn" bằng cách đặt slug là `ltt_video`.** Làm thế là lặp lại đúng
lỗi `ltt_llm`, và tệp test nói thẳng rằng gỡ nó ra sau này là *"một cuộc di trú,
không phải một lần đổi tên"* vì slug đã nằm trong các dòng `job_type` đã lưu.

---

## V-003 ✅ CHỐT (2026-09-04) — Giá bán = **2 × giá vốn theo giây** (đáp **ADR-2**)

**Biên lợi nhuận ×2 so với chi phí gốc tạo ra, tính theo giây sản xuất.**

Chốt này rõ. Phần dưới đây **không phải là sửa nó** — mà là viết ra *"giá vốn"
nghĩa là gì*, vì một con số ×2 không nói được nó nhân với cái gì, và chỗ mơ hồ
duy nhất ở đây đúng là chỗ đắt nhất.

### Ba khoản, và chỉ khoản đầu là hiển nhiên

```
giá vốn một video =  ① giây GPU chạy thật     × giá/giờ Pod
                  +  ② phần khởi động phân bổ  (boot + nạp model) / số job mỗi phiên
                  +  ③ phần cố định phân bổ    (storage tháng) / số video mỗi tháng
```

Khoản ② và ③ **phụ thuộc mức sử dụng**, mà mức sử dụng thì chưa biết lúc báo giá.
Một Pod bật 20 phút chạy 3 phút video: **17 phút phải nằm ở đâu đó**.

### Cách giải — giữ được cả ×2 lẫn D09 ("khách thấy giá ổn định")

1. **Giá công bố = `2 × giá_vốn_chuẩn`**, trong đó `giá_vốn_chuẩn` là **hằng số
   đã ĐO, có phiên bản, theo từng pipeline**, tính ở một mức sử dụng **được khai
   ra** (ví dụ *"≥ N video mỗi phiên Pod"*).
   Đúng khuôn đang chạy: `ltt-image-2026-08-24b`, `ltt-voice-2026-08-30a`,
   `ltt-vlm-2026-08-22` — giá nằm ở **một** tệp `gia.py`, có phiên bản, công bố
   ở `/gia-api`.
2. **Giá vốn THẬT ghi lại từng job** (`pod_billed_seconds`, giá/giờ lúc chạy,
   phần boot được phân bổ) → đây chính là nửa sau của D09. Sổ credit **đã có chỗ
   đựng**: `credit.SettlementResult` tách `provider_credit` khỏi `charged_credit`
   và có sẵn `variance` + `capped`.
3. **Trần thu = số đã báo cho khách.** Chi phí thật vượt thì nền tảng chịu — đó
   chính là nội dung của chữ *"giá ổn định"*. Khuôn có sẵn:
   `apps/taovideo/cost.py:91::customer_charge_cap`.
4. **Biên tụt thì bump PHIÊN BẢN GIÁ, không đổi giá lẻ từng job.** Ngưỡng cảnh
   báo vận hành: biên đo được trên một cửa sổ tụt dưới **×1,5**.

### 🔑 Và đây là chỗ ×2 biến thành một cổng GO/NO-GO có số

P08 trước đây chỉ so các workflow OSS **với nhau**. Với V-003 nó có một phép thử
dứt khoát:

> **Một pipeline chỉ đáng bán nếu `2 × giá_vốn_chuẩn` còn cạnh tranh được với giá
> mua ngoài cho một video tương đương.**

Mốc so sánh đã có sẵn trong kho: `apps/taovideo/cost.py` là mô hình giá của đương
kim, chạy thật, có hiệu chỉnh từ một job thật (`_CAL_TOKENS = 50638`).

⚠️ Và ngược lại: nếu `2 × giá_vốn_chuẩn` **đắt hơn** đi mua, thì với V-001 nó vẫn
có thể đáng làm cho **việc nội bộ** (giá vốn ×1) — nhưng **không đáng mở bán**.
Hai kết luận khác nhau, phải nói riêng, không được trộn.

### Còn một câu hỏi nhỏ chưa hỏi

Tài khoản của chính công ty có bị trừ credit theo giá ×2 không? Về tiền thì đó là
một khoản chuyển nội bộ nên không mất gì. Nhưng nó đổi **con số biên lợi nhuận
đọc được trên báo cáo**. `apps/qualitylab` có tiền lệ `credit_cost = 0` cho app
nội bộ. → gộp vào V-004.

---

## V-004 ✅ CHỐT (2026-09-04) — Mở **bề mặt nội bộ trước**, bán sau

> Chủ dự án duyệt cùng lúc với ADR-3: *"Duyệt như bạn khuyến nghị."*
>
> ⇒ `lttvideo` ra mắt `surface="admin"`, **P13 hoãn cả pha**, P12 co xuống một
> trang cho chính mình dùng. Tài khoản vận hành của công ty dùng ở **giá vốn**
> (không ×2); báo cáo biên tách hai cột *nội bộ* / *bán ngoài*.

Hệ quả trực tiếp của V-001, và là đòn bẩy lớn nhất cho *"tối giản chi phí đầu tư"*.

**Đề xuất:** V1 của `lttvideo` ra mắt với `surface="admin"` (hoặc `public=False`),
đúng khuôn `apps/qualitylab`. Lật sang `surface="customer"` khi — và chỉ khi —
V-003 chứng minh `2 × giá_vốn_chuẩn` còn cạnh tranh.

**Được gì:**

| | |
|---|---|
| P12 (GUI khách) | co từ *"dựng giao diện bán hàng"* xuống *"một trang cho chính mình dùng"* |
| P13 (public API) | **hoãn được cả pha** — không mở `LTT_PUBLIC_API_TOOLS` thì không có hợp đồng công khai nào phải giữ mãi |
| Rủi ro | không có khách nào chờ một pipeline chưa chín |
| Ngân sách | phần tiết kiệm ở P12/P13 đẩy sang P07/P08 — đúng chỗ cần đo |

**Mất gì:** doanh thu ngoài đến muộn hơn. Với V-001 (*"bán nếu dư"*) thì đó đúng
thứ tự ưu tiên chủ dự án đã nói.

⛔ Điều này **không** đụng D03 (vẫn đủ 4 mode) và **không** đụng D10 (vẫn một tier
Quality/Pro). Nó chỉ đổi **ai nhìn thấy**, không đổi **có cái gì**.

**Kèm theo — câu hỏi cuối của V-003:** đề xuất tài khoản vận hành của công ty
dùng `lttvideo` ở **giá vốn** (không ×2), và báo cáo biên tách hai cột *nội bộ* /
*bán ngoài*. Trộn hai loại vào một con số biên là tự nói dối mình.

---

## V-005 — Hai câu hỏi mà *"tối giản chi phí lâu dài"* mở ra
### ② đã được chủ dự án đóng 2026-09-04 (tối); ① vẫn ⏳ CHỜ ĐO (P03)

> ✅ **② THUÊ, không mua.** Chủ dự án chốt: *"máy B hiện tại đang max tải và mua
> card giá rất đắt không khả thi. Ta sẽ phải triển máy C là kế hoạch phát triển
> theo hướng đang xây dựng."*
>
> Hệ quả không nhỏ: C-CLOUD là **vĩnh viễn**, không phải một POC có thể vứt. Điều
> đó **đổi trọng số của ADR-3** và đã làm bản **v2** sửa cách trả nợ trùng lặp —
> tách `gateway_core/` **ngay từ đầu** thay vì chép rồi hẹn dọn. Xem
> `ADR_REMOTE_VIDEO_COMPUTE.md` §0.
>
> ✅ **① ĐÃ ĐÓNG bởi `V-008`** (2026-09-04): model chọn là Wan2.2 **A14B**, và
> README chính chủ đòi **≥80GB ngay cả khi đã bật offload** ⇒ **A100 80GB**, không
> có bậc 48GB nào để nhắm tới. Ngân sách thực: **~55 giờ GPU/tháng**, không phải 123.

V-001 nói **lâu dài**, mà D05/D06/D08 là các quyết định cho giai đoạn **R&D**.
Không mâu thuẫn — nhưng nếu không viết ra bây giờ thì sáu pha nữa sẽ không ai hỏi.

⛔ **P00 không tự đổi D05/D06/D08.** Đây là hai phép đo P03 phải trả lời, rồi
trình chủ dự án.

### ① Lớp GPU cho **sản xuất** — ~~ĐÃ THAY~~ bởi `V-008`. Giữ lập luận gốc:

D06 chốt A100 80GB, và cho **R&D** thì đó là lựa chọn hợp lý: dư VRAM nghĩa là
một thí nghiệm thất bại vì OOM không làm mất một lượt đo.

Nhưng ở trạng thái sản xuất ổn định, thứ quyết định là **$ mỗi video**, không phải
$ mỗi giờ. Giả thuyết P02/P03 phải kiểm bằng số thật: nhiều pipeline video mã
nguồn mở ở 480p/720p **có thể** chạy vừa trên card 24–48 GB rẻ hơn đáng kể mỗi
giờ. Nếu đúng, A100 80GB là **dư cho sản xuất** dù vẫn đúng cho R&D.

⇒ P03 báo cáo **$ mỗi video trên ít nhất hai lớp GPU**, không chỉ trên A100.

### ② Thuê hay mua? — ~~ĐÃ THAY~~ bởi chốt ở đầu mục. Giữ lập luận gốc để truy được lý do:

Chủ dự án **đã chạy GPU tại nhà** (B-LAN có RTX 3090 đang bán ảnh và LLM thật).
Nên "mua card" không phải một ý tưởng lạ ở đây — nó là mô hình đang vận hành.

P03 phải tính **điểm hoà vốn**: *bao nhiêu giờ GPU mỗi tháng thì mua rẻ hơn thuê*,
gồm cả điện, chỗ đặt, và giá trị còn lại. Không cần quyết bây giờ — nhưng con số
đó là thứ duy nhất biến *"tối giản chi phí lâu dài"* từ một mong muốn thành một
ngưỡng.

⭐ Và điều này ràng buộc ngược lại **ADR-3**: kiến trúc phải để việc *"chạy ở đâu"*
là một **quyết định triển khai**, không phải một **quyết định kiến trúc**. Đúng
điều mà `ltt_image` đang chứng minh hôm nay — `base_url` đọc từ biến môi trường,
nên cổng đó chạy ở LAN hay ở đâu khác là chuyện cấu hình.

---

## V-006 ✅ CHỐT (2026-09-04) — ADR-3 do Claude nghiên cứu và đề xuất

Chủ dự án giao lại. Đề xuất ở `docs/VIDEO_AI/ADR_REMOTE_VIDEO_COMPUTE.md`,
trạng thái **PROPOSED**, kèm `ARCHITECTURE_SCORECARD.csv` đã chấm.

⛔ Vẫn giữ D01: **không viết code kiến trúc tích hợp** cho tới khi chủ dự án gật
ADR-3. Đề xuất là đề xuất.

---

## V-007 ✅ CHỐT (2026-09-04) — C-CLOUD **được** giữ credential lưu trữ

**Chủ dự án:** *"Với S3 không ảnh hưởng bản chất, không lo lộ thông tin. Ta bỏ quy
tắc máy B không giữ bí mật nào của nền tảng đi."*

**Chốt:** worker trên C-CLOUD **được** cầm credential ghi thẳng vào R2. Không phải
xin presigned PUT cho từng tệp nữa.

### Vì sao nó thật sự tiện — không chỉ là bớt một bước

Với presigned PUT, **máy A phải biết trước có bao nhiêu tệp ra và tên là gì**.
Với ảnh thì dễ (xin 4 ảnh, cấp 4 vé). Với video thì không: một workflow có thể trả
video + khung xem trước + tệp mô tả, và số lượng phụ thuộc node lưu. Cầm credential
thì worker tự ghi bao nhiêu tuỳ nó.

### Hình dạng thi hành — R2 có sẵn thứ cần, dùng nó thì gần như không tốn gì

Đọc `developers.cloudflare.com/r2/api/s3/temporary-credentials/`: R2 có **temporary
access credentials** sinh từ một token cha, và tài liệu ghi rõ ba tính chất:

| | |
|---|---|
| **`ttlSeconds`** | *"Use short TTLs. A credential that lives for 15 minutes has a smaller blast radius than one that lives for a day."* |
| **Giới hạn theo đường dẫn** | *"Set paths and permission scope so the credential can only do what the caller needs."* |
| **Thu hồi dây chuyền** | *"If you revoke the parent API token, all temporary credentials derived from it stop working immediately."* |

⇒ Máy A (môi trường tin cậy) sinh credential **giới hạn ở tiền tố
`lttvideo/<user>/<job_id>/`**, TTL bằng trần thời gian job, đưa cho worker cùng
lời gọi. Worker ghi tự do **trong đúng ngăn đó, trong đúng khoảng đó**.

⭐ Đây không phải một điều kiện tôi thêm vào để giữ lại luật cũ — nó **rẻ hơn**
presigned PUT về mặt viết mã (một lời gọi thay vì N vé), và tài liệu R2 nói thẳng
*"Never ship your parent secret access key to a client. Local signing must happen
in a trusted environment (such as your backend)."* Tức đường này là đường hãng
khuyên, không phải đường vòng.

### Phạm vi — và một điểm cần nói rõ để sau này không ai đọc nhầm

Chủ dự án nói *"bỏ quy tắc"*, và nguyên tắc thì được bỏ. Nhưng **quy tắc đó nằm
trong Q102, và Q102 điều chỉnh MÁY B** — máy đang bán ảnh và LLM cho khách thật,
đang được D02 và gate **G-B** bảo vệ.

⇒ **Thi hành:** ① C-CLOUD giữ credential — có hiệu lực **ngay**, đây là chỗ quyết
định này có việc để làm. ② **Máy B: không đụng.** Cách presigned GET/PUT của nó
**đang chạy đúng**, đổi sang credential không được thêm gì, mà lại phải sửa
`render_gateway/storage_io.py` + `platform_core/image_gen/dieu_phoi.py` — tức phá
D02 để lấy về **không gì cả**.

⛔ Đây **không phải** tôi giữ lại luật cũ sau lưng. Nếu sau này có lý do thật để
đổi máy B (ví dụ cổng ảnh cũng cần ghi số tệp không đoán trước), thì làm — cùng
lúc với giai đoạn 2 của ADR-3, khi `render_gateway` vốn đã được mở ra.

### Thứ vẫn KHÔNG bao giờ rời máy A

Ranh giới hạ một bậc, không phải bỏ hẳn. C-CLOUD **không** nhận: mật khẩu
PostgreSQL · `LTT_TOKEN_ENCRYPTION_KEY` · khoá phiên · **token cha** của R2 ·
khoá API của các provider khác. Nó nhận **đúng một** credential tạm, giới hạn
tiền tố, có hạn.

---

## V-008 ✅ CHỐT (2026-09-04) — GPU: **A100 80GB**. Không tra cứu thêm.

**Chủ dự án:** *"Với các model hướng tới theo workflow xây dựng Wan 2.2 theo thông
số chất lượng tốt nhất ta phải dùng A100 đúng không? Đúng thì chốt máy luôn."*

**Trả lời: đúng.** Đọc README chính chủ `github.com/Wan-Video/Wan2.2`, và nó nói
ba lần, cho ba mode:

| Lệnh trong README | Yêu cầu |
|---|---|
| `--task t2v-A14B --size 1280*720` | *"can run on a GPU with at least **80GB VRAM**"* |
| `--task i2v-A14B --size 1280*720` | *"at least **80GB VRAM**"* |
| `--task s2v-14B --size 1024*704` | *"at least **80GB VRAM**"* |
| `--task ti2v-5B --size 1280*704` | *"at least **24GB VRAM** (e.g, RTX 4090)"* |

🔴 **Và con số 80GB đó ĐÃ BAO GỒM tiết kiệm bộ nhớ.** Cả ba lệnh trên đều chạy
kèm `--offload_model True --convert_model_dtype`. Tức 80GB không phải mức "chạy
thoải mái" — nó là mức **đã nén rồi**.

**A14B là bậc chất lượng**, TI2V-5B là bậc nén cao. Wan2.2 A14B là MoE hai chuyên
gia, tổng **27B tham số**, 14B hoạt động mỗi bước. *"Chất lượng tốt nhất"* = A14B
= **80GB**.

⇒ **CHỐT: A100 80GB.** D06 giữ nguyên, không phải xem lại.

### Điều này đóng luôn `V-005①` — và đóng theo hướng đắt hơn

`V-005①` hỏi *"lớp GPU cho sản xuất có phải cũng là A100 không"*, và tôi đã gọi
ngưỡng 48GB là **đòn bẩy chi phí lớn nhất còn lại** (2,23×: $150 mua được 123 giờ
thay vì 55 giờ). **Câu trả lời là không có đòn bẩy đó** — model chọn không vừa
48GB. Ngân sách thực tế:

```
$150 / tháng ÷ $2,72/giờ (RunPod serverless A100 80GB) = ~55 giờ GPU/tháng
```

P03 lập envelope theo con số này, không phải 123.

### ⭐ Và chốt A100 lại đúng cả về mặt phương pháp, không chỉ về mặt bắt buộc

`P07` yêu cầu *"chạy upstream nguyên bản trước mọi tối ưu"*. Có 80GB nghĩa là chạy
được **đúng cấu hình chính chủ, không lượng tử hoá** — tức đo được **trần chất
lượng thật** của Wan2.2. Một baseline chạy trên bản fp8 nén không trả lời được câu
*"model này giỏi tới đâu"*, nó chỉ trả lời *"bản nén này giỏi tới đâu"*.

### ⏳ Một đường giảm giá cho SAU NÀY — ghi ra để không quên, KHÔNG mở lại quyết định

README Wan2.2 tự nhắc: DiffSynth-Studio hỗ trợ Wan 2.2 với *"low-GPU-memory
layer-by-layer offload, FP8 quantization"*; và ComfyUI (baseline D04) có bản fp8
của A14B mà cộng đồng chạy trên card nhỏ hơn nhiều.

⛔ **Đây là việc của P08/P09, không phải lý do để tra cứu thêm bây giờ.** Trình tự
đúng là: chạy bf16 trên A100 để có trần chất lượng (**P07**) → rồi mới hỏi *"bản
fp8 mất bao nhiêu chất lượng để đổi lấy 2,23× chi phí"* (**P08**). Hỏi ngược lại
là tối ưu một thứ chưa từng chạy — đúng điều `GLOBAL_RULES` cấm.

---

## V-009 — Đóng gói workflow dạng **API format đã làm phẳng**, không đóng gói tệp template dạng UI

**Chốt 2026-09-04. Căn cứ: đo trên chính tệp đã ghim, không suy luận.**

`P02` để lại một câu hỏi mở và gọi nó là "chỗ phải xác minh ở P06": template
T2V/I2V dùng **subgraph**. Đo ngày 04/09 trên `video_wan2_2_14B_t2v.json` tại tag
`v0.11.55`:

| | |
|---|---|
| Node ở cấp 1 | **4** — `MarkdownNote`, `SaveVideo`, và một node có `type` là UUID `cb63cc72-…` |
| `definitions.subgraphs` | **1**, tên `Text to Video(Wan2.2)` |
| Node **thật** bên trong | **30** |

⇒ Mã nào duyệt `workflow["nodes"]` để tìm node theo tên sẽ thấy **bốn** node và
không thấy cái nào nó cần — rồi **thất bại im lặng**, trả về một workflow không
đổi tham số nào. Không lỗi, không cảnh báo, chỉ là video sai tham số.

### Quyết định

**Không bao giờ đóng gói tệp template dạng UI vào image.** Đóng gói bản **API
format đã làm phẳng**, sinh một lần, ghim trong kho.

⭐ Lý do không phải tiện lợi mà là **tính xác định**. Bộ thực thi của ComfyUI
(`/prompt`) không có khái niệm subgraph, nên việc làm phẳng **phải** xảy ra ở đâu
đó. Để nó xảy ra lúc build thì ta kiểm tra được; để nó xảy ra lúc chạy thì ta phụ
thuộc vào một hành vi của frontend thay đổi theo từng phiên bản — và ta ghim
ComfyUI `v0.34.0` chứ không ghim frontend của người dùng.

### Phép kiểm đi kèm (dải 700–799)

Mỗi chỗ đánh dấu tham số (`@ten`) phải giải được ra **đúng một** node trong bản
API format. Không giải được ⇒ **gate đỏ**, không phải **video sai**.

⛔ Đây là cùng lớp với bài học `render_gateway/workflows.py`: chỗ thay tham số là
chỗ hỏng âm thầm nhất, vì đầu ra vẫn là một JSON hợp lệ.

---

## V-010 — Sản xuất bằng **fp16/bf16**, không bằng fp8. LoRA 4 bước giữ lại làm **bậc nháp**

**Chốt 2026-09-05, sau khi chủ dự án bác lập luận trước đó của tôi.**

### 🔴 Lỗi tôi mắc, ghi ra vì nó là một lỗi về **cách suy**, không phải về dữ kiện

Tôi đọc đúng: template chính chủ **mặc định** `fp8_scaled` + 4 bước. Rồi tôi suy:
*"cộng đồng mặc định fp8 ⇒ ta dùng fp8"*. Bước suy đó sai.

**Vì sao template mặc định fp8** thì chính tài liệu ComfyUI nói thẳng — và tôi đã
đọc câu đó rồi vẫn không rút ra kết luận đúng:

> *"By default, a relatively small size is set to prevent low VRAM users from
> consuming too many resources. If you have enough VRAM, you can try a resolution
> around 720P."*

fp8 + 640×640 + 4 bước là **mặc định cho card 24GB phổ thông**. Ta thuê **80GB**.
Ràng buộc ép cộng đồng chọn fp8 **không áp lên ta**.

⭐ Và điều đáng nhớ hơn: **cộng đồng CÓ đưa bậc chất lượng, tôi trích nhầm bậc.**
Ngay trong `video_wan2_2_14B_fun_control.json` có hai nhánh song song:

```
KSamplerAdvanced   4  buoc, cfg 1.0     <- toi bao cao cai nay
KSamplerAdvanced   20 buoc, cfg 3.5     <- va bo qua cai nay
```

⛔ Bài học cho phiên sau: *"đi theo cộng đồng"* không có nghĩa là **lấy giá trị
mặc định**. Giá trị mặc định của một dự án mã nguồn mở được chọn cho **người dùng
đông nhất của nó**, không cho ràng buộc của ta. Phải đọc **vì sao** nó mặc định
như thế trước khi chép con số.

### Hai trục tôi đã gộp làm một

| Trục | Bậc nhanh | Bậc chất lượng |
|---|---|---|
| **A. Độ chính xác trọng số** | fp8_scaled 13,31 GB/chuyên gia | **fp16/bf16 26,61 GB** |
| **B. Số bước + CFG** | 4 bước, cfg 1 (LoRA chưng cất) | **20–40 bước, cfg 3,5** |

Trục **B** là đòn bẩy chất lượng lớn hơn. Cắt 40 bước xuống 4 là một đánh đổi
sâu, và nó tồn tại để chạy được trên card yếu.

### Quyết định

**Nạp fp16/bf16 làm mặc định sản xuất.** Giữ **4 LoRA `lightx2v`** (4,57 GB) để
có bậc nháp.

⭐ **Không cần tải bản fp8.** LoRA áp lên nền fp16 được — bậc nháp là *fp16 + LoRA
4 bước*, không phải *fp8 + LoRA*. Tiết kiệm ~80 GB và bỏ hẳn một trục biến thiên.

| Bậc | Kích thước | Bước | cfg | Lượt truyền | A100 | Giá vốn | Bán ×2 (5 s) |
|---|---|---|---|---|---|---|---|
| **Nháp** | 640×640 | 4 | 1,0 | 4 | ~1–2 phút | $0,07 | ~3.600 đ |
| **Cân bằng** | 640×640 | 20 | 3,5 | 40 | ~6,5 phút | $0,30 | ~15.600 đ |
| **Chất lượng** | 1280×720 | 20 | 3,5 | 40 | ~23 phút | $1,04 | ~54.000 đ |
| *Trần tham chiếu* | 1280×720 | 40 | 3,5 | 80 | ~46 phút | $2,08 | ~108.000 đ |

Suy từ bảng đo chính chủ (A100 1 GPU: 480P 785,7 s · 720P 2 735,7 s, ở 80 lượt
truyền). ⛔ **Ước tính** — bảng gốc chạy có `--offload_model`, ta không cần offload
trên 80GB nên số thật có thể **thấp hơn**. `Đ2` thay được cả khoảng này.

### Ba thứ quyết định này kéo theo

**1. ⛔ Rút lại đề xuất hạ volume xuống 150 GB.** BOM fp16 = **175,08 GB**.
**300 GB là đúng**, còn trống 124,9 GB. Đây là **lần thứ hai** con số chủ dự án
chốt đúng hơn con số tôi tính (lần đầu: 275 vs 300 GB).

**2. ✅ `V-008` (A100 80GB) đứng vững, và giả thuyết L40 48GB CHẾT.** Đỉnh VRAM đo
được ở 720P là **59,8 GB** — không vừa 48 GB. Nếu đích là chất lượng tốt nhất thì
**80GB là bắt buộc**, đúng như đã chốt.

**3. `P08` sống lại nhưng đổi câu hỏi.** Không còn là *"so mù bf16 vs fp8"* (ta
không chạy fp8 nữa) mà là *"mỗi bậc tốn bao nhiêu, được chất lượng nào"* — và
`KE_HOACH_DO_LUONG.md` đã có VBench để trả lời bằng số thay vì bằng mắt.

### ⚠️ Con số phải nói kèm

$18,50 khả dụng = **6,8 giờ GPU**. Ở bậc **Chất lượng** (~23 phút/video) đó là
**~17 video**; ở bậc Nháp là ~250. Chọn bậc sản xuất **là** chọn số video làm
được trong tháng.

---

## V-011 — ⭐ **LUẬT XÂY DỰNG BẮT BUỘC: đi tìm tài liệu cộng đồng trước, tự suy sau cùng**

**Chủ dự án chốt 2026-09-05, thành luật của chương trình, không phải lời khuyên.**

> *"Sử dụng workflow, pipeline từ cộng đồng xây sẵn được đánh giá tối ưu nhất để
> ta áp dụng, hạn chế tự suy 100 % thay vào đó là tìm tài liệu xây dựng từ cộng
> đồng. Đây phải là quy tắc xây dựng bắt buộc."*

### Vì sao thành luật — hai lần trong hai ngày

| Ngày | Tôi tự suy | Sự thật cộng đồng | Cái giá |
|---|---|---|---|
| 04/09 | 220,8 GB bf16 cho V1 | template chính chủ ghi rõ từng tệp | suýt nạp thừa 130 GB |
| 05/09 | *"cộng đồng mặc định fp8 ⇒ dùng fp8"* | mặc định ấy dành cho card 24GB, và bậc 20 bước nằm **ngay trong cùng tệp** | suýt sản xuất ở chất lượng thấp hơn phần cứng cho phép |

⭐ Lần thứ hai đáng sợ hơn lần đầu: tôi **có** tài liệu trong tay, **đã đọc** đúng
câu giải thích, và vẫn rút ra kết luận ngược. Nên luật này không phải *"nhớ tra
cứu"* — mà là *"tra cứu **vì sao**, đừng chỉ chép **cái gì**"*.

### Bốn điều khoản — kiểm được, không phải khẩu hiệu

**① Trước mỗi hạng mục kỹ thuật, phải trả lời được ba câu, bằng đường dẫn:**

```
1. Cộng đồng đã giải bài này chưa?   -> kho nào, bao nhiêu sao, cập nhật lần cuối
2. Bản được dùng nhiều nhất là gì?   -> lượt tải / sao / là bản chính chủ?
3. Nó mặc định như thế VÌ SAO?       -> trích câu giải thích, không chỉ trích giá trị
```

Không trả lời được câu **3** thì **chưa được chép giá trị đó**.

**② Mặc định của dự án mã nguồn mở được chọn cho người dùng ĐÔNG NHẤT của nó,
không cho ràng buộc của ta.** ComfyUI mặc định fp8 + 640×640 vì phần lớn người
dùng có 24GB. Ta thuê 80GB. ⇒ Chép mặc định mà không đọc lý do là **thừa hưởng
ràng buộc của người khác**.

**③ Lệch khỏi đường cộng đồng thì phải GHI RA, kèm lý do và nguồn.** Ví dụ đang
có trong `MODEL_BOM_V1.csv`: *"CO Y KHAC TEMPLATE: template goi ban
fp8_e4m3fn_scaled vi no nham card 24GB. Ta co 80GB nen lay ban fp16."* Một dòng
lệch không ghi lý do là một dòng phiên sau sẽ "sửa lại cho đúng template".

**④ Không lấy được thì nói thẳng là KHÔNG CÓ, đừng tự chế rồi gọi là chuẩn.**
Nếu cộng đồng không có lời giải cho một câu hỏi thì hoặc bỏ câu hỏi đó khỏi V1,
hoặc ghi rõ *"phần này ta tự dựng, không có tiền lệ"* — để phiên sau biết chỗ nào
đứng trên đá và chỗ nào đứng trên cát.

### Áp vào chính lúc này — bốn nguồn đã tra, kèm kết luận

| Nguồn | Uy tín | Ta lấy gì |
|---|---|---|
| `Comfy-Org/workflow_templates` v0.11.55 | chính chủ ComfyUI, MIT | **hình dạng đồ thị**, sampler, số khung, cấu trúc hai chuyên gia |
| `Wan-Video/Wan2.2` `wan/configs/*` | **tác giả model** | **bước, cfg, shift** — cấu hình tác giả khuyến nghị |
| `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` | 4,9 triệu lượt tải | **trọng số fp16** |
| `kijai/ComfyUI-WanVideoWrapper` | 6.682 ★, Apache-2.0 | ⛔ **KHÔNG dùng** — xem dưới |

⛔ **Vì sao loại `WanVideoWrapper` dù nó nhiều sao hơn** (điều khoản ③ buộc ghi):
`pushed 2026-05-24`, tức **hơn ba tháng** không cập nhật, trong khi template chính
chủ cập nhật **cùng ngày** ta tra. Và đường native chạy **0 custom node** cho cả
ba mode — một ưu thế vận hành lớn hơn mọi tính năng nó thêm. Nếu sau này cần một
tính năng chỉ nó có thì mở lại quyết định này, đừng lặng lẽ thêm.

---

## V-012 — **Một đường duy nhất: fp16, 720P, cấu hình tác giả. Không có bậc thấp hơn.**

**Chủ dự án chốt 2026-09-05:**

> *"Hệ thống của ta chỉ tồn tại 1 đường duy nhất là mạnh nhất so với cấu hình
> máy, không cần model yếu hơn làm fallback. Mặc định và duy nhất là fp16."*
> *"Fix với A100 không cần test hay suy luận để tìm card vram thấp nữa, cần loại
> khỏi plan tránh tốn công."*

### Cái bị GỠ khỏi kế hoạch — gỡ hẳn, không để lại như "tuỳ chọn"

| Gỡ | Vì |
|---|---|
| Ba bậc Nháp / Cân bằng / Chất lượng | một đường duy nhất |
| 4 LoRA `lightx2v_4steps` (4,57 GB) | chưng cất 40 bước → 4 là **hạ chất lượng** để chạy card yếu |
| Mọi trọng số `fp8_scaled` | fp16 là mặc định **và duy nhất** |
| L40 48GB, và mọi phép đo tìm card VRAM thấp | `A100 80GB` **cố định**, không tra cứu thêm |
| `P08` so bậc | không còn bậc để so |

### Cấu hình sản xuất — **một** bảng, và mỗi dòng ghi nguồn

| Tham số | Giá trị | Nguồn |
|---|---|---|
| Trọng số | **fp16/bf16** | `Wan_2.2_ComfyUI_Repackaged` |
| Text encoder | **`umt5_xxl_fp16`** (10,59 GB) | *cố ý khác template* (template lấy fp8 vì card 24GB) |
| VAE | `wan_2.1_vae` | template — kho **Wan2.1**, không phải 2.2 |
| Kích thước | **1280×720** | giới hạn trên mà A14B hỗ trợ; ComfyUI docs: *"If you have enough VRAM, you can try a resolution around 720P"* |
| Số khung · fps | **81 · 16** ⇒ 5,06 s | `wan_shared_cfg.frame_num = 81` |
| **Số bước** | **40** | `t2v_A14B.sample_steps = 40` — **cấu hình tác giả**, không phải bản chưng cất |
| **cfg** | T2V **(3,0 cao / 4,0 thấp)** · I2V **3,5** | `sample_guide_scale` của tác giả |
| **shift** | T2V **12,0** · I2V **5,0** | `sample_shift` của tác giả ⚠️ template dùng 5,0 cho T2V vì đó là số của **đường chưng cất** |
| Sampler / scheduler | euler / simple | template |
| Chia hai chuyên gia | nửa/nửa (0→20, 20→40) | cấu trúc template (`fun_control` bậc 20 bước chia 0→10, 10→10000) |
| LoRA | **không có** | `V-012` |
| GPU | **A100 80GB**, dự phòng **H100 NVL 94GB** | ⭐ dự phòng chỉ được **mạnh hơn**, không bao giờ yếu hơn |

⭐ Ba dòng in đậm (**bước, cfg, shift**) là chỗ đường của ta **rời khỏi template
ComfyUI để về đúng cấu hình của tác giả model** — vì template ComfyUI mã hoá các
số của đường chưng cất 4 bước. Đây là điều khoản ③ của `V-011` áp dụng ngược:
lệch khỏi cộng đồng ComfyUI **để bám sát cộng đồng gốc là Wan-Video**.

### ⭐ Một đòn bẩy chất lượng nữa, chính tác giả khuyến nghị: **mở rộng prompt**

`README` của Wan2.2:

> *"Extending the prompts can effectively enrich the details in the generated
> videos, further enhancing the video quality. **Therefore, we recommend enabling
> prompt extension.**"*
> T2V: `Qwen2.5-14B/7B/3B-Instruct` · I2V: `Qwen2.5-VL-7B/3B-Instruct`

⇒ Đưa vào V1, và **không tốn một giây GPU thuê**: nền tảng đã có sẵn đúng khuôn
này cho sinh ảnh — `platform_core/image_gen/prompt_dich` + `dich_gemini` đi qua
`api_pool` (`D-027`). Dựng lại cùng dạng cho video.

⛔ **Không** dùng `apps/ltt_llm` trên máy B: ranh giới `P00` cấm V1 chạm B-LAN, và
`api_pool` đã đủ.

### Cái giá phải nói thẳng

| | |
|---|---|
| Thời gian/video (A100, 720P, 40 bước) | **~46 phút** *(ước từ bảng đo chính chủ: 2 735,7 s)* |
| Giá vốn/video 5,06 s | **~$2,08** ⇒ bán ×2 ≈ **108.000 đ** |
| $18,50 khả dụng | **~9 video** |

⚠️ Bảng đo gốc chạy có `--offload_model`; trên 80GB ta **không cần offload**, nên
số thật có thể thấp hơn đáng kể. `Đ2` đo một lượt là biết.

⛔ Và đây là đánh đổi chủ dự án đã chọn có ý thức: **chất lượng tối đa, ít video
hơn**. Đừng có phiên nào "tối ưu" bằng cách lén hạ bước hay thêm LoRA.

---

## V-013 — **20 bước + H100 trước A100**: nhanh hơn 5,2 lần, rẻ hơn 3,5 lần, **không hạ chất lượng**

**Chốt 2026-09-05, sau khi chủ dự án nghi ngờ con số 46 phút.**

> *"Ý bạn nói wan 2.2 workflow tạo 1 video 5,06s sẽ mất 46 phút à??? Tôi nghi ngờ
> bạn nhầm thông số... time sản xuất như vậy cũng không hợp lý cho công việc."*

### Con số 46 phút **đúng** — nhưng nghi ngờ vẫn đúng chỗ

Tra hai issue trong chính kho `Wan-Video/Wan2.2`:

| Issue | Nội dung |
|---|---|
| [#39](https://github.com/Wan-Video/Wan2.2/issues/39) | H100, 720P: bảng nói **1.041 s**, chạy thật **1.600 s**. *"But I use FA2 instead of FA3."* |
| [#88](https://github.com/Wan-Video/Wan2.2/issues/88) | H800, 720P, video 5 giây: **1.600 s**. Trả lời cộng đồng: *"so u need more gpus"* |

⇒ Bảng chính chủ đo bằng **FlashAttention-3**, mà FA3 **chỉ chạy trên Hopper**.
A100 là Ampere — **không bao giờ** chạm được mức đó. Số của tôi nếu sai thì sai
về phía **lạc quan**.

### 🔴 Lỗi thật: chọn nhầm cấu hình, không nhầm con số

Tôi lấy `sample_steps = 40` từ `wan/configs/wan_t2v_A14B.py`. Đó là mặc định của
**bản tham chiếu nghiên cứu**, không phải cấu hình ai đó thật sự chạy để sản xuất.

⛔ **`V-011` bị vi phạm lần thứ hai, ở một dạng tinh vi hơn:**

```
lan 1 (V-010):  chep mac dinh cua ComfyUI      -> nham card 24GB pho thong
lan 2 (V-013):  chep mac dinh cua TAC GIA      -> nham bai bao tham chieu
```

⭐ Cả hai đều **trông giống** "đi theo cộng đồng" nếu chỉ hỏi *"ai viết ra nó"*.
Chỉ khi hỏi *"ai **CHẠY** nó để sản xuất"* mới ra câu trả lời đúng — và câu trả
lời ấy nằm ngay trong tệp tôi đã đọc: `fun_control` ship **hai** nhánh, và nhánh
chất lượng của ComfyUI là **20 bước, cfg 3,5**, không phải 40.

⇒ Bổ sung cho `V-011` điều khoản ①: câu hỏi thứ ba không chỉ là *"nó mặc định
thế vì sao"* mà còn là **"mặc định này phục vụ ai — người dùng phổ thông, người
viết bài báo, hay người sản xuất?"**

### 🔑 Và một phát hiện ngược trực giác: **H100 vừa nhanh hơn vừa rẻ hơn A100**

```
nhanh hon  2,63 lan   (720P: 1.041,5 s vs 2.735,7 s — bang comp_effic)
dat hon    1,53 lan   ($0,00116 vs $0,00076 moi giay)
=>  moi VIDEO re hon  1,72 lan
```

Đúng ở **mọi** độ phân giải và mọi số bước, vì cả hai đều là hệ số nhân.

⛔ **Không trái lệnh *"fix A100, thôi tra card VRAM thấp"*:** H100 NVL là **94 GB**,
**mạnh hơn** A100 80GB. Đây là nâng cấp, không phải hạ cấp — và A100 vẫn nằm
trong `gpuTypeIds` làm đường lui, nên không mất gì.

### Kết quả

| | `V-012` (40 bước, A100) | **`V-013` (20 bước, H100)** |
|---|---|---|
| Thời gian video 5,06 s | 45,6 phút | **8,7 phút** |
| Giá vốn | $2,08 | **$0,60** |
| Video 10 s (nối 2 đoạn) | 91 phút | **17,4 phút** |
| Giây GPU cho 1 giây video ra | 540 | **103** |
| $18,50 khả dụng đổi được | ~9 video | **~30 video** |

Vẫn là **fp16 · 1280×720 · không LoRA** — đúng `V-012`. Hai thứ đổi đều làm nhanh
hơn **mà không hạ chất lượng**: một card mạnh hơn, và bỏ 20 bước thừa mà chính
ComfyUI cũng không dùng.

### ⚠️ Vẫn chậm hơn dịch vụ thương mại — nói thẳng vì sao

Seedance/Kling ra video 5 s trong 1–3 phút. Ba lý do, đều có nguồn:

1. **Nhiều GPU cho một video.** Bảng chính chủ: 720P trên A100 giảm 2.736 s → 725 s
   với 4 GPU. ⛔ Đường ComfyUI native **không có** song song chuỗi (FSDP+Ulysses
   chỉ có ở bản tham chiếu), nên ta **không dùng được** đòn bẩy này.
2. Model **đã chưng cất** — đúng thứ `V-012` gỡ để giữ chất lượng.
3. Hạ tầng phục vụ tối ưu riêng.

⇒ Đánh đổi thật: **8,7 phút ở fp16/720P/20 bước**, hoặc ~1,7 phút ở bản chưng cất
8 bước. Chủ dự án đã chốt hướng chất lượng; con số 8,7 phút là giá của hướng đó
sau khi đã vắt hết những gì không phải đánh đổi.

⚙️ Cấu hình sống ở `platform_core/video_gen/cau_hinh_san_xuat.py`, `test_712` canh —
kể cả phép tính "H100 rẻ hơn 1,72 lần", để con số trong chú thích không trôi khỏi
sự thật.

---

## V-014 — **MỘT nguồn duy nhất: ComfyUI native + SageAttention.** Không thử nhiều workflow.

**Chủ dự án chốt 2026-09-05:**

> *"Không nên test nhiều workflow mà chỉ chọn của 1 nguồn chuẩn và có xác thực tối
> ưu để xây dựng."*

### Hai ứng viên, và tiêu chí quyết định không phải tốc độ

| | **ComfyUI native + SageAttention** | TurboDiffusion |
|---|---|---|
| Phủ ba mode V1 | ✅ T2V · I2V · V2V | ❌ **chỉ I2V** cho Wan2.2 A14B |
| Trưởng thành | template cập nhật **cùng ngày** tra cứu | *"checkpoints and paper are **not finalized**"* |
| Custom node | **0** | không phải ComfyUI — **stack riêng** |
| Tăng tốc có xác thực | SageAttention: ICLR2025 · ICML2025 · NeurIPS2025 Spotlight, *"without losing accuracy"*, Apache-2.0 | ✅ SageAttention + SLA + rCM |
| Thời gian công bố | ❌ không ai công bố | ✅ **4.549 s → 38 s** (120×) |
| Có chưng cất không | **không** | **có** (rCM) — trái `V-012` |

⭐ TurboDiffusion thắng ở đúng **một** tiêu chí — có số công bố — và thua ở tiêu
chí quyết định: **nó không làm được 2 trong 3 mode của V1.**

⛔ **Một nguồn không phủ hết phạm vi thì không phải "một nguồn"** — nó là hai
nguồn trá hình, và ta sẽ phải dựng hai stack, đo hai lần, bảo trì hai đường.
Đúng thứ chủ dự án vừa cấm.

### Chốt

**Nguồn duy nhất:**

```
pipeline    Comfy-Org/workflow_templates  v0.11.55 / bffc534e   (MIT)
runtime     comfyanonymous/ComfyUI        v0.34.0  / 12d52794   (GPL-3.0)
trong so    Comfy-Org/Wan_2.2_..._Repackaged  c4f60d30          (Apache-2.0)
tang toc    --use-sage-attention          (co san trong ComfyUI, cli_args.py:150)
```

🔑 **`--use-sage-attention` là một CỜ, không phải một nhánh.** Không custom node,
không đổi workflow, không đổi trọng số, không đổi mode nào. Chạy được trên
**Ampere, Ada và Hopper** — tức cả A100 lẫn H100. Đây là lý do nó **không** vi
phạm *"một đường duy nhất"*: nó không tạo ra đường thứ hai.

⛔ **`P08` (so nhiều lựa chọn) chết hẳn, lần thứ ba và lần cuối.** Chuỗi mới
không có pha nào so sánh. Nếu một pha phát hiện nguồn sai thì nó **dừng và trình
chủ dự án**, không tự mở nhánh thứ hai.

### TurboDiffusion — đường lui đã khảo sát, ghi ra để không phải tra lại

Mở lại quyết định này **khi và chỉ khi** cả hai điều sau đúng:

1. Họ phát hành `TurboWan2.2-**T2V**-A14B` (nay chỉ có I2V);
2. README bỏ dòng *"not finalized"*.

Số của họ đáng nhớ: `TurboWan2.2-I2V-A14B-720P` đi từ **4.549 s xuống 38 s** trên
**một RTX 5090**. Con số gốc 4.549 s cũng là một phép đối chứng độc lập cho thang
đo của ta (2.736 s trên A100) — nên nếu sau này ai nghi ngờ bảng thời gian, đây là
nguồn thứ hai.

⚠️ Và 38 s là *"E2E diffusion latency, **excluding text encoding and VAE
decoding**"* — cộng thêm ~10–30 s nữa mới là thời gian thật.

### 🔴 Điều tôi KHÔNG biết, và sẽ không gõ một con số cho nó

**SageAttention tăng tốc bao nhiêu end-to-end cho Wan2.2 trên ComfyUI.** "2–5×"
là số cho riêng phép attention, không phải cho cả lượt. Không nguồn nào công bố
số end-to-end cho đúng đường này.

⇒ Đó là câu hỏi của `Đ2`, và là **lý do duy nhất còn lại** để đốt GPU thuê.

---

## V-015 — Bộ làm phẳng subgraph là phần **ta tự dựng**, và tôi nói thẳng như vậy

**Chốt 2026-09-05.** `V-011` điều ④: *cộng đồng không có lời giải thì nói thẳng
là KHÔNG CÓ, đừng tự chế rồi gọi là chuẩn.*

### Đã tra, và thật sự không có

| Tra gì | Kết quả |
|---|---|
| `Comfy-Org/workflow_templates` có bản API format? | **Không** — chỉ có bản UI |
| Backend ComfyUI làm phẳng subgraph? | **Không**. `app/subgraph_manager.py` chỉ nạp *blueprint* từ custom node; `execution.py` có `has_subgraph` nhưng đó là node **tự nở ra lúc chạy**, việc khác hẳn |
| Có kho công cụ chuyển đổi? | **Không đáng dùng** — cao nhất 2 sao |

⇒ Việc làm phẳng nằm ở **frontend**, trong JavaScript, chạy khi bấm
*"Export (API)"*. Worker không có trình duyệt.

### Nên ta tự dựng, và bù bằng hai thứ

**① `test_714` — 19 phép kiểm**, mỗi cái chốt một bất biến **đã suýt sai**, không
phải một hành vi tưởng tượng.

**② Worker đối chiếu với `/object_info` THẬT lúc khởi động.** Thứ tự widget của
một `class_type` là thứ **chỉ ComfyUI đang chạy mới biết**; tệp UI lưu chúng dưới
dạng **mảng theo vị trí**. ⛔ Đoán thứ tự đó offline là cách gán `height` vào
`width` mà không có gì báo — video vẫn ra, chỉ là sai.

### ⭐ Hai bộ chặn đã THỰC SỰ NỔ, và cả hai lần đều đúng

Tôi viết `lam_phang` theo cấu trúc đo trên `t2v`, kèm hai giả định có bộ chặn.
Cả hai giả định **sai với `i2v`**, và bộ chặn bắt được — thay vì vứt đi trong im
lặng đúng hai thứ quý nhất:

| Bộ chặn nổ | Thứ nó cứu |
|---|---|
| *"không có gì từ ngoài đẩy vào ranh giới"* | **ảnh đầu vào của khách** — mất nó thì I2V lặng lẽ thành T2V |
| *"thẻ gọi subgraph không có `widgets_values`"* | **12 giá trị**: prompt của khách, 640×640, seed, tên bốn model, clip, vae |

⭐ Đây là lý do viết giả định thành **bộ chặn** thay vì thành **chú thích**. Một
chú thích sai thì im lặng; một bộ chặn sai thì nổ.

### Hai cái bẫy trong chính phép biến đổi

**1. Thứ tự `inputs` của thẻ gọi KHÔNG trùng thứ tự `sg['inputs']`.** Đo trên
`t2v`: thẻ gọi bắt đầu bằng `value`, ranh giới bắt đầu bằng `text` (`value` là
slot 3). Ghép theo **chỉ số** là nối nhầm dây mà đồ thị vẫn hợp lệ ⇒ ghép theo
**tên**.

**2. `widgets_values` đi theo thứ tự SLOT RANH GIỚI, bỏ qua slot đã bị dây
chiếm** — không theo thứ tự `inputs` của thẻ gọi. `i2v` có **13** slot và thẻ gọi
chỉ liệt kê **8** input; dùng nhầm danh sách là lệch toàn bộ 12 giá trị.

### Kết quả đo

```
t2v          cap 1:  4 node  ->  phang: 33   (0 widget day len)
i2v          cap 1:  5 node  ->  phang: 34   (12 widget day len)
fun_control  cap 1: 44 node  ->  phang: 44   (von da phang)
```

⭐ `fun_control` **vốn đã phẳng** — nên nếu chỉ nhìn mode V2V thì cả lớp lỗi này
không tồn tại. Đó là một lời nhắc: một phép kiểm chạy trên **một** mode không nói
gì về hai mode kia.

---

## V-016 — **CUDA 12.8, không phải 12.4.** Một dòng `--index-url` đã âm thầm tắt `V-012`

**Ngày:** 2026-09-05 · **Trạng thái:** ✅ CHỐT · **Đổi:** `video_gateway/Dockerfile`,
`minCudaVersion` của endpoint (12.0 → 12.8)

### Việc đã xảy ra

`Dockerfile` ghim `--index-url https://download.pytorch.org/whl/cu124`. Đo ngày
05/09 trên chính các chỉ mục đó, cho `cp310`:

| chỉ mục | bản torch cao nhất còn phục vụ |
|---|---|
| `cu124` | **2.6.0** |
| `cu126` | 2.14.0 |
| `cu128` | 2.11.0 |

Còn trong `comfy/model_management.py` ở **đúng commit ta ghim**
(`12d52794`):

```python
def extended_fp16_support():
    if torch_version_numeric < (2, 7):
        return False
```

⇒ Pin `cu124` nghĩa là torch ≤ 2.6 nghĩa là **fp16 mở rộng tắt** — đúng con
đường mà `V-012` chốt là *"mặc định và duy nhất"*, sau khi chủ dự án nói thẳng:
*"Hệ thống của ta chỉ tồn tại 1 đường duy nhất là mạnh nhất so với cấu hình máy…
Mặc định và duy nhất là fp16."*

### Vì sao không ai thấy

🔴 **Triệu chứng không mang tên nó.** Không log nào in chữ `fp16`. Không tham số
nào của ta sai. `cau_hinh_san_xuat.DO_CHINH_XAC == "fp16"` vẫn xanh, `MODEL_BOM_V1.csv`
vẫn toàn fp16, `test_712` vẫn xanh, và **cả 25 hạng mục chấm đều đạt**. Quyết định
bị vô hiệu ở tầng **ảnh Docker** — tầng duy nhất không phép kiểm nào nhìn tới.

⭐ Và lý lẽ biện minh cho pin thấp thì **đã chết mà không ai gỡ**. Chú thích cũ
ghi: *"đặt CUDA thấp để không tự loại bớt máy — chạy được cả Ampere (A100) lẫn
Hopper (H100)"*. `V-013` đã bỏ A100; danh sách GPU của endpoint giờ chỉ có ba
loại H100. Không còn máy nào để "không loại bớt", nên cái giá phải trả không mua
được gì nữa. **Một chú thích đúng lúc viết đã trở thành một lời biện minh sai.**

### Đối chứng độc lập (`V-011`: cộng đồng trước, tự suy sau)

Ảnh **chính chủ RunPod** trong danh mục template: `runpod/comfyui:cuda12.8` và
`runpod/comfyui:1.4.7-cuda13.0`; ảnh PyTorch của họ là cu128/cu130. Không ai chạy
ComfyUI đời này trên cu124.

### Chốt

| | |
|---|---|
| ảnh nền | `nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04` |
| chỉ mục torch | `https://download.pytorch.org/whl/cu128` |
| `minCudaVersion` | **12.8** (đã PATCH lên endpoint, HTTP 200) |

⚠️ `requirements.txt` của ComfyUI khai `torch` **trần** (không cận dưới). Cài
torch trước từ một chỉ mục rồi mới `-r requirements.txt` ⇒ pip thấy đã thoả và
**không nâng cấp**. Nghĩa là bản torch cuối cùng do dòng `--index-url` quyết,
**không** do ComfyUI quyết.

### Canh gác

`tests/test_716_anh_worker.py` chốt bốn mệnh đề, tất cả **không gọi mạng** (đọc
số đo trong `docs/VIDEO_AI/COMFYUI_NODES.json`, do
`tools/video_ra_soat.py sinh-so-node` ghi từ thượng nguồn):

1. trần torch của chỉ mục ≥ cận dưới ComfyUI đòi;
2. `FROM nvidia/cuda:X.Y` cùng dòng CUDA với `--index-url cuXY`;
3. không cài tuỳ chọn mà truyền cờ bắt buộc;
4. tiến trình con phải bị hứng đầu ra.

Đã tự kiểm: cho phép kiểm (1) đọc bản `Dockerfile` **cũ** ⇒ nó **đỏ**. Một phép
kiểm chưa từng đỏ là một phép kiểm chưa biết có canh gì không.

⛔ Và một **đính chính** với chính tôi. Tôi đã kết luận lượt chạy $0,22 chết vì
thiếu `sageattention`. Sai: ComfyUI gọi `exit(-1)` ở nhánh đó, POSIX ra mã
**255**; mã đã đo được là **1**, tức một ngoại lệ chưa bắt. Giả thuyết cũ khớp
quá vừa nên đã kết thúc điều tra sớm. Log worker của RunPod thì **hết hạn nhanh**
(đo 05/09: bảng log rỗng hoàn toàn sau vài giờ) nên nguyên nhân gốc của lượt đó
**không còn lấy lại được** — `V-016` là ứng viên có cơ sở nhất, và bản vá hứng
`stderr` là thứ bảo đảm lần sau có **câu trả lời** thay vì một con số.

---

## V-017 — **Giá compute là $4,79/giờ (H100), không $2,74 (A100).** Và mọi số tiền phải phái sinh

**Ngày:** 2026-09-05 · **Trạng thái:** ✅ CHỐT · **Đổi:** `ngan_sach.py`,
`handler.py`, `cau_hinh.json`, `test_710`

### Ba lỗi cùng một gốc

| # | Chỗ hỏng | Giá trị sai | Giá trị đúng |
|---|---|---|---|
| ① | `GIA_COMPUTE_USD_GIAY` | `0,00076` (**A100**) | **`0,00133`** (H100, đo được) |
| ② | `ENVELOPE_PHA_GIO["_du_phong"]` | `33.8` gõ tay | phép trừ, tự tính |
| ③ | `timeout_s` trong `handler` | `1800` gõ tay | `TRAN_USD_MOT_JOB / giá` = **1.052** (751 trước 06/09, **quá thấp**) |

**Gốc chung: một con số phái sinh bị gõ tay thì nó sẽ trôi.** `V-013` bỏ A100 và
chuyển sang H100-only, nhưng hằng số giá vẫn là giá A100 — nguồn đúng, trích
đúng, và **sai**, vì thứ nó mô tả đã bị thay mà không ai quay lại gỡ. Đúng cơ
chế đã làm hỏng `V-016` (`cu124`).

### Phép đo

```
worker chay 1  ->  currentSpendPerHr $4,8190   (tru $0,0290 o dia = GPU $4,79)
worker chay 0  ->  currentSpendPerHr $0,0290
```

⚠️ Và $4,79/giờ **cao hơn cả ba giá bảng** (`securePrice`: NVL $3,19 · HBM3
$3,49 · PCIe $2,89) — vì `securePrice` là giá **Pod**, còn Serverless Flex tính
khác. ⇒ **Bảng giá không phải nguồn chân lý cho Serverless. Phép đo mới là.**

### Hệ quả đo được của giá trị cũ

| | báo cáo | thực tế |
|---|---|---|
| Giờ GPU mua được với $48,24 | **6,1 giờ** | **3,5 giờ** |
| Envelope compute tháng | 35,6 giờ | **20,36 giờ** |
| Bảng cấp phát theo pha | 35,6 giờ | vượt ngân sách **+75%** |

Một cầu dao nói ta còn nhiều tiền hơn thật — sai số đẩy về phía **hành động**.

### Trần thời gian là quyết định về tiền

`timeout_s=1800` ở giá thật là **$2,40 một job**, và là trần **mỗi lần**: vòng
thử lại tám lần (đã xảy ra 05/09) = **$19,20**.

```
TRAN_USD_MOT_JOB = 1.40   ->  tran_giay_mot_job() = 1.052 giay      (06/09)
TRAN_USD_MOT_JOB = 1.00   ->  tran_giay_mot_job() =   751 giay      (SAI, xem duoi)
```

Đối chiếu số cộng đồng để biết trần có đủ rộng: Wan2.2 chính chủ 720P/81
khung/**40 bước** trên H100 = **1 041,5 s** (⚠️ bản đầu ghi `326,9 s` — đó là
cột **480P**, trích nhầm cột) ⇒ 20 bước ≈ 520 s, cộng ~300 s nạp model.

#### 🔴 SỬA 06/09 — một phép cộng sai làm trần nằm DƯỚI nhu cầu

Bản trước của chính đoạn này viết: *"⇒ dự kiến **~363 s**, biên **2,07 lần**"*.

**520 + 300 = 820, không phải 363.** Và mọi thứ phái sinh từ con số ấy đều sai
theo, theo hướng **an toàn giả**:

| | Ghi | Thật |
|---|---|---|
| giây dự kiến một job | `363` | **815** (`P07` `Đ2`, `executionTime` nguội) |
| biên của trần 751 giây | `2,07 lần` | **0,92 lần** — tức trần nằm **DƯỚI** nhu cầu |
| `ngan_sach.GIAY_DU_KIEN_MOT_JOB` | `363` | lấy thẳng từ dòng sai này |

⛔ Hệ quả nếu không sửa: `dieu_phoi` gửi `timeout_s=751` xuống worker, một lượt
cold start cần **814,6 giây** trong handler ⇒ **mọi** job nguội bị cắt trước khi
ra sản phẩm, sau khi đã đốt gần trọn trần. Và với `workersMax=1` +
scale-to-zero thì lượt nguội là **mặc định**, không phải ngoại lệ.

⭐ **Một cái phanh luôn ăn thì tệ hơn không có phanh** — nó biến "job thất bại"
thành trạng thái mặc định, và tiền vẫn mất.

🔑 Vì sao nó sống sót lâu: docstring của `tran_giay_mot_job` **đã tự tính đúng**
(*"dự kiến ~820 giây"*) và **đã ghi số đo đúng** (*"đo được 814 giây. Khớp."*)
— nằm cách hằng số sai đúng vài dòng. Không gì so hai con số ấy với nhau. Nay
`test_tran_phai_phu_duoc_mot_luot_nguoi` so, **kèm self-test hai chiều** chứng
minh trần cũ **không** qua được nó.

⚠️ Và ba đại lượng trước đây bị gộp làm một, nay tách:

```
executionTime (trong handler)   814,6 s   <- cai `timeout_s` chan duoc
delayTime     (khoi dong nguoi) 154,7 s   <- xay ra TRUOC handler
-----------------------------------------------------
billed        (RunPod tinh tien) 969,3 s  <- cai sinh ra $1,29
```

So trần với cột **thứ ba** là so sai đại lượng — tôi đã viết một phép kiểm như
thế và nó đỏ vì lý do sai trước khi đỏ vì lý do đúng.

⚠️ `200 s` nạp model là **đo gián tiếp** (lượt 256×256×5 chạy 208,7 s, mà ở kích
thước nhỏ nhất gần như toàn bộ là nạp model). `P07` `Đ1` thay bằng đo trực tiếp.

⭐ Đặt trần bằng **tiền** thì nó tự đúng lại khi giá đổi — đúng thứ vừa hỏng.

### Ba phép kiểm chỉ chép lại hằng số

`test_710` có ba `assert` dạng `GIA_COMPUTE_USD_GIO == 2.736` — **chốt hằng số
bằng chính nó**. Khi giá hoá sai, cả ba vẫn xanh.

⭐ Mệnh đề đáng chốt không phải *"giá bằng 2,736"* mà là *"giá thuộc hạng máy ta
thật sự thuê"* — vẫn đúng sau khi ai đó đổi hạng máy, và **đỏ** đúng lúc họ quên
đổi giá. Kèm một phép kiểm chiều ngược: giá A100 cũ phải **rơi ra ngoài** khoảng
hợp lệ, nếu không thì khoảng đã rộng tới mức không canh gì.

### Còn nợ

`sageattention` trên PyPI **chỉ có tới 1.0.6** — bản V1 Triton mà README chính
chủ gọi là *"slower than V2/V2++/V3"*. Bản 2.2.0 README bảo cài thì **không tồn
tại trên PyPI**; muốn V2 phải build từ nguồn, cần `nvcc`, tức đổi ảnh nền
`-runtime` → `-devel`. Đã ghim `==1.0.6` và `handler` báo `sage_ban`; lên V2 là
hạng mục riêng, **đo lợi ích trước**.

---

## V-018 ✅ **CHỐT: đường A — giữ `V-012`, giữ Serverless, nội bộ trước**

**Ngày:** 2026-09-05 · **Trạng thái:** ✅ **CHỐT** (chủ dự án: *"theo đề xuất"*) · **Cổng `P14a`:** đỏ cho việc **bán ra ngoài**, xanh cho việc **dùng nội bộ**

### Số đo, không phải ước

**Giá vốn của ta** (đo 05/09, `DO_LUONG_KET_QUA.csv`):

| | giây | tiền |
|---|---|---|
| khởi động nguội | 154,7 | $0,21 |
| chạy (720P · 81 khung · 20 bước · fp16) | 814,6 | $1,08 |
| **cold start** | 969,3 | **$1,29** |
| **worker ấm** (sau khi `idleTimeout`→300s) | ~675 | **$0,90** |

**Giá thị trường** (tra 05/09 bằng browser, trang render JS nên `curl` không đọc được):

| Nơi | Giá | Ghi chú |
|---|---|---|
| **fal.ai** | **$0,08/giây video @720p** | chạy **chính Wan2.2 A14B**, 16 fps — *giống hệt ta* |
| fal.ai | $0,06 @580p · $0,04 @480p | |
| **Replicate** `wan-2.2-t2v-**fast**` | **$0,10/video** | bản **distill**, ít bước |

### Đối chiếu — video 5,06 giây 720P

```
fal.ai BAN                      $0,41
Replicate BAN (ban fast)        $0,10
GIA VON cua ta (worker am)      $0,90
GIA BAN cua ta (V-003, x2)      $1,80

gia VON cua ta / gia BAN cua fal        = 2,2 lan
gia BAN cua ta / gia BAN cua fal        = 4,4 lan
gia BAN cua ta / gia BAN cua Replicate  =  18 lan
```

⛔ **Ta không hoà vốn được kể cả khi bán bằng giá fal.ai.**

### Vì sao — và đây không phải lỗi kỹ thuật

Khoảng cách **không** đến từ việc dựng sai. Số của ta **khớp bảng chính chủ**
(1 041,5 s @720P/40 bước ⇒ ~520 s @20 bước, cộng ~300 s nạp model = ~820 s; đo
được 814 s). Đường ống đúng, cấu hình đúng, kiểm cơ học 7/7 đạt.

Khoảng cách đến từ **cấu hình ta cố ý chọn**:

- `V-012` chốt **fp16 · 20 bước · không LoRA distill**, theo lệnh chủ dự án:
  *"chỉ tồn tại 1 đường duy nhất là mạnh nhất so với cấu hình máy… mặc định và
  duy nhất là fp16"*.
- Replicate bán bản `-fast` = **distill 4 bước**. 4 bước so với 20 bước là nhanh
  ~5 lần ⇒ giá vốn rơi từ $0,90 xuống **~$0,18**.

⭐ Đây là **mâu thuẫn thật giữa chất lượng và giá**, không phải khuyết tật cần
vá. Và đó là quyết định thương mại của chủ dự án, không phải của tôi.

### 🔴 ĐÍNH CHÍNH (cùng ngày, sau khi đọc bảng giá GPU của fal.ai)

Đoạn trên kết luận *"phải chọn giữa chất lượng và giá"*. **Thiếu một đường, và
đó là đường quan trọng nhất.**

Bảng giá fal.ai ghi: *"Deploy your own app on our competitively priced GPU
fleet, **as low as $1.89/hr for H100**."*

```
Ta tra RunPod Serverless Flex : $4,79/gio   (DO DUOC)
fal.ai ban H100               : $1,89/gio   (bang gia cua ho)
=> ta tra dat gap 2,53 lan
=> khoang cach gia von do duoc: 2,2 lan
```

⭐ **Hai con số khớp gần như hoàn toàn.** Gốc của khoảng cách **không** phải
cấu hình 20 bước — mà là **ta đang trả tiền thuê GPU đắt gấp 2,5 lần**.

Cùng cấu hình `V-012`, chỉ đổi hạng máy:

| Nơi thuê | $/giờ | Giá vốn/video | so với fal bán $0,41 |
|---|---|---|---|
| RunPod Serverless Flex *(hiện tại)* | $4,79 | $0,90 | **lỗ 2,2×** |
| RunPod **Pod** H100 PCIe | $2,89 | $0,54 | lỗ 1,3× |
| RunPod **Pod** H100 NVL | $3,19 | $0,60 | lỗ 1,5× |
| fal.ai bán H100 | $1,89 | **$0,35** | **CÓ BIÊN** |

⛔ **Serverless Flex là hạng đắt nhất RunPod có.** Ta chọn nó ở `ADR-3` vì
*scale-to-zero* — không có job thì không tốn tiền. Đó là lựa chọn đúng **khi
lưu lượng thưa**, và là lựa chọn **đắt nhất** khi lưu lượng dày.

### Ba đường, không phải hai

| | Đường | Được | Mất |
|---|---|---|---|
| **A** | Giữ `V-012`, giữ Serverless | chất lượng cao nhất · không tốn khi rảnh | **không bán được ở thị trường mở** |
| **B** | Mở nhánh distill 4 bước | giá vốn ~$0,18 | phá luật *"một đường duy nhất"* đã chốt **hai lần** |
| **C** | Giữ `V-012`, **đổi sang Pod** hoặc nhà rẻ hơn | **không đụng `V-012` một chút nào** | mất scale-to-zero: Pod tính tiền **liên tục**, kể cả khi không ai dùng |

⭐ **C là đường duy nhất không phải đánh đổi chất lượng.** Nhưng nó đổi *mô hình
chi phí*: Pod $2,89/giờ chạy 24/7 = **$2 081/tháng** dù có khách hay không. Nó
chỉ có nghĩa khi lưu lượng đủ dày để lấp — và ta **chưa có một khách nào**.

⇒ Với giai đoạn hiện tại (nội bộ, `surface="admin"`), **A vẫn là đường đúng**:
trả đắt trên mỗi video nhưng **không trả gì khi rảnh**. Câu hỏi giá chỉ thành
thật khi có lưu lượng thật, và lúc đó C mở ra mà **không cần đụng `V-012`**.

⛔ Tôi **không** tự chọn giữa ba đường. `V-012` được chốt sau khi chủ dự án nói
thẳng hai lần, và mô hình chi phí là quyết định thương mại — đúng giao thức đổi
quyết định trong `AGENTS.md`.

### ✅ CHỐT 05/09 — đường **A**

Chủ dự án chọn **A**: giữ `V-012` (fp16 · 20 bước · không distill), giữ RunPod
Serverless Flex, app ra mắt **nội bộ**.

**Vì sao A đúng cho giai đoạn này** — và lý do không phải "chất lượng quan trọng
hơn giá":

| | A (Serverless) | C (Pod) |
|---|---|---|
| Trả khi **có** job | $0,90/video | $0,54/video |
| Trả khi **rảnh** | **$0** | **$2 081/tháng** |
| Số khách hôm nay | \-- | **0** |

⭐ Với **không** khách, A tốn $0 còn C tốn $2 081/tháng. Khoảng cách giá vốn 2,2
lần chỉ thành tiền thật **khi có lưu lượng thật** — và đúng lúc đó C mở ra mà
**không cần đụng `V-012`**.

⛔ Nên A **không phải** là "chấp nhận lỗ". Nó là *"chưa trả tiền cho một bài toán
chưa xảy ra"*. Ngày có khách đều, phép tính đảo chiều và `V-018` được mở lại —
điều kiện đảo chiều ghi rõ ngay dưới.

#### Điều kiện mở lại `V-018`

Chuyển sang **C** khi **cả hai** đúng:

1. Lưu lượng đủ để Pod rẻ hơn: `$2 081/tháng ÷ ($0,90 − $0,54)` ≈ **5 780
   video/tháng** ≈ **193 video/ngày**. Dưới mức đó, Pod đắt hơn.
2. Lưu lượng **đều**, không dồn cục — Pod không co giãn được.

⭐ Con số 193 video/ngày là **ngưỡng đảo chiều**, và nó nên nằm trong bảng theo
dõi vận hành chứ không nằm trong trí nhớ ai cả.

### Điều KHÔNG nên làm lúc này

**Tối ưu cold start.** $0,40 tiết kiệm được (cold → ấm) không lấp nổi khoảng cách
**2,2 lần**. `KE_HOACH_GO_COLD_START.md` vẫn đúng về kỹ thuật nhưng **sai về ưu
tiên** cho tới khi `V-018` có lời giải.

### Việc vẫn chạy được, 0 GPU, đúng dù đi hướng nào

`ADR` đã chốt `lttvideo` ra mắt `surface="admin"` (**nội bộ trước, bán sau**).
Nên `P09` (provider) và `P10` (app) **không phụ thuộc** câu trả lời thương mại —
hạ tầng cần cho cả hướng A lẫn B.

