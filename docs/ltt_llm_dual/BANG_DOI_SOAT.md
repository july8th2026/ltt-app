# BẢNG ĐỐI SOÁT — hệ ltt_llm dual-model

> Lập **2026-09-13**. Mọi dòng **đo được trong ngày**, bằng lệnh trên production
> và trên cây này. Không dòng nào chép lại từ hồ sơ cũ.
>
> ⛔ Tệp này **không** định nghĩa quy trình. Nguồn chân lý của nghiệm thu là
> `docs/superpowers/specs/2026-09-11-ltt-llm-dual-model-design.md` §23 (**A–Q**).

## 0. Ký hiệu — chốt một hệ, bỏ hệ kia

Hai hệ đang cùng tồn tại và **không** ánh xạ 1-1:

| Hệ | Ở đâu | Phán quyết |
|---|---|---|
| **A–Q** | spec §23 | ✅ **canonical** |
| `S2.1 … S6.7` | `BAN_GIAO_PHIEN.md` §7 | ⛔ cách đánh số riêng của phiên 12/09 — **bỏ** |

## 1. Tầng hạ tầng — đo 13/09

| Tầng | Đo được | Khớp spec? |
|---|---|---|
| Bề mặt công khai | `/api/v1/models` → `ltt-3.5` + `ltt-3.8`, kèm `context_window`, `reads_images:true` | ✅ D02 · L-19 |
| `llm_waiters` | 20 cột, có `model`, `cho_residency_s` | ✅ §7 |
| `execution_leases` | 13 cột, có `lop`, `token_dat_truoc`, `token_prefill_moi`, `la_whale` | ✅ T3 |
| `gpu_residency` | 6 cột: `nhom`·`trang_thai`·`tu_luc`·`cua_so_bat_dau`·`lan_nap_loi`·`phien_ban` | ⚠️ §2 dưới |
| Trọng tài residency | 1 dòng `rtx3090` → `trang_thai=llm`, `lan_nap_loi=0`, cửa sổ ảnh đóng | ✅ §12 |
| Sổ lượt | **297 dòng**: 161 `qwen38-api`/`ltt_38_3090` + 136 `qwen35-api`/`ltt_35_5060`, **100 % `xong`** | ✅ hai pool tách |
| Lease sống | 0 khi máy rảnh | ✅ không rò |
| alembic | production `a3f7c214e8b9` **=** head của cây | ✅ deploy được |
| Mã vs `C:\LTTPlatform\app` | khác **đúng 1 tệp**: `platform_core/api_pool.py` | biến số cô lập |
| Khoá provider `ltt_llm` | **1 hàng**, `active`, `total_requests=923` | 🔴 gốc L-01 |

## 2. ⚠️ `gpu_residency`: spec trôi, KHÔNG phải mã thiếu

Spec §7 đòi thêm `thanh_vien_dang_giu` và `so_anh_trong_cua_so`; CSDL và
`models.py` **không có cả hai**. Suýt ghi đây là lỗi — **nó không phải**:

| Trường spec | Mã làm gì thay thế | Phán quyết |
|---|---|---|
| `thanh_vien_dang_giu` | suy từ `trang_thai` (`llm` ⇒ `ltt_38_3090` giữ; `anh` ⇒ `anh_3090`) | dư thừa, bỏ đúng |
| `so_anh_trong_cua_so` | **đếm từ bảng `jobs`** (`residency.py:216` `anh_bat_dau_trong_cua_so`) | **tốt hơn** spec |

`residency.py:216` nói thẳng lý do: *"Đếm từ bảng `jobs`, không phải một bộ đếm
ghi tay"* — một bộ đếm ghi tay lệch được, đếm từ nguồn thật thì không.

⇒ Việc đúng là **sửa spec §7**, không phải thêm cột.

## 3. Bảng nghiệm thu A–Q — trạng thái

Quy trình đã chốt: `P0→P7 → Spec 2 → nghiệm thu tích hợp A–Q **một lần**` (D05).

### ⚠️ Đợt đang chạy là **nghiệm thu Spec 1**, không phải đợt tích hợp của D05

