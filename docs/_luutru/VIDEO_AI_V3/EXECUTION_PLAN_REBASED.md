# KẾ HOẠCH THI HÀNH ĐÃ REBASE — LTT VIDEO AI V3

> ⛔ **HỒ SƠ ĐƯỜNG ĐI — KHÔNG PHẢI CHỈ DẪN (đóng băng 2026-09-05).**
> Kế hoạch đang sống là **`KE_HOACH_XAY_DUNG.md`**; tham số sản xuất sống trong
> **`platform_core/video_gen/cau_hinh_san_xuat.py`**. Tệp này viết trước
> `V-010`/`V-012` nên nó còn mang giả định **fp8 · 4 bước · 640×640 · nhiều bậc
> chất lượng · L40**. Cả năm giả định đó **đã bị gỡ**. Đọc tệp này để hiểu
> *chương trình đã đi qua đâu*, đừng đọc để lấy con số.


> Sản phẩm của **P00**, nhiệm vụ 7.
> Cơ sở: `CURRENT_SYSTEM_MAP.md` (hệ thống thật) + `PROMPT_PACK_V3_REVIEW.md` (rà pack).
>
> ⛔ **Tài liệu này KHÔNG sửa `USER_DECISIONS.md`.** D01–D12 giữ nguyên. Chỗ nào
> P00 thấy một quyết định cần người dùng xem lại thì nó nằm ở §1 dưới dạng **câu
> hỏi**, không phải một thay đổi đã làm.
>
> ⛔ **Không hard gate nào của `policies/NON_NEGOTIABLE_GATES.md` bị bỏ.** Có hai
> gate được **thêm**.

Ngày: **2026-09-04** · Cây `...\worktrees\ltt-llm-api-http-guide-a3e123` ·
nhánh `claude/ltt-video-ai-v3-p00-3f5713` · commit gốc `d225a48`.

---

## 1. Bốn ADR — **ba đã được chủ dự án trả lời 2026-09-04**

> ✅ **ADR-0 · ADR-1 · ADR-2 đã CHỐT** → ghi thành `V-001` / `V-002` / `V-003`
> trong `DECISIONS.md`. **ADR-3** được giao lại cho Claude (`V-006`) và nay ở
> trạng thái **PROPOSED** tại `ADR_REMOTE_VIDEO_COMPUTE.md`.
>
> Phần dưới **giữ nguyên lập luận gốc của P00** — không xoá, vì lý do đặt câu
> hỏi là thứ giải thích vì sao câu trả lời quan trọng. Mỗi mục có một dòng
> **KẾT** ghi câu trả lời thật.

### ADR-0 — **Vì sao C-CLOUD?** ✅ **ĐÃ TRẢ LỜI** → `V-001`

`apps/taovideo` đang bán T2V + I2V + tham chiếu + video-input qua BytePlus
Seedance, **hôm nay, trên production**. Nên câu hỏi thật của dự án này không phải
*"làm sao có video"*.

Bốn lý do khả dĩ, và mỗi cái dẫn tới một V1 **khác hẳn**:

| Nếu lý do là… | thì "Quality/Pro" nghĩa là | thì P08 phải đo | thì scope V1 nên |
|---|---|---|---|
| **A. Biên lợi nhuận** — tự chạy rẻ hơn mua | rẻ hơn Seedance ở **cùng mức chấp nhận được** | `$ / video được chấp nhận`, so trực tiếp Seedance | giữ 4 mode, nhưng chỉ mở mode nào **rẻ hơn thật** |
| **B. Kiểm soát nội dung** — Seedance chặn thứ ta được phép bán | làm được thứ Seedance từ chối | tỉ lệ bị chặn, chứ không phải điểm thẩm mỹ | hẹp lại quanh đúng loại nội dung đó |
| **C. Chất lượng/khả năng** — có mode Seedance không làm được | hơn hẳn ở **một** trục đo được | so mù theo trục đó | có thể **chỉ 1–2 mode** |
| **D. Chiến lược** — không phụ thuộc một nhà cung cấp | tương đương là đủ | tính sẵn sàng, không phải điểm đẹp | 4 mode, mức "đủ dùng" |

⭐ Repo có tiền lệ đúng cho chuyện này: model ảnh nhà **thua Gemini 24–4** trong so
mù (D-045) và vẫn được mở bán — nhưng được định vị lại thành *"rẻ hơn, và không bị
chính sách nội dung của hãng khác chi phối"*, kèm lệnh cấm nói nó "đẹp hơn"
(`providers.py:178`). Đó là lý do **A + B**, được viết ra rõ ràng, sau khi đo.

**KẾT (2026-09-04):** lý do là **A**, ở một dạng P00 đã không liệt kê ra —
*nhà sản xuất video AI, **công ty dùng trước**, bán phần dư, tối giản chi phí
đầu tư dài hạn*. Tức **khách hàng đầu tiên là chính nền tảng**. Bốn hệ quả
(đổi tiêu chí P08 · giờ Pod nhàn rỗi mới là kẻ thù · nội bộ-trước làm cho gộp
lô khả thi thật · thứ tự mở bán) ở `DECISIONS.md` V-001. **P02 mở khoá.**

### ADR-1 — **Mở rộng `apps/taovideo` hay app mới?** ✅ **ĐÃ TRẢ LỜI** → `V-002`

