# P01 — GHIM WanGP THƯỢNG NGUỒN + CỔNG GIẤY PHÉP + TIỀN TRẠM CLOUD

Đo 2026-09-06. Mọi số ở đây **đọc từ nguồn thật** (GitHub API, RunPod API), không
chép từ tài liệu.

---

## 1. Danh tính thượng nguồn

| | |
|---|---|
| Kho | **`deepbeepmeep/Wan2GP`** (sản phẩm tên **WanGP**) |
| Mô tả | *"A fast AI Video Generator for the GPU Poor. Supports Wan 2.1/2.2, LTX-2, Qwen Image, Hunyuan Video, LTX Video and Flux."* |
| Sao / fork | **9.190** ⭐ · 1.446 fork |
| Là fork của | **`Wan-Video/Wan2.1`** (Apache-2.0, 16.937 ⭐) |
| Nhánh mặc định | `main` |
| Hoạt động | commit gần nhất **2026-09-05** — kho đang sống |

### SHA ghim

```
1e1dd2757f24923f008593d9d4ec09062234be20
```

Commit `2026-09-05T02:02:35Z`, *"fixed ref video memory"*. **Mọi việc từ P01 tới
P03 đứng trên đúng SHA này.** Đổi SHA là một quyết định, phải ghi vào
`DECISIONS.md`.

### sha256 các tệp đã đọc ở SHA trên

| Tệp | sha256 | Byte |
|---|---|---:|
| `LICENSE.txt` | `67c8e68389c945423c560c13936f0a960e5d2ffdcc5bb2ded4122fe1b095960f` | 21.469 |
| `README.md` | `2a79e0c6077100044617de47d07f986dc059eccaee9bcb8e56658d5681a32cf7` | 53.494 |
| `plugins.json` | `b2b8c24f84bca72983b0efc73c87971ec29b63f02459d31edc8c0e3b072d2638` | 12.408 |
| `docs/API.md` | `21268a666077d550d3da60b82ddfdc8664878c1d231d64e3c0fe1b0a8e4b29dc` | 47.761 |
| `docs/DEEPY.md` | `4d6c6c9d63eb3882ebcbe3e0d5e3d5a05da966e93f38eca202552ba8034fa0f2` | 30.630 |
| `docs/CLI.md` | `15cb9b74c1d4b6c593cc01736076103c3f0405a4b2e4ee7587428f1b7d08a74b` | 12.107 |
| `docs/PLUGINS.md` | `82845c231683301ec02eb039e1c9cf887380533ec0476aabf0448eb33da64414` | 25.291 |

Tái hiện:

```bash
SHA=1e1dd2757f24923f008593d9d4ec09062234be20
curl -sS "https://raw.githubusercontent.com/deepbeepmeep/Wan2GP/$SHA/LICENSE.txt" | sha256sum
```

---

## 2. 🔴 CỔNG GIẤY PHÉP — phần quan trọng nhất của P01

⚠️ GitHub gắn nhãn `NOASSERTION / Other`. **Không phải Apache-2.0.** Kho là fork
của `Wan-Video/Wan2.1` (Apache-2.0) nhưng tác giả áp giấy phép riêng lên phần
đóng góp của mình.

Giấy phép thật: **`WanGP Community License 2.0`** — giấy phép tự viết, không phải
OSI, 21.469 byte, 11 mục.

### Phán quyết: ✅ **PASS cho V2.1 nội bộ**, ⛔ **CHẶN cho việc bán ra ngoài**

Bốn điều khoản nói thẳng, không cần suy diễn:

| Điều | Nội dung |
|---|---|
| **1.8** định nghĩa *Free Use* | *"personal use, hobby use, research use, educational use, evaluation, **internal company use, internal business use**, studio use, agency use, client work..."* |
| **1.9** loại trừ khỏi *Restricted Commercialization* | *"(i) **internal company use or internal business use**"* |
| **3.3** | *"**No separate reseller or commercial license is required solely because the user is a company**, studio, agency, or revenue-generating business, so long as the Software is not sold, monetized, or made available to third parties in a manner described in Section 5."* |
| **7.1** | *"**Private use** of the Software through an API, local service, automation, batch processing, **queue processing**, script, plugin, or **Headless Usage** is permitted for Free Use."* |

