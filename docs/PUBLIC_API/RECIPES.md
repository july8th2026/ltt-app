# Gọi API mà không cần SDK

SDK chỉ là tiện lợi. Toàn bộ API là HTTP + JSON, nên bất cứ thứ gì gửi được một
request đều dùng được — và **đây là bài kiểm tra thật của một API**: nếu chỉ SDK
của chúng tôi gọi được thì đó không phải API, đó là một thư viện.

Mọi ví dụ dưới đây làm **đúng một việc**: tạo một ảnh và tải nó về.

## Ba điều bắt buộc, dù bạn dùng gì

1. **`Authorization: Bearer <khoá>`** trên mọi lời gọi.
2. **Báo giá trước, rồi mới tạo job.** Báo giá đã ký, và nó khoá giá cho đúng
   đầu vào đó.
3. **`Idempotency-Key` trên `POST /jobs`.** Thử lại **cùng một key**. Đổi key
   khi thử lại là cách biến một lần timeout thành hai lần bị tính tiền.

---

## cURL

```bash
BASE=https://app.lttstudios.com/api/v1
KEY=ltt_sk_...

# 1. Xem có gì gọi được
curl -s -H "Authorization: Bearer $KEY" "$BASE/tools"

# 2. Báo giá
QUOTE=$(curl -s -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"tool":"image.thumbnail","input":{"topic":"cà phê buổi sáng","count":1}}' \
  "$BASE/quotes")
echo "$QUOTE"          # có "credit" và "pricing_version"

# 3. Tạo job — CÙNG một Idempotency-Key cho mọi lần thử lại
IDEM=$(uuidgen)
JOB=$(curl -s -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -H "Idempotency-Key: $IDEM" \
  -d "{\"tool\":\"image.thumbnail\",\"quote\":$(echo "$QUOTE" | jq -r '.quote|@json'),\"input\":{\"topic\":\"cà phê buổi sáng\",\"count\":1}}" \
  "$BASE/jobs")
JOB_ID=$(echo "$JOB" | jq -r .id)

# 4. Chờ
until [ "$(curl -s -H "Authorization: Bearer $KEY" "$BASE/jobs/$JOB_ID" | jq -r .status)" != "queued" ]; do sleep 2; done

# 5. Tải kết quả
ART=$(curl -s -H "Authorization: Bearer $KEY" "$BASE/jobs/$JOB_ID" | jq -r '.outputs[0].id')
curl -s -H "Authorization: Bearer $KEY" "$BASE/artifacts/$ART/content" -o thumbnail.png
```

---

## PowerShell

```powershell
$Base = "https://app.lttstudios.com/api/v1"
$Key  = "ltt_sk_..."
$Head = @{ Authorization = "Bearer $Key" }

$quote = Invoke-RestMethod -Method Post -Uri "$Base/quotes" -Headers $Head `
  -ContentType "application/json" `
  -Body (@{ tool = "image.thumbnail"; input = @{ topic = "cà phê"; count = 1 } } | ConvertTo-Json)

# Idempotency-Key sinh MỘT lần, dùng lại cho mọi lần thử lại.
$idem = [guid]::NewGuid().ToString("N")
$job = Invoke-RestMethod -Method Post -Uri "$Base/jobs" `
  -Headers ($Head + @{ "Idempotency-Key" = $idem }) -ContentType "application/json" `
  -Body (@{ tool = "image.thumbnail"; quote = $quote.quote
            input = @{ topic = "cà phê"; count = 1 } } | ConvertTo-Json -Depth 5)

do {
  Start-Sleep -Seconds 2
  $state = Invoke-RestMethod -Uri "$Base/jobs/$($job.id)" -Headers $Head
} while ($state.status -in @("queued", "running"))

$artifact = $state.outputs[0].id
Invoke-WebRequest -Uri "$Base/artifacts/$artifact/content" -Headers $Head -OutFile thumbnail.png
```

---

## n8n

Bốn node **HTTP Request**, nối tiếp:

| Node | Method | URL | Ghi chú |
|---|---|---|---|
| Quote | POST | `{{$env.LTT_BASE}}/quotes` | Header `Authorization`. Body JSON. |
| Create job | POST | `{{$env.LTT_BASE}}/jobs` | Thêm header `Idempotency-Key` = `{{$json.quote_intent}}` hoặc một giá trị **cố định theo lần chạy** |
| Wait | — | — | Node **Wait** 5 giây |
| Poll | GET | `{{$env.LTT_BASE}}/jobs/{{$json.id}}` | Nối vào **IF**: `status` = `succeeded` thì đi tiếp, chưa thì quay lại Wait |

Cạm bẫy hay gặp nhất trong n8n: đặt `Idempotency-Key` bằng `{{$guid}}`. Node
retry của n8n sẽ sinh key mới mỗi lần → **bị tính tiền nhiều lần**. Hãy lấy một
giá trị cố định trong lần chạy đó (ví dụ `{{$execution.id}}`).

Muốn khỏi poll: đăng ký webhook (`POST /webhooks`) trỏ vào một node **Webhook**
của n8n, rồi **xác minh chữ ký** trước khi tin payload.

---

## Make (Integromat)

