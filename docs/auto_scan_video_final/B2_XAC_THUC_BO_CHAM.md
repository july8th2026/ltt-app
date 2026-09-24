# B2 — XÁC THỰC BỘ CHẤM ngữ nghĩa (làn `xac-thuc-cham`, 24/09/2026)

> 🔴 **HAI THƯỚC ĐO BÁO ĐỘNG GIẢ TRONG TỆP NÀY — ⛔ ĐỪNG ĐẶT SỐ CỦA CHÚNG CẠNH NHAU.**
>
> | | cách **CŨ** | cách **MỚI** |
> |---|---|---|
> | giả định | „FLORES luôn đúng“ ⇒ mọi lần gắn cờ = BĐG | đối chiếu **người soi mù** |
> | sàn lỗi FLORES mang sẵn | **10–23 %** | 0 % (đã trừ) |
> | **trần hoàn hảo** | **10/12/23 %** | **0 %** |
> | cỡ mẫu | `n = 30` | `n = 100` |
> | số đã công bố | V1 **43,3** · V2 **16,7** · V3 **23,3** | V3 **33 %** · MetricX **39 %** |
>
> ⭐ **Vì sao quan trọng:** *„V3 23,3 % → 33 %“* trông như **tệ đi**, nhưng hai con số
> đó ⛔ **không cùng đơn vị** — V3 ⛔ **không hề tệ đi**, nó chỉ được đo bằng một thước
> ⛔ **không còn tặng** cho bộ chấm phần sai vốn là của **chính FLORES**. Cùng bài học
> với `N-24`: *hai con số từ hai tập khác nhau thì ⛔ không được đặt cạnh nhau.*
>
> 📌 **Nguồn của cột „cách CŨ“ là §14 ngay trong tệp này** (sàn lỗi FLORES, `n = 100`, đọc mù): §14.2 cho **10 % / 12 % / 23 %** tuỳ định nghĩa „lỗi“. ⇒ Một bộ chấm **hoàn hảo** đo bằng cách CŨ vẫn hiện **10–23 %** báo động giả, vì phần sai đó là của **chính FLORES**. (⚠️ §14 nằm ở tệp NÀY, ⛔ không phải `B2_KTC_VA_PHAN_QUYET.md` — bản đồ trỏ nhầm tệp một lần, 25/09.)
>
> ⇒ Mỗi bảng dưới đây mang **nhãn đơn vị** ngay trên nó. ⛔ Thêm bảng mới mà không dán
> nhãn là tái lập đúng cái bẫy này.


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


> 📏 **ĐƠN VỊ: CÁCH ĐO CŨ** — giả định *„FLORES luôn đúng“* ⇒ **MỌI** lần gắn cờ bị tính là báo động giả. ⚠️ Thước này mang sẵn **sàn lỗi FLORES 10–23 %**, nên **trần hoàn hảo** của nó là **10/12/23 %**, ⛔ không phải 0 %. `n = 30`. ⛔ **Không so ngang** với bảng „CÁCH ĐO MỚI“ bên dưới.

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


> 📏 **ĐƠN VỊ: CÁCH ĐO CŨ** — giả định *„FLORES luôn đúng“* ⇒ **MỌI** lần gắn cờ bị tính là báo động giả. ⚠️ Thước này mang sẵn **sàn lỗi FLORES 10–23 %**, nên **trần hoàn hảo** của nó là **10/12/23 %**, ⛔ không phải 0 %. `n = 30`. ⛔ **Không so ngang** với bảng „CÁCH ĐO MỚI“ bên dưới.

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


> 📏 **ĐƠN VỊ: CÁCH ĐO CŨ** — giả định *„FLORES luôn đúng“* ⇒ **MỌI** lần gắn cờ bị tính là báo động giả. ⚠️ Thước này mang sẵn **sàn lỗi FLORES 10–23 %**, nên **trần hoàn hảo** của nó là **10/12/23 %**, ⛔ không phải 0 %. `n = 30`. ⛔ **Không so ngang** với bảng „CÁCH ĐO MỚI“ bên dưới.

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

---

# 13. VIỆC A — cả ba bản trên CÙNG một nền sạch

Lời nhắc V1/V2 được **đóng băng** trong `tools/` (chép nguyên văn từ git: V1 =
trước `91d921f4`, V2 = `91d921f4`), gọi qua `--ban {v1,v2,v3}`. ⛔ Ba bản chạy
**cùng một nhiệt độ ghim** — đo ở hai nhiệt độ là so hai *hệ thống*, không phải
so hai *lời nhắc*.

