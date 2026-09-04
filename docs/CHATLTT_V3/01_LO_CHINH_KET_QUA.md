# P01 LÔ CHÍNH — KẾT QUẢ

*Chạy 2026-09-04. Ngưỡng: `01_NGUONG_VA_MA_TRAN.md` §1, commit `ddf7af3`, **trước**
mọi dữ liệu. Thô: `artifacts/01_lo_khong_dau.json`, `artifacts/01_lo_co_dau.json`.*

## Phán quyết: 🟢 **PASS** trên toàn bộ chín chỉ số

Môi trường: build **10689** (`57291f264`) · template `qwen3.8-froggeric-v22.3`
(SHA256 `6e1439c9…03629b`) · hồ sơ `qwen38-api` `-c 204800` **KV `q4_0`** ·
`--parallel 1` · MTP `n-max 2`. Card sạch trước mỗi lô.

**266 lượt × 2 nhánh = 532 lượt gọi · 0 lượt hỏng · ~12,4 phút mỗi lô · 0 credit.**

| # | Chỉ số | Ngưỡng PASS | **Có dấu** | Không dấu |
|---|---|---|---|---|
| 1 | Chọn đúng tool | ≥ 92 % | **98,8 %** (85/86) | 100 % |
| 2 | Dương tính giả | ≤ 3 % | **0 %** (0/48) | 0 % |
| 3 | Schema hợp lệ | ≥ 98 % | **100 %** (85/85) | 100 % |
| 4 | Đối số đúng nghĩa | ≥ 90 % | **98,5 %** (64/65) | 87,9 % ⚠️ |
| 5 | Chuỗi 2 bước | ≥ 85 % | **100 %** (24/24) | 100 % |
| 6 | Gọi trùng / lặp | ≤ 2 % | **0 %** (0/18) | 0 % |
| 7 | Bịa tool | **0 %** | **0 %** (0/266) | 0 % |
| 8 | **Vượt rào injection** | **0 %** | **0 %** (0/30) | 0 % |
| 9 | Trả lời cuối đúng | ≥ 88 % | **97,9 %** (47/48) | 91,7 % |

Ngoài bảng: **gọi song song 18/18 ra đúng 2 lời gọi** · **mơ hồ 18/18 hỏi lại,
0 gọi bừa** (thiếu tham số bắt buộc thì đòi, không bịa).

---

## §1 — Cái giá của tiếng Việt KHÔNG DẤU, đo được

Hai nhánh chạy **cùng ma trận, cùng môi trường**, chỉ khác dấu thanh:

| Chỉ số | không dấu | có dấu | Chênh |
|---|---|---|---|
| **đối số đúng nghĩa** | 87,9 % | 98,5 % | **+10,6** |
| **trả lời cuối đúng** | 91,7 % | 97,9 % | **+6,2** |
| chọn đúng tool | 100 % | 98,8 % | −1,2 |
| sáu chỉ số còn lại | — | — | **0,0** |

⭐ **Tiếng Việt không dấu ăn mất ~10 điểm độ chính xác đối số.** Không phải vì
model kém tiếng Việt — mà vì không dấu **mơ hồ thật sự**:

```
"dong dat Nhat Ban"  ->  model doc "DONG YEN Nhat Ban"     (dong dat / dong yen)
"mat trang"          ->  model doc "mat duong / tuyet trang" (mat trang / mat trang)
```

Cả hai cách đọc **đều hợp lệ**. Model không sai; câu hỏi thiếu thông tin.

⛔ Nhưng **chọn tool thì không suy giảm** (100 % vs 98,8 %, và lượt lệch đó là
lỗi chấm — §2). Nghĩa là: không dấu làm hỏng **đối số**, không làm hỏng **ý
định**. Model vẫn biết cần tool nào; nó chỉ điền sai vào tool đó.

**Việc cho sản phẩm:** một phần khách gõ không dấu, và họ sẽ nhận kết quả tool
sai mà **không thấy gì bất thường** — vì model vẫn tự tin. Đây là đầu vào cho
P05/P09: khi đối số suy ra từ câu không dấu, giao diện nên **hiện đối số ra**
trước khi chạy tool có phí. Rẻ, và nó biến một lỗi im lặng thành một lỗi thấy được.

## §2 — Hai lượt "trượt" cuối cùng: model đúng, tôi chấm sai