Chủ sản phẩm chốt **13/09/2026** (phương án B): đợt nghiệm thu này chạy **sau
Spec 1**, trong khi D05 định chạy A–Q **một lần sau CẢ HAI** Spec.

Hệ quả đúng một ô: **cổng L (đa tệp) thuộc Spec 2**, và Spec 2 chưa tồn tại —
chưa brainstorming, chưa spec, chưa plan, chưa một dòng mã (đường tệp→chữ của
ChatLTT, Docling cho PDF bố cục/bảng·XLSX·PPTX·OCR, đa tệp dưới/trên ngưỡng
token, ghi nguồn từng đoạn). Nên L **không thiếu thời gian, nó thiếu thứ để đo**.

⛔ Đừng "chạy thử" cổng L bằng một tính năng tự nghĩ ra. Một cổng xanh đo một
   thứ chưa ai duyệt thì tệ hơn một ô trống có ghi lý do.

⇒ L giữ nguyên trong bảng, trạng thái **⏸️ hoãn**, và sẽ chạy cùng đợt nghiệm
  thu của chính Spec 2. Mười sáu cổng còn lại đóng trong đợt này.

| | Nội dung | Trạng thái | Ghi chú |
|---|---|---|---|
| **A** | Tĩnh: hai ID, UUID, hash engine | ✅ | test 1200·1210·1220·1233 |
| **B** | C1 LTT-3.8 ≥ 90 % mốc b10883 | ✅ | đo ở P3 |
| **C** | C1 LTT-3.5 text + ảnh | ✅ | đo ở P3 |
| **D** | C3 LTT-3.8 | ⚠️ **đo lần 1** | 93,7 tok/s tổng, scaling 1,88×. Chưa chốt — §7 dưới nói vì sao |
| **E** | C4 LTT-3.5 | ⬜ | ngưỡng `2 × C1` chưa chốt số |
| **F** | Hai model đồng thời ≥ 85 % | ✅ **ĐẠT 13/09** | 4 vòng: 0,99× · 1,08× · 1,15× · 1,10× (ngưỡng ≥ 85 % ⇔ ≤ 1,18×); `pg_locks` 0/369 |
| **G** | Ngữ cảnh hỗn hợp, `requests_deferred=0` | ✅ **ĐẠT 13/09** | 4 số 0; ngữ cảnh thật 56.967 tok |
| **H** | 3.8 ngữ cảnh dài + cổng MTP | ⚠️ | đích **221.184 / `-np 3`** (L-14), không phải 262.144/`-np 4` |
| **I** | Residency: ảnh ↔ LLM xen kẽ | ✅ **ĐẠT 13/09** | chu trình đủ 182 s; huỷ giữa chừng lui 30 s. §7g |
| **J** | 3.5 chạy khi 3090 vẽ ≥ 90 % | ✅ **ĐẠT 13/09** | 111,5 vs 111,2 tok/s = **100 %** |
| **K** | Kho ấm: nạp lạnh vs ấm | ✅ **ĐẠT 13/09** | 9B: 12,93/0,43 s · 27B: 18,29/0,92 s; đối chứng hằng số 25 s trong mã |
| **L** | Đa tệp | ⏸️ **HOÃN** | thuộc **Spec 2** (chưa tồn tại) — chạy cùng nghiệm thu Spec 2. Lý do đầy đủ ở §3 |
| **M** | Hủy 6 trạng thái, slot trống ≤ 2 s | ⚠️ **đạt ở tầng mã** | huỷ job 0,33/0,36 s · client cắt: **1,43 s** thẳng máy A, 16,8 s qua Cloudflare (biên) |
| **N** | 7 lỗi hạ tầng | ⬜ | |
| **O** | Tiền: 7 tình huống, 0 thu hai lần | ✅ **ĐẠT 13/09** | 4 hold / 2 refund / 2 settle khớp đôi; 0 khoản treo |
| **P** | Rò lease generator, 5 điểm | ✅ **ĐẠT 13/09** | `execution_leases` về 0 sau cả 4 kịch bản |
| **Q** | Soak hỗn hợp | ⬜ | đòi A–P qua trước |

## 4. 🔴 Vì sao F là cổng CHẶN, không phải một lỗi lẻ

