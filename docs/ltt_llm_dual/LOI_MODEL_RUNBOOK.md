# Runbook đo hợp đồng lỗi model B → A → API client

## Mục tiêu và ranh giới

Công cụ chuẩn là:

```powershell
python tools\kiem_hop_dong_loi_llm.py --help
```

Nó trả lời ba câu hỏi khác nhau; không dùng kết quả của chế độ này để suy ra
điều mà chỉ chế độ kia đo được:

| Chế độ | Chứng minh | Không chứng minh |
|---|---|---|
| `fixture` | Registry, decoder và renderer trong code hiện tại khớp golden độc lập | Dịch vụ production đang chạy đúng artifact đó |
| `live` | Event có cấu trúc trong đúng cửa sổ log đã chọn không mất request ID, không tăng unknown/legacy/mismatch | Một lỗi chưa xuất hiện trong traffic là đúng |
| `inject` | API ở URL được chỉ định trả đúng mã cho ba protocol trước khi chạy model | GPU/model sinh nội dung đúng; tải thật chịu được bao nhiêu |

Không chế độ nào được ghi prompt, raw body, Authorization, token hoặc prose thô
của provider vào report. `tmp/kiem_loi_model_<timestamp>/` là dữ liệu vận hành,
không commit.

## 1. Fixture offline

```powershell
python tools\kiem_hop_dong_loi_llm.py fixture `
  --output tmp\kiem_loi_model_fixture
```

Fixture không gọi mạng, không đọc log, không hỏi CPU/GPU. Nó dựng dữ liệu tổng
hợp đã khử dữ liệu nhạy cảm, rồi đo 33 mã qua bốn giao thức và hai pha
`before_headers`/`after_headers`. Một ca riêng replay envelope 413 legacy có
`truong=images`; golden độc lập đòi kết quả là `image_count_exceeded`, không
phải `context_window_exceeded`.

Đạt khi `report.json` có `pass=true`, `summary.failed=0`; `report.md` là bản dễ
đọc của cùng dữ liệu. Golden đến từ `llm_gateway.error_contract.ERROR_SPECS` và
bảng protocol viết rõ trong công cụ, không lấy từ log production và không dùng
output của chính lần chạy trước làm chuẩn.

## 2. Live thụ động trong một cửa sổ thời gian

Nguồn vào là JSONL structured đã được A/B ghi. Mỗi event bắt buộc có
`timestamp`/`time`/`ts` dạng ISO-8601 có múi giờ hoặc Unix epoch. Dòng không có
thời gian bị loại vì không thể chứng minh nó nằm trong cửa sổ cần đo.

```powershell
python tools\kiem_hop_dong_loi_llm.py live --minutes 20 `
  --log C:\duong-dan-chi-doc\a-llm.jsonl `
  --log C:\duong-dan-chi-doc\b-llm.jsonl `
  --output tmp\kiem_loi_model_live
```

Có thể đặt danh sách đường dẫn trong `LTT_LLM_CONTRACT_LOGS`, phân cách theo
`os.pathsep`; `--log` rõ ràng vẫn là cách nên dùng khi nghiệm thu. Không truyền
nguồn thì công cụ dò `ltt-server*.jsonl`, `ltt-job-worker*.jsonl` và
`*llm*.jsonl` dưới `LTT_LOGS_DIR` (mặc định production A là
`C:\LTTPlatform\logs`). Nó vẫn đọc thêm vị trí `LTT_DATA_DIR\logs` cũ để không
làm mất một bản log đã được operator xuất theo hướng dẫn Task 9 trước khi đường
dẫn được sửa. Công cụ chỉ đọc file; nó không SSH, không gọi API, không gửi prompt
và không chạy `nvidia-smi`. Log B phải được operator xuất/copy theo đường chỉ-đọc
trước khi chạy.

Report chỉ giữ:

- tổng event và tỷ lệ có `request_id`;
- số `upstream_unknown`, legacy và contract mismatch;
- histogram hữu hạn theo `canonical_code` và `action`.

Một dòng snapshot counter **không kèm** `event=llm_model_error` được nhận diện
bằng `llm_error_total`; bốn counter
đi kèm là `llm_error_unknown_total`, `llm_error_legacy_total`,
`llm_error_contract_mismatch_total` và
`llm_error_request_id_missing_total`. Nhiều snapshot cùng `source` chỉ lấy dòng
cuối trong cửa sổ; các source hữu hạn khác nhau được cộng lại. Snapshot chỉ là
fallback khi cửa sổ không có event riêng lẻ. Nếu có event, công cụ đếm từng event
thay vì lấy counter cộng dồn: máy A có nhiều process, mỗi process có counter riêng
nên lấy một snapshot theo nhãn `source=A` sẽ làm thiếu số mà không báo lỗi.

