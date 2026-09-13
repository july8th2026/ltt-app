# Nghiệm thu vận hành thật — LTT LLM hai model

> Thiết kế chốt 13/09/2026. Chủ sản phẩm duyệt cả năm mục.
>
> ⛔ Mọi con số trong tệp này **đo được** hoặc là **hằng số trong mã**. Chỗ nào
> chưa có thì ghi *"chốt sau lượt đầu"*, không điền số cho đẹp bảng.

---

## 0. Vì sao cần nó, khi đã có cổng A–Q

Cổng A–Q đo **từng bất biến rời nhau**: một chu trình residency, một lần huỷ,
một lượt tính tiền. Bộ này đo **hệ thống dưới tải trộn có tranh chấp** — thứ
không cổng nào chạm tới.

Mục tiêu: giả lập người dùng thật và app thật gọi vào **hệ thống production**,
đi xuyên `API → job → admission → queue → runtime → GPU → stream/result →
credit → persistence`.

⛔ **Unit test và internal function test không phải bằng chứng nghiệm thu
   production.** Hôm nay L-08 qua mọi phép kiểm trong cây rồi hoá ra **chưa từng
   chạy** trên máy chủ. Khoảng cách giữa hai điều đó là cả một lớp lỗi.

## 1. Phạm vi — ba quyết định đã chốt

| | chốt | ghi chú |
|---|---|---|
| Tải | **chỉ LLM** | tranh chấp LLM ↔ ảnh đã do cổng I và N đo riêng |
| "Job" nghĩa là gì | **cả hai, hai đợt** | cửa `/api/v1/jobs` trước, rồi ba cửa trộn |
| Mức xâm lấn | **bão hoà hoàn toàn, bất cứ lúc nào** | production có ~380 lượt/ngày; khách thật có thể chờ trong cửa sổ đo |

**Còn mở**: tài khoản nào trả tiền cho các lượt đo, và có tài khoản **thứ hai**
cho kịch bản X2 (công bằng giữa người dùng) hay không.

## 2. Sự thật nền — đã kiểm, không suy

```
SO_SLOT = SO_SLOT_MAY_B = 3            apps/ltt_llm/ngan_sach.py:415
ltt-3.8 → resource ltt_38_3090, 3 slot, cổng /metrics 8282
ltt-3.5 → resource ltt_35_5060, 3 slot, cổng /metrics 8281
⇒ 6 lượt đồng thời; lượt thứ 7 xếp hàng
```

Hai pool là **hai khoá advisory độc lập** (bất biến L-7, cổng F đã đo). Tải
`3.8` không lấy được suất của `3.5`.

⚠️ Mô hình "6 slot" **không đúng trong cửa sổ ảnh**: trọng tài đuổi LTT-3.8 khỏi
   3090 để ComfyUI vẽ, và trong ~182 s ấy `ltt-3.8` có **0 slot**. Phạm vi này
   không tạo ra tải ảnh, nhưng **phải phát hiện** khi một khách thật tạo ra nó.

## 3. Kiến trúc

```
tools/nghiem_thu_van_hanh/
├── soi.py          lớp QUAN SÁT — sáu sổ, mỗi sổ một hàm, tự kiểm khi khởi động
├── kich_ban.py     ma trận kịch bản — DỮ LIỆU, không phải mã
├── chay.py         bộ chạy: nộp tải theo khai báo, lấy mẫu, ghi bản ghi JSON
└── bao_cao.py      sinh bảng chất lượng từ bản ghi
```

Kịch bản là **dữ liệu**. Thêm một tình huống là thêm một dòng khai, không phải
một tệp mới.

### 3.1 Sáu sổ

| sổ | đọc gì | trả lời câu |
|---|---|---|
| HTTP | mã, thời gian, `usage` | khách thấy gì |
| `jobs` | `status`, mốc thời gian | hàng đợi **bền** — ai chờ, bao lâu, ra theo thứ tự nào |
| `execution_leases` | `resource`, `mode`, số suất | máy A **tưởng** đang cấp bao nhiêu |
| `credit_entries` | `hold`/`settle`/`refund` | tiền có khớp đôi không |
| máy B `/metrics` | `llamacpp:requests_processing`, `requests_deferred` — cổng **8282** và **8281** | GPU **thật sự** đang làm gì |
| `gpu_residency` | `trang_thai` | phép đo có bị nhiễu không |

⭐ Hai sổ cuối là lý do bộ này khác một bộ đo tải thông thường. `execution_leases`
   nói máy A *tưởng* gì; `/metrics` nói máy B *thật sự* có gì. L-08 hỏng đúng ở
   khe giữa hai cái đó — lease nhả mà slot không nhả. Một bộ đo đọc một sổ sẽ
   báo ĐẠT cho đúng cái hỏng ấy.