Ba module **HTTP → Make a request**, cùng mẫu như n8n. Đặt `Idempotency-Key`
bằng một biến của scenario execution, **không** phải một hàm sinh ngẫu nhiên.

---

## Backend thuần (không SDK, không thư viện ngoài)

Python chuẩn thư viện:

```python
import json, time, urllib.request, uuid

BASE, KEY = "https://app.lttstudios.com/api/v1", "ltt_sk_..."

def call(method, path, body=None, extra=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Authorization", f"Bearer {KEY}")
    req.add_header("Content-Type", "application/json")
    for k, v in (extra or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"{}")

payload = {"topic": "cà phê", "count": 1}
quote = call("POST", "/quotes", {"tool": "image.thumbnail", "input": payload})

idem = uuid.uuid4().hex                      # MỘT lần, không sinh lại khi retry
job = call("POST", "/jobs",
           {"tool": "image.thumbnail", "quote": quote["quote"], "input": payload},
           {"Idempotency-Key": idem})

while job["status"] in ("queued", "running"):
    time.sleep(2)
    job = call("GET", f"/jobs/{job['id']}")
```

---

## Xác minh webhook (bắt buộc, mọi ngôn ngữ)

Chữ ký là `v1=HMAC_SHA256(secret, "<timestamp>.<event_id>.<body thô>")`, gửi
trong header `X-LTT-Signature`, kèm `X-LTT-Timestamp` và `X-LTT-Event-Id`.

Ba luật:

1. Dùng **body thô**, không phải JSON đã parse rồi in lại — thứ tự khoá đổi là
   chữ ký sai.
2. So sánh bằng hàm **thời gian hằng định** (`hmac.compare_digest`,
   `crypto.timingSafeEqual`).
3. Từ chối timestamp lệch quá 5 phút — đó là thứ chặn một delivery cũ, hợp lệ,
   bị phát lại vào mặt bạn sau này.

Header có thể chứa **nhiều chữ ký cách nhau bằng dấu phẩy** trong 24 giờ sau khi
xoay secret. Khớp **bất kỳ** cái nào là hợp lệ.

---

## Tiến trình của bạn chết giữa chừng thì làm gì

Đây là tình huống mà mọi tích hợp thật sẽ gặp, và là chỗ dễ mất tiền nhất: bạn
gửi `POST /jobs`, mạng đứt hoặc tiến trình bị kill **trước khi đọc được phản
hồi**. Job đã tạo hay chưa? Đã bị tính tiền chưa?

**Đừng đoán. Gửi lại đúng request đó với đúng `Idempotency-Key` cũ.**

```bash
# Lần đầu — và lần thử lại, giống hệt nhau
curl -sS -X POST "$LTT_API_BASE/jobs"   -H "Authorization: Bearer $LTT_API_KEY"   -H "Idempotency-Key: don-hang-2026-08-15-0001"   -H "Content-Type: application/json"   -d '{"tool":"image.thumbnail","quote":"'"$QUOTE"'","input":{"topic":"…"}}'
```

- Nếu job **chưa** được tạo, nó được tạo bây giờ → `201`.
- Nếu job **đã** được tạo, bạn nhận lại **chính job đó** → `200`, cùng `id`.
- Không có đường nào dẫn tới hai job hay hai lần trừ tiền.

Khoá idempotency có hiệu lực **7 ngày**. Quá hạn đó, cùng một khoá sẽ tạo job
mới — nên với việc gián đoạn dài hơn, hãy đối chiếu thay vì gửi lại.

### Đối chiếu: hỏi hệ thống thay vì suy đoán

```bash
# Bạn đã bị tính những gì trong khoảng này?
curl -sS "$LTT_API_BASE/usage?since=2026-08-15T00:00:00Z"   -H "Authorization: Bearer $LTT_API_KEY"
```

`/usage` liệt kê **từng job kèm số credit thật sự bị tính**, nên nó là nguồn để
đối chiếu với sổ sách của bạn — không phải log phía bạn, vốn có thể mất đúng
những dòng cuối trước khi tiến trình chết.

### Phản hồi lỗi tự nói nó có thử lại được không

Mọi lỗi đều mang trường `retry`, nên bạn **không phải tra bảng** để biết nên làm
gì tiếp:

| `retry` | Nghĩa | Làm gì |
|---|---|---|
| `never` | Gửi lại y hệt sẽ hỏng y hệt | Sửa request, hoặc dừng |
| `after_fix` | Request đúng, nhưng tài khoản/báo giá có vấn đề | Sửa cái đó trước; thử lại ngay chỉ tốn hạn mức nhịp |
| `after_delay` | Tạm thời | Đợi `Retry-After` giây rồi thử lại, giãn cách tăng dần |

Khi phản hồi có `"reuse_idempotency_key": true`, lần thử lại **bắt buộc** mang
lại đúng khoá cũ — đó là thứ giữ cho một lần gián đoạn không thành hai lần mua.

## Vì sao không có CLI

Một CLI là một bề mặt nữa phải giữ khớp hợp đồng, và cURL + `jq` đã làm đúng
việc đó mà không cần ai bảo trì. Khi nào có một thao tác nhiều bước mà một dòng
lệnh làm gọn hơn hẳn — ví dụ tải hàng loạt — thì đó là lúc CLI có lý do tồn tại,
không phải bây giờ.
