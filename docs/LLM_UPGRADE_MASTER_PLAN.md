# LLM_UPGRADE_MASTER_PLAN

Phase 0 chốt ngày 2026-09-09. Căn cứ: `LLM_UPGRADE_BASELINE.md` (mã) và
`LLM_OPEN_SOURCE_RESEARCH.md` (thượng nguồn). Điểm: `LLM_QUALITY_LEDGER.md`.

---

## 0. Một chỗ đi chệch thứ tự của prompt — và vì sao

Prompt xếp: `1 identity → 2 observability → 3 lifecycle → 4 security → …`

**W2 không thể làm ở vị trí thứ 2.** Toàn bộ lời giải quan trắc (mẫu A/B/C của
báo cáo nghiên cứu) đứng trên một câu hỏi mà kho **không trả lời được**: máy B
đang chạy llama-swap và llama.cpp bản nào? (G-02). Thiết kế trước khi biết là
thiết kế trên giấy — đúng cạm bẫy *"đọc thứ đại diện thay vì đọc thứ thật"*.

Và W7 (fail-open auth) là hạng mục **duy nhất** đang bị rubric ép trần cứng
(Security ≤ 90), trong khi bản sửa là một điều kiện khởi động — rẻ, cơ học, đo
được mà không cần máy B.

⇒ Thứ tự thi hành:

```
P1  W1  + W12(a)   identity / config / chú thích đã hết đúng
P2  W7             fail-closed khởi động            (kéo lên từ vị trí 4)
P3  W10            ghim + ghi lại phiên bản          (mở khoá cho P4)
P4  W2             quan trắc                         (phụ thuộc P3)
P5  W5 + W4        phân loại lỗi · vòng đời
P6  W6             điều phối máy A
P7  W8 + W9        token/ngữ cảnh · tính tiền
P8  W3 + W13       baseline hiệu năng · corpus hồi quy
P9  W11 + W12(b)   phát hành · tài liệu · runbook
P10 rà soát liên hệ thống → FULL GATE #1
```

`ASSUMPTION` của prompt: quan trắc làm được ngay sau identity.
`ACTUAL EVIDENCE`: `grep -rniE "dau_van_tay|VERSION_FILE|api/version" llm_gateway/` → rỗng.
`ACTUAL STATE`: kho không biết bản đang chạy.
`IMPACT`: W2 không có nền để thiết kế.
`NEW DECISION`: chèn P3 trước W2, kéo W7 lên P2.

---

## P1-01 · Chú thích trỏ sai phép kiểm

**ID** P1-01 · **HỆ CON** W1/W12 · **ĐIỂM HIỆN TẠI** 93 (W1) / 85 (W12)

**VẤN ĐỀ** — `llm_gateway/config.py:121` nói `tests/test_312` giữ cho hai bản
sao của trần token không lệch. `tests/test_312_vps_khoa_dich_vu.py` là khoá dịch
vụ VPS. Phép kiểm thật là `tests/test_250_llm_gateway.py:45`.
Chỗ thứ hai: `platform_core/public_api/config.py:76`.

**BẰNG CHỨNG** — `docs/VLM_NOI_BO/RA_SOAT_THAM_SO_LTT_LLM.md:559` **đã ghi nhận**
vụ trùng số test này. Bản vá lúc đó sửa tài liệu và bỏ quên hai chú thích trong
mã.

**NGUYÊN NHÂN GỐC** — một chú thích viện dẫn phép kiểm bằng **số hiệu**, mà số
hiệu test là thứ hai phiên có thể cùng cấp phát. Tên tệp thì không đụng nhau.

**HÀNH VI HIỆN TẠI** — người đọc `config.py` đi tra `test_312`, thấy nó nói về
VPS, và kết luận sai theo **một trong hai** hướng: "chú thích nói dối, chắc
không có phép kiểm nào" (sai, có) hoặc "chắc mình tra nhầm" (rồi bỏ qua).