⇒ Kiến trúc V2.1 — A-CONTROL gọi WanGP riêng tư qua API/MCP, hàng đợi, headless,
nội bộ nhân viên, `public=False`, `api_exposed=False` — **nằm đúng trong phần
được cấp miễn phí**. `D-V2-011` không phải một lựa chọn thận trọng nữa; nó là
**điều kiện của giấy phép**.

### ⛔ Và đây là phần chặn tương lai thương mại

**5.2** liệt kê thứ **cần giấy phép thương mại riêng bằng văn bản**:

> (b) offering paid API, paid SaaS, paid hosted, or paid managed access to WanGP;
> (d) embedding the Software in a paid product or paid service;
> (f) charging separately for access to the Software, even if the Software is
> bundled with other tools or services;
> **(g) exposing the Software to customers or end users as a paid feature,
> add-on, or monetized backend component.**

**7.2** nhắc lại: *"Exposing the Software to third parties through an API, local
service, hosted endpoint... in exchange for consideration is Restricted
Commercialization and requires a separate written reseller or commercial
license."*

🔴 **`5.2(g)` mô tả gần như nguyên văn mô hình của LTT**: nền tảng bán công cụ AI
theo credit, mỗi công cụ là một app có thu tiền. Một app video chạy WanGP, người
dùng trả credit để bấm nút — đó là *"exposing the Software to end users as a paid
feature"*.

### Có một đường hẹp, và tôi KHÔNG tự kết luận nó đi được

**§6** cho phép bán **Output**: *"you may use, reproduce, publish... **sell**, and
license Outputs for any lawful purpose"*, chỉ cần ghi công (*"Made with WanGP"*)
khi có **Direct Output Sale**. Và **1.9(iv)** nói Direct Output Sale **không**
thuộc Restricted Commercialization.

**1.7** định nghĩa *Direct Output Sale* là *"charging separate consideration for
an Output... where the **principal value of the transaction is the Output
itself**"*.

⇒ Hai cách đọc cho **cùng một nút bấm** của LTT:

| Cách đọc | Kết luận |
|---|---|
| Khách trả credit để **nhận một video** — giá trị chính là tệp video | Direct Output Sale → **được phép**, chỉ cần ghi công |
| Khách trả tiền để **dùng công cụ tạo video** trên nền tảng | `5.2(g)` → **cần giấy phép thương mại** |

⛔ **Tôi không phải luật sư và không kết luận cái nào đúng.** Đây là việc của chủ
dự án + tư vấn pháp lý, và nó phải xong **trước khi** mở cổng thương mại, không
phải sau.

⭐ Điểm đáng nhớ: **giấy phép là cổng thứ hai, độc lập với cổng kinh tế.** V3 chết
ở `V-018` vì giá vốn cao hơn giá bán của đối thủ. Kể cả khi V2.1 giải xong bài
toán giá, nó **vẫn** còn cổng này. Hai cổng không thay thế nhau.

📇 Liên hệ cấp phép thương mại (ghi trong **5.4** của chính giấy phép):
`deepbeepmeep@yahoo.com`, hoặc Discord của tác giả.

### Vật liệu bên thứ ba

**2.2** giữ nguyên giấy phép riêng cho Third-Party Materials; kho có sẵn
`docs/third_party_licenses/` (`Apache-2.0.txt`, `BSD-3-Clause.txt`, `MIT.txt`).
⚠️ **Giấy phép của bản thân các model/weight là một cuộc kiểm riêng**, chưa làm ở
P01 — Wan 2.2, LTX-2, Qwen Image, Hunyuan, Flux mỗi cái một điều khoản. Flux nói
riêng có bản thương mại và bản phi thương mại.

---

