# 02 — Journey & Control Registry: Tạo ảnh AI + Thumbnail

## Journey

| ID | Hành trình | Kết quả | Gate |
|---|---|---|---|
| J-01 | Mở product/chọn mode | Một entry, hai mode rõ | PASS |
| J-02 | Prompt → preview → quote | General cost đổi theo model/count; preview thiếu model/ref/giá | PARTIAL |
| J-03 | Generate → progress → output | General có polling; provider chưa blind-test | PASS có điều kiện |
| J-04 | Chọn edit không source | CTA vẫn bật; submit 400 và xóa prompt/mode | FAIL/P1 |
| J-05 | Remix output | owner-only và prefill | PASS với giới hạn 60 job |
| J-06 | Partial 1/4 | settle đúng ảnh thật | UI ghi requested 4 nhưng không giải thích partial/refund | FAIL honest UI |
| J-07 | Thumbnail model/quote | Pro vẫn 5 credit | FAIL/P1 |
| J-08 | Thumbnail Brand Kit | nhập/lưu cùng submit | PARTIAL; không manage/version/logo |
| J-09 | Thumbnail progress | queued card không tự refresh | FAIL |
| J-10 | History/recovery | 12 recent, lỗi/output | FAIL search/page/cancel/retry/delete/retention |
| J-11 | English | general dịch, fragment Thumbnail VI; link rơi về VI | FAIL |
| J-12 | Mobile | không overflow | PARTIAL; form 7 section dài, CTA không sticky |
| J-13 | Purge/revisit old output | policy Job và artifact tách rời | FAIL/P1 |

## Control registry

| Control | State/feedback | Cost/ownership | Kết quả |
|---|---|---|---|
| Prompt/topic/title/subtitle | max length server | owner | PASS cơ bản |
| Model chips | 4 model | General đúng, Thumbnail sai | FAIL money |
| Mode edit/style/outpaint | không disable theo prerequisite | owner | FAIL validation UX |
| Source/style/reference upload | MIME+decode+pixels sau full read | owner key | PARTIAL security/lifecycle |
| Count/aspect | 1–4, 5 ratio | quote client + server reserve | PARTIAL model capability |
| Preview config | không tiêu credit | thiếu model/cost/ref/brand state | PARTIAL |
| Submit | POST/HTMX, CSRF | hold/settle/refund | PARTIAL; no confirm/signed quote |
| History/progress | general poll; thumbnail static | owner | PARTIAL |
| Compare | 2 ảnh, aria-pressed | local-only | PASS cơ bản |
| Edit/remix/open | owner-only | scan recent 60 ở một số path | PARTIAL |
| Brand save | checkbox cùng queue | owner AppProject | PARTIAL |
