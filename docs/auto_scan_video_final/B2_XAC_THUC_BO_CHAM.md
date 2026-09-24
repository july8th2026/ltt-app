# B2 — XÁC THỰC BỘ CHẤM ngữ nghĩa (làn `xac-thuc-cham`, 24/09/2026)

> **Câu hỏi duy nhất:** lượt chạy thật chấm **44/95 mục (46%)** là *dịch sai*.
> **46% đó là bản dịch tệ thật, hay bộ chấm quá tay?**

## 1. NGƯỠNG — viết TRƯỚC khi chạy dòng lệnh nào

```
Bộ chấm ĐÁNG TIN khi: tỉ lệ báo động giả ≤ 15% trên ≥ 100 cặp FLORES zh→vi.
> 15% ⇒ con số 44/95 KHÔNG dùng được để kết luận về bản dịch, và việc tiếp theo
        là sửa BỘ CHẤM, không phải sửa bản dịch.

Bộ chấm còn SỐNG khi: tỉ lệ bắt lỗi tiêm ≥ 50% ở MỖI loại (lật nghĩa / sai
        thực thể), trên ≥ 30 cặp đã làm hỏng có chủ ý.
```

🔴 Không có đối chứng âm thì *"báo động giả 0%"* có thể chỉ nghĩa là bộ chấm
**không bao giờ báo gì**, và ta sẽ kết luận nó đáng tin trong khi nó đã chết.

## 2. Cách đo (Q6)

FLORES-200 `zho_Hans` ↔ `vie_Latn` **do người dịch**, split `dev`. Cặp (nguồn zh,
bản dịch chuẩn vi) đi qua **chính** đường sản phẩm — `qc_ai.loi_nhac_ngu_nghia`
→ `ai.goi(QC_NGU_NGHIA)` → `qc_ai.doc_ngu_nghia`, model `ltt-3.8`
(`Qwen3.8-27B-UD-Q4_K_M`), lô 10. Mọi phán quyết *"dịch sai"* ⇒ **báo động giả
theo định nghĩa**. Cổng áp `--temp 1.0` và `seed` không có hiệu lực ⇒ **3 lượt**
mỗi cặp, lấy **trung vị**, báo kèm **dải**.
Công cụ: `tools/bench_b2_xac_thuc_bo_cham.py` · bằng chứng:
`bang_chung/b2_xac_thuc_bo_cham.json`.

## 3. Kết quả

| Phép đo | Cỡ mẫu | Tỉ lệ (trung vị) | Dải từng lượt | Lượt/cặp |
|---|---|---|---|---|
| **Báo động giả** (FLORES, NGƯỜI dịch) | 100/100 | **45,0%** | 40,0 – 44,4% | 3 |
| Bắt lỗi tiêm — `lat_nghia` | 15/15 | **100%** | 100 – 100% | 3 |
| Bắt lỗi tiêm — `sai_thuc_the` | 15/15 | **100%** | 100 – 100% | 3 |

- 90/100 cặp có đủ 3 lượt; **10 cặp chỉ có 2** — một lô trả JSON hỏng
  (`LuocDoSai`, 1/30 lô = 3,3%). Giả định thuận lợi nhất (mọi cặp 2-lượt hoà đều
  là ĐẠT) vẫn cho **43%** ⇒ phán quyết không đổi.
- ⭐ **Ngưỡng độ tin không lọc được gì:** **98,4%** (120/122) báo động giả mang
  `do_tin ≥ 0,70` = `sua_chua.DO_TIN_TOI_THIEU`. Trung vị `do_tin` của một báo
  động giả là **0,85**. Đúng khuôn M-10 ở lớp hình (14/15 vượt ngưỡng).
- ⭐ **Lỗi tiêm bị bắt THẬT, không phải trúng nền:** 28/30 `ly_do` **gọi đúng
  tên** thứ đã bị đổi (9/9 số, 6/6 tên riêng, 13/15 từ phủ định/trái nghĩa).
  Nếu 100% chỉ là hệ quả của nền 45% thì lý do đã nói sang chuyện khác.

## 4. PHÁN QUYẾT

🔴 **Bộ chấm KHÔNG đáng tin. 45,0% > ngưỡng 15% — gấp ba.**

⇒ **Con số 44/95 (46%) KHÔNG dùng được để kết luận về bản dịch.** Nó gần như
trùng khít tỉ lệ mà chính bộ chấm này gán cho **bản dịch của người dịch chuyên
nghiệp** (45%), nên nó không phân biệt được bản dịch của ta với một bản dịch
hoàn hảo. ⛔ Việc tiếp theo là **sửa BỘ CHẤM**, không phải sửa bản dịch.

