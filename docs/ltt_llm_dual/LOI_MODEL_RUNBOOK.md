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
nguồn thì công cụ chỉ dò `*llm*.jsonl` dưới `LTT_DATA_DIR\logs` (mặc định
`C:\LTTPlatform\data\logs`). Công cụ chỉ đọc file; nó không SSH, không gọi API,
không gửi prompt và không chạy `nvidia-smi`. Log B phải được operator xuất/copy
theo đường chỉ-đọc trước khi chạy.

Report chỉ giữ:

- tổng event và tỷ lệ có `request_id`;
- số `upstream_unknown`, legacy và contract mismatch;
- histogram hữu hạn theo `canonical_code` và `action`.

Một dòng snapshot counter được nhận diện bằng `llm_error_total`; bốn counter
đi kèm là `llm_error_unknown_total`, `llm_error_legacy_total`,
`llm_error_contract_mismatch_total` và
`llm_error_request_id_missing_total`. Nhiều snapshot cùng `source` chỉ lấy dòng
cuối trong cửa sổ; các source hữu hạn khác nhau được cộng lại. Khi có snapshot,
nó là nguồn tổng số chính để tránh đếm đôi với event log cùng request.

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

## 5. Tiêu chí dùng ở mốc A+B

Trước khi mở hạng mục LTTCODE, Task 11 phải có đủ ba artifact cùng thời điểm:

- fixture `failed=0`;
- live 20 phút có request-ID coverage được ghi rõ, mismatch bằng 0, không tăng
  unknown/legacy so với baseline;
- inject/canary trực tiếp qua API A xanh cả ba protocol, không qua LTTCODE.

Bất kỳ invariant nào đỏ thì dừng rollout và giữ cờ
`LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS=0` (hoặc trả về 0 nếu vừa bật). Không
được sửa client để che lỗi server.