| bản (`temp 0.0`) | báo động giả | `lat_nghia` | `sai_thuc_the` | lô hỏng |
|---|---|---|---|---|
| **V1** nhị phân | 43,3% | 100% | 100% | 0% |
| **V2** phân mức | **16,7%** | 100% | ⛔ **33%** | 0% |
| **V3** + sàn thực thể | 23,3% | ✅ 100% | ✅ **87%** | 0% |

⚠️ V2 trên nền sạch còn **tệ hơn** con số đo trên nền bẩn (33% so với 40%) ⇒ chỗ
mù thực thể của nó là **thật**, không phải nhiễu kênh. ⛔ V2 loại dứt khoát.

⭐ **V1 không hề bị nhiễu kênh:** 43,3% ở nhiệt độ mặc định và 43,3% khi ghim —
y hệt, độ nhạy 100/100 cả hai. ⇒ Nền bẩn **chỉ** đánh vào đầu ra MQM dài, và
mốc V1 ta so suốt từ đầu là mốc **sạch**. (⛔ Không có phép đo này thì ta không
biết điều đó — đúng lý do điều phối đòi đo lại cả V1.)

⇒ **V3 + `temp 0.0` là ứng viên dẫn đầu**: đổi **+6,6 điểm** báo động giả lấy
**+47 điểm** độ nhạy thực thể.

# 14. VIỆC B — SÀN LỖI FLORES, n = 100, đọc mù

Sổ đầy đủ: `bang_chung/b2_san_loi_flores.json` (chỉ số dòng · phán quyết ·
**đoạn trích nguồn** · lý do).

## 14.1 Giao thức

- **Mù**: bộ chấm **chưa bao giờ chạy** trên dải 500–899. Người đọc không thấy
  phán quyết nào.
- **Mẫu**: 50 dòng (500–699, seed 20260924) + 50 dòng (700–899, seed 20260925).
- ⛔ **Ca không trích được đoạn nguồn ⇒ KHÔNG tính là lỗi.**
- **Người đọc 2**: mẫu con 30 dòng đã rút sẵn trong sổ
  (`mau_con_cho_nguoi_doc_2`), ⛔ **không kèm phán quyết** — để điều phối đọc
  độc lập rồi lấy **tỉ lệ bất đồng**.

## 14.2 Kết quả

| | số ca | tỉ lệ |
|---|---|---|
| Lỗi **rõ** (người xem tin một sự việc sai) | **10**/100 | **10%** |
| Cộng cặp **bản ZH mới là phía lệch** | 12/100 | 12% |
| Cộng cả ca **biên** | 23/100 | 23% |
| Không lỗi | 77/100 | 77% |

Ví dụ lỗi rõ: `营养补品` (*thực phẩm bổ sung*) → *"tập luyện bổ sung"* · `珍稀动物`
(*thú quý hiếm*) → *"thú ngoại nhập"* · `山寨货` (*hàng nhái*) → *"bị ngừng kinh
doanh"* · `溪降` (*canyoning*) → *"chèo thuyền vượt thác"* · `离出发日期应至少有
6 个月` (hiệu lực 6 tháng **từ** ngày đi) → *"6 tháng **trước** chuyến đi"*.

## 14.3 🔴 Giới hạn — ngay cạnh con số, ⛔ không giấu ở cuối

1. 🔴 **Người đọc 1 là một LLM — cùng họ với thứ đang bị nghi.** Đây là **ý kiến
   thứ hai**, ⛔ không phải chân lý nền. Đó chính là lý do phải có người đọc 2.
2. **n = 100, KTC 95% của 10/100 ≈ 5,5% – 17,4%** — vẫn rộng.
3. Dải đo sàn (500–899) **khác** dải đo báo động giả (200–229) ⇒ phép trừ là
   **ước lượng**, không phải phép tính trên cùng tập.

## 14.4 Phép trừ — và nó ĐỔI CHIỀU so với ước lượng cũ

```
V3:  bao dong gia do duoc  23,3 %
     san loi FLORES         10 %  (KTC 5,5 – 17,4 %)
  => bao dong gia THAT   ~ 13,3 %   (thay vi 11–19 % uoc tu mau n=25)