## 3. Bề mặt kỹ thuật ở SHA ghim

Bố cục gốc: `wgp.py` (**825 KB**, một tệp), `Dockerfile`, `entrypoint.sh`,
`run-docker-cuda-deb.sh`, `plugins.json`, `setup.py`, và các thư mục `models/`
`plugins/` `preprocessing/` `postprocessing/` `profiles/` `defaults/` `shared/`
`docs/` `tests/` **`wangp-agent/`**.

### Ánh xạ vào hợp đồng engine của pack

Pack định nghĩa giao diện khái niệm: `health · capabilities · stage_media ·
submit · progress · cancel · result · cleanup`. Ở SHA này, **cả tám đều có thật**:

| Hợp đồng pack | Thứ thật trong WanGP | Nguồn |
|---|---|---|
| `capabilities` | `list_model_defs()` · `list_model_metadata()` · `get_default_settings(model_type)` | `docs/API.md` |
| `stage_media` | `wangp_create_gallery_upload(filename)` → **PUT byte thô vào URL dùng-một-lần, ngắn hạn** | `docs/API.md` §MCP Server |
| `submit` | `submit_task(settings)` · `submit_manifest([...])` · `submit(source)` | `docs/API.md` |
| `progress` | `ProgressUpdate` · `PreviewUpdate` · `StreamMessage` (Streaming Events) | `docs/API.md` |
| `cancel` | `job.cancel()` — **hợp tác**, kết quả trả `success == False` + mục huỷ trong `result.errors` | `docs/API.md` §Cancellation |
| `result` | `GenerationResult` / `GenerationError` | `docs/API.md` |
| `cleanup` | thư mục output + gallery | `docs/API.md` |

⭐ **`stage_media` là bất ngờ đẹp nhất.** Kiến trúc V2.1 §5 đòi *"scoped transfer"*
cho media — WanGP đã có sẵn đúng thứ đó: route truyền media **dùng một lần, sống
ngắn**. Không phải tự chế.

### API là **Python in-process**, không phải REST

`docs/API.md` tên đầy đủ là *"WanGP Python API"*: `init(...) -> WanGPSession`, rồi
`session.submit_task(...)`. Tức muốn gọi từ A-CONTROL (máy khác) thì **phải có
một tiến trình trên C-CLOUD** — hoặc MCP server của chính WanGP, hoặc một service
mỏng của ta import API đó.

### MCP server — bằng chứng cho `O-001`

```bash
python wgp.py --mcp --mcp-transport streamable-http --mcp-host 127.0.0.1 --mcp-port 7866
```

Client nối tới `http://<host>:<port>/mcp`. Giữ **một `WanGPSession` ấm**, nên
agent làm discovery rồi generate nhiều lượt mà không phải khởi động lại tiến
trình WanGP.

🔴 **Nhưng tài liệu của chính nó cảnh báo:** *"Use `--mcp-host 0.0.0.0` **only on
a trusted network or behind an authenticated reverse proxy**."* ⇒ **MCP không có
xác thực.**

⇒ `O-001` (MCP trực tiếp vs cầu mỏng) đã có bằng chứng, và câu trả lời **không
phải một trong hai**: MCP dùng được làm giao thức, nhưng **vẫn cần một lớp xác
thực trước nó**. Chốt chính thức ở P02 theo đúng lịch, nhưng hướng đã rõ.

⛔ `COST_AND_SAFETY` cấm *"unauthenticated raw WebUI/MCP port"* — điều này giờ có
một lý do kỹ thuật cụ thể, không còn là nguyên tắc chung.

### Deepy

`docs/DEEPY.md` (30.630 B) + `wangp-agent/SKILL.md` + `wangp-agent/agents/`.
README: Deepy nối được tới **MCP Server ngoài**, có *"Deepy Prime Guidance"* và
*"Deepy Filesystem"*. `D-V2-007` (Deepy trước, chưa dựng agent LTT song song)
đứng vững — Deepy có thật và là công dân hạng nhất trong kho.