Spec §8 tuyên bố bất biến **L-7**: *"advisory lock theo `resource` ⇒ hai pool là
hai khoá độc lập, tải 3.8 không bao giờ lấy suất/ngân sách 3.5 và ngược lại"*.

Lý luận ấy **chỉ xét admission** — và ở tầng admission nó **đúng**: hai resource
`ltt_38_3090` / `ltt_35_5060` cho hai khoá advisory rời nhau (đã đọc mã, đã đo).

Nhưng đường đi thật có một điểm tuần tự hoá **nằm ngoài admission**:

```
dieu_phoi.goi(db, ...)
  api_pool.chon_key(db, ...)   -> UPDATE api_keys ... flush()   (KHONG commit)
  _goi_openai(...)             -> 3-20 giay goi may B
  api_pool.danh_dau_thanh_cong -> UPDATE lan hai
... commit mai o _finish_chat, SAU khi model tra loi
```

Một hàng `api_keys` duy nhất, chung cho **cả hai** model, bị khoá suốt lượt gọi.
⇒ **F không thể qua khi L-01 còn sống**, và đó mới là lý do L-01 xếp CHẶN —
không phải vì "nó đang đỏ".

Bản sửa khôi phục L-7 ở tầng spec chưa nhìn tới. Vì nó sửa tại `chon_key`, nó gỡ
luôn một nguồn khoá thứ hai: **vòng thăm `/health` của worker**
(`job_runner.py:1239`) cũng gọi `chon_key` mỗi vài giây trên đúng hàng ấy.

## 5. Lưu lượng thật 14 ngày — và một mục PHẢI ĐO, chưa phải phát hiện

| ngày | `done` | `error` |
|---|---:|---:|
| 04/09 | 103 | 5 |
| 05/09 | 184 | 7 |
| 06/09 | 207 | 12 |
| 07/09 | 610 | 5 |
| **08/09** | 490 | **64** |
| **09/09** | 81 | **34** |
| 10/09 | 35 | 3 |
| 11–13/09 | — | — |

**108/131 lỗi là một loại duy nhất:**
`AmbiguousProviderError: mat ket noi sau khi bat dau gui`.

⚠️ **CHƯA kết luận đây là hậu quả của L-01.** Nó khớp gọn — chờ khoá ăn mòn
`timeout_s` (`_con_lai_s` tính từ lúc request **vào cửa**, không phải lúc gọi),
rồi httpx đứt giữa chừng. Nhưng bàn giao §9 ghi đúng bài học này: *"một giả
thuyết khớp quá vừa là lúc phải nghi nhất"* — và L-01 đã bác bỏ một giả thuyết
khớp y như vậy ("khoá advisory theo tài khoản").

⇒ Ghi vào sổ là **mục cần đo**, đo sau khi deploy bản sửa: nếu L-01 là nguyên
nhân thì lớp lỗi này phải **biến mất**, không phải giảm.

## 6. Việc tiếp theo — thứ tự cứng

1. gate xanh
2. deploy máy A (biến số cô lập: **1 tệp**)
3. đo cổng **F** trên đường thật: `do_cheo_l01.py` **+** `soi_khoa_hang.py`
   (bằng chứng cơ học `pg_locks`, không chỉ con số thời gian)