### 3.2 Mỗi phép dò TỰ KIỂM khi khởi động

Trước khi nộp lượt tải nào, hỏi cả sáu sổ một lần và **thất bại ồn ào** nếu sổ
nào trả giá trị vô nghĩa.

Lý do cụ thể: phép dò `requests_processing` viết ngày 13/09 trả `-1` suốt vì sai
cổng (8299 trả 404) và thiếu tiền tố `llamacpp:`. **`-1` trông y hệt `0`.**

## 4. Ma trận kịch bản

Nguyên tắc: mỗi kịch bản phải **có khả năng hỏng theo một cách nói lên điều gì
đó**. Một kịch bản không thể đỏ thì không chứng minh gì.

### 4.1 Đợt 1 — cửa `/api/v1/jobs`

| # | nộp | mong đợi | đỏ nghĩa là |
|---|---|---|---|
| J1 | 1 job `3.8` | chạy ngay | nền không sạch |
| J2 | 2 job, mỗi model 1 | song song; 2 `resource` khác nhau | hai pool không độc lập |
| J3 | 4 job, mỗi model 2 | song song hết | trần thấp hơn khai báo |
| J4 | 6 job, mỗi model 3 | chạm trần; `requests_processing` = 3 ở **cả hai** cổng | máy A cấp 6 mà máy B chạy <6 ⇒ suất ảo |
| J5 | 8 job, mỗi model 4 | 6 chạy · 2 `queued` | từ chối thay vì xếp hàng, hoặc nhận quá trần |
| J6 | 9 job **dồn `3.8`** | 3 chạy · 6 chờ · `3.5` **rảnh hoàn toàn** | 🔴 vỡ bất biến L-7 |
| J7 | huỷ 1 job `queued` | rời hàng; hoàn đủ; **không tốn suất** | huỷ mà vẫn thu, hoặc vẫn chiếm chỗ |
| J8 | huỷ 1 job `running` | suất trống ≤ 2 s | huỷ chỉ hợp tác |
| J9 | 9 job, ghi thứ tự ra | thứ tự **có quy luật đọc được** | không hứa được gì với khách |

### 4.2 Đợt 2 — ba cửa trộn

| # | nộp | mong đợi | đỏ nghĩa là |
|---|---|---|---|
| C1 | 3 job + 3 stream cùng `3.8` | tổng 6 suất; tới trước nhận trước | một cửa bị đói |
| C2 | 6 stream + 1 đồng bộ | đồng bộ chờ rồi `429` + `Retry-After` | treo 100 s rồi `504` vô nghĩa |
| C3 | 6 suất đầy + 1 chờ, rồi **cắt** một stream | suất nhả, người chờ vào ngay | 🔴 L-08 ở tình huống nó gây hại thật |
| C4 | tải trộn 10 phút | 0 rò lease · 0 `hold` lệch · 0 thu hai lần | rò rỉ chỉ lộ dưới thời gian |

### 4.3 Ba kịch bản mở rộng

| # | nộp | vì sao đáng |
|---|---|---|
| X1 | 12 job một lượt | vượt gấp đôi trần — hàng đợi có trần không? Vượt thì từ chối **có lý do** hay nuốt im lặng? |
| X2 | 6 job đầy + 1 job **tài khoản khác** | công bằng. **Cần tài khoản thứ hai** — chưa có thì ghi "chưa đo", không suy từ mã |
| X3 | nộp job rồi **cắt mạng máy khách** | job nền phải chạy tiếp — khác hẳn cửa stream |

### 4.4 Cổng nhiễu

Trước và sau mỗi kịch bản: đọc `gpu_residency` và đếm job của **người khác**.
Residency rời `llm`, hoặc có job lạ ⇒ kịch bản đánh dấu **NHIỄU**, **không** vào
bảng chất lượng. Chạy lại, không diễn giải.

## 5. Bảng chất lượng — 23 tham số

Mỗi ngưỡng phải có **nguồn**: một hằng số trong mã, một câu trong spec, hoặc
một phép đo đã có.

⚠️ Ngưỡng sai còn tệ hơn không có ngưỡng — nó xanh vĩnh viễn. Cổng D/E là ví dụ:
   spec đòi `≥ 2 × C1`, và tiêu chí ấy **thưởng cho việc làm nền tảng chậm đi**
   (phí nền tảng là khoản cố định mỗi request nên ăn vào C1 nặng hơn C3; máy A
   chậm hơn mà scaling cao hơn, 1,92× so với 1,71×).