```

> 🔴 **CON SỐ 13,3 % Ở TRÊN ĐÃ BỊ THAY — ⛔ đừng trích nó làm số hiện hành.**
>
> Nó là một **phép trừ giữa hai ước lượng đo trên hai tập khác nhau** (báo động giả `n = 30`, dải 200–229 ↔ sàn `n = 100`, dải 500–899), và chính §14.3 giới hạn 3 đã nói trước điều đó. Khi đo **thẳng** trên `n = 100` đã soi mù (§17.1): gắn cờ **43**, lỗi thật **10**, bắt trúng **10** ⇒ **báo động giả THẬT = 33/100 = 33 %**.
>
> ⭐ Chỗ sai ⛔ **không** phải giả định *„bắt hết lỗi sẵn có“* — giả định đó hoá ra **đúng** (10/10). Chỗ sai là **số bị trừ**: `23,3 %` đo trên `n = 30` ở một vùng khác, còn `n = 100` cho **43 %**. ⇒ **Hai con số từ hai tập khác nhau thì ⛔ không được đặt cạnh nhau** — cùng bài học với `N-24`.
>
> ⇒ Số hiện hành của V3 là **33 %** (cách MỚI, trần hoàn hảo 0 %), và nó **TRƯỢT** cổng 15 %. ⛔ Không nới ngưỡng.

```
```

⭐ Mẫu 25 ban đầu cho sàn **4%**; mẫu 100 cho **10%**. ⇒ ⛔ **Ước lượng cũ quá
thấp**, và nó kéo kết luận sai hướng. Đây đúng lý do điều phối bắt nâng cỡ mẫu
**trước** khi mang câu hỏi đi.

⚠️ **Nhưng vẫn CHƯA tuyên bố đạt.** 13,3% nằm dưới 15%, nhưng cả hai số đều có
khoảng tin rộng (báo động giả đo trên n=30; sàn trên n=100), và người đọc 2 chưa
đọc. ⛔ Không bấm cổng bằng một hiệu số của hai ước lượng rộng.

**Cần để chốt:** (a) điều phối đọc mẫu con 30 dòng ⇒ **tỉ lệ bất đồng**;
(b) đo lại báo động giả V3 trên **≥ 100 cặp** thay vì 30.

# 15. MQM-APE — vì sao vế hai LẬT, và nó dạy điều gì

Điều kiện mở lại: *phần dư chủ yếu là **lỗi bịa có trích đoạn***. Kiểm: ⛔ **không
khớp**.

🔑 **Và phần đáng giữ không phải "không khớp" mà là CÁCH nó lật.** Cùng một tập
"phần dư", hai cách đọc ngược nhau:

```
doc A: "bo cham bia loi"        -> sua BO CHAM   (them mot tang loc: MQM-APE)
doc B: "chan ly nen co loi"     -> sua PHEP DO   (do san FLORES)
```

Soi tay cho đọc **B**: đoạn trích đều **có thật và đúng chỗ**, và thứ sai là bản
dịch FLORES. ⇒ Lần sau gặp chữ *"phần dư"*, câu hỏi đầu tiên là **"phần dư của
ai?"** — của bộ chấm, hay của chân lý nền.

⇒ **MQM-APE: ĐÓNG.** Điều kiện đã được kiểm và trả lời, ⛔ không treo.

# 16. ⭐ Một nước đi đáng ghi lại

**Trước khi giải thích một con số lạ, hỏi kênh đo có sạch không.**

`lat_nghia` tụt 53% ở V3 trông như một khiếm khuyết của lời nhắc và mời gọi cả
một giả thuyết. Điều phối dặn ⛔ đừng dựng giả thuyết; ghim nhiệt độ xong nó về
**100%** — nó **chưa bao giờ tồn tại**. Một giờ lý luận về nguyên nhân của một
hiện vật đo đạc là một giờ mất trắng, và tệ hơn: nó có thể sinh ra một bản vá
cho một vấn đề không có thật.

---

# 17. ⭐ ĐỐI CHIẾU THẲNG — bỏ phép trừ. Và cổng báo động giả **TRƯỢT RÕ**

Chạy **V3 + `temp 0.0`, 3 lượt** trên **đúng 100 dòng đã soi mù** (`--theo-so`),
rồi đối chiếu **thẳng** với phán quyết người soi — ⛔ không trừ, không giả định.

⭐ Phép này hợp lệ đúng ở chỗ trước đây bị cấm: phán quyết người soi ghi **trước**,
**mù**, và **đã commit** (`c9dfc01d` và trước đó) — ⛔ không ai chỉnh được sau khi
thấy bộ chấm nói gì.

**Nền: SẠCH.** 5/5 phần có **0 %** lô hỏng JSON, độ phủ **100 %** mọi lượt.
Tỉ lệ gắn cờ thô từng phần: 40 · 40 · 30 · 60 · 45 % ⇒ **43/100**.

## 17.1 Bảng 2×2 (n = 100, người đọc 1)


> 📏 **ĐƠN VỊ: CÁCH ĐO MỚI** — đối chiếu **người soi mù** (phán quyết ghi trước, commit trước) ⇒ chỉ lần gắn cờ **sai thật** mới tính. **Trần hoàn hảo = 0 %**. `n = 100`. ⛔ **Không so ngang** với bảng „CÁCH ĐO CŨ“ bên trên.

| coi là lỗi | gắn cờ | lỗi thật | bắt trúng | **BÁO ĐỘNG GIẢ THẬT** | **bỏ sót** |
|---|---|---|---|---|---|
| `chinh` (chỉ lỗi **rõ**) | 43 | 10 | 10 | **33/100 = 33 %** | **0** |
| `rong` (+ `zh_lech`) | 43 | 12 | 12 | 31/100 = 31 % | 0 |
| `rong_nhat` (+ **biên**) | 43 | 23 | 22 | 21/100 = 21 % | 1 |

```
BAO DONG GIA THAT   = 33/100  (33 %)   ⛔ > 15 %  — TRUOT, ca ba dinh nghia
DO NHAY TREN LOI TU NHIEN = 10/10 = 100 %  ✅  <- con so ta CHUA BAO GIO co
```

## 17.2 🔴 Phép trừ sai — nhưng **KHÔNG** sai ở chỗ ta ngờ

Giả định ngầm của phép trừ (*bộ chấm bắt được mọi lỗi sẵn có của FLORES*) hoá ra
**đúng**: độ nhạy trên lỗi **tự nhiên** đo được là **10/10 = 100 %**, không một
lỗi rõ nào bị bỏ sót. Chỗ sai nằm ở **số bị trừ**: `23,3 %` đo trên **n = 30**
dòng 200–229, còn trên **n = 100** tỉ lệ gắn cờ thô là **43 %**.

```
uoc cu :  23,3 % − 10 %  = 13,3 %   -> "gan dat"
do thang:            33 %           -> TRUOT gap doi nguong
```

⇒ ⛔ **Bộ chấm V3 KHÔNG qua cổng.** Vế độ nhạy đạt dư (100 % tự nhiên, 100 %
`lat_nghia` / 87 % `sai_thuc_the` trên lỗi tiêm), vế báo động giả trượt.

## 17.3 Lát cắt có đối chứng kép (n = 30) — ⛔ không dùng làm tập chính

| người đọc | gắn cờ | lỗi rõ | bắt trúng | báo động giả thật | bỏ sót |
|---|---|---|---|---|---|
| người 1 | 13 | 3 | 3 | 10/30 | 0 |
| **người 2** (điều phối) | 13 | 5 | 5 | 8/30 | 0 |

⭐ **Hai người đọc, cùng một kết luận về ĐỘ NHẠY: 100 %.** Bất đồng vẫn **một
chiều** — người 2 gọi là lỗi những dòng người 1 gọi là biên (vd. 514 `更加重要`),
nên sàn thật có thể cao hơn 10 %, và phần dư 33 % có thể thấp hơn. ⛔ Nhưng n=30
quá nhỏ để chốt, và cả hai người đọc đều là LLM (§14.3 giới hạn 1).

## 17.4 Phần dư thuộc lớp nào — ⛔ chẩn, chưa vá

33 báo động giả thật, phân theo **loại của lỗi quyết định** (mức ≥ `nang`):

| lớp | số ca | | phán quyết người soi cho chính dòng đó |
|---|---|---|---|
| `lat_nghia` | **14** | | "không lỗi" hẳn: **21** |
| `sai_thuc_the` | **11** | | "biên": **10** |
| `bo_sot` | 5 | | `zh_lech`: **2** |
| `them` | 2 | | |
| `khac` | 1 | | mức: `nang` 25 · `nghiem_trong` 8 |

⇒ Phần dư **không** tụ vào một lớp. Nó là **sắc thái/phạm vi nghĩa** bị xếp
`nang`: `推广` → *khuyến mãi*, `街区` → *các con phố*, `国家展馆` → *gian hàng*,
`该设想` → *lời khuyên này*. Đúng hình dạng **`minor` của MQM** mà V2 từng xếp
đúng — và V2 đổi lấy chỗ mù 67 % ở `sai_thuc_the`. ⛔ Không vá lời nhắc ở đây:
sàn mức thực thể của V3 và chỗ mù của V2 là **một cặp đánh đổi**, cần điều phối
chốt hướng.

## 17.5 Tái lập

```
python tools\bench_b2_xac_thuc_bo_cham.py do --pha fa --luot 3 --ban v3 ^
    --theo-so <phan 20 dong cua b2_san_loi_flores.json> --ra fa_k.json