4. **hai vòng liên tiếp trùng khớp** mới chốt (điều kiện dừng của chủ sản phẩm)
5. chốt ngưỡng **D**/**E** theo 3 luồng (L-14)
6. G–Q theo lô, máy B đi trước

## 7. Cổng D — đo lần 1 (13/09/2026), **chưa chốt**

Spec §23 ghi cổng D là *"C4 LTT-3.8: tổng ≥ 100 tok/s"*. L-14 đã hạ **C4 → C3**,
nên con số 100 — viết cho 4 luồng — không còn trả lời được câu hỏi này.

⛔ Và **không được** suy `100 × 3/4 = 75`. Thông lượng không tỉ lệ tuyến tính với
số luồng: nó bị chặn bởi băng thông bộ nhớ, và phần chia ấy không chia đều. Đo
được scaling **1,88×** từ 1 → 3 luồng, không phải 3×.

| | đo được |
|---|---:|
| C1 đơn, **qua máy A** | 49,9 tok/s |
| **C3 tổng** | **93,7 tok/s** |
| mỗi luồng ở C3 | 31,7 tok/s (3 luồng đều nhau: 31,3 / 31,7 / 32,5) |
| scaling 1 → 3 luồng | **1,88×** |

### ⚠️ Hai lý do con số này CHƯA chốt được

1. **Khác đường đo.** Mốc C1 `63,01 tok/s` (G3b, 12/09) đo **thẳng máy B**; phép
   đo này đi **qua máy A + Cloudflare**. Hai con số trả lời hai câu khác nhau —
   so trực tiếp là đúng lỗi *"phạm vi phép đo hẹp hơn lời tuyên bố"*.
2. **Máy có tải.** Một lượt gate đang chạy trong lúc đo. `docs/BAY_TRONG_CONG_CHAT_LUONG.md`
   ghi rõ tải nặng làm phép đo **sai**, không chỉ chậm.

⇒ Phải đo lại khi máy rảnh, **≥ 3 lượt**, và đo **cả hai đường** (qua máy A và
  thẳng máy B) để tách phần overhead của máy A ra khỏi thông lượng của engine.

⛔ Chưa đề xuất ngưỡng mới cho C3. Một ngưỡng đặt theo một lượt đo có nhiễu là
   đúng thứ `nguong-dat-theo-mot-luot-do-tin-hieu-ngau-nhien` cảnh báo — và
   phiên này đã vấp nó một lần ở L-02 (300 → "đúng" ở 1 lượt, rỗng 3/5 khi đo 5).

## 7b. Cổng D và E — đo lần 2 (13/09), **máy rảnh, 3 lốt, hai đường**

Máy A: gate đã xong, deploy đã xong. Mỗi lốt đo **thẳng máy B** rồi **qua máy A**,
sát nhau về thời gian. `-np 3` cho cả hai hồ sơ ⇒ C3 là đúng cấu hình.

### Số đo (trung vị 3 lốt, tok/s)

| | C1 | C3 | scaling | 2 × C1 | spec đòi |
|---|---:|---:|---:|---:|---|
| **D** `ltt-3.8` thẳng B | 55,5 | **95,0** | 1,71× | 110,9 | — |
| **D** `ltt-3.8` qua A | 47,0 | **90,3** | 1,92× | 94,0 | ≥ 100 (viết cho C4) |
| **E** `ltt-3.5` thẳng B | 64,6 | **120,2** | 1,86× | 129,2 | ≥ 2 × C1 |
| **E** `ltt-3.5` qua A | 56,2 | **111,2** | 1,98× | 112,4 | ≥ 2 × C1 |

Dải 3 lốt: D qua A 87,0–91,9 · E qua A 110,8–114,0. 0 lượt hỏng trong cả 12 lốt.

### 🔴 Tiêu chí *"≥ 2 × C1 của chính nó"* là một tiêu chí HỎNG

Nhìn hai dòng của `ltt-3.8`: qua máy A, scaling **cao hơn** (1,92×) so với đo
thẳng máy B (1,71×). Máy A **chậm hơn** mà lại **ghi điểm tốt hơn**.

Không phải nghịch lý — đó là số học. Phí nền tảng là một khoản **cố định mỗi
request**, nên nó ăn vào C1 nặng hơn ăn vào C3 (nơi nó được chia cho 3 luồng):

```
ltt-3.8   C1  55,5 -> 47,0   giam 15,3 %
          C3  95,0 -> 90,3   giam  4,9 %
```

Mẫu số co nhiều hơn tử số ⇒ **tỉ số tăng**.

⛔ Tức một tiêu chí dạng tỉ số sẽ **thưởng cho việc làm nền tảng chậm đi**. Bất
kỳ ngưỡng nào cho D/E phải đặt trên **thông lượng tuyệt đối**, không trên tỉ số.
Tỉ số vẫn đáng ghi — nó chẩn đoán tốt — nhưng nó không được làm cửa.

### Đề xuất ngưỡng cho C3 — đặt dưới lượt tệ nhất đo được

Ngưỡng là **bộ dò hồi quy**, không phải lời chúc. Nó phải bắt được một suất bị
mất hay một khoá bị đặt lại, mà không đỏ vì nhiễu ±3 % đo được.

| cổng | đo qua | tệ nhất đo được | **ngưỡng đề xuất** | biên |
|---|---|---:|---:|---:|
| **D** `ltt-3.8` | máy A | 87,0 | **≥ 78** | 10 % |
| **E** `ltt-3.5` | máy A | 110,8 | **≥ 99** | 10 % |
| D bạn đồng hành | thẳng B | 94,8 | ≥ 85 | 10 % |
| E bạn đồng hành | thẳng B | 114,2 | ≥ 103 | 10 % |

⭐ **Vì sao cả hai đường.** Một mình số qua-A nói *khách chờ bao lâu* nhưng không
nói **hỏng ở đâu**. Có cặp số thì một lần đỏ tự phân loại: cả hai cùng tụt ⇒
engine/GPU; chỉ qua-A tụt ⇒ nền tảng máy A.

### ⚠️ Một chênh lệch CHƯA giải thích được — đừng lấp nó

| model | mốc C1 ghi 12/09 | C1 thẳng B đo 13/09 | lệch |
|---|---:|---:|---:|
| `ltt-3.8` | 63,01 | 54,8–57,9 | **−10 %** |
| `ltt-3.5` | 76,21 | 63,4–65,5 | **−15 %** |

Cả hai lệch **cùng chiều, cùng cỡ** — dấu hiệu của khác biệt **hệ thống**, không
phải nhiễu. Ba khả năng, chưa loại trừ cái nào: (a) đề đo khác (độ dài ra khác
⇒ tỉ lệ prefill/decode khác), (b) bộ đo 12/09 tính thời gian khác, (c) một hồi
quy thật.

⛔ **Chưa được dùng mốc 63,01 / 76,21 làm đối chứng cho tới khi biết đó là (a),
(b) hay (c).** Đây đúng là cái bẫy mà chính tệp này cảnh báo ở §7: so hai con số
sinh ra từ hai phép đo khác nhau rồi gọi hiệu số là một phát hiện.

### Phí nền tảng — đại lượng đo được, và nó rẻ dần khi tải tăng

| | C1 (B − A) | C3 (B − A) |
|---|---:|---:|
| `ltt-3.8` | 7,9–11,2 | 4,7–7,8 |
| `ltt-3.5` | 8,4–9,7 | 3,0–10,1 |

Đây là hai con số **được phép trừ vào nhau**: cùng một đại lượng, đo trong cùng
một lốt, trên cùng một trạng thái máy.


## 7c. Cổng G — ngữ cảnh hỗn hợp: **ĐẠT**, cả bốn số 0

Spec §23 đòi: `0 "Context size has been exceeded"` · `0 OOM` · `0 cắt ngầm` ·
`requests_deferred = 0`.

| cỡ | cửa | `ltt-3.8` | `ltt-3.5` |
|---|---|---|---|
| 200 tok | sync | 235 vào, nhớ mã | 235 vào, nhớ mã |
| 8K tok | sync | 7.634 vào, nhớ mã | 7.636 vào, nhớ mã |
| 60K tok | **job** | **56.967** vào, nhớ mã, 64–67 s | **56.965** vào, nhớ mã, 36 s |

2 vòng × 3 cỡ, thứ tự **ngẫu nhiên** (một lô tăng dần không phải lô hỗn hợp).
0 lỗi HTTP · 0 chuỗi cấm · 0 quên mã · `requests_deferred` đỉnh **0**.

⭐ **"Nhớ mã" là bằng chứng CHIỀU DƯƠNG cho "0 cắt ngầm".** Mỗi prompt mang một
mã ngẫu nhiên ở **ngay đầu**, và câu hỏi ở cuối là đọc lại chính nó. Ngữ cảnh bị
cắt từ đầu ⇒ model không thể trả lời — khác hẳn "không thấy chuỗi lỗi nào", thứ
vẫn xanh trong một hệ thống đã chết.

### Ba lần bộ đo suýt chấm điểm sai một hệ thống khoẻ

| bộ đo báo | sự thật |
|---|---|
| `chuỗi cấm: ['oom']` | khớp vào chữ **"room"** trong *"leaving **room** for at most 0 output tokens"* |
| `60K → 400 ⇒ cổng G TRƯỢT` | đó là **ngân sách thời gian của cửa sync** (100 s), không phải tràn ngữ cảnh. Ngữ cảnh dài thuộc về cửa **job** |
| `60K` | thật ra chỉ **24.634** token: `KY_TU_MOI_TOKEN` = 2,5 là ước **CAO** (đúng cho giữ tiền), nên dùng nó để *dựng* prompt thì prompt chỉ bằng 41 % cỡ đã đặt tên |

🔴 Cái thứ ba nguy hiểm nhất: nó khiến cổng báo **ĐẠT cho một điều kiện nó chưa
   từng dựng**. Sửa bằng một lượt **hiệu chuẩn** — hỏi chính máy chủ tỉ lệ thật
   (`usage.prompt_tokens`) rồi nhân lên. Sau hiệu chuẩn, cỡ thật đạt 56.967 và
   `llamacpp:n_tokens_max` **trên máy B** xác nhận độc lập: **56.979**.

### Và `requests_deferred` là GAUGE, không phải counter

Đọc nó lúc máy rảnh bao giờ cũng ra 0 — con số ấy không trả lời câu hỏi nào cả.
Phải lấy mẫu **trong cửa sổ có tải**, và phải chứng minh cửa sổ ấy trùng với lúc
có tải:

| model | số mẫu | đỉnh `requests_processing` | đỉnh `requests_deferred` |
|---|---:|---:|---:|
| `qwen35-api` | 229 | **3** | **0** |
| `qwen38-api` | 253 | **3** | **0** |

⭐ Cột `requests_processing` = 3 là **đối chứng của chính phép đo**: không có nó,
"deferred = 0" chỉ chứng minh tôi đã lấy mẫu lúc không có gì chạy.

## 7d. Cổng K — kho ấm: **ĐẠT**, và nó đối chứng một hằng số trong mã

| model | card | `t_lạnh` | `t_ấm` | **chi phí nạp** | lạnh/ấm |
|---|---|---:|---:|---:|---:|
| `qwen35-api` 9B | 5060 Ti | 12,93 s | 0,43 s | **12,50 s** | 29,9× |
| `qwen38-api` 27B | 3090 | 18,29 s | 0,92 s | **17,37 s** | 19,9× |

⛔ **`t_lạnh` một mình KHÔNG phải "thời gian nạp"** — nó gồm cả phần sinh chữ.
Chỉ **hiệu** hai số mới là phần nạp. Bộ đo đầu của tôi ở cổng D lấy nhầm `t_lạnh`
làm C1 và cho ra *"scaling 3,93×"* cho 3 slot — một con số bất khả.

### Đối chứng: hằng số dự phòng nạp model trong mã

`features.SYNC_DU_PHONG_NAP_MODEL_GIAY = 25` — cửa đồng bộ chừa 25 giây cho ca
llama-swap phải nạp lại model. Đo được **17,37 s** cho model nặng nhất ⇒ hằng số
ấy **đủ, còn biên 30 %**. Một con số gõ tay nay có phép đo đứng sau.

### Và nhả THEO TÊN MODEL hoạt động đúng — L-17 được xác nhận trên đường thật

`POST /api/models/unload/qwen35-api` làm `/running` mất **đúng một** mục;
`qwen38-api` ở lại nguyên vẹn. Đó chính là điều L-17 sinh ra để bảo đảm: hai
đường không tham số (`GET /unload`, `POST /api/models/unload`) nhả **hết**, và
từ khi máy B có hai model, chúng giết luôn model trên card **không ai tranh**.

⭐ Bộ đo tự dựng hai rào trước khi nhả, và cả hai đều cần thiết:

1. **`requests_processing` phải bằng 0.** `unload` của llama-swap không drain
   (`fifo.go:222-270`), nên một lệnh nhả phát ra lúc còn in-flight là cắt một
   lượt của khách giữa chừng (L-9).
2. **`/running` sau khi nhả phải hết tên model ấy.** Thành công im lặng là kết
   cục tệ nhất: nếu lệnh nhả không có tác dụng thì `t_lạnh` đo được thực ra là
   một `t_ấm` thứ hai, và nó sẽ nói dối về chi phí nạp — theo hướng đẹp lên.

## 7e. Cổng M, O, P — hai đạt, một lộ ra lỗi mới (L-06)

Bốn kịch bản, đo `execution_leases` **trước** mỗi kịch bản làm đối chứng — một
số 0 sau kịch bản không chứng minh gì nếu trước đó cũng là 0.

| kịch bản | kết cục | trả slot | tiền |
|---|---|---:|---|
| bình thường (sync) | 200 | — | `hold −1` + `settle +1` |
| huỷ lúc **xếp hàng** | `cancelled` | **0,33 s** | `refund` đủ, không thu |
| huỷ lúc **đang chạy** | `cancelled` | **0,36 s** | `refund` đủ, không thu |
| **client cắt kết nối** | — | **15,4 s** 🔴 | vẫn bị tính |

### Cổng P — ĐẠT

`execution_leases` về **0** sau tất cả bốn kịch bản. Không rò.

### Cổng O — ĐẠT

4 `hold` (−4) · 2 `refund` (+2) · 2 `settle` (+2), khớp đôi. **0 khoản treo**,
0 thu hai lần, job huỷ được hoàn.

⛔ Và phép đếm khoản treo đầu tiên của tôi ra **62** — một dương tính giả: sổ
ghi kép giữ *cả* dòng `hold` lẫn dòng `settle`, nên đếm `hold` trên job đã xong
là đếm bút toán bình thường. Khoản treo thật là một `hold` **không có** bản đối
ứng, và chỉ một phép `NOT EXISTS` mới nói được điều ấy.

### Cổng M — huỷ job ĐẠT, cắt kết nối TRƯỢT ⇒ **L-06**

Huỷ qua API đạt thừa (0,33 / 0,36 s so với ngưỡng 2 s). Nhưng client **cắt kết
nối** giữa chừng thì slot bị giữ tới **15,4 s**, và thời gian ấy **tỉ lệ với
`max_tokens`** (900 → 15,4 s · 1024 → 17,2 s · 2000 → 31,9 s).

Gốc: `apps/ltt_llm/jobs.py:81` bọc lượt trong `huy_luot.phien(ma_luot)`;
`server/api/chat.py` **không có** dòng tương đương. Chi tiết ở `SO_LOI_DO_TAI.md`
mục L-06.

## 7f. Cổng J — **ĐẠT 100 %**; cổng I — **TRƯỢT**, và nó tìm ra L-07

### J: `ltt-3.5` chạy trong lúc 3090 vẽ

| | tok/s |
|---|---:|
| C3 riêng, đo ở cổng E cùng ngày | 111,2 |
| C3 **trong lúc 3090 đang xả LLM cho ảnh** | **111,5** |

**100 %** (ngưỡng ≥ 90 %), 0 lỗi. Hai card thật sự độc lập: `ltt-3.5` trên
5060 Ti không mất gì khi 3090 đổi cư trú.

⭐ Mốc lấy từ phép đo **cùng ngày cùng máy**, không lấy mốc 12/09 — chính tệp này
ghi một chênh 10–15 % giữa hai ngày mà chưa ai giải thích được, và mượn mốc ấy
là mang theo cả phần chưa giải thích.

### I: TRƯỢT — nhưng không vì lý do bộ đo nói

Bộ đo báo *"3 lượt LLM chết giữa chừng"*. **Sai.** Ba lượt ấy nhận **HTTP 429
`concurrency_limited`** — admission **từ chối đúng**, vì 3090 đã rời trạng thái
`llm`. Một lượt bị từ chối ở cửa không phải một lượt chết giữa chừng. Đây là
lần thứ tư trong phiên bộ đo chấm điểm một hành vi ĐÚNG thành một cổng trượt.

Cái trượt thật nằm ở chỗ khác, và nó nặng hơn nhiều:

| | |
|---|---|
| job ảnh | **không bao giờ được vẽ** — `queued`, `progress 0`, heartbeat đập suốt 17 phút |
| `gpu_residency` | kẹt ở `nha_llm` **32 phút** |
| `ltt-3.8` | **429 cho mọi yêu cầu** suốt 32 phút |
| 3090 | 184 MiB / 24576 — nằm không, không ai dùng |

Gốc: cổng render máy B chạy bản cũ, thiếu `/v1/nha_comfy` → `chay_comfy()` 404 →
không vào được `ANH` → mà `nha_llm` **không có đường lui nào khác**. Toàn văn ở
`SO_LOI_DO_TAI.md` mục **L-07**.

🔴 **Đây là sự cố production thật**, không phải một con số trượt. Đã khôi phục
bằng can thiệp tay lúc 05:29 (ba rào tự kiểm trước khi ghi). **Gốc chưa sửa** —
job ảnh kế tiếp lặp lại y nguyên.

## 7g. Cổng I — **ĐẠT**, và L-07 đóng bằng hai phép đo chứ không một

### Phép 1 — chu trình bình thường

```
 0,6s llm · 4,1s xa_llm · 7,0s nha_llm · 16,3s anh
148,8s job ảnh succeeded
151,7s tra_anh · 159,9s nap_llm · 182,1s llm   →  ltt-3.8 HTTP 200 trong 2,0 s
```

Bước từng gãy — `nha_llm → anh`, tức lượt `chay_comfy()` — nay đi qua trong
**9,3 s**.

### Phép 2 — HUỶ giữa chừng, đúng kịch bản đã hỏng

```
 0,8s xa_llm · 3,5s nha_llm
 4,9s HUỶ job ảnh → HTTP 200
11,4s nap_llm     ← ĐƯỜNG LUI, nó không tồn tại trước 13/09
29,9s llm         →  ltt-3.8 HTTP 200 trong 1,7 s
```

Chuỗi **bỏ qua `anh` hoàn toàn** — đúng thiết kế: đường lui 1 nổ khi
`job_anh_cho == 0`.

⛔ **Vì sao phép 1 một mình là chưa đủ.** Nó đi qua `anh`, tức nó chỉ chứng minh
   phần deploy máy B. Đường lui **không bao giờ được chạm tới** trong một lượt
   chạy suôn sẻ. Dừng ở đó là báo "đã sửa" cho một nửa chưa ai thử — và nửa ấy
   chính là nửa mà hôm 13/09 phải ghi tay vào CSDL mới gỡ được.

⭐ Cùng hình dạng với bài học *"không đối chứng thì số không không phải phát
   hiện"*: một cổng chỉ hỏi kết cục sẽ **ĐẠT cho đúng sự cố đã xảy ra**.

## 8. Sổ lỗi L-* — trạng thái cuối lượt 13/09

| mã | trạng thái | ghi chú |
|---|---|---|
| **L-01** | ✅ **đóng** | 4 vòng 0,99–1,15×; `pg_locks` 0/369; deploy + nghiệm thu 0/0/0 |
| **L-02** | ✅ **đóng** | sàn `max_tokens` theo model × mức, đặt **sau** 413; nghiệm thu 4/4 mệnh đề trên đường thật |
| **L-03** | ✅ **đóng** | cả hai model khai `reads_images`; `DEVELOPER_GUIDE` + CHANGELOG đã sinh lại |
| **L-04** | ✅ **đóng** | bộ chấm đổi sang mệnh đề dương; bản cũ chấm 3/3 câu sai thành "đúng" |
| **L-05** | ✅ **đóng** | 48/48 done, 0 lỗi; p = 0,3 % nếu tỉ lệ 11,6 % còn nguyên |
| **L-06** | ✅ **đóng ở tầng mã** | loopback 16,54 → **1,43 s**. Qua Cloudflare vẫn 16,8 s — biên không báo origin, không sửa được ở tầng mã |
| **L-07** | ✅ **đóng** | deploy máy B + đường lui; nghiệm thu 2 phép trên đường thật |

⭐ Năm mục L-01…L-05 đều đóng, và mỗi mục đóng bằng một **phép đo trên đường
thật**, không bằng một bản vá đã commit. L-06 là mục **mới**, do chính cổng M
tìm ra — đó là điều một cổng nghiệm thu sinh ra để làm.