### A · Đúng đắn cấp phát

| tham số | đơn vị | ngưỡng | nguồn |
|---|---|---|---|
| suất tối đa mỗi model | suất | = 3 | `SO_SLOT_MAY_B` |
| suất toàn hệ | suất | = 6 | 3 + 3 |
| độc lập hai pool | bool | dồn `3.8` ⇒ `lease(ltt_35_5060)` = 0 | L-7, spec §8 |
| nhận quá trần | lượt | = 0 | định nghĩa trần |

### B · Hàng đợi

| tham số | đơn vị | ngưỡng | nguồn |
|---|---|---|---|
| job `queued` khi nộp N | job | = N − 6 | số học |
| job không bao giờ chạy | job | = 0 | đói là lỗi |
| chờ trung vị | giây | **chốt sau lượt đầu** | — |
| chờ p95 | giây | **chốt sau lượt đầu** | — |
| thứ tự ra | mô tả | có quy luật đọc được | — |

### C · Huỷ

| tham số | đơn vị | ngưỡng | nguồn |
|---|---|---|---|
| suất trống sau huỷ job chạy | giây | ≤ 2 | spec cổng M |
| huỷ job `queued` tốn suất | suất | = 0 | chưa chạy thì chưa tốn |

### D · Tiền

| tham số | đơn vị | ngưỡng | nguồn |
|---|---|---|---|
| `hold` không khớp | khoản | = 0 | cổng O |
| thu hai lần | lượt | = 0 | INV-011/012 |
| hoàn khi huỷ `queued` | % | = 100 | chưa chạy thì không thu |

### E · Rò rỉ

| tham số | đơn vị | ngưỡng | nguồn |
|---|---|---|---|
| `execution_leases` sau kịch bản | lease | = 0 | cổng P |
| `requests_processing` sau kịch bản | lượt | = 0 | máy B rảnh |
| ⭐ **lệch lease ↔ slot tại đỉnh** | lượt | = 0 | *xem dưới* |

⭐ Tham số cuối **không có trong đề bài**, thêm vì nó là tham số duy nhất bắt
   được L-08. Máy A nói *"đang cấp 6 suất"*; máy B nói *"đang chạy 6 lượt"*. Khi
   hai con số lệch, có một **suất ma**: hoặc máy A giữ chỗ cho lượt đã chết
   (L-08: lease sống 643 s sau khi khách cắt), hoặc máy B chạy thứ máy A không
   biết.

### F · Thông lượng

| tham số | đơn vị | ngưỡng | nguồn |
|---|---|---|---|
| `3.8` C3 qua máy A | tok/s | ≥ 78 | chốt 13/09 |
| `3.5` C3 qua máy A | tok/s | ≥ 99 | nt |
| thông lượng theo mức 1/2/3 suất | tok/s | **chốt sau lượt đầu** | — |

### G · Trung thực

| tham số | ngưỡng | ý nghĩa |
|---|---|---|
| `residency` suốt kịch bản | = `llm` | rời ⇒ **NHIỄU** |
| job người khác trong hàng | = 0 | có ⇒ **NHIỄU** |
| tự kiểm sáu sổ | 6/6 | thiếu một ⇒ **dừng** |

**Ba ô ghi "chốt sau lượt đầu"** — để trống có chủ ý, không phải sót.

## 6. An toàn production

### 6.1 Bốn điều KHÔNG BAO GIỜ làm

1. Không dừng/khởi động lại dịch vụ nào.
2. Không sửa cấu hình (`llama-swap.yaml`, `gateway.env`, cờ manifest).
3. Không ghi thẳng vào CSDL — sáu sổ **chỉ đọc**.
4. Không đụng `gpu_residency`.

⇒ Mọi thứ bộ đo làm, một khách trả tiền cũng làm được. Đó là định nghĩa của
"giả lập người dùng thật".

### 6.2 Sổ rác

| tạo ra | gỡ bằng | ai gỡ |
|---|---|---|
| job `queued`/`running` | `POST /jobs/{id}/cancel` | `finally` mỗi kịch bản |
| khoản `hold` | nền tảng tự `refund` khi huỷ | kiểm lại ở nhóm D |
| kết nối stream mở | đóng socket | `with` của httpx |

Chế độ `--don-rac`: quét job **do bộ đo tạo** còn sống từ lượt trước rồi huỷ.
Nhận ra job của mình bằng **nhãn trong `input`**, không bằng thời gian tạo —
thời gian tạo lại là "đọc thứ đại diện".