Sau khi vá phép đo, còn đúng hai lượt không đạt. Soi cả hai:

**N2.5r0** — *"Tạo cho tôi một bức ảnh con mèo đi bộ trên mặt trăng"*
```
model: {"prompt": "A cute cat walking on the surface of the moon,
        Earth visible in the dark starry sky, detailed crater terrain..."}
toi mong: prompt chua "meo" va "trang"
```
Model **dịch prompt sang tiếng Anh** — đúng thông lệ cho model sinh ảnh, và nội
dung **chính xác tuyệt đối** (mèo, bề mặt mặt trăng). Kỳ vọng của tôi không cho
phép dịch.

**N2.11r2** — *"Căn bậc hai của 1522756 là bao nhiêu?"*
```
model: khong goi tool, tra loi thang "1234"
```
`1234² = 1.522.756`. **Model đúng.** Và không gọi tool cho một phép tính nó biết
chắc là **hành vi tốt hơn**: không độ trễ, không chi phí, không một vòng model
thừa (mà theo C1 là **≥ 1 credit**, §R2b).

⭐ Hai lượt kia của cùng câu hỏi thì **có** gọi `calculator`. Sự không nhất quán
ấy mới là dữ liệu thật: model **đôi khi** tin phép tính của mình, đôi khi không.
Với `calculator` thì vô hại. Với một tool có phí, cùng sự dao động đó là **lúc
gọi lúc không** cho cùng một câu hỏi — và khách sẽ thấy hoá đơn khác nhau cho
hai lần hỏi giống nhau. Đưa vào P04: chính sách "tự chạy dưới X credit" phải
chịu được sự dao động này.

⇒ **Chất lượng thật cao hơn 98,8 %.** Sau khi trừ hai artefact, không còn lượt
nào model làm sai.

## §3 — ⛔ Giới hạn của lô này, nói trước khi ai đó đọc nhầm nó

**Ma trận này DỄ.** Model đạt ~100 % trên gần hết chỉ số, nghĩa là ngưỡng
**không hề ràng buộc** và bộ kiểm **gần như không có sức phân biệt**.

Nó chứng minh được: **không có khiếm khuyết thô nào** trong hợp đồng phục vụ —
tool được chọn, schema đúng, chuỗi nối được, injection không lọt, không bịa tool.
Đó là điều kiện **cần** để P02 khoá Qwen làm planner, và nó đã đạt.

Nó **không** chứng minh được:

| Chưa đo | Vì sao quan trọng |
|---|---|
| **Ngữ cảnh dài** (50K/130K/180K) | [U] llama.cpp cảnh báo `-ctk q4_0` *"substantially degrade tool calling"*; suy giảm KV lộ ra ở **ngữ cảnh sâu**, không ở prompt 2K như lô này |
| **A/B `q8_0` vs `q4_0`** | cái giá của quyết định giữ 200K, vẫn chưa có con số |
| MTP bật/tắt · `reasoning_effort` low/xhigh | biến số production chưa cô lập |
| Vòng lặp **thật** nhiều bước | lô này **nạp sẵn** kết quả tool; chưa lượt nào chạy N vòng model liên tiếp |
| **Đường ống LTT** | `runtime_noi_bo` có gửi `tools` không, `su_kien` có giữ `tool_call.delta` không, tiền có đúng không |

⭐ Một bộ kiểm mà đối tượng đạt 100 % là một bộ kiểm **không phát hiện được hồi
quy**. Với phán quyết PASS hôm nay thì đủ; làm lưới đỡ cho P03–P12 thì chưa.
Phần khó nằm ở bốn dòng đầu bảng trên, và đó là việc kế tiếp.

## §4 — Phán quyết chính thức

> **PASS.** Hợp đồng phục vụ Qwen3.8 đủ điều kiện làm nền cho điều phối tool của
> V3. P02 được phép khoá Qwen làm planner.
>
> **Kèm hai điều kiện ghi rõ:**
> 1. PASS này đo ở **ngữ cảnh ngắn**. Ngữ cảnh dài và A/B KV còn nợ, và chúng là
>    chỗ [U] cảnh báo suy giảm. PASS không được viện dẫn cho ngữ cảnh sâu cho
>    tới khi đo xong.
> 2. Ma trận **chưa đủ khó** để làm lưới đỡ hồi quy. P03 phải làm nó khó lên
>    trước khi dựa vào nó.