**Nhưng nó KHÔNG chết, và đây là chỗ khác hẳn M-10:** độ nhạy 30/30. Bệnh là
**độ đặc hiệu**, không phải độ nhạy — nên đường sửa là *siết điều kiện
`dat=false`* (lời nhắc đang cho phép gắn cờ mọi khác biệt diễn đạt), ⛔ không
phải đổi model và càng không phải hạ lớp này xuống tư vấn.

⚠️ **Và nó mạnh đúng chỗ MetricX yếu:** `L_DICH.md` §3 ghi MetricX có AUC **0,61**
cho lật nghĩa zh→vi; `qc_ai` bắt **15/15**. Hai bộ đo bù nhau — ⛔ đừng bỏ lớp
`qc_ai` để chỉ còn MetricX.

## 5. ⛔ Những điều phép đo này KHÔNG trả lời

1. **Miền văn bản khác.** FLORES là văn **tin tức/Wikipedia**, câu dài ~21 từ,
   dấu câu đầy đủ. Ta là **lời nói clip mạng** qua ASR: câu ngắn, thiếu dấu câu,
   có lỗi nhận dạng. Con số 45% là **giới hạn dưới** của tỉ lệ báo động giả
   trong miền của ta, ⛔ **không phải con số đúng miền** — câu nguồn nhiễu chỉ
   cho bộ chấm thêm cớ để gắn cờ.
2. **Bản dịch của ta có tệ không.** Phép đo này nói *"thước đo hỏng"*, ⛔ nó
   **không** nói bản dịch tốt. Câu đó còn mở, và cần một thước khác (MetricX QE,
   hoặc người soi tay) — Task 12.
3. **Bao nhiêu trong 44 là thật.** Cần soi tay chính 44 mục đó; ở đây chỉ mới
   chứng minh con số **không dùng được như một tỉ lệ**.
4. **Model khác / lời nhắc khác.** Chỉ đo `ltt-3.8` với lời nhắc hiện tại.
5. **Cặp tiêm cũng là FLORES**, nên 100% bắt được là trên văn tin tức sạch; chưa
   biết tỉ lệ bắt trên câu ASR nhiễu.

## 6. Tái lập

```
python tools\bench_b2_xac_thuc_bo_cham.py tai
python tools\bench_b2_xac_thuc_bo_cham.py do --pha fa --tu 0  --n 50 --luot 3 --ra fa_a.json
python tools\bench_b2_xac_thuc_bo_cham.py do --pha fa --tu 50 --n 50 --luot 3 --ra fa_b.json
python tools\bench_b2_xac_thuc_bo_cham.py do --pha tiem --tiem-moi-loai 15 --tiem-bo-qua 100 --luot 3 --ra tiem.json
python tools\bench_b2_xac_thuc_bo_cham.py gop --fa fa_a.json fa_b.json --tiem tiem.json --ra b2.json
python tools\bench_b2_xac_thuc_bo_cham.py bang-chung b2.json --ra docs\auto_scan_video_final\bang_chung\b2_xac_thuc_bo_cham.json
```

⛔ Bằng chứng commit lên kho **không mang một chữ nào của FLORES** (CC-BY-SA-4.0,
ShareAlike) — `ban_ghi_sach` cưỡng chế điều đó, `test_3600` chốt nó. Giấy phép:
`THIRD_PARTY_METRICS.md` §1 dòng 11. Hai tiến trình chạy song song = trần 2
request/model; ⛔ không giữ `cpu_nhieu` (chỉ chờ mạng máy B).

---

# 7. TRA NGUỒN trước khi sửa (luật 10) — và nguồn nói CÁCH CHẤM NHỊ PHÂN LÀ SAI THIẾT KẾ

⛔ Mục này viết **trước** khi sửa một chữ nào trong lời nhắc. Bản brief đầu bảo
*"đọc lý do rồi sửa lời nhắc"* — tức bảo tự suy. Đây là bước tra nguồn thay thế.

## 7.1 Phát hiện lớn hơn một bản vá: **nhị phân là chỗ độ đặc hiệu chết**

Bộ chấm của ta hỏi model một câu **nhị phân** — `dat: true/false`. Không một giao
thức nào trong tài liệu làm thế. **Tất cả** đều yêu cầu model liệt kê **từng lỗi**
kèm **phân loại** và **mức nghiêm trọng**, rồi **tính điểm** từ đó:

| Giao thức | Nguồn | Đầu ra | Giấy phép |
|---|---|---|---|
| **GEMBA-MQM** | Kocmi & Federmann, WMT 2023 · arXiv **2310.13988** · `MicrosoftTranslator/GEMBA` | lỗi = `phân loại/tiểu loại - "đoạn trích"`, mức `critical/major/minor` | **CC BY-SA 4.0** (`LICENSE.md`) |
| **GEMBA-ESA** | cùng repo, `gemba/gemba_esa.py` | hai chặng: đánh dấu đoạn lỗi (`major/minor`) → chấm 0–100 **dựa trên đoạn lỗi đó** | CC BY-SA 4.0 |
| **AutoMQM** | Fernandes et al., WMT 2023 · arXiv **2308.07286** | lỗi + phân loại; *"improves performance compared to just prompting for scores"* | không thấy mã mở |
| **MQM-APE** | Lu et al. 2024 · arXiv **2409.14335** · `Coldmist-Lu/MQM_APE` | GEMBA-MQM **+ bộ lọc lỗi** | ⛔ **KHÔNG có tệp LICENSE** ⇒ mặc định giữ toàn quyền |
| **xCOMET** | arXiv 2310.10482 | điểm + đoạn lỗi | ⛔ **CC-BY-NC-SA-4.0** — đã ở §2 DO NOT SHIP |

🔑 **Cơ chế hạ báo động giả nằm ở THANG ĐIỂM, không ở lời văn.** `GEMBA/gemba/
gemba_mqm_utils.py::parse_mqm_answer`: `critical = 25 · major = 5 · minor = 1`,
chặn ở **5 lỗi đầu** và trần **25**. ⇒ một câu có năm lỗi **minor** vẫn chấm
5/25, tức **vẫn tốt**.

⭐ **Và đó đúng là hình dạng báo động giả của ta.** Đọc `ly_do` của 122 lượt báo
động giả: gần hết là **minor** theo MQM — mất sắc thái (*"nổi tiếng"* không đủ
*"tai tiếng"*), thiếu một bổ ngữ (*"thiếu 地区"*, *"thiếu 空军"*), thêm một chữ
(*"thêm phản lực"*), thay tên riêng bằng đại từ (*"Đài Loan" → "nước này"*). Bộ
chấm của ta **không có chỗ để nói "minor"** — nó chỉ có `false`. ⇒ Mọi nhận xét
tinh tế đều rơi xuống cùng một ô với *"lật nghĩa"*.

⇒ **Không phải lời nhắc dài hơn. Là thiếu một CHIỀU.**

## 7.2 Ba câu hỏi — trả lời từ nguồn

**1. Cộng đồng hạ báo động giả bằng cách nào?** Ba cơ chế, cả ba đều đã đo:
- **Phân mức nghiêm trọng** thay vì nhị phân, và **trọng số** (25/5/1) — GEMBA-MQM.
  Định nghĩa neo vào **hậu quả cho người đọc**: *critical* cản hiểu; *major* phá
  mạch nhưng vẫn hiểu được; *minor* là lỗi nhưng không cản hiểu.
- **Bắt trích dẫn ĐOẠN lỗi** (`- "involvement"`), không cho nhận xét chung chung —
  GEMBA-MQM, xCOMET, AutoMQM đều vậy. Đúng giả thuyết của điều phối.
- **Lọc lỗi bằng hậu kiểm** — MQM-APE: sửa bản dịch theo **từng** lỗi, rồi hỏi bản
  sửa có **tốt lên** không; lỗi nào sửa mà không tốt lên thì **vứt**. Đặt tên cho
  đúng thứ ta đang gặp: *non-impactful errors*.