### 6.3 Ba điều kiện DỪNG NGAY

| điều kiện | vì sao |
|---|---|
| tự kiểm thiếu một sổ | chạy tiếp là đo mù một mắt |
| rò lease ở cuối một kịch bản | rò chồng rò, kịch bản gây ra biến mất trong đống |
| `residency` rời `llm` quá 2 kịch bản liên tiếp | có việc ảnh thật; đo tiếp sinh số vô nghĩa |

⛔ **Hỏng thì dừng ồn ào, đừng chạy tiếp cho đủ bảng.**

### 6.4 Trần chi tiêu

Mỗi lượt có trần credit khai trước. Chạm trần thì dừng và ghi rõ đã tới kịch bản
nào. Một vòng lặp hỏng có thể nộp hàng trăm job trước khi ai kịp nhìn.

### 6.5 Bản ghi gắn với BẢN ĐANG CHẠY

Dòng đầu mỗi bản ghi JSON là **commit production** đọc từ `/health/version`.

Ngày 13/09 tôi đo L-08 trên máy chủ **chưa mang bản vá**, thấy 99 s, và suýt kết
luận bản vá "chạy chậm" — trong khi nó **chưa hề chạy**. Một con số không gắn
với bản sinh ra nó thì không tái lập được và không bác được.

Bản ghi gồm: commit production · commit bộ đo · giờ · sáu sổ trước/sau mỗi kịch
bản · mọi mẫu lấy trong lúc chạy · cờ **NHIỄU**.

## 7. Quy trình chạy

### Pha 0 — dựng bộ đo, và tự chứng minh nó không mù

Hai cửa của chính nó: **tự kiểm sáu sổ**, và **chạy J1 + J2** — hai kịch bản hệ
thống chắc chắn làm đúng. Chúng đỏ ⇒ lỗi ở **bộ đo**, không ở hệ thống.

### Pha 1 — chạy hết, GOM lỗi, KHÔNG sửa

Gặp lỗi thì ghi lại và đi tiếp (trừ ba điều kiện dừng). Sửa giữa chừng làm các
kịch bản sau chạy trên một hệ thống khác các kịch bản trước.

### Pha 2 — phân loại TRƯỚC khi sửa

| ngăn | xử |
|---|---|
| lỗi hệ thống | vào sổ lỗi, sửa ở pha 3 |
| lỗi bộ đo | sửa ngay, chạy lại kịch bản ấy |
| nhiễu | chạy lại, không diễn giải |
| **hệ thống đúng, kỳ vọng sai** | sửa **kỳ vọng**, ghi rõ |

⭐ Ngăn thứ tư dễ bỏ sót nhất. Ngày 13/09 nó xuất hiện thật: một prompt 195.696
   token bị từ chối, và tôi suýt ghi "221K không với tới được" — trong khi nền
   tảng khai **171.458** và từ chối là **đúng**.

### Pha 3 → 8

| pha | việc | thời gian |
|---|---|---|
| 3 | sửa **một lượt** mọi lỗi hệ thống | tuỳ số lỗi |
| 4 | chạy lại ma trận trên cây đã sửa | ~1 giờ |
| 5 | **một** lượt gate L3 | 15–18 ph |
| 6 | deploy hai lớp + nghiệm thu ba chiều | 2 ph 18 + 2 ph |
| 7 | chạy lại ma trận **trên bản đã deploy** | ~1 giờ |
| 8 | commit + đẩy GitHub | ~5 ph |

⚠️ Pha 7 không thừa: pha 4 chứng minh mã đúng **trong cây**, pha 7 chứng minh nó
   đúng **trên máy chủ**.

### Định nghĩa "xong"

Mọi kịch bản không-nhiễu đạt ngưỡng của nó, **và** ba ô "chốt sau lượt đầu" đã
có số cùng nguồn của số ấy.

### Không ước lượng tổng

Cổng N dự kiến "7 tình huống" đã sinh ra **ba** mục sổ lỗi, mỗi mục kéo theo một
chu kỳ sửa–gate–deploy riêng. Một bộ đo đi tìm lỗi mà ước lượng được chính xác
thì thường là một bộ đo không tìm ra gì.

## 8. Ngoài phạm vi

- Tải ảnh / voice / Auto Scan Video trộn vào (chốt: chỉ LLM).
- Cổng M — dư ở biên Cloudflare, **không sửa được ở tầng mã**.
- Cổng L (đa tệp) — thuộc Spec 2, chưa tồn tại.
- Cổng Q (soak) — spec không định nghĩa, chủ sản phẩm chốt bỏ qua.