**HÀNH VI ĐÍCH** — chú thích trỏ tên tệp đầy đủ; và một phép kiểm **cưỡng chế**
rằng mọi viện dẫn `tests/test_NNN` trong mã lõi phải khớp một tệp có thật.

**PHƯƠNG ÁN**
1. Sửa hai chú thích. — rẻ, nhưng lần trôi sau lặp lại y hệt.
2. Sửa + một phép kiểm quét viện dẫn. — **CHỌN**.
3. Cấm viện dẫn test trong chú thích. — vứt đi một thứ đang có ích.

**THIẾT KẾ TỐI THIỂU ĐÃ CHỌN** — (2). Phép kiểm đọc mã bằng **AST/regex trên
chuỗi chú thích**, không import gì, và tự kiểm chính nó (bộ nhớ dự án:
*"bộ dò quét văn bản trừng phạt việc giải thích"* — nên nó phải bỏ qua chính
tệp phép kiểm và các tệp `docs/`).

**TỆP** `llm_gateway/config.py` · `platform_core/public_api/config.py` ·
`tests/test_NNN_*.py` (mới)
**BẢO MẬT / HIỆU NĂNG / TIỀN / STREAM / GPU / DEPLOY** — không chạm.
**HOÀN NGUYÊN** — `git revert`; không có trạng thái runtime.
**NGHIỆM THU HẸP** — chạy tệp test mới + `test_250` + `test_334`.
**ĐIỂM KỲ VỌNG** W12 → 92 · **TRẠNG THÁI** CHƯA LÀM

---

## P1-02 · Số đã trôi trong `manifest.py` và `ngan_sach.py`

**ID** P1-02 · **HỆ CON** W1/W8/W12 · **ĐIỂM HIỆN TẠI** 94 (W8)

**VẤN ĐỀ** — ba khối văn nói số cũ:
* `apps/ltt_llm/ngan_sach.py:66` — *"`qwen38-vision` nạp với `-c 65536`"*; giá
  trị gán ngay dưới là `131_072`.
* `apps/ltt_llm/manifest.py:32,94` — trần vào **96 256**; thật là **169 984**.
* `apps/ltt_llm/manifest.py:42-46` — *"engine `-c 131072`, công bố 89K; vision
  trần vào 30 720, công bố 28K"*; thật là `-c 204800`, **156 385**.

**BẰNG CHỨNG** — `llama-swap.yaml:155,199` = `204800` / `131072`;
`ngan_sach.py:103,120` = `169_984` / `156_385`. Runtime **nhất quán**; chỉ văn sai.