`pass=false` khi không có event hoặc có mismatch. Unknown/legacy được đếm để
rollout quyết định, không tự biến thành lỗi khác. Trước khi dùng phép đo làm
gate, phải mở tay **hai mismatch đầu tiên** ở nguồn log gốc, đối chiếu cùng
request ID tại A và B, và xác nhận bộ dò không đọc nhầm nguồn/ngôn ngữ/kỹ thuật.

## 3. Inject lỗi rẻ trên môi trường test

Token chỉ đi qua biến môi trường, không đặt trên command line:

```powershell
$env:LTT_LLM_CONTRACT_TOKEN = '<operator cấp ngoài git/log>'
python tools\kiem_hop_dong_loi_llm.py inject `
  --base-url http://127.0.0.1:18100/api `
  --output tmp\kiem_loi_model_inject
```

Inject gửi đúng ba request nhỏ tới Messages, Chat và Responses với model giả
`__ltt_contract_missing__`. Lookup phải từ chối trước GPU, không sinh dài, không
dùng ảnh thật hay ảnh người dùng. Thành công đòi HTTP 404 và
`canonical_code=model_not_found` ở cả ba giao thức.

Mặc định công cụ chặn:

- mọi hostname thuộc `lttstudios.com`;
- loopback cổng production máy A `8100`;
- cổng gateway production máy B `192.168.2.66:8299`.

`--allow-production` là override có chủ ý, chỉ dùng ở Task 11 sau khi có gate
xanh đúng SHA, baseline live, health xanh, credential test và rollback đã sẵn
sàng. Cờ chỉ gỡ rào URL; nó không tự cấp token hay mở rộng loại request.

## 4. Đọc report và xử lý đỏ

Mỗi hàng matrix có `code`, `protocol`, `phase`, `status`, `canonical_code`,
`protocol_code`, `action` và `pass`. Khi đỏ:

1. Giữ nguyên report và request ID; không đổi mapping theo câu chữ lỗi.
2. Mở tối đa hai mismatch đầu để xác định lớp sai: B phát, A decode, A render hay
   client đọc.
3. So với registry/spec, không so với report của một lần chạy cũ.
4. Nếu chỉ một lớp vừa deploy sai, rollback đúng lớp đó; không restart worker hay
   model đang phục vụ nếu lỗi chỉ nằm ở web renderer.
5. Chạy lại đúng chế độ/phép đo đã đỏ. Không tuyên bố các mã chưa xuất hiện trên
   traffic production là đã được chứng minh bởi `live`.

## 5. Telemetry A/B và giới hạn dữ liệu

Mỗi lỗi model phát một event `llm_model_error`. Event chỉ có trường đã chuẩn
hoá: `request_id`, `gateway_code`, `canonical_code`, `protocol_code`,
`category`, `http_status`, `upstream_status`, `protocol`, `stream_phase`,
`retry`, `recovery`, `model`, `elapsed_ms`, `endpoint`, `action`, `source`,
`legacy` và `contract_mismatch`. Không có đường truyền raw body, prompt, ảnh,
Authorization, credential hay message thô của provider vào hàm ghi event.

Năm counter cộng dồn được chụp ngay trong event để sống qua file log:
`llm_error_total`, `llm_error_unknown_total`, `llm_error_legacy_total`,
`llm_error_contract_mismatch_total`, `llm_error_request_id_missing_total`.
Counter chỉ gắn label hữu hạn `canonical_code`, model đã được catalog xác nhận,
endpoint, phase, protocol và action. Model lạ thành `other`; model trống thành
`missing`. Request ID và message không bao giờ là label.

Action phía A/B chỉ là `retry`, `terminal`, `legacy`, `unknown` hoặc
`client_disconnected`. `client_disconnected` là log-only (`counted=false`): nó
không tăng counter lỗi và không phải bằng chứng để phạt provider/API key. Action
`compact`/`offload` của LTTCODE chỉ được thêm ở Task 12, tại đúng lớp client.

`live` đọc được cả JSONL của máy A (event nằm trong trường `message`) và JSON
message của máy B. Nó chỉ giữ histogram/counter; phần vỏ log và prose không được
chép vào report.

## 6. Tiêu chí dùng ở mốc A+B

Trước khi mở hạng mục LTTCODE, Task 11 phải có đủ ba artifact cùng thời điểm:

- fixture `failed=0`;
- live có request-ID coverage được ghi rõ, mismatch bằng 0, không tăng
  unknown/legacy so với baseline. Quan sát 20 phút chỉ có nghĩa khi có traffic
  thật; không có traffic thì thay bằng probe/canary chủ động + snapshot log
  sau probe (chủ dự án chốt 22/09/2026) — "đủ mẫu hoặc đủ thời gian";
- inject/canary trực tiếp qua API A xanh cả ba protocol, không qua LTTCODE.

Bất kỳ invariant nào đỏ thì dừng rollout. Từ Task 13 không còn cờ
`LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS` để tắt — đường lui là bản trước
(§9). Không được sửa client để che lỗi server.

## 7. Kết quả Task 11 — rollout A+B 22/09/2026

Giờ Việt Nam (UTC+7). Không có dữ liệu người dùng trong report.

| Bước | Kết quả |
|---|---|
| Baseline live A trước deploy (bản `42c79a26`) | 0 event có cấu trúc — đúng dự kiến, bản cũ chưa có telemetry |
| Baseline B 20 phút | 23 lượt `messages` (19 qwen38, 4 qwen35), 23/23 HTTP 200, 0 ERROR |
| L1 trên SHA deploy | đỏ 2 phép ngoài LTT LLM (bộ khung `video_crawler` dở + DB migration tạm còn sót) → rút bộ khung khỏi SHA (`f587f497`), khép đúng 2 phép: governance 102 passed, migration PostgreSQL PASS |
| Deploy A `f587f497` | fingerprint 1.092 tệp lệch 0; `/health/ready` ready; rollback `42c79a26` |
| Deploy B gateway-only | snapshot `auto-20260922-133432`, hash 45 tệp khớp, YAML/model không đổi, chỉ restart `LTTLlmGateway`; nghiệm thu B 17/17 |
| Canary thành công A→B | 9/9 (key pool, giải mã credential, sinh thật, usage, tính phí) |
| Bật `LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS=1` | chỉ nạp lại `LTTStudioWeb` |
| Inject `model_not_found` | B 3/3; A lộ lỗi thật: lỗi validator cục bộ đi đường `ApiError(400)` cũ → sửa `e94dd9a2` (300/300 test public route + renderer), deploy lại A |
| Bộ đo | 2 lỗi bộ đo sửa bằng TDD: User-Agent mặc định bị Cloudflare chặn 403; probe Chat thiếu `Idempotency-Key` (`4567a70d`) |
| Ma trận sau cùng | A 3/3, B 3/3; fixture 265/265 |
| Snapshot log sau probe (10 phút) | 11 event lỗi có cấu trúc, request ID 11/11, unknown 0, legacy 0, mismatch 0 |
| Lỗi xuyên tầng thật | `image_count_exceeded` (5 ảnh > trần 4, chặn trước GPU): SSE `event:error` sau 200, `field=images limit=4 actual=5`, cùng request ID ở client, log A, log B |

Ghi nhận ngoài hạng mục: wrapper `chay_nghiem_thu.cmd` trả `rc=255` sau bước dọn
dù 17/17 hành vi đạt (dọn kill đúng tiến trình nó dựng) — lỗi công cụ, chưa sửa.

## 8. Rà tài liệu 413/câu chữ (Task 14)

`git grep -n` (case-insensitive) trên hai kho cho các mẫu: `413` gần
`context`/`ngữ cảnh`/`CONTEXT_WINDOW`, `prompt is too long`, "nhận ra bằng câu
chữ", `payload_too_large`. Phân loại theo quyết định L-34: hợp lệ = fallback
tương thích có chủ đích, hoặc tài liệu/nhật ký lịch sử tự đóng khung là ảnh
chụp một thời điểm; chết = mô tả hành vi cũ như đang là hiện hành.

### `D:\LTTSTUDIOSAPP-llm-loi-nghia`

| Tệp | Phân loại | Vì sao |
|---|---|---|
| `docs/superpowers/plans/2026-09-21-chuan-hoa-ngu-nghia-loi-llm.md` | Hợp lệ | Chính plan đang thi hành, không phải mô tả cái cũ |
| `docs/superpowers/specs/2026-09-21-chuan-hoa-ngu-nghia-loi-llm.md` | Hợp lệ | Spec hiện hành của chính chương trình này |
| `docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md` | Hợp lệ | Tự đóng khung ở đầu tệp: "ĐÃ THỰC THI 17/09 (L-23)... §1–§2 là ảnh chụp TRƯỚC khi sửa"; dòng 413/"context" ở §1.4 là audit lịch sử client trước Task 12, có commit mốc |
| `docs/_luutru/multijob_2026-09/2026-09-11-ltt-llm-multijob-design.md` | Hợp lệ | Nằm trong `_luutru/` — đã lưu trữ, không phải tài liệu sống |
| `docs/_luutru/codex_2026-08-27/QUEUE_REVIEW_NHIEU_API.md` | Hợp lệ | Nằm trong `_luutru/` — đã lưu trữ |
| `docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md` | Hợp lệ | Nhật ký điều tra có mốc ngày/trạng thái ĐÓNG cho từng phát hiện (N-1…N-15), không phải đặc tả hiện hành |
| `docs/QUYET_DINH_NEN_TANG.md` (Q120) | Hợp lệ | Mô tả việc dịch 413 khi khách vượt **trần đầu vào đã khai** — một cơ chế cụ thể vẫn đúng, không phải "mọi 413 là context"; đã tự đánh dấu phần số liệu ĐÃ GỠ ở L-23 |
| `docs/LTT_CLI_COMPAT_DECISIONS.md` (dòng "413 ngữ cảnh không tiêu `create_rpm`") | Hợp lệ | Nói về kế toán RPM/billing khi có 413, không phải cơ chế nhận diện lỗi bằng status/câu chữ |
| `docs/PUBLIC_API/CHANGELOG.md` (mục "Và `413` vẫn đứng trước") | Hợp lệ | Log thay đổi có mốc ngày, mô tả trạng thái tại thời điểm phát hành đó |
| `docs/PUBLIC_API/HUONG_DAN_CAM_CLI.md:683` (`413/ngữ cảnh quá dài`) | **Chết — đã sửa (R6b, 22/09)** | Đo: status công khai của lỗi quá dài là **400** ở cả ba giao thức (`tests/test_1480_loi_qua_dai_dung_giao_thuc.py` 10 passed; `server/api/su_kien_loi.py::loi_qua_dai_json`), 413 công khai chỉ cho `request_body_too_large` (`server/api/deps.py:104`). `http_status=413` trong `KhongMoDuoc`/`LoiLuongVlm` là **status dây nội bộ** bắt chước máy B (spec §3 giữ status B trong giai đoạn tương thích; decoder ghi đúng 413 của B cho lỗi B báo) ⇒ hai đường nhất quán, không phải bug; renderer lấy status công khai từ registry. Không tách canonical: cùng nghĩa, cùng recovery `reduce_input`. Sửa dòng hướng dẫn thành 400 + thêm dòng 413 body; chú thích mã làm rõ ở `luong.py`, `luong_vlm.py`, `tham_so_da_luot.py`. Văn bản công khai cùng lỗi (`huong_dan.html`, `examples.py` NGU_CANH_NAM_SO/LOI_413, `dieu_khoan.py` `tran_ngu_canh`) sửa ở làn R6c |

### `D:\LTTCODEAPP` — chỉ liệt kê, KHÔNG sửa (làn khác giữ kho này)

| Vị trí | Ghi chú |
|---|---|
| `docs/LTTCODE/DANH_MUC_CONG_VIEC.md:280` | `"413 → CONTEXT_WINDOW_EXCEEDED"` ghi như kết quả A3 — đối chiếu lại với `plugins/llm-ltt/CONTRACT.md:137,151,153` (đã cập nhật: `request_body_too_large` là 413/`INVALID_REQUEST`, "413 không còn thành CONTEXT") |
| `docs/LTTCODE/KE_HOACH_XU_LY_LAI.md:104` | Dòng A3 liệt "413 → `CONTEXT_WINDOW_EXCEEDED`" cạnh cột "trước sửa" — kiểm lại chiều trước/sau còn khớp `errors.ts` hiện tại không |
| `plugins/llm-ltt/src/errors.ts:82,84` | Regex khớp câu chữ (`"The input exceeds the model's context limit"`, `"prompt is too long"`) → `context_window_exceeded`; là mã nguồn (không sửa qua tài liệu), cần làn giữ kho đó xác nhận đây vẫn là fallback tương thích ngược có chủ đích chứ không phải đường chính |
| `docs/LTTCODE/reports/self-improve/SO_LOI_VAN_HANH.md`, `AUDIT_DOI_SOAT_2026-09-16.md`, `docs/LTTCODE/_superseded/2026-09-17-truoc-build-0.1.5.md`, `docs/LTTCODE/reports/harness-nang-cap/A_H1_H3.md`, `docs/LTTCODE/reports/H11_headless.md` | Có hit `413`/`payload_too_large`/`prompt is too long`; không đọc sâu trong lượt này — liệt kê để làn LTTCODE tự phân loại |

## 9. Gỡ legacy (Task 13)

Chủ dự án cho làm ngay 22/09 (miễn điều kiện "một chu kỳ"): A+B chạy hợp đồng
v1 từ 22/09, `kiem_hop_dong_loi_llm.py live --minutes 720` = 7 sự kiện,
legacy 0, mismatch 0, unknown 0.

**Đã gỡ**

| Máy | Gỡ gì | Giữ lại |
|---|---|---|
| B | khoá `ly_do`/`truong`/`tran`/`thay`/`legacy` trong `VuotNganSach.as_dict`; `ly_do`/`co_the_dung`/`ma` trong `detail`; khoá anh em `ly_do`/`ma_thuong_nguon`/`ma` ngoài `detail` (499/502/504) | **HTTP status dây y nguyên** (413 ngân sách, 429, 499, 502, 504 — spec §3/§10.9); `model`/`available_models` ở lỗi 404; trường `legacy` của telemetry (luôn `false`) để bảng đo cũ còn đọc |
| A decoder | `_LEGACY_FIELD_TO_CODE`, nhánh đọc `{truong,tran,thay}`, counter `legacy`; `as_detail()` hết khoá tiếng Việt | thân không có `schema_version=1` + mã đã đăng ký ⇒ `upstream_unknown` |
| A cửa stream/đồng bộ | boolean `ban`/`qua_dai`/`het_gio` (kwarg + thuộc tính) của `KhongMoDuocLuong`/`KhongMoDuoc`; suy nghĩa từ status (429⇒bận, 504⇒hết giờ, 499⇒huỷ, 400/413/422⇒yêu cầu sai); dò câu parser tool-call | mọi quyết định đọc `failure.*` |
| A public | cờ `LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS`, renderer cũ (`_MA`, `_loi_openai`, …), `tran_bi_vuot` | renderer có cấu trúc là đường duy nhất, giữ `ltt_error` |

**Bất biến tự nén giữ nguyên** (`tests/test_1480`, `test_1706`): mã quá dài
(`context_window_exceeded`, `input_tokens_exceeded`) mang câu
`prompt is too long: N tokens > M maximum` ở cả ba giao thức, trước lẫn sau 200
(Claude Code); Responses **stream** trước 200 = 200 + đúng một
`response.failed` với `code=context_length_exceeded` (Codex); Chat/Responses
không stream = 400 `{"error": {..., "code": "context_length_exceeded"}}` kèm
`limit_name`/`limit_value`. Thay đổi dây kèm theo: lỗi Responses **trước 200**
(không phải quá dài) nay là `{"error": {...}}` khuôn OpenAI thay vì vỏ
`response.failed` (vỏ đó chỉ còn cho SSE sau 200, spec §7).

**Thứ tự deploy bắt buộc: B trước, A sau.** A hiện hành đã đọc v1 trước nên
không cần khoá legacy của B; ngược lại A mới coi thân thiếu v1 là
`upstream_unknown`, nên B cũ (còn đường nào chưa phát v1) phải được thay trước.

**Rollback** (ngược thứ tự: A trước, B sau)

- A: chép lại `C:\LTTPlatform\app.previous\` (xem `app.previous\dau_van_tay.json`
  trước deploy, `docs/16_CAP_NHAT_VA_DEPLOY.md` §3). Bản trước còn cờ, nhưng
  production đang đặt `LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS=1` nên hành vi
  public không đổi.
- B: `llm_gateway/deploy/deploy.ps1` chụp `H:/LTT_LLM/releases/auto-<giờ>` ở
  bước 1b trước khi chép; lùi = `xcopy /E /I /Y` bản chụp đó về
  `H:\LTT_LLM\gateway` rồi `Restart-Service LTTLlmGateway`.

⚠️ **Bẫy đo (23/09):** `inject --base-url` nhận GỐC, công cụ tự thêm `/v1/...`.
Truyền `https://app.lttstudios.com/api/v1` ⇒ URL thành `/api/v1/v1/messages` ⇒ 404
route-không-tồn-tại, **trùng đúng status kỳ vọng** nên report chỉ đỏ ở `canonical`
rỗng và dễ bị đọc nhầm thành "A mất `ltt_error`". Đúng: `--base-url
https://app.lttstudios.com/api`. Đối chứng nhanh: gọi thẳng một request và xem thân
có `ltt_error` không.

Sau deploy: `python tools/kiem_hop_dong_loi_llm.py fixture` PASS và
`live --minutes 60` phải giữ mismatch 0; `unknown` tăng ⇒ có đường B chưa phát
v1 — lùi A trước.