**2. Có bộ lời nhắc đã công bố cho zh→vi không?** Không có zh→vi riêng. GEMBA-MQM
**cố ý dùng lời nhắc bất khả tri ngôn ngữ** (*"language-agnostic prompts, thus
avoiding the need for manual prompt preparation for new languages"*) với 3 ví dụ
cố định (ende/encs/**zhen**). ⇒ Dùng được cho zh→vi **theo thiết kế**.
⛔ **Nhưng giấy phép chặn việc CHÉP:** GEMBA là **CC BY-SA 4.0** — ShareAlike, nên
dán nguyên văn lời nhắc vào một sản phẩm đóng sẽ kéo ShareAlike theo. MQM-APE
**không có LICENSE** ⇒ còn chặt hơn. ⇒ **Dùng lại GIAO THỨC** (ý tưởng + thang
điểm MQM, vốn là chuẩn MQM chứ không phải của GEMBA), ⛔ **không chép lời văn**.

**3. `do_tin` tự khai có hiệu chỉnh không? — KHÔNG, và có nên bỏ cổng 0,70.**
- arXiv **2603.25052**: *LLM khai điểm tin cậy "largely detached from their actual
  accuracy"*; và ⭐ **khi model vừa lập luận vừa tự khai độ tin thì chính quá trình
  lập luận phá tín hiệu độ tin, làm lệch hiệu chỉnh NẶNG THÊM**. Lời nhắc của ta
  đòi **đúng** hai thứ đó trong một phản hồi: `ly_do` **và** `do_tin`.
- arXiv **2605.12446** (ORCE): *"LLMs often produce answers with high certainty even
  when they are incorrect"*.
- Và số của chính ta khớp: **98,4%** báo động giả có `do_tin ≥ 0,70`, trung vị 0,85.
⇒ ⛔ `DO_TIN_TOI_THIEU = 0,70` **không cứu được bằng lời nhắc**. Phải bỏ, hoặc thay
bằng một tín hiệu **đo được**.

## 7.3 ⭐ Một tín hiệu thay thế, đã đo, MIỄN PHÍ từ dữ liệu đang có

Cổng đang chạy `--temp 1.0` nên ba lượt của ta là ba mẫu độc lập. Đổi luật gộp từ
**đa số (≥2/3)** sang **đồng thuận (3/3)**:

| Luật gộp | Báo động giả | Bắt `lat_nghia` | Bắt `sai_thuc_the` |
|---|---|---|---|
| đa số ≥ 2/3 (hiện tại) | 43–45% | 100% | 100% |
| **đồng thuận 3/3** | **23%** | **100%** | **100%** |

Cả 30 cặp tiêm đều bị bắt ở **cả ba** lượt (`so_bao_sai = 3/3`, không một cặp nào
thấp hơn) ⇒ siết lên đồng thuận **không mất một chút độ nhạy nào** mà cắt gần một
nửa báo động giả. ⛔ Vẫn **23% > 15%**, nên nó **không đủ một mình** — nhưng nó là
bằng chứng trực tiếp rằng *self-consistency* phân biệt được còn `do_tin` thì không.
⚠️ Cái giá: đường sản phẩm hiện gọi **một** lượt mỗi lô; đòi 3/3 là **gấp ba** chi
phí lớp này. Đó là một quyết định về GIÁ, phải hỏi chủ dự án.

---

# 8. BẢN SỬA V2 — phân mức MQM. Bảng ánh xạ viết TRƯỚC khi đo

⛔ Mục này viết **trước** khi chạy phép đo V2. Không chỉnh bảng sau khi thấy số.

## 8.1 Giấy phép GEMBA — đã kiểm lại, đọc thẳng nguồn

Ba nguồn khớp nhau (24/09): GitHub API `spdx_id` = **`CC-BY-SA-4.0`**; **không có**
tệp `LICENSE` trần ở gốc (HTTP **404**), chỉ `LICENSE.md` (200) chứa nguyên văn
CC BY-SA 4.0; và `README.md` §License nói thẳng — *"GEMBA code **and data** are
released under the CC BY-SA 4.0 license"*. ⇒ ShareAlike phủ **cả mã**, không chỉ
dữ liệu/bài báo.

⇒ ⛔ **Không chép lời văn lời nhắc của GEMBA.** ⭐ Nhưng **thang mức MQM là một
đặc tả công khai** (chuẩn MQM), không phải tài sản của GEMBA — ta hiện thực đặc tả
bằng lời của mình, ghi công GEMBA-MQM là **nguồn giao thức**. Không chép mã ⇒
không phát sinh mục `THIRD_PARTY_NOTICES.md`.

## 8.2 Bảng ánh xạ: mức nào ⇒ `dat=false`

| Mức (MQM) | `dat=false`? | Vì sao |
|---|---|---|
| `nghiem_trong` (critical) | ✅ **CÓ** | cản hiểu — người xem hiểu **sai** sự việc |
| `nang` (major) | ✅ **CÓ** | phá mạch, nhưng vẫn hiểu được điều câu muốn nói |
| `nhe` (minor) | ⛔ **KHÔNG** | là lỗi thật, nhưng **không cản hiểu** |
| không lỗi nào | ⛔ KHÔNG | — |

⭐ **`nhe` được GHI LẠI, ⛔ không vứt.** Phán quyết trả về **cả danh sách lỗi kèm
mức** (`loi`) chứ không chỉ một cờ. Vứt `nhe` là dựng lại đúng bẫy *"hai trạng
thái gộp thành một giá trị"*: *"không có lỗi nào"* và *"chỉ có lỗi nhẹ"* lại rơi
chung một ô, và ta mất đúng khả năng phân biệt mà bản sửa này sinh ra để có.

## 8.3 ⭐ Lọc CƠ HỌC: lỗi không trích được đoạn ⇒ LOẠI

GEMBA-MQM và GEMBA-ESA đều bắt model **chỉ ra đoạn lỗi** (`- "involvement"`). Ta
cưỡng chế bằng máy, ⛔ không nhờ lời nhắc *"hãy chính xác"*:

```
Loại một lỗi khi: `doan` rỗng, HOẶC `doan` không xuất hiện trong câu nguồn
                  lẫn câu dịch (so khớp chuỗi, sau chuẩn hoá khoảng trắng).
```

⚠️ Phải nhận **cả hai phía**: lỗi *thêm/dịch sai* trích đoạn ở **bản dịch**, còn
lỗi *bỏ sót* trích đoạn ở **câu nguồn** — đúng như ví dụ của GEMBA
(`accuracy/omission - "the account holder"` là đoạn **nguồn**). Chỉ so với bản
dịch sẽ loại sạch lỗi bỏ sót, tức đổi thước quá tay lấy thước mù ở đúng loại
MetricX vốn mạnh.

## 8.4 ⛔ `do_tin` bị BỎ khỏi lời nhắc ngữ nghĩa, không phải chỉ bỏ ngưỡng

Giữ trường ấy không chỉ vô dụng mà **gây hại**: arXiv **2603.25052** đo được rằng
khi model **vừa lập luận vừa tự khai độ tin**, chính quá trình lập luận **phá**
hướng biểu diễn độ tin và làm lệch hiệu chỉnh **nặng thêm** — mà lời nhắc cũ đòi
đúng hai thứ đó trong một phản hồi (`ly_do` + `do_tin`). Cộng thêm arXiv
**2605.12446** (*"high certainty even when incorrect"*) và số của chính ta (98,4%
báo động giả có `do_tin ≥ 0,70`, trung vị 0,85).

⛔ **Đừng thêm lại "cho chắc".** Cổng thay thế là **mức nghiêm trọng**, đo được.

## 8.5 Hai cổng ĐẠT — giữ nguyên, cùng lúc

```
bao dong gia <= 15%  tren >= 100 cap FLORES
VA do nhay  >= 50%  MOI loai tiem (lat_nghia / sai_thuc_the)
```
⛔ Phân mức mà làm rơi độ nhạy ⇒ đổi thước quá tay lấy thước mù, **không nhận**.

## 8.6 Nền V1 trên dải GIỮ RIÊNG (để so V2 công bằng)

Đo trên dòng FLORES **200–229** (báo động giả) và **300+** (tiêm) — rời hẳn dải
phán quyết 0–99/100+, nên V2 không bị đo trên chính dải đã dùng để chỉnh.

| | báo động giả | `lat_nghia` | `sai_thuc_the` |
|---|---|---|---|
| **V1, dải giữ riêng** | **43,3%** (dải 43,3–56,7%) | **100%** (15/15) | **100%** (15/15) |
| V1, dải phán quyết | 45,0% (dải 40,0–44,4%) | 100% | 100% |

⇒ Hai dải cho cùng một câu trả lời ⇒ dải giữ riêng **đại diện được**, và mọi thay
đổi đo trên nó nói về bộ chấm chứ không về việc chọn câu.

## 8.7 Hoãn có điều kiện — ⛔ viết ra trước để sau khỏi cãi

- **MQM-APE** (hậu kiểm từng lỗi): **hoãn**, vì luật một-thay-đổi-một-lượt — làm
  cùng lúc với phân mức thì hạ được báo động giả cũng không biết nhờ cái nào.
  **Điều kiện mở lại:** phân mức một mình vẫn **> 15%** *và* phần dư **chủ yếu là
  lỗi bịa có trích đoạn**. Khi đó MetricX-24 (Apache-2.0, đã có) vào vai verifier
  thay CometKiwi (⛔ NC, ta không dùng được) — nhưng nó đang chạy **trên CPU**,
  nên mở lại là một quyết định **có giá**.
- **Đồng thuận 3/3**: **ghi số, chưa áp dụng.** 45% → 23% mà **không mất chút độ
  nhạy nào** ⇒ ⭐ khoảng **một nửa** báo động giả là model **tự mâu thuẫn giữa các
  lượt**, tức **nhiễu**, không phải lệch hệ thống. Phân mức chữa nửa **hệ thống**;
  đo xong mới biết còn phải mua gì bằng **3× chi phí** (đường sản phẩm gọi **một**
  lượt/lô).

---

# 9. KẾT QUẢ V2 và V3 — ⛔ CẢ HAI ĐỀU KHÔNG ĐẠT

Đo trên **dải giữ riêng** (báo động giả: dòng 200–229 · tiêm: dòng 300+), 3 lượt,
một lượt gọi/lô như đường sản phẩm.

| | báo động giả | `lat_nghia` | `sai_thuc_the` | lô hỏng JSON |
|---|---|---|---|---|
| **V1** nhị phân | 43,3% | 100% | 100% | 1/30 (3,3%) |
| **V2** phân mức MQM | **16,7%** ✅ | 100% ✅ | **40%** ⛔ | 0/9 |
| **V3** + sàn mức thực thể | **58,3%** ⛔ | **53%** ⛔ | **100%** ✅ | **2/9 (22%)** ⛔ |

⛔ **Không bản nào qua được CẢ HAI cổng.** Theo luật viết trước: **không nhận**.

## 9.1 V2 — hạ báo động giả 2,6 lần, rồi mù 60% lỗi thực thể

⭐ **Và đối chứng âm là thứ duy nhất bắt được điều đó.** Nếu chỉ đo báo động giả,
V2 trông như một thắng lợi sạch (43,3% → 16,7%) và ta đã phát hành một bộ chấm
**mù 60% lỗi sai thực thể** — đúng cái "đổi thước quá tay lấy thước mù".

🔑 **Soi ra nguyên nhân, và nó rất cụ thể: 9/9 ca bỏ sót là model CÓ THẤY lỗi và
CÓ gọi đúng tên `sai_thuc_the`, rồi chấm `nhe`.** Không một ca nào là không phát
hiện được. ⇒ Lỗi **xếp mức**, không phải lỗi **phát hiện** — hai thứ cần hai bản
sửa khác hẳn nhau, và gộp chúng lại sẽ dẫn tới sửa sai chỗ.

## 9.2 V3 — chữa đúng chỗ đã chẩn, nhưng vỡ hai chỗ khác

Sàn mức (*"số/tên riêng/đơn vị/ngày tháng bị đổi ⇒ ít nhất `nang`"*) **chữa đúng
thứ đã chẩn**: `sai_thuc_the` 40% → **100%**. Nhưng:

1. **Báo động giả bật lên 58,3%** — cao hơn cả V1. Lý do đọc được từ chính dữ
   liệu V1: người dịch chuyên nghiệp **thường xuyên** chỉnh thực thể một cách
   chính đáng (*"Đài Loan" → "nước này"*, *"400 người giàu nhất nước Mỹ"* →
   *"400 người Mỹ giàu nhất thế giới"*). Một sàn cứng ép **mọi** chỉnh sửa ấy
   thành `nang`. ⇒ Sàn theo **loại lỗi** là công cụ quá cùn cho việc này.
2. **`lat_nghia` tụt còn 53%** — ngoài dự đoán, và chưa giải thích được.

## 9.3 🔴 MỘT CONFOUND phải sửa TRƯỚC khi so tiếp

Tỉ lệ **lô trả JSON hỏng** (`LuocDoSai`) theo bản: V1 **3,3%** → V3 **22%**
(2/9 lô). Mỗi lô hỏng mất trọn **10 mục**. Độ phủ từng lượt của V3 chỉ còn
**19/30, 13/30, 13/30**.

⛔ **Nên con số 58,3% của V3 không phải một phép đo sạch** — nó tính trên một tập
con bị cắt không ngẫu nhiên (mất theo **lô**, không theo **mục**). Nó đủ để nói
*"V3 không tốt hơn"*, ⛔ **không** đủ để nói *"V3 tệ đúng bằng 58,3%"*.

⚠️ **Và đây đúng bài học Task 11b, áp sang lớp này:** *"cổng đang chạy
`--temp 1.0` … ghim nhiệt độ TRƯỚC, đo lại tỉ lệ qua lược đồ, RỒI mới sửa lời
nhắc"*. Đầu ra MQM dài hơn hẳn đầu ra nhị phân, nên nó làm lộ đúng điểm yếu bám
lược đồ đã biết. ⇒ **Việc tiếp theo không phải một lần chỉnh lời nhắc nữa**, mà
là làm lược đồ đứng vững (ghim nhiệt độ · lô nhỏ hơn `DOAN_MOI_LO` · hoặc nới
`NGAN_SACH_RA`), rồi **đo lại V2 và V3 trên nền sạch**.

## 9.4 Điều kiện mở lại MQM-APE — vẫn CHƯA khớp

Điều kiện đã chốt: *phân mức một mình vẫn > 15% **và** phần dư chủ yếu là **lỗi
bịa có trích đoạn***. Vế hai **không khớp**: phần dư của V2 soi tay ra phần lớn
là **lỗi THẬT của bản dịch FLORES** — ví dụ dòng 216 dịch `壁球` (squash) thành
*"quần vợt"* (tennis), dòng 215 `联合会式橄榄球` (rugby union) thành *"liên đoàn
bóng bầu dục"*. ⇒ ⛔ Chưa mở MQM-APE.

⭐ **Và điều đó lật một giả định của chính phép đo này:** *"mọi phán quyết trên
FLORES = báo động giả theo định nghĩa"* ngầm coi bản dịch FLORES là **hoàn hảo**.
Nó không hoàn hảo. ⇒ **16,7% của V2 là một CẬN TRÊN** của tỉ lệ báo động giả
thật, không phải giá trị đúng. Muốn biết sàn thật thì phải soi tay phần dư —
và nếu sàn thật đã gần 15% thì **ngưỡng 15% cần chính chủ dự án chốt lại**, chứ
không phải nới lén.

---

# 10. NỀN SẠCH — và một lỗi ĐẾM của chính phép đo

## 10.1 🔴 Con số 58,3% báo ở §9 là SAI — lỗi của phép đo, không phải của bộ chấm

`gop_trung_vi` gộp **hai** cách một mã vắng mặt vào một ô:

```
mã nằm trong một lô HỎNG        -> chưa hỏi xong        ⇒ KHÔNG đếm
mã model không nhắc tới trong
một lô CHẠY ĐƯỢC               -> không thấy lỗi nào    ⇒ ĐẠT
```

⭐ Đo 24/09 cho thấy model **chỉ liệt kê những mục nó thấy có lỗi**: lô 200–209
trả về **0/10** mã kèm `khong_dat=0`, lô 220–229 trả về **10/10**. Coi 10 mục
**sạch** đó là *"chưa trả lời"* làm mẫu số tụt 30 → 16 và tỉ lệ báo động giả
**nhảy từ 23% lên 44%** mà **không một phán quyết nào đổi**.

⛔ Và `qc_ai.doc_ngu_nghia` vốn ghi rõ mã thiếu là **ĐẠT** — phép đo phải đếm
theo **cùng hợp đồng với sản phẩm**, nếu không nó đo một hệ thống khác. Đây đúng
bẫy *"hai trạng thái gộp thành một giá trị"* của chính kho này, và tôi đi thẳng
vào nó.

Đếm lại mọi lượt đã lưu (miễn phí — dữ liệu có sẵn):

| bản | FA đã báo | **FA đúng** | lô hỏng | nền |
|---|---|---|---|---|
| V1 dải giữ riêng | 43,3% | 43,3% | 0% | sạch |
| V2 dải giữ riêng | 16,7% | 16,7% | 0% | sạch |
| V3 nhiệt độ mặc định | ~~58,3%~~ | **40,0%** | 22,2% | ⛔ bẩn |
| **V3 + `temp 0.0`** | ~~43,8%~~ | **23,3%** | **0%** | ✅ sạch |

## 10.2 Ghim nhiệt độ dọn sạch kênh — một thay đổi, hai vấn đề biến mất

| | lô hỏng JSON | độ phủ mỗi lượt |
|---|---|---|
| V3, `temp` mặc định (≈1.0) | **22,2%** (2/9) | 66,7% |
| V3, `temp = 0.0` | **0%** (0/9) | **100%** |

⇒ Cổng nền sạch (lô hỏng ≤ 3,3% **và** độ phủ ≥ 28/30): **ĐẠT**.

⭐ Và `lat_nghia` tụt 53% ở §9 là **hiện vật của kênh bẩn**, không phải của lời
nhắc — trên nền sạch nó về **100%**. ⛔ Đúng như điều phối dặn: đừng dựng giả
thuyết cho một con số đo trên kênh hỏng.

## 10.3 V3 trên nền sạch — hai vế

| | báo động giả | `lat_nghia` | `sai_thuc_the` |
|---|---|---|---|
| V1 | 43,3% | 100% | 100% |
| V2 | **16,7%** | 100% | ⛔ **40%** |
| **V3 + `temp 0.0`** | **23,3%** | ✅ **100%** | ✅ **87%** |

⇒ **Độ nhạy: ĐẠT cả hai loại, dư nhiều.** Chỉ còn cổng báo động giả:
**23,3% > 15%**.

# 11. SÀN LỖI CỦA FLORES — đo mù, và nó chưa kết luận được

## 11.1 Tra nguồn trước (luật 10)

- ⛔ **Không** có phân tích chất lượng FLORES-200 **cho tiếng Việt** đã công bố:
  tra arXiv (`FLORES-200`+`quality`, `FLORES`+`annotation errors`,
  `FLORES`+`Vietnamese`+`translation quality`) — không ra.
- ⭐ **Nhưng khiếm khuyết của FLORES được thượng nguồn THỪA NHẬN**: kho kế nhiệm
  `openlanguagedata/flores` (FLORES+) có issue **#9 *"Faulty translations of
  Persian (prs) text"*** và **#8** (bộ test các biến thể Ả Rập quá giống nhau,
  *"need flagging"*). ⇒ *"Bản dịch FLORES là chân lý"* là một **giả định**, và
  thượng nguồn không tự nhận vậy.

## 11.2 Đo mù, mẫu ngẫu nhiên, ⛔ KHÔNG soi tập bị gắn cờ

25 cặp rút ngẫu nhiên (`Random(20260924)`) từ **dòng 400–499** — dải bộ chấm
**chưa bao giờ chạy**, nên phán quyết của nó không thể ảnh hưởng.

| | số ca | tỉ lệ |
|---|---|---|
| Lỗi **rõ** (người xem tin một sự việc sai) | **1**/25 | **4%** |
| Cộng cả ca **biên** | 3/25 | 12% |

- **Rõ — dòng 469:** `黑斯廷斯勋爵` = **Lord** Hastings → *"**Vua** Hastings"*
  (King). Một lãnh chúa không phải một ông vua.
- Biên — dòng 433: `部分地区` (*một số vùng*) → *"**Rất nhiều** khu vực"*.
- Biên — dòng 456: `变焦镜头` (*ống kính zoom*) → *"ống kính **khuếch đại**"*,
  trong khi chính dòng 454 kề bên dịch đúng là *"ống kính zoom"*.

## 11.3 ⛔ Vì sao con số này CHƯA kết luận được

1. **Mẫu 25 là quá nhỏ.** 1/25 có khoảng tin 95% chừng **0,1%–20%** — nó không
   phân biệt được *"FLORES gần như sạch"* với *"FLORES lỗi 1/5"*.
2. 🔴 **Người soi là tôi, tức CÙNG LOẠI với thứ đang bị nghi.** Một LLM chấm bản
   dịch, đúng loại phán quyết mà cả tài liệu này dựng lên để nghi ngờ. ⇒ Đây là
   **ý kiến thứ hai**, ⛔ không phải chân lý nền. Ít nhất ba ca nêu trên cần
   **người** xác nhận.
3. Dải 400–499 là văn Wikipedia; dải 200–229 (nơi đo báo động giả) cũng vậy —
   nhưng đây vẫn là hai **tập câu khác nhau**, nên phép trừ chỉ là ước lượng.

## 11.4 Phép trừ, và vì sao nó chưa đủ để bấm cổng

```
bao dong gia THAT ≈ 23,3 %  −  san loi FLORES (4 % … 12 %)  =  11 % … 19 %
```

⇒ ⛔ **Vắt ngang ngưỡng 15%.** Không nói được *"đã đạt"*, cũng không nói được
*"chưa đạt"*. ⛔ Không nới ngưỡng, ⛔ và cũng không tuyên bố đạt.

**Việc cần để chốt:** một mẫu lớn hơn (≥ 100 cặp) và **người** soi — đây là chỗ
cần chủ dự án, vì nó quyết định cả ngưỡng lẫn kết luận về bản dịch.

# 12. Điều kiện mở lại MQM-APE — ĐÃ KIỂM, KHÔNG KHỚP

Điều kiện đã chốt: *phân mức một mình vẫn > 15% **và** phần dư chủ yếu là **lỗi
bịa có trích đoạn***.

- Vế một: **khớp** (23,3% > 15%).
- Vế hai: ⛔ **không khớp.** Soi tay phần dư: phần lớn là **lỗi THẬT của bản dịch
  FLORES** (`壁球` squash → *"quần vợt"*; `联合会式橄榄球` rugby union → *"liên
  đoàn bóng bầu dục"*), không phải lỗi bịa — đoạn trích đều có thật và đúng chỗ.

⇒ **MQM-APE giữ ĐÓNG.** Điều kiện không treo nữa: nó đã được kiểm và trả lời.
⭐ Và chính vế hai lật ngược cách đọc: phần dư *không* là bằng chứng bộ chấm bịa,
nó là bằng chứng **chân lý nền của ta có lỗi** — nên việc tiếp là đo sàn (§11),
⛔ không phải thêm một tầng lọc lên bộ chấm.