**NGUYÊN NHÂN GỐC** — và đây là phần đáng học: đoạn văn sai ở `manifest.py`
**chính nó là một thông báo đính chính** (*"🔴 SỬA 01/09 — BA CON SỐ Ở ĐOẠN NÀY
ĐỀU ĐÃ TRÔI"*). Đợt 03/09 nâng 131K→200K sửa **giá trị** ở `ngan_sach.py` và
không sửa **văn** ở hai nơi trích lại giá trị ấy. Chính `manifest.py` đã đặt tên
cho lỗi này: *"Sửa giá trị không phải sửa hình dạng."*

**HÀNH VI ĐÍCH** — không khối văn nào trong `apps/ltt_llm/` và `llm_gateway/`
**gõ lại** một con số đã có tên hằng. Nói tên hằng, hoặc nói "hỏi `/health`".

**PHƯƠNG ÁN**
1. Sửa ba khối văn. — sẽ trôi lại ở lần đổi `-c` sau.
2. Sửa + phép kiểm cấm gõ lại các số dẫn xuất trong văn của hai gói ấy. — **CHỌN**.
3. Sinh chú thích tự động. — quá tay cho một hệ nội bộ.

⚠️ Cạm bẫy đã biết (bộ nhớ dự án): phép kiểm quét văn bản **báo động trên chính
đoạn giải thích nó**. Nên nó phải cho phép một dấu miễn trừ tường minh cho ngữ
cảnh lịch sử (mẫu đã có ở `test_604`: nhắc số cũ thì phải nói rõ đó là lịch sử).

**TỆP** `apps/ltt_llm/ngan_sach.py` · `apps/ltt_llm/manifest.py` · test mới
**HOÀN NGUYÊN** — `git revert`.
**NGHIỆM THU HẸP** — test mới + `test_334` + `test_604` + `test_256`.
**ĐIỂM KỲ VỌNG** W8 → 98 · W12 → 95 · **TRẠNG THÁI** CHƯA LÀM

---

## P1-03 · Bản sao `169984` gõ tay trong đường deploy

**ID** P1-03 · **HỆ CON** W1 · **[?] cần đối chiếu trước khi thiết kế**

**VẤN ĐỀ** — `deploy.ps1:274,283,309` ghi `LTT_LLM_MAX_INPUT_TOKENS=169984` bằng
số gõ tay, ba lần. `ngan_sach.py:59-62` **đã cảnh báo đúng chuyện này** và nói
`test_334` chốt "hai bản sao đó".

**PHẢI LÀM TRƯỚC KHI THIẾT KẾ** — đọc `test_334:270-290` để biết nó chốt **mấy**
trong số ba chỗ. Nếu đủ ⇒ **KHÔNG CẦN THAY ĐỔI**, chỉ ghi lại. Nếu thiếu ⇒ mở
rộng phép kiểm, **không** viết bộ sinh cấu hình.

⛔ Không được giả định thiếu. Baseline đánh dấu mục này `[?]` đúng vì thế.

**ĐIỂM KỲ VỌNG** W1 → 98 · **TRẠNG THÁI** CHƯA ĐỌC

---

## P2-01 · Cổng fail-closed khi nghe ra ngoài loopback

**ID** P2-01 · **HỆ CON** W7 · **ĐIỂM HIỆN TẠI** 88 (trần rubric ép ≤ 90)

**VẤN ĐỀ**

```python
# llm_gateway/api.py:255
def auth(authorization: str = Header(default="")) -> None:
    if not cfg.token:
        return          # dev: chưa đặt token → không chặn
```

`main.py:118-120` chỉ log cảnh báo. Không chỗ nào nối `host` với `token`.

**BẰNG CHỨNG** — `deploy.ps1:301,303` ghi `LTT_LLM_HOST=127.0.0.1` + token sinh
ra ⇒ đường mặc định **an toàn**. Nhưng máy A phải gọi được ⇒ ai đó phải sửa
`gateway.env` thành `0.0.0.0` bằng tay. `nap_env` (`main.py:32-56`) nhận **mọi**
khoá `LTT_LLM_*` kể cả giá trị rỗng ⇒ `token=""` ⇒ mọi đường mở cho cả LAN.

⚠️ **Chưa xác minh trạng thái máy B thật.** Đây là rủi ro tiềm tàng, không phải
tuyên bố "production đang mở". Phần đo máy B thuộc chính phase này, làm **trước**
khi sửa.

**NGUYÊN NHÂN GỐC** — ranh giới đang là **giao ước** ("nhớ đặt token khi mở
host"), và `CLAUDE.md` của chính dự án ghi: *"ranh giới CƠ HỌC thắng giao ước"*.

**HÀNH VI ĐÍCH** — `host` không phải loopback **và** `token` rỗng ⇒ **từ chối
khởi động** (`SystemExit`), cùng khuôn với chốt "cổng đã có người giữ" đã có ở
`main.py:122-146`. Loopback + không token ⇒ vẫn chạy (đường dev, giữ nguyên).

**PHƯƠNG ÁN**
1. Bắt buộc token luôn. — phá đường dev trên máy không có GPU, và phá test.
2. Điều kiện `host ≠ loopback ∧ token rỗng` ⇒ từ chối khởi động. — **CHỌN**.
3. Chặn trong `auth()` (trả 401 khi cấu hình sai). — **TỪ CHỐI**: dịch vụ vẫn
   "chạy", `/live` vẫn xanh, người vận hành thấy một cổng khoẻ nhưng vô dụng.
   Hỏng lúc **khởi động** to hơn hỏng lúc **phục vụ**.

**THIẾT KẾ TỐI THIỂU ĐÃ CHỌN** — (2), đặt trong `main.py` cạnh chốt cổng-bị-giữ.
Không đổi `api.py`: `auth()` giữ nguyên ngữ nghĩa, chỉ là trạng thái nguy hiểm
không còn tới được nó.

⭐ Vì sao ở `main.py` chứ không ở `Config.from_env()`: `Config` là dữ liệu thuần
và **test dựng nó tự do** (`test_250`, `test_269`, `test_363` đều gọi nó). Ném
lỗi trong đó sẽ phá các test không liên quan gì tới bảo mật.

**TỆP** `llm_gateway/main.py` · test mới
**BẢO MẬT** — đây chính là mục đích. **HIỆU NĂNG/TIỀN/STREAM/GPU** — không chạm.
**DEPLOY** — ⚠️ **có**: nếu máy B **đang** chạy `0.0.0.0` + token rỗng, bản này
sẽ **không khởi động lại được**. Nên thứ tự bắt buộc: **đo máy B trước, sửa
`gateway.env` trước, deploy sau.**
**HOÀN NGUYEN** — `git revert`; và `releases/auto-*` của `deploy.ps1:99` giữ bản
đang chạy.
**NGHIỆM THU HẸP** — test mới (4 tổ hợp host×token) + `test_250` toàn tệp.
**ĐIỂM KỲ VỌNG** W7 → 98 · **TRẠNG THÁI** CHƯA LÀM

---

## P3-01 · Ghi lại phiên bản thượng nguồn máy B

**ID** P3-01 · **HỆ CON** W10 · **ĐIỂM HIỆN TẠI** 78

**VẤN ĐỀ** — không tệp nào trong kho ghi phiên bản llama-swap / llama.cpp đang
chạy. `/health` của cổng báo `thuong_nguon.{url,ma,song}` — không có phiên bản.

**BẰNG CHỨNG** — `grep -rniE "dau_van_tay|VERSION_FILE|api/version" llm_gateway/`
→ rỗng. `deploy.ps1` chỉ chép `llama-swap.yaml`, không chạm binary.

**HÀNH VI ĐÍCH** — `/health` mang thêm `thuong_nguon.phien_ban`, đọc từ
`GET /api/version` của llama-swap (mẫu A). Và kho có một tệp ghim ghi **bản được
chúc phúc**, để `nghiem_thu.py` so được.

**RỦI RO ĐÃ BIẾT** — nếu bản đang chạy cũ hơn `8fa85899` thì `/api/version` có
thể **không tồn tại**. Xử lý: thiếu ⇒ báo `null` + `"khong doc duoc"`, **không**
làm `/health` đỏ. Một chốt quan trắc không được biến thành một chốt vào cửa —
đúng luật `_xem_gpu()` đã đặt ở `api.py:305-310`.

**ĐIỂM KỲ VỌNG** W10 → 95 · **TRẠNG THÁI** CHƯA LÀM

## P3-02 · `nang_llamacpp.ps1` mặc định lấy bản mới nhất

**ID** P3-02 · **HỆ CON** W10

**VẤN ĐỀ** — `nang_llamacpp.ps1:107-118`: không có `-Ban` ⇒ hỏi GitHub API, lấy
release đầu tiên có gói `win-cuda-$Cuda-x64`. Trái §25.

**NÓI CÔNG BẰNG** — script **đã có** rollback (`$saoLuu`, dòng 95-101), in phiên
bản trước/sau, và có chốt `if ($Ban -eq $cu) { exit 0 }`. Nó chỉ chạy khi người
vận hành gõ tay. Khuyết tật là **không có bản được chúc phúc nào để so**.

**HÀNH VI ĐÍCH** — mặc định là **bản ghim trong kho**; `-Ban latest` phải gõ
tường minh mới đi hỏi GitHub.

**ĐIỂM KỲ VỌNG** W10 → 98 · **TRẠNG THÁI** CHƯA LÀM

---

## P4-01 · Bật `--metrics`, và đọc thứ đã đếm sẵn

**ID** P4-01 · **HỆ CON** W2 · **ĐIỂM HIỆN TẠI** 72 (thấp nhất)

**VẤN ĐỀ** — cổng không có bề mặt đo lường nào. Không TTFT, không tok/s, không
số đếm theo nhóm lỗi, không lịch sử.

**BẰNG CHỨNG THƯỢNG NGUỒN** — `server-context.cpp:4669`: `/metrics` tắt theo mặc
định. `llama-swap.yaml:112-117` (`CHUNG`) không có `--metrics`. Nhưng các điểm
cộng dồn chạy **vô điều kiện** (`server-context.cpp:3412,4066,4072,4075,4129`).

⇒ **Máy B đang đếm và vứt đi.** Bật cờ tốn **0** trên đường nóng.

Và `CHUNG` đã bật `--spec-type draft-mtp`, còn thượng nguồn phơi
`llamacpp:spec_decode_num_accepted_tokens_per_pos_total` — tức tỉ lệ chấp nhận
suy đoán (số W3 cần) đang bị vứt cùng.

**THIẾT KẾ TỐI THIỂU** — (a) thêm `--metrics` vào `CHUNG`; (b) `/health` tóm tắt
vài số từ `/metrics` (loopback, sau khoá bearer); (c) cổng tự đếm thứ **chỉ nó
biết**: từ chối theo nhóm (429-đầy / 429-bận / 429-card bẩn / 413 / 404 / 502),
vì llama.cpp không bao giờ thấy các lượt ấy.

**KHÔNG LÀM** — không Prometheus server, không Grafana, không Langfuse, không
bắt prompt/response. Lý do đầy đủ ở báo cáo nghiên cứu O6/O7/O8.

**PHỤ THUỘC** — P3-01 phải xong trước: (b) chỉ thiết kế được khi biết bản đang
chạy có gì.
**ĐIỂM KỲ VỌNG** W2 → 98 · **TRẠNG THÁI** CHẶN BỞI P3-01

---

## P5 → P9 — thiết kế sau, và cố ý thế

Rubric §19 nói *"không code trước khi item quan trọng có design đủ rõ"*. Nó
**không** nói phải thiết kế hết mọi item ở Phase 0. Bốn item dưới đây đều phụ
thuộc số đo mà P2/P3/P4 sẽ sinh ra; thiết kế chúng bây giờ là đoán.

| ID | Hệ con | Câu hỏi phải trả lời trước khi thiết kế |
|---|---|---|
| P5-01 | W5 | timeout có **thật sự** lẫn với unreachable ở tải thật không? (`upstream_timeout_s=600` vs prefill 180K ≈ 280 s ⇒ biên hơn gấp đôi; G-06 có thể là lỗ hổng **phân loại** chứ không phải lỗ hổng **đang chảy máu**) |
| P6-01 | W6 | có đường retry/timeout nào **trùng** giữa `dieu_phoi` và `executor`/`jobs` không? |
| P7-01 | W8/W9 | đường **stream** và đường **job** có quyết toán đúng như đường đồng bộ không? |
| P8-01 | W3/W13 | số đo 03/09 (`catalog.py:38-60`) tái lập được bao nhiêu phần? |

---

## Bảng phụ thuộc

```
P1-01 ─┐
P1-02 ─┼─> (độc lập)
P1-03 ─┘
P2-01 ────> cần: đo gateway.env máy B TRƯỚC khi deploy
P3-01 ────> mở khoá P4-01
P3-02 ────> độc lập
P4-01 ────> cần P3-01
P5..P9 ───> cần số đo từ P2/P3/P4
P10 ──────> cần tất cả  →  FULL GATE #1
```

## Luật thi hành

1. Sau mỗi item: **chỉ** targeted verification. Không gate đầy đủ.
2. Điểm < 98 ⇒ không sang item sau.
3. Không thêm phụ thuộc/dịch vụ nào mà không trả lời 15 câu của §2.
4. Không deploy trong các phase thi hành.
5. Full gate **một lần** sau P10.