| | Mở rộng `taovideo` | App mới (vd `videoai`) |
|---|---|---|
| Khách thấy | một sản phẩm, chọn "chạy ở đâu" | hai mặt hàng riêng |
| Rủi ro | **đụng app đang phục vụ khách** | không đụng ai |
| Tiền lệ | — | ⭐ `apps/anhnoibo`: *"Model nội bộ là một provider… nhưng bán nó ra `/api/v1` cần một `ToolSpec`, mà ToolSpec chỉ khai được trong manifest của một app. Thêm nó vào `taoanh`/`thumbnail` là đụng vào app đang phục vụ khách; thêm một thư mục vào `apps/` thì không đụng ai."* |
| Giao diện | dùng lại `taovideo.html` + 5 tệp test giao diện | phải dựng (hoặc `catalog_parent="taovideo"` và chưa có UI) |
| Giá | mô hình token của Seedance ≠ mô hình giây-GPU | mỗi app một `gia.py`, sạch |

**KẾT (2026-09-04): app mới, tên `Lttvideo`.** Định danh chốt ở `V-002` —
slug **`lttvideo`** · prefix `/lttvideo` · tool **`video.ltt`** (khớp gia đình
`image.ltt` · `speech.ltt`) · `requires=("api",)`.

🔴 **Và tên đó vô tình tránh đúng cái bẫy `ltt_llm` đã sập.** Slug **không có
gạch dưới** nên nó khác chuỗi provider `ltt_video`, và `test_60` **không phải
cấp miễn trừ thứ tư** — chính tệp test viết rằng thêm một miễn trừ *"is not
free: it blinds this check"* (`tests/test_60_app_registry.py:396`).

Nếu sau này có mode "nâng cấp video vừa tạo" kiểu `taovideo→upscalevideo` thì
phải **khai cạnh app→app** trong `tools/lint_app_contract.py` (`test_308` chốt
hai chiều).

### ADR-2 — **Mô hình giá cho compute theo giây** ✅ **ĐÃ TRẢ LỜI** → `V-003`

Hôm nay mọi giá vốn của nền tảng là *"mỗi lượt tốn $X"* (token / ảnh / giây tiếng
nói). GPU thuê thì giá vốn là:

```
giá vốn một video = (giây GPU chạy + giây khởi động phân bổ) × giá/giờ
                  + phần khấu hao storage cố định
                  + phần Pod bật mà không có việc
```

Một Pod bật 20 phút để chạy 3 phút video ⇒ **17 phút phải tính vào đâu đó**. Ba
đường:

