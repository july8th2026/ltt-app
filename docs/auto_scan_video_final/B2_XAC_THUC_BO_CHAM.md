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