python tools\bench_b2_xac_thuc_bo_cham.py gop --fa fa_0..fa_4.json --ra cham100.json
python tools\bench_b2_xac_thuc_bo_cham.py doi-chieu ^
    --so-soi bang_chung\b2_san_loi_flores.json --cham cham100.json ^
    --con <mau_con_cho_nguoi_doc_2> --ra bang_chung\b2_doi_chieu_v3_voi_soi_mu.json
```

Bằng chứng: `bang_chung/b2_doi_chieu_v3_voi_soi_mu.json` (bảng 2×2 cả ba định
nghĩa, cả hai người đọc) · `bang_chung/b2_cham_v3_tren_100_dong_soi_mu.json`
(bản ghi **sạch**, ⛔ không một chữ FLORES).

⚠️ `gop_phan` trước đó ghép theo `tu`/`n` — sai với dải **rời rạc** của
`--theo-so` (sinh ra mã của dòng chưa hề hỏi rồi đếm là "thiếu"). Đã vá + chốt
bằng `test_gop_phan_ghep_dung_DONG_ROI_RAC_cua_phan_theo_so`.

---

# 18. ⭐ TA ĐÃ VỨT BƯỚC CHẤM ĐIỂM — và có TỒN TẠI điểm vận hành đạt cả hai cổng

## 18.1 Tra nguồn: giao thức gốc cho ra một **ĐIỂM**, ta cho ra một **CỜ**

`MicrosoftTranslator/GEMBA`, `gemba/gemba_mqm_utils.py::parse_mqm_answer`
(sha `a7a7eff`), đọc thẳng:

```python
final_score += 25 if error_level == 'critical' else 5 if error_level == 'major' else 1
...
if error_counter < 5 and not list_mqm_errors:   # chi dem 5 LOI DAU
...
if final_score > 25: final_score = 25           # tran 25
return -final_score                             # mot DIEM, khong phai mot co
```

⇒ ⭐ **Bước ta thiếu có tên:** biến danh sách lỗi thành **điểm** rồi mới ngưỡng
trên **tổng**. `qc_ai` phán `dat=false` ngay khi có **≥ 1 lỗi `nang`** — một cờ
**nhị phân trên mức cao nhất**. Ở giao thức gốc, **một** lỗi bị xếp quá tay ⛔
**không** lật nổi phán quyết (5 điểm trên trần 25); ở ta thì lật.

⚠️ Và chính xác đó là hình dạng phần dư ở §17.4: `nang` 25/33 ca, lớp rải đều.
⛔ Không có ngưỡng "đạt/không đạt" nào trong kho GEMBA — điểm ở đó dùng để **tương
quan/xếp hạng**. Ngưỡng là việc của ta, nên nó phải được **đo**, không phải chọn.

## 18.2 Đường cong — tính lại **offline**, ⛔ không gọi model lần nào

Dữ liệu đã lưu (mức từng lỗi, từng dòng, từng lượt). Trung vị trên 3 lượt, mẫu số
là **100 dòng** (cùng định nghĩa với cổng 15 %), định nghĩa lỗi `chinh`:

| luật gắn cờ | gắn cờ | **BĐG thật** | **độ nhạy tự nhiên** | hai cổng |
|---|---|---|---|---|
| `dem ≥ 1` nang — **V3 hiện hành** | 43 | **33 %** | 100 % | ⛔ |
| `diem ≥ 2…5` | 43 | 33 % | 100 % | ⛔ |
| **`diem ≥ 6`** | 20 | **12 %** | **80 %** | ✅ |
| **`diem ≥ 7…10`** | 17 | **10 %** | **70 %** | ✅ |
| **`diem ≥ 11…25`** | 14 | **7 %** | **70 %** | ✅ |
| `dem ≥ 2` nang | 8 | 5 % | 30 % | ⛔ mù |
| `dem ≥ 3` nang | 1 | 0 % | 10 % | ⛔ mù |

## 18.3 ~~Trả lời câu CÓ/KHÔNG: **CÓ**~~ — 🔴 **ĐÃ BỊ LẬT ở §20**

> 🔴 **Mục này đo SAI vế hai.** "Độ nhạy" dưới đây là trên lỗi **TỰ NHIÊN** của
> FLORES; cổng đòi **≥ 50 % MỖI LOẠI TIÊM**. Đo đúng vế hai (§20) cho ra
> **KHÔNG có một điểm nào**. ⛔ Giữ nguyên văn để thấy sai ở đâu, ⛔ không đọc
> nó như một kết luận.

**Tồn tại** điểm vận hành thoả **cả hai** cổng — và không phải một điểm lẻ mà
**cả một dải** (`diem ≥ 6` … `≥ 25`). ⇒ ⛔ Khuyết tật **không** nằm ở lời nhắc
hay ở model: nằm ở **luật quyết định**. Cùng đầu ra thô, cùng model, cùng lời
nhắc — đổi cách đọc là qua cổng.

⚠️ **Giá phải trả, nói thẳng:** `diem ≥ 6` đổi **20 điểm** độ nhạy (100 % → 80 %)
lấy **21 điểm** báo động giả (33 % → 12 %). Và `diem ≥ 25` ≈ *"chỉ đếm khi có
`nghiem_trong`, hoặc 5 lỗi `nang`"* — gần như **bỏ hẳn** mức `nang` đơn lẻ.

## 18.4 Chống chỉnh-trên-bài-thi — chọn một nửa, báo nửa kia

Chia **xen kẽ** theo vị trí trong danh sách đã sắp (⛔ không chia 500–699/700–899:
10 lỗi rõ nằm 3/7 giữa hai dải đó). Luật chọn viết trước: *trong các điểm có độ
nhạy ≥ 50 %, lấy điểm báo động giả thấp nhất*.

| | ngưỡng chọn được | **báo trên nửa KIA** | |
|---|---|---|---|
| chọn trên A → báo B | `diem ≥ 25` | **BĐG 6 %** (3/50) · **độ nhạy 60 %** (3/5) | ✅ hai cổng |
| chọn trên B → báo A | `diem ≥ 25` | **BĐG 8 %** (4/50) · **độ nhạy 80 %** (4/5) | ✅ hai cổng |

⚠️ **Mỏng, khai ngay cạnh số: mỗi nửa chỉ có 5 lỗi thật.** Một lỗi đổi bên là
20 điểm độ nhạy. ⇒ Kết luận *"có điểm vận hành"* là **vững** (cả một dải, hai
chiều chia đều đạt); con số **chính xác** của độ nhạy thì ⛔ **chưa**.

Bằng chứng: `bang_chung/b2_quet_nguong_v3.json` (cả đường cong + mức từng dòng
từng lượt, ⛔ không một chữ FLORES) · `tools/…::quet_nguong`, `diem_mqm`.
Tái lập: `python tools\bench_b2_xac_thuc_bo_cham.py quet --cham <tho> --so-soi
bang_chung\b2_san_loi_flores.json --ra <ra>`.

---

# 19. BÀN GIAO cho cuộc đấu MetricX — và DỪNG nhánh lời nhắc tự nặn

⭐ **Chủ dự án chốt (24/09 khuya):** *"nghiên cứu từ cộng đồng GitHub để giải bài
toán thay vì tự suy luận; ⛔ không xây hệ thống khi có thể lấy từ cộng đồng"* —
luật này nay áp cho **cả lời giải**, không chỉ cho bộ đo.

⇒ ⛔ **DỪNG** nhánh V1→V2→V3: không V4, không sửa lời nhắc, không biến thể.
`MetricX-24-Hybrid` (Apache-2.0, đã khai ở `THIRD_PARTY_METRICS.md`, chạy trong
`qc-venv`) là **model được huấn luyện để chấm chất lượng dịch** — nó phải được
thử **trước** một lời nhắc ta tự nghĩ ra, không phải sau.

⭐ **Công sức V1→V3 ⛔ không phí:** nó để lại **chân lý nền đã soi mù** (100 dòng,
hai người đọc) và **cách tính** mà cuộc đấu dựa vào. ⚠️ Nhưng nó đáng lẽ là bước
**HAI**, ⛔ không phải bước **MỘT**.

## 19.1 Ba thứ bàn giao

**(1) Đường cong ngưỡng của V3** — ⛔ để so **công bằng**, đừng so V3-ở-điểm-tồi
với MetricX-ở-điểm-tốt-nhất. KTC Wilson, `scipy`:

| luật gắn cờ | **BĐG** (trên 100 dòng) | **độ nhạy tự nhiên** |
|---|---|---|
| `dem ≥ 1` nang — **điểm V3 đang chạy** | 33,0 % [24,6 ; 42,7] | 100 % [72,2 ; 100] |
| `diem ≥ 6` | **12,0 %** [7,0 ; 19,8] | **80 %** [49,0 ; 94,3] |
| `diem ≥ 7…10` | 10,0 % [5,5 ; 17,4] | 70 % [39,7 ; 89,2] |
| `diem ≥ 11…25` | 7,0 % [3,4 ; 13,7] | 70 % [39,7 ; 89,2] |

🔴 **ĐÃ BỊ LẬT — đọc §20.** Cột "độ nhạy" trên là trên lỗi **tự nhiên**, ⛔ không
phải vế hai của cổng. Đo đúng vế hai: **KHÔNG tồn tại điểm nào** thoả cả hai.

**(2) Bằng chứng đã commit** (đường dẫn chính xác, gốc `docs/auto_scan_video_final/`):

| tệp | có gì |
|---|---|
| `bang_chung/b2_san_loi_flores.json` | **chân lý nền** — 100 dòng, người đọc 1, mù, commit TRƯỚC |
| `bang_chung/b2_san_loi_flores_nguoi_doc_2.json` | mẫu con 30 dòng, người đọc 2 |
| `bang_chung/b2_cham_v3_tren_100_dong_soi_mu.json` | phán quyết V3 từng dòng (sổ `gop`) |
| `bang_chung/b2_doi_chieu_v3_voi_soi_mu.json` | bảng 2×2 · ba định nghĩa lỗi · cả hai người đọc |
| `bang_chung/b2_quet_nguong_v3.json` | đường cong + **mức từng lỗi từng dòng từng lượt** |

**(3) ⛔ CÙNG một cách đếm** — `tools/do_luong.py` trên `main`:

```
dl.nhan_nguoi_doc(<b2_san_loi_flores.json>)   -> {dong: phan_quyet}
dl.co_gan_co(<ban ghi bo cham>)               -> {dong: bi_gan_co | None}
   # None = CHUA HOI XONG (so_luot == 0) ⇒ ⛔ bo khoi ca hai vector