1. **Khách trả cố định, nền tảng chịu rủi ro nhàn rỗi** (đúng tinh thần D09: *"user
   thấy giá/credit ổn định"*). Cần một mức tải tối thiểu để không lỗ.
2. **Gộp lô**: chỉ bật Pod khi hàng đợi đủ N việc ⇒ khách chờ lâu hơn nhưng giá ổn.
3. **Bậc "chạy ngay" đắt hơn** ⇒ mâu thuẫn D10 (V1 chỉ một tier).

**KẾT (2026-09-04): giá bán = 2 × giá vốn tính theo giây sản xuất.**

`V-003` viết ra *"giá vốn"* nghĩa là gì (giây GPU + phần khởi động phân bổ +
phần cố định phân bổ), và giải chỗ mơ hồ bằng đúng khuôn đang chạy trong kho:
**giá công bố = 2 × một hằng số đã ĐO, có phiên bản, theo từng pipeline**
(như `ltt-image-2026-08-24b`), còn **giá vốn thật ghi lại từng job** cho biên
lợi nhuận — `credit.SettlementResult` đã có sẵn chỗ đựng.

🔑 **Và đây là chỗ ×2 biến P08 thành một cổng GO/NO-GO có số:** *một pipeline
chỉ đáng **bán** nếu `2 × giá_vốn_chuẩn` còn cạnh tranh với giá mua ngoài cho
một video tương đương.* Mốc so sánh có sẵn: `apps/taovideo/cost.py`.
⚠️ Nếu đắt hơn đi mua thì nó **vẫn có thể** đáng làm cho việc **nội bộ** (giá
vốn ×1) mà **không** đáng mở bán — hai kết luận khác nhau, phải nói riêng.

Gộp lô vẫn là cơ chế **nội bộ** của P14, khách không thấy.

### ADR-3 — **Kiến trúc remote compute** 🟡 **PROPOSED** → `ADR_REMOTE_VIDEO_COMPUTE.md`

Chủ dự án giao lại cho Claude nghiên cứu (`V-006`). Đã chấm
`ARCHITECTURE_SCORECARD.csv` và **đề xuất phương án C** (worker cloud riêng):
**A 168 · B 210 · C 277** trên tối đa 300. C thắng 11/14 tiêu chí, hoà 2, thua
đúng một — `code_reuse`/`maintainability`, tức món nợ ~600 dòng ống nước ComfyUI
được canh bằng một phép kiểm ghim-từng-byte trong dải 700–799 và trả sau P09.

⛔ Vẫn **chờ chủ dự án duyệt** (D01): PROPOSED không phải APPROVED.

Bảng bằng chứng gốc của P00 giữ nguyên bên dưới — nó là thứ ADR được xây trên:

| | Bằng chứng ủng hộ | Bằng chứng chống |
|---|---|---|
| **A** tổng quát hoá `render_gateway` tại chỗ | phần lõi (`comfy.py` ghim ComfyUI `6f7cd7f`, `workflows.py`, `catalog.py`) đã tổng quát | **đụng thẳng vào cổng đang bán ảnh** ⇒ vi phạm tinh thần D02 |
| **B** lõi/giao thức chung + runtime riêng | cùng bằng chứng trên; phần đặc thù ảnh chỉ nằm ở `api.py`/`runner.py`/`storage_io.py` | phải refactor ⇒ **cần characterization test trước**, và đó là chạm `render_gateway` |
| **C** worker cloud riêng, tương thích hợp đồng sẵn có | ⭐ Q102 là tiền lệ trực tiếp; `providers.py` chừa sẵn cửa; `APIKEY_CAT_VIDEO` đã có; `cong_render.py`/`dieu_phoi.py` là khuôn client đã chạy thật; **blast radius bằng 0** | chép lại một phần plumbing ComfyUI |
| **D** khác | — | phải có bằng chứng |

⚠️ **Bẫy phải tránh:** phương án B nghe "sạch" nhất về mặt kỹ thuật, nhưng nó là
phương án **duy nhất bắt buộc phải sửa `render_gateway`** — tức phải qua cổng D02
và cần ADR người dùng duyệt trước. Phương án C mua được quyền *chạy trước, dọn
sau*, và repo đã nhận món nợ đúng kiểu đó một cách có ý thức (Q102: *"adapter ảnh
dùng chung đúng ra phải có từ H5… gộp lại là G12, làm sau"*).

---

## 2. Đồ thị pha sau rebase

Thay đổi so với `PHASE_GRAPH.json`: **thêm hai nút cổng** (ADR-0 và ADR-APPROVED),
**không đổi thứ tự các pha kỹ thuật**, **không xoá gate nào**.

```
P00 ─┬─────────────────────────────────────────────────────► (xong)
     │
     ├─► ⛔ ADR-0  "vì sao C-CLOUD"   ── người dùng ──┐
     │                                                │
     ├─► P01 audit sâu + scorecard + ADR-3 ĐỀ XUẤT ───┤   (chạy song song)
     │                                                │
     └─► P02 OSS mining (đợi ADR-0 để biết đo gì) ────┤
                                                      ▼
                                            P03 BOM + chi phí + ENVELOPE
                                                      │
                                    ⛔ CỔNG DUYỆT ADR (ADR-1,2,3)  ← người dùng
                                                      │
                                                      ▼
                                        P04 tài khoản + storage + cost guard
                                                      │
                                          ┌───────────┴───────────┐
                                          ▼                       ▼
                                  P05 preload không GPU     P06 tạo C-CLOUD
                                          └───────────┬───────────┘
                                                      ▼
                                              P07 upstream 4 mode
                                                      ▼
                                        P08 benchmark + SO MÙ với đương kim
                                                      ▼
                                              P09 golden pipelines
                                                      ▼
                                        P10 implement ADR + E2E A↔C
                                                      ▼
                                      P11 app backend (theo ADR-1)
                                        ├─► P12 GUI (mở rộng cái đã có)
                                        ├─► P13 public API (additive, co lại)
                                        └─► P14 GPU lifecycle
                                                      ▼
                                              P15 final audit
```

**Vì sao cổng duyệt ADR chuyển xuống sau P03:** `NON_NEGOTIABLE_GATES.md` đòi ADR
được duyệt *"trước code tích hợp"*. Code tích hợp ở **P10**. Giữa P01 và P10 có
tám pha sinh ra bằng chứng mà ADR cần — và `P01` tự nói *"nếu chưa đủ evidence,
ADR = OPEN"*. Đặt cổng sau P03 là chỗ sớm nhất mà **chi phí** đã biết, và vẫn sớm
hơn code tích hợp **sáu pha**. Gate không bị nới, nó bị đặt vào chỗ nó đo được.

### Hai gate được THÊM

| Gate mới | Nội dung | Vì sao |
|---|---|---|
| **G-A** *(sau P08)* | Đối chiếu **31 chốt** của `docs/KHUON_BAN_MODEL_NHA.md` trước khi coi bất kỳ pipeline nào là "bán được" | Đó là checklist mở-bán-model-nhà của chính dự án, và nó ghi rằng H37 **đã mắc lại đúng lỗi tiền của H38** |
| **G-B** *(mọi pha)* | `git diff --stat` phải **rỗng** trên `render_gateway/**` và `llm_gateway/**`, trừ khi ADR-3 được duyệt cho phép | Biến D02 từ lời hứa thành phép kiểm chạy được |

---

## 3. Việc thật của từng pha sau rebase

Chỉ ghi **phần khác** so với pack. Phần không ghi = giữ nguyên prompt gốc.

| Pha | Thêm | Bớt |
|---|---|---|
| **P01** | đọc thêm `apps/taovideo/**`, `registry.py`, `leases.py`, `gia_von.py`, `apps/qualitylab` · viết `B_LAN_COMPATIBILITY_BASELINE.md` bằng **tên tệp test**, không bằng văn xuôi · ADR-3 ra **đề xuất**, không đòi duyệt ngay | — |
| **P02** | bước 0: kiểm ComfyUI **đã ghim** (`6f7cd7f` / 0.30.0) — candidate đòi bản mới hơn là chi phí tương thích, phải ghi · ghi rõ mode nào **không có** candidate tử tế (nghi ngờ: V2V) · ⭐ trục đo theo `V-001`: **đủ dùng để công ty xuất bản, ở chi phí thấp hơn đi mua** — không phải *đẹp nhất* | — |
| **P03** | **envelope theo pha** (§4) · giá vốn chuẩn theo giây cho `V-003` (**có phiên bản**, một chỗ duy nhất, khuôn `ngan_sach.py`/`gia.py`) · **`V-005`**: `$ mỗi video` trên **ít nhất hai lớp GPU** + **điểm hoà vốn thuê-hay-mua** · phương án dự phòng nếu A100 PCIe 80GB hết hàng (đề xuất, **không tự đổi** — D06 khoá) | — |
| **P04** | chốt **chỗ cất khoá** kèm lý do (đề xuất: vòng đời Runpod → `secrets/app.env`; token cổng C-CLOUD → APIKEYS như `ltt_image`) · mở trình duyệt bằng `--cdp` vào Chrome thật | — |
| **P05** | dùng lại `render_gateway/deploy/tai_model.py` (bản khai JSON + `BANG_KE.json` sha256, tải tiếp được); `MODEL_BOM_ACTUAL.csv`/`STORAGE_MANIFEST.json` **sinh ra từ** nó | định dạng bảng kê thứ ba |
| **P06** | cổng C-CLOUD phải **trùng khuôn hợp đồng `render_gateway`**: `/live` không khoá · `/health` · `/v1/models` khuôn `{"data":[…]}` · submit **202 + job_id idempotent** · **429 + `Retry-After`** · `/v1/jobs/{id}` · `/cancel` **có `prompt_id`** | — |
| **P07** | mỗi lần terminate GPU vì "đi đọc tài liệu" ghi **một dòng sổ chi phí** | — |
| **P08** | **so mù với đương kim Seedance** · dùng `tools/cham_mu.py` + `tools/bradley_terry.py` + `apps/qualitylab` · ghi `pod_billed_seconds` và `pod_boot_seconds` · 🔑 **cổng GO/NO-GO có số** theo `V-003`: đáng **bán** chỉ khi `2 × giá_vốn_chuẩn` còn cạnh tranh với giá mua ngoài; đáng dùng **nội bộ** thì chỉ cần `giá_vốn` thắng — **hai kết luận tách riêng** | dựng bảng chấm mới |
| **P09** | nếu ADR-3 = C thì golden pipeline **là** một `ModelInfo` trong `providers.py`; nếu không thì phải biện minh registry thứ hai · đối chiếu G-A | `PIPELINE_REGISTRY_PROPOSED.json` như một định dạng độc lập |
| **P10** | characterization test **trước** mọi refactor dùng chung · ba luật của `cong_render.py` là bắt buộc · `mark_provider_dispatched`/`mark_ambiguous` phải được dùng ở đường gọi C-CLOUD | — |
| **P11** | app `lttvideo` theo `V-002` (slug **không** gạch dưới) · khai `admission_resource`/`admission_slots` (Q114) · dịch 429 của cổng thành `jobs.DangBan` (**không** import lớp lỗi của cổng khác) · `requires` phải khớp làn `LTT_WORKER_POOLS` đang đặt ở production, nếu không **job nằm `queued` mãi mãi mà `/health/ready` vẫn 200** (Q118 ghi đúng cái bẫy này) | dựng lại job/credit/storage |
| **P12** | ⚠️ phạm vi phụ thuộc **`V-004`**: nếu mở nội bộ trước thì đây là *một trang cho chính mình dùng*, không phải giao diện bán hàng · mở rộng giao diện đã có; nếu app mới chưa có UI thì khai `catalog_parent` (nếu không: link 404 trong header của **mọi** khách đã đăng nhập — `AGENTS.md` §8.2c) · cache-bust `?v={{ asset_ver }}` · kiểm **URL công khai**, không chỉ loopback | GUI mới từ đầu |
| **P13** | ⚠️ **hoãn được cả pha** nếu `V-004` được duyệt (không mở `LTT_PUBLIC_API_TOOLS` thì không có hợp đồng công khai nào phải giữ mãi) · khi làm: khai `api_contract` + bật cờ + `tools/check_api_compat.py`, tool tên **`video.ltt`** · **không thêm route** (`test_178` chốt hai chiều) · xác nhận lại con số 27 route và sửa `CLAUDE.md:228` | trang developer, hệ khoá, scope, webhook — đã có |
| **P14** | dùng `leases.acquire` cho single-flight · `DangBan`/`defer_resource` cho backpressure · `manifest.bao_tri` (dưới lease) cho đối soát mồ côi · **mới**: ghi `billed lifetime` + trần thời gian phiên + đối chiếu ngân sách còn lại | scheduler/queue mới |
| **P15** | `python tools\gate.py` **đầy đủ** · `lint_app_contract` · `check_api_compat` · `scan_source_secrets` · `so_deploy` · `api_prod_canary trang-thai` · G-B · cập nhật `docs/_luutru/PROJECT_MEMORY.md` · sinh lại `ho_so_he_thong.txt` | bảng "cái gì đang sống" chép tay |

---

## 4. Ngân sách $150 — chia theo pha, và luật không cho mượn

🔴 Đây là sửa đổi quan trọng nhất về mặt vận hành. **Bảy pha cần GPU trả tiền, một
túi tiền, pack không đặt ai giữ cửa** — và pha tốn nhất (P08) chạy **trước** pha
chứng minh hệ thống an toàn (P14/P15).

Envelope đề xuất, tính theo **% của $150/tháng**. P03 phải quy ra giờ GPU sau khi
hỏi **giá live** — P00 cố ý **không viết một con số $/giờ nào**, vì
`GLOBAL_RULES.md` cấm coi snapshot là hằng số và P00 chưa hỏi Runpod:

| Pha | Envelope | Vì sao |
|---|---|---|
| P04 storage + guard | **10 %** | phí cố định của tháng, tiêu đều |
| P05 preload | **0 %** GPU | mục tiêu của cả pha là không đốt GPU |
| P06 bootstrap + recreate | **10 %** | vài giờ, gồm một lần dựng lại để chứng minh |
| P07 upstream 4 mode | **20 %** | 4 baseline + ít nhất một lần lặp lại |
| P08 benchmark | **25 %** | tốn nhất — nhưng **không được quá một phần tư** |
| P09 golden | **5 %** | chốt, không khám phá |
| P10 E2E A↔C | **10 %** | E2E + recreate + chạy lại |
| P14 failure injection | **10 %** | bật/chạy/drain/terminate lặp — **phải còn tiền lúc này** |
| P15 canary | **5 %** | |
| **dự phòng** | **5 %** | |

**Ba luật đi kèm:**
1. **Pha sau không mượn trước được của pha trước.** Hết envelope ⇒ thu hẹp ma trận
   thí nghiệm theo *information gain* (chính `P08` đã viết vậy), không tiêu lấn.
2. **Mỗi lần tạo/dừng resource ghi một dòng `COST_LEDGER`** kèm `phase_envelope_usd`
   và `envelope_remaining_usd`.
3. **Cuối mỗi pha có GPU: kiểm kê resource còn đang bị tính tiền.** Không có dòng
   này thì pha chưa đóng.

⭐ Repo có tiền lệ đúng cho hình dạng này: `render_gateway/ngan_sach.py`,
`llm_gateway/ngan_sach.py`, `apps/ltt_llm/ngan_sach.py` — **một** hàm ngân sách,
**một** đơn vị, **một** nguồn. Ngân sách tiền cloud phải được đối xử y như vậy,
và nên là một mô-đun `ngan_sach.py` của app video chứ không phải một bảng tính.

---

## 5. Danh sách **chính xác** tệp và test mà P01–P03 phải đọc

Đây là deliverable cuối của P00 (*"danh sách exact files/tests cần P01–P03 đọc"*).
Chia theo pha để không ai phải đọc thừa.

### 5.1 P01 — audit sâu + ADR-3 (đọc đủ cả mã lẫn test)

**Cổng B-LAN (phía máy B) — chỉ đọc, tuyệt đối không sửa:**
```
render_gateway/api.py                 364   hợp đồng HTTP: /live /health /v1/models
                                            /v1/images/generations /v1/jobs/{id}
                                            /v1/jobs/{id}/cancel /v1/exclusive
render_gateway/config.py               67   mọi tham số từ env; mặc định Windows
render_gateway/comfy.py               247   client ComfyUI, ghim commit 6f7cd7f
render_gateway/runner.py              321   ⚠️ đặc thù ảnh
render_gateway/busy.py                364   trọng tài bận + ETA từ lịch sử
render_gateway/jobs.py                142   JobStore + 7 trạng thái
render_gateway/catalog.py              99   ModelSpec: modes / ref_slots / defaults
render_gateway/workflows.py           121   template JSON + thẻ "@ten"
render_gateway/workflows/catalog.json       dữ liệu; đọc cả 3 tệp workflow
render_gateway/storage_io.py          124   ⚠️ đặc thù ảnh (8MB/20MB, _MAGIC)
render_gateway/nhuong_card.py         326   N hộ dùng chung card — đọc để HIỂU B-LAN
render_gateway/ngan_sach.py           172   khuôn "một hàm ngân sách"
render_gateway/main.py                 95   NSSM, gateway.env, bẫy AppEnvironmentExtra
render_gateway/deploy/tai_model.py          bộ tải model + BANG_KE.json  → dùng ở P05
```

**Phía A-CONTROL — khuôn client đã chạy thật:**
```
platform_core/image_gen/cong_render.py      client A→B; BA LUẬT ở docstring
platform_core/image_gen/dieu_phoi.py        điều phối trọn job + presigned GET/PUT
platform_core/image_gen/__init__.py         sơ đồ đường đi một job
```

**Provider / khoá:**
```
platform_core/providers.py            359   REGISTRY; xem kỹ ltt_image + ltt_llm
platform_core/providers_live.py        91   parse_models — quyết định khuôn /v1/models
platform_core/api_pool.py             261   cấp phát, cooldown, cascade, disable-5-lần
platform_core/api_keys.py             168
platform_core/models.py:640-660             APIKEY_CAT_* (video đã có)
```

**Job / lease — đọc kỹ, đây là chỗ V3 được cho không nhiều nhất:**
```
platform_core/jobs.py                 478   ⭐ DangBan · LoiNguoiGoi · defer_resource
                                            mark_provider_dispatched · mark_ambiguous
                                            admission_resource · reclaim_orphans
platform_core/job_submit.py            76   job + credit trong MỘT transaction
platform_core/job_runner.py:190-260,520-620 _chay_mot_job, _provider_failure_kind
platform_core/leases.py               146   ⭐ single-flight cho P14
platform_core/gpu_lease.py            254   khuôn giành/đập nhịp/trả (GPU cục bộ)
platform_core/job_events.py           234
platform_core/job_metrics.py          204
```

**Tiền:**
```
platform_core/credit.py               678   giu_cho / quyet_toan / hoan; SettlementResult
platform_core/gia_von.py + gia_von.json     giá vốn
platform_core/to_tien.py · billing_math.py
apps/taovideo/cost.py                 102   ⭐ khuôn giá lai D09 ĐÃ CHẠY
apps/anhnoibo/gia.py                        ⭐ khuôn "giá ở một chỗ, có phiên bản"
```

**Lưu trữ / media:**
```
platform_core/storage.py              428   Storage / LocalStorage / R2Storage
platform_core/upload_sessions.py      400
platform_core/media.py                262
platform_core/image_input.py           49
```

**Hợp đồng app — đọc TRƯỚC khi nghĩ tới app mới:**
```
platform_core/registry.py             1201  ⭐ tệp quan trọng nhất của hợp đồng
apps/anhnoibo/manifest.py                   ⭐ tiền lệ gần nhất (app chỉ-job, model nhà)
apps/taovideo/manifest.py             223   ⭐ hợp đồng public API của video
apps/taovideo/jobs.py                 314   ⭐ khuôn async submit→poll→tải→quyết toán
apps/taovideo/models.py · modelark.py · refs.py · assets.py · quotes.py
docs/03_THEM_APP_MOI.md               273
AGENTS.md §8 (dòng 344-495)                 bố cục mã, 4 module server, cạnh app→app
```

**Test — bản mô tả hành vi B-LAN (P01 phải liệt kê chính xác ca nào là "hợp đồng"):**
```
tests/test_245_render_gateway.py            cổng ảnh
tests/test_250_cong_render.py               client phía A
tests/test_227_nexus_render.py              đường Nexus
tests/test_334_*                            trần token cổng LLM ↔ manifest
tests/test_79_taovideo.py                   app video
tests/test_172_taovideo_money_contract.py   ⭐ hợp đồng TIỀN của video
tests/test_111/112/113/158/170_taovideo*    giao diện
tests/test_178_public_api_kernel.py         bề mặt đóng băng, chốt hai chiều
tests/test_212_*                            không rò model id của nhà cung cấp
tests/test_308_*                            cạnh app→app, chốt hai chiều
tests/test_60_*                             chống hardcode slug trong nền tảng
tests/conftest.py                           fixture `app_thu` (thay apps/demo đã gỡ)
```

**Quyết định — đọc nguyên văn, không đọc tóm tắt:**
```
docs/QUYET_DINH_NEN_TANG.md   Q92 · Q102 · Q106 · Q107 · Q114 · Q117 · Q118 · Q120
                              + §2 "Ràng buộc bất biến" (8 mục)
docs/ANH_NOI_BO/DECISIONS.md  D-005 (429≠hỏng) · D-010 · D-018 · D-027 · D-045
                              D-050 · D-051 · D-056 · D-057
docs/KHUON_BAN_MODEL_NHA.md   ⭐ 31 chốt trước khi mở bán một model nhà
docs/VLM_NOI_BO/              tiền lệ H38 (model ngôn ngữ nhà)
docs/BAY_TRONG_CONG_CHAT_LUONG.md   sáu cái bẫy trong chính cổng chất lượng
```

### 5.2 P02 — OSS mining (đọc trước khi đi tìm ngoài internet)

```
render_gateway/comfy.py               ComfyUI GHIM Ở ĐÂU (6f7cd7f / 0.30.0)
render_gateway/workflows.py           cơ chế template + thẻ
render_gateway/workflows/README.md    cách thêm một model
render_gateway/workflows/catalog.json _khong_co_structure: ví dụ mẫu mực về
                                      cách GHI RA một thứ model KHÔNG làm được
                                      (đã grep mã ComfyUI để kết luận, không đoán)
apps/taovideo/models.py               4 mode đương kim làm được tới đâu
docs/QUALITY_LAB/04_EVALUATOR_LICENSE_MODEL_MATRIX.md   khuôn ghi giấy phép
```

### 5.3 P03 — BOM + chi phí

```
platform_core/gia_von.py + gia_von.json     giá vốn hiện hành trông thế nào
apps/taovideo/cost.py                       ⭐ mô hình giá của ĐƯƠNG KIM — mốc so sánh
apps/anhnoibo/gia.py                        giá của một model nhà đã mở bán
render_gateway/ngan_sach.py                 ⭐ khuôn "một hàm ngân sách, một đơn vị"
llm_gateway/ngan_sach.py · apps/ltt_llm/ngan_sach.py
platform_core/storage.py:300-390            R2Storage — chi phí egress/lưu trữ
docs/DATA_RETENTION_POLICY.md               giữ dữ liệu bao lâu = tốn bao nhiêu
```

---

## 6. Hàng rào an toàn cho **mọi** pha

Rút từ `CLAUDE.md` (dự án + toàn cục), `AGENTS.md`, và những gì P00 đo được.

### 6.1 Production và B-LAN

1. ⛔ Không sửa `C:\LTTPlatform\app\` — mất trắng, âm thầm, ở lần cập nhật sau.
2. ⛔ Không sửa `render_gateway/**` và `llm_gateway/**` (gate **G-B**).
3. ⛔ `D:\BOT GEMINI` chỉ đọc.
4. Deploy production: chuẩn bị hết, **người dùng bấm UAC**. Kiểm `git status` +
   migration + `ListAgents` trước khi deploy (deploy chép **cả cây**, không tách
   được phần của một phiên).

### 6.2 Ngân sách CPU — 10 lõi, dùng chung mọi phiên

Lúc P00 có **ba phiên tương tác khác** đang sống.

```powershell
python tools\cua_so_yen.py trang-thai     # TRƯỚC mọi lệnh nặng
```

- Lệnh nặng = `gate.py` (mọi chế độ), `test_nhanh.py`, ≥3 tệp test,
  `build_system_profile.py`.
- Trần cứng **`-n 6`**. Cây này **có** `loi_cho_bo_test` trong `tools/gate.py`
  (đã kiểm) ⇒ ngân sách được cưỡng chế đúng.
- ⛔ **Đừng chạy lệnh nặng để DÒ lỗi.** Gate ra phán quyết, không chẩn đoán.

### 6.3 GPU

- ⛔ Video V1 **không** chạy inference GPU trên máy A. Máy A đang phục vụ khách và
  **đã sập thật** vì tranh card (`0x116 VIDEO_TDR_FAILURE`, 26/08).
- ⛔ Không tải model lớn về máy A hay máy B cho việc của C-CLOUD.
- Test nào nạp model thật phải nằm sau rào `LTT_TEST_NANG`.

### 6.4 Cây và test

- Một cây duy nhất cho V3 (§0 của `CURRENT_SYSTEM_MAP.md` — xử lý hai nhánh
  `claude/ltt-video-ai-v3-audit-*` trước).
- **Dải số test: `700–799`.**
- Hai phiên cùng cây ⇒ lập giao ước file, dùng `Edit` chứ không `Write` cho tệp chung.
- `ho_so_he_thong.txt` là tệp **dẫn xuất** — người chạy lượt cuối sinh lại.

### 6.5 Bí mật

- Không xin người dùng gõ mật khẩu/OTP/thẻ vào chat.
- ⛔ Không dùng `cam` để kiểm artefact — nó **ghi đè biến môi trường thật của chủ
  máy**. Dùng `sdk/ltt_cai_dat_cli.py --home`.
- `tools/scan_source_secrets.py` trước mỗi commit có đụng cấu hình.
- C-CLOUD **không** giữ: khoá CSDL, khoá phiên, khoá gốc R2. Media vào/ra bằng
  presigned GET/PUT có hạn (Q102).

### 6.6 Giao diện

- Kiểm loopback để soi nhanh → **URL công khai `https://app.lttstudios.com` để chốt**.
- Đổi CSS/JS ⇒ cache-bust `?v={{ asset_ver }}`.
- Mở trình duyệt: `--cdp` vào Chrome thật của người dùng (Playwright tự mở bị
  Cloudflare CAPTCHA).
- Tài khoản kiểm thử: `akakenly.design@gmail.com`, **không** dùng admin.

---

## 7. Pha nên chạy tiếp — và điều kiện

**Đề xuất: P01 và P02 chạy song song — cả hai đã hết vật cản.**

| | Điều kiện | Ghi chú |
|---|---|---|
| **P01** | ✅ **chạy được ngay** | phần ADR-3 đã làm trước (`V-006`); P01 còn lại: ma trận generic-vs-ảnh-vs-Windows, đặc tả hợp đồng B-LAN bằng tên ca test, và **rà lại** scorecard bằng con mắt độc lập |
| **P02** | ✅ **đã mở khoá** bởi `V-001` | trục đo nay rõ: *đủ dùng cho video công ty xuất bản, ở chi phí thấp hơn đi mua* — không phải *đẹp hơn Seedance* |
| **P03** | cần P01 + P02 | phải hỏi giá **live**; và nay gánh thêm hai phép đo của `V-005`: **$ mỗi video trên ít nhất hai lớp GPU**, và **điểm hoà vốn thuê-hay-mua** |
| **P04 trở đi** | cần **duyệt ADR-3** | pha đầu tiên tiêu tiền thật |

⛔ **P00 dừng ở đây.** Không tự khởi động P01.

---

## 8. Đối chiếu D01–D12 — từng dòng, không bỏ dòng nào

Bắt buộc trong self-review của P00. Cột cuối trả lời đúng một câu: *kế hoạch rebase
này có làm sai quyết định đó không?*

| ID | Quyết định | Kế hoạch rebase làm gì | Có phá không |
|---|---|---|---|
| **D01** | Claude audit → đề xuất ADR → user duyệt **trước khi code kiến trúc tích hợp** | Cổng duyệt ADR chuyển từ cuối P01 xuống **sau P03**. Code tích hợp ở **P10** — vẫn nằm **sáu pha** sau cổng | ❌ **không**. Chữ trong D01 là *"trước khi code"*, không phải *"ở cuối P01"*. Cổng được đặt vào chỗ nó đo được, không được nới |
| **D02** | B-LAN tuyệt đối không đổi behavior/deployment trước khi C-CLOUD POC chạy độc lập | Thêm gate **G-B**: `git diff --stat` phải **rỗng** trên `render_gateway/**` + `llm_gateway/**`. Định nghĩa "không đụng" bằng **tên tệp test** thay vì văn xuôi | ❌ **không** — làm mạnh hơn |
| **D03** | V1: T2V + I2V + Character + V2V | Giữ nguyên 4 mode. **ADR-0 có thể dẫn tới đề nghị thu hẹp**, nhưng đó là **câu hỏi cho người dùng**, không phải một thay đổi P00 tự làm | ❌ **không** — P00 **không** sửa `USER_DECISIONS.md` |
| **D04** | ComfyUI là baseline; backend production quyết sau benchmark | Giữ. Thêm bằng chứng ủng hộ: repo **đã** có client ComfyUI ghim `6f7cd7f` và hệ template theo dữ liệu | ❌ **không** |
| **D05** | Runpod là provider V1; chỉ thiết kế interface đủ để thêm provider sau | Giữ. Ghi thêm: `platform_core/providers.py` **chính là** interface đó, đã có sẵn | ❌ **không** |
| **D06** | GPU baseline: A100 PCIe 80GB | Giữ. P03 phải ghi phương án dự phòng **dưới dạng đề xuất** nếu hết hàng — **không tự đổi** | ❌ **không** |
| **D07** | Sau khi budget khoá, Claude tự create/terminate trong budget | Giữ. **Siết thêm**: envelope theo pha (§4), và pha sau không mượn trước được | ❌ **không** — vẫn trong quyền D07, chỉ chia nhỏ để không cháy sớm |
| **D08** | Budget R&D cloud: **USD 150/tháng** | Giữ nguyên **tổng**. Chia theo pha, không đổi tổng | ❌ **không** |
| **D09** | Giá lai: khách thấy giá ổn định; backend ghi cost/margin thật | Giữ. **ADR-2** là câu hỏi *"giây-GPU quy ra giá ổn định bằng cách nào"* — không thay D09, mà là cách **thi hành** D09 cho một mô hình chi phí chưa từng có trong repo | ❌ **không** |
| **D10** | Launch V1 chỉ tier Quality/Pro | Giữ. Trong ADR-2, đường "bậc chạy-ngay đắt hơn" được nêu **và bị đánh dấu là mâu thuẫn D10** | ❌ **không** |
| **D11** | B-LAN không tham gia Video V1 | Giữ. Ghi rõ mã nguồn có sẵn câu *"video là hộ thứ tư"* để không ai đọc nhầm thành cho phép | ❌ **không** |
| **D12** | Mọi thay đổi ở feature branch/worktree; không làm trực tiếp master/production | Giữ, và đo được: cây `...\ltt-llm-api-http-guide-a3e123`, nhánh `claude/ltt-video-ai-v3-p00-3f5713`, `git status` chỉ có `?? docs/VIDEO_AI/` | ❌ **không** |

### Còn "thứ Claude vẫn phải hỏi user" trong `USER_DECISIONS.md`

| Mục | Trạng thái sau P00 |
|---|---|
| ADR kiến trúc sau P01/P03 | ⏳ ADR-0 hỏi **ngay**; ADR-1/2/3 ở cổng sau P03 |
| Login/password/OAuth · CAPTCHA · OTP/2FA · KYC · thẻ/nạp tiền · pháp lý | ⏳ chưa chạm — P00 **không** mở tài khoản nào |
| Chi phí vượt $150 hoặc đổi provider chính | ⏳ chưa phát sinh; envelope §4 làm việc này nhìn thấy sớm |
| Breaking change public API | ⏳ chưa chạm; P13 mặc định **additive** |
| Bất kỳ đề xuất dùng/sửa B-LAN cho Video V1 | ⏳ **không có đề xuất nào**; gate G-B chặn kể cả vô tình |

---

## 9. Tự rà soát P00 — cái gì đã kiểm lại, và cái gì đã sửa

Sau khi viết xong ba tài liệu, P00 đọc lại và đối chiếu **từng trích dẫn** với mã.
Ghi ra vì một tài liệu audit sai số dòng thì lượt sau sẽ đi tìm nhầm chỗ.

| Đã sửa | Sai thế nào |
|---|---|
| **28 số dòng** trong `CURRENT_SYSTEM_MAP.md`, 7 trong `PROMPT_PACK_V3_REVIEW.md` | Bản đầu lấy số dòng từ **tệp gộp nhiều nguồn** thay vì từ tệp thật (vd `render_gateway/api.py:299` → thật là `:82-89`; `jobs.py:159` → `:140`) |
| `setup/rollback.ps1` | **không tồn tại** — đường thật là `deploy/windows/rollback.ps1` |
| *"24 route đóng băng"* | Đếm bằng mã ra **27**. Tài liệu repo trôi 3 — thành một phát hiện riêng (`CURRENT_SYSTEM_MAP.md` §3.6b) |
| *"6 tệp test UI"* của `taovideo` | `test_172` là **hợp đồng tiền**, không phải UI ⇒ 5 tệp UI + 1 tệp tiền |
| *"App GPU trên máy A: `autosubvideo`, …"* | `autosubvideo` khai `requires=("ffmpeg",)`, **không** khai `gpu`. Chỉ `taoclipngan` và `upscalevideo` khai `("gpu","ffmpeg")` |
| *"2× card ~16GB"* | Suy từ tên card. Thay bằng trích thẳng `platform_core/gpu.py:4` |

| Đã kiểm và **đúng** | Bằng chứng |
|---|---|
| Mọi tệp/test được trích dẫn có tồn tại | `docs/ANH_NOI_BO/DECISIONS.md`, `docs/KHUON_BAN_MODEL_NHA.md`, `tools/cham_mu.py`, `sdk/ltt_cai_dat_cli.py`, `render_gateway/workflows/README.md`, `voice_sidecar/`, và 8 tệp `tests/test_{60,79,148,172,178,212,308,334}_*` |
| "31 chốt" của `KHUON_BAN_MODEL_NHA.md` | tệp tự ghi *"Tổng: 18/31"* |
| `LTT_WORKER_POOLS` có thi hành thật | `job_worker.py:83`, `setup/4-nghiem-thu.ps1:72` |
| Đồ thị pha không có phụ thuộc vòng/chồng chéo | P10←P09 · P11←P10 · {P12,P13,P14}←P11 · P14←P10+P11 · P15←P12+P13+P14 — khớp `PHASE_GRAPH.json`, chỉ thêm hai nút cổng |
| P00 không đụng B-LAN/production | `git status` = `?? docs/VIDEO_AI/`; `git diff --stat -- render_gateway llm_gateway` **rỗng** |

**Giả định còn lại chưa có bằng chứng — ghi ra thay vì giấu:**

1. Ba route lệch (24 vs 27) *"gần như chắc chắn"* là `chat/completions` + `messages`
   + `responses`. Suy từ Q106/Q107, **chưa đối chiếu lịch sử git**. P13 xác nhận.
2. B-LAN *"đang chạy"* suy từ **provider đang bán trên `/gia-api`**, không phải từ
   một cú `GET /live`. P01 kiểm (chỉ-đọc).
3. Hai nhánh `claude/ltt-video-ai-v3-audit-*` *"là lượt khởi động V3 trước"* — suy
   từ tên nhánh + commit gốc trùng. **Chỉ người dùng xác nhận được.**
4. `apps/taovideo` *"đang bán"* — bằng chứng mạnh (nav công khai + manifest
   `enabled=True`, `lifecycle="released"`), nhưng **không** kiểm được là có đơn
   hàng thật hay không (cần DB production).