---

## 4. Tiền trạm cloud — đo lúc 2026-09-06

### Tài nguyên đang sống (RunPod `kiem-ke`, chỉ đọc)

| Loại | ID | Tên thật |
|---|---|---|
| network volume | `uizchbiet5` | **`lttv-models-v1`** |
| endpoint serverless | `uwzftpd3utftfn` | **`lttv-worker`** |
| **pod** | — | **0 — không có compute nào đang chạy** ✅ |
| tài nguyên mồ côi | — | **0** ✅ |

⚠️ **Sửa một chỗ tôi chép sai ở P00:** tôi ghi volume tên `lttvideo-models-v1`
theo tài liệu V3. Tên **thật** là `lttv-models-v1`. Tiền tố đã đổi thành `lttv-`
từ `V-002` mà tài liệu V3 không được cập nhật hết. Đúng lỗi *"đọc thứ đại diện
thay vì đọc thứ thật"* — và nó lọt vào chính tệp tôi vừa viết để chống điều đó.

### Tiền (kỳ 01/09 → 06/09)

| | |
|---|---|
| Số dư | **$45,35** |
| Sàn credit không được tiêu | **$31,50** |
| ⇒ **thật sự tiêu được** | **≈ $13,85** |
| Mức chi hiện thời | **$0,0290/giờ** — chính là volume, chảy liên tục |
| Đã tiêu tháng này | compute **$3,33** · lưu trữ **$1,11** |
| Cầu dao | **PHỤC VỤ [CẢNH BÁO]** |

🔴 **Con số "2,9 giờ GPU mua được" mà công cụ V3 in ra là SAI cho P01.** Nó chia
$13,85 cho hằng số **$4,79/giờ** — giá **Serverless Flex** mà `V-017` đo được.
P01 thuê **Pod**, và Pod tính giá khác hẳn. Ở giá Pod thật đo hôm nay, $13,85 mua
được **~10 giờ** A100, không phải 2,9.

⭐ Đây đúng là cơ chế `V-017`: một hằng số đúng cho ngữ cảnh này bị dùng cho ngữ
cảnh khác, và không có gì đỏ lên. Đừng sửa bằng cách gõ số mới — **P01 dùng giá
đo được tại thời điểm chạy**, và số ở đây có ngày tháng đi kèm.

### 🔴 US-KS-2 chỉ còn HAI loại GPU, cả hai đều "Low"

Volume `uizchbiet5` nằm ở **`US-KS-2`** và `dataCenterId` **không sửa được** — Pod
muốn gắn volume thì **phải** ở đúng datacenter đó.

| GPU | VRAM | Giá/giờ | Tồn kho |
|---|---:|---:|---|
| **A100 SXM** | 80 GB | **$1,390** | **Low** |
| **H100 NVL** | 94 GB | $2,590 | **Low** |

Để so sánh, **toàn cầu** có 40/48 loại mua được, rẻ nhất $0,130/giờ (RTX 3070
8 GB); RTX A5000 24 GB **$0,160**, RTX 4090 24 GB **$0,340**, A40 48 GB $0,350.

⇒ Gắn volume có **giá của nó**: sàn $1,39/giờ thay vì $0,16/giờ, và tồn kho thấp
nghĩa là có thể **không thuê được lúc cần**.

---

## 5. Trạng thái P01

**Nửa không tốn tiền: XONG.** Mục 1, 2, 3 của *Việc phải làm* đã đủ bằng chứng.

**Nửa tốn tiền: CHỜ DUYỆT CHI.** Mục 5–9 (boot WanGP thật, kiểm WebUI/API/MCP/
queue/cancel, rồi tắt) cần thuê GPU thật. Theo luật thường trực của dự án
(*ba ranh giới giữ lại: deploy, **bút toán tiền**, UAC*), phiên này dừng ở đây và
trình phương án.

Phương án chi tiết + hai lựa chọn: `PROJECT_STATE.md`, mục *Kế hoạch chi P01*.