that = 1 neu phan_quyet == "ro"     # dinh nghia `chinh`
dl.ma_tran_va_diem(that, du_doan)             -> tn/fp/fn/tp
dl.ti_le_kem_ktc(k, n)                        -> ti le + KTC Wilson
```

Chạy lại trên bằng chứng đã commit cho **đúng** bảng của §17:
`tn 57 · fp 33 · fn 0 · tp 10`.

🔴 **MỘT chỗ dễ làm cuộc đấu vô nghĩa, đọc kỹ:** `ma_tran_va_diem` trả
`bao_dong_gia_tren_gan_co` = **FP/số gắn cờ** = **76,7 %**. ⛔ Đó **KHÔNG** phải
con số của cổng. Cổng 15 % nói *"tỉ lệ báo động giả trên ≥ 100 cặp"* ⇒ mẫu số là
**tổng số cặp** ⇒ `ti_le_kem_ktc(fp, n)` = **33,0 %**. Hai số cùng tên, khác mẫu
số, lệch **43 điểm**. ⛔ Hai bên phải khai mẫu số trước khi so.

## 19.2 ⚠️ Mốc giờ — lượt nào còn đứng sau sự cố 23:37–23:44 (24/09)

Production sập ~15 phút do một phiên khác deploy. Đã soát **cửa sổ giờ** của mọi
lượt gọi máy B của làn này:

| lượt | cửa sổ (giờ máy, UTC+7) | |
|---|---|---|
| **V3, 100 dòng** (§17, §18) | **22:11 → 22:59** | ✅ trước sự cố — **mọi số vẫn đứng** |
| quét ngưỡng (§18) | 23:07 | ✅ **offline**, ⛔ không gọi model một lần nào |
| V2, phần 3 và 4 | 23:31→23:38 · 23:38→23:46 | 🔴 **VẮT QUA ⇒ đã VỨT**, ⛔ không cứu |

⇒ ⛔ **Không một con số nào của §17/§18 bị ảnh hưởng.** V2 trên 100 dòng **không
được phân tích và không được báo** (làn dừng theo lệnh điều phối); dữ liệu thô
nằm ngoài kho, ⛔ chưa có kết luận nào rút ra từ nó.

⭐ Và bộ đo nay **ghi mốc giờ UTC** của từng phần (`cua_so_utc`,
`cua_so_utc_cac_phan`) — vì một lượt vắt qua sự cố cho **mẫu số thiếu** mà ⛔
**không báo lỗi**: nó chỉ ra một tỉ lệ **khác**, ⛔ không phân biệt được từ bên
ngoài. Chốt bằng `test_ban_ghi_GHI_CUA_SO_UTC_de_kiem_lai_su_co`.

---

# 20. 🔴 VẾ HAI CỦA CỔNG — đo rồi: **KHÔNG có một điểm vận hành nào**

⚠️ §18–19 báo *"CÓ"* dựa trên độ nhạy trên lỗi **TỰ NHIÊN** (80 %). Cổng viết
trước đòi **≥ 50 % MỖI LOẠI TIÊM**. Đó là **hai con số khác nhau**, và đây là
con số đúng của cổng.

Chạy lại đối chứng âm: V3 · `temp 0.0` · 3 lượt · 15 cặp mỗi loại · dòng FLORES
≥ 300 · nền sạch (**0** lô hỏng) · cửa sổ UTC `17:09→17:21` (⛔ ngoài sự cố
23:37–23:44 giờ máy).

| luật gắn cờ | BĐG | `lat_nghia` | **`sai_thuc_the`** | cổng |
|---|---|---|---|---|
| `dem ≥ 1` nang — **V3 đang chạy** | 33,0 % | 100 % | **86,7 %** [62,1;96,3] | ⛔ vế 1 |
| `diem ≥ 2…5` | 33,0 % | 100 % | 86,7 % | ⛔ vế 1 |
| **`diem ≥ 6…10`** | **10–12 %** ✅ | 100 % ✅ | ⛔ **46,7 %** [24,8;69,9] | ⛔ vế 2 |
| `diem ≥ 11…15` | 7,0 % ✅ | 100 % ✅ | ⛔ 26,7 % | ⛔ vế 2 |
| `diem ≥ 16…25` | 7,0 % ✅ | 100 % ✅ | ⛔ 20,0 % | ⛔ vế 2 |
| `dem ≥ 2` nang | 5,0 % ✅ | ⛔ 20,0 % | ⛔ 26,7 % | ⛔ vế 2 |

## 20.1 ⭐ Câu trả lời: **KHÔNG** — và nó là một kết quả QUYẾT ĐỊNH

⛔ **Không một điểm nào trong 30 luật quét được thoả cả hai vế.** Và cơ chế đọc
thẳng ra từ bảng: **đúng một bậc** — `diem ≥ 5` → `≥ 6` — báo động giả rơi
**33 % → 12 %** trong khi `sai_thuc_the` rơi **86,7 % → 46,7 %**. ⭐ Cùng một
bậc thang mua cả hai: **cái giá của báo động giả CHÍNH LÀ chỗ mù thực thể.**

🔑 Vì sao, và nó khớp đúng chẩn đoán của điều phối: `diem ≥ 6` đòi **hai** lỗi
`nang` (5+5) hoặc một `nghiem_trong`. Một lỗi **sai thực thể đơn lẻ** bị model
chấm `nhe` (1 điểm) ⇒ ⛔ **không kích nổi cổng**. ⇒ Dải ngưỡng này **dựng lại
đúng chỗ mù đã giết V2** (V2: `sai_thuc_the` 33 %), chỉ bằng một đường khác.

⇒ ⭐ **Bằng chứng: thiết kế "lời nhắc tự nặn + một ngưỡng" này ⛔ KHÔNG đạt được
cổng** — không phải ở một điểm, mà trên **toàn bộ** không gian ngưỡng đã quét.
⛔ Đây không phải thất bại cần vá; nó là câu trả lời, và nó **đóng** nhánh V1→V3.

⚠️ **Khai thẳng cỡ mẫu:** 15 cặp mỗi loại ⇒ KTC rất rộng (46,7 % là [24,8;69,9],
tức chưa loại trừ được 50 % về mặt thống kê ở **một** điểm). ⛔ Nhưng kết luận
"không có điểm nào" không dựa vào một điểm: nó dựa vào **cả hình dạng** — mọi
ngưỡng hạ được BĐG xuống dưới 15 % đều kéo `sai_thuc_the` xuống ≤ 46,7 %.

## 20.2 Bổ sung cho bàn giao (§19)

`bang_chung/b2_quet_nguong_v3.json` nay có **`duong_cong_tiem`** — độ nhạy trên
lỗi tiêm **theo từng loại** ở mọi ngưỡng; `bang_chung/b2_tiem_v3_nen_sach.json`
là bản ghi sạch của lượt tiêm. ⇒ Cuộc đấu MetricX phải so **cả hai vế**:
⛔ một đường cong BĐG–độ-nhạy-tự-nhiên **không đủ** để tuyên bố ai thắng.
