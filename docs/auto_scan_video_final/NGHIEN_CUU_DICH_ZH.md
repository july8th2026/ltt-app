# NGHIEN_CUU_DICH_ZH — model dịch zh→vi (24/09/2026)

⛔ Nghiên cứu. Chưa cài, chưa đổi mã.

## 1. Bảng ứng viên

Cột *bằng chứng*: FLORES-200 **ZH⇔XX** XCOMET-XXL, arXiv **2605.22064** Table 2 (Tencent tự đo).

| Ứng viên | Loại | VRAM | GP mã | GP trọng số | Bằng chứng zh→vi | Tích hợp | Dùng? |
|---|---|---|---|---|---|---|---|
| ⭐ **`ltt-3.8` + sửa lời nhắc** | LLM tổng quát | 0 | — | Apache-2.0 (card `Qwen/Qwen3-8B`) | **chưa từng đo** | chỉ `long_tieng.py` | **ĐƯỢC** |
| ⭐ **Hy-MT2-1.8B** Q4_K_M | MT chuyên, 33 ngôn ngữ | **1.081 MiB** | Apache-2.0 | **Apache-2.0** (`LICENSE.txt` HF: nguyên văn Apache, không NC/lãnh thổ) | **84,26** | llama.cpp có `conversion/hunyuan.py`, GGUF chính thức | **ĐƯỢC** |
| Hy-MT2-7B Q4 · 30B-A3B | như trên | 4.410 MiB · ~18 GB | Apache-2.0 | Apache-2.0 | **89,45** · 89,83 — trên Qwen3.5-397B 88,50 · Gemma4-31B 88,40 · MS-Translator 82,95 · Tower-Plus-72B 79,69 | phải đuổi model khỏi card | hết chỗ |
| HY-MT1.5-7B · Hunyuan-MT-7B | MT chuyên | 4,4 GB+ | NOASSERTION | **Tencent Hunyuan Community** §1k/§5c: cấm dùng **Output** ngoài Territory (trừ EU/UK/Hàn); §4 trần 100 M MAU | 86,90 · "nhất 30/31 hạng WMT25" | — | **chủ dự án quyết** (không NC ⇒ không tự loại) |
| Seed-X-PPO-7B | MT chuyên, có `vi` | ~4,4 GB Q4 tự làm | OpenMDW-1.0 | **OpenMDW-1.0** ("without restriction", giữ notice, báo thù bằng sáng chế) | không có | tự convert | KHÔNG |
| madlad400-3b-mt · M2M-100 | seq2seq 2023/2020 | 3 · 2 GB | Apache/MIT | Apache-2.0 · MIT | không có | không ăn ngữ cảnh/độ dài | KHÔNG |
| opus-mt-zh-vi | Marian 2020 | 0,3 GB | Apache-2.0 | Apache-2.0 | **BLEU 20,0 · chrF 0,385** (Tatoeba, card HF) | rẻ nhất | KHÔNG (quá yếu) |
| NLLB-200 · TowerInstruct · SeamlessM4Tv2 | — | — | MIT/Apache | **CC-BY-NC-4.0** (card HF) | — | — | **KHÔNG — NC** |
| ALMA-R · Qwen-MT | LLM MT · API | 26 GB · — | MIT · đóng | MIT · **không phát trọng số** | ALMA **không có `vi`** | DashScope $0,5/M | KHÔNG |

⚠️ **Brief sai:** máy B có **hai** card (`ngan_sach.py:302–318`): 3090 giữ `qwen38-api` (biên **445 MiB**),
5060 Ti giữ `qwen35-api` (biên **2.888**), mà MetricX đã xin 2.435 ở đó (L_DICH §4) ⇒ chỉ 1.8B Q4 vừa.

## 2. Đặc thù zh

`l_ocr_gt_v2.json` = 33 dòng hardsub zh thật, **0 dấu câu**, tên `小美`, hashtag.
- Không dấu cách/câu ⇒ LLM và Hy-MT2 ăn trực tiếp; seq2seq mất ranh giới. Phân đoạn chỉ cần khi tra glossary: `jieba` (MIT) · `HanLP` (Apache-2.0).
- Giản/phồn ⇒ `BYVoid/OpenCC` (Apache-2.0, 10,0k★); Hy-MT2 khai `zh-Hant` riêng. **Hán sót**: regex
  `[\u4e00-\u9fff]` trên bản ra — `doc_chuyen` chưa có.
- **Tên riêng = quyết định sản phẩm, tôi không chốt:** (a) `小美`→Tiểu Mỹ; (b) →Xiao Mei. Dùng lại được:
  `ph0ngp/hanviet-pinyin-wordlist` · `chi-vi/qt_plus` (cả hai MIT). `ryanphung/chinese-hanviet-cognates`
  **không khai giấy phép** ⇒ chưa dùng.
- Glossary/thành ngữ/tên game: Hy-MT2 có lời nhắc **Terminology/Style/Delimiters** sẵn; `ltt-3.8` cũng làm
  được — hiện `loi_nhac` không truyền gì.
- WMT26 có **Sub-Task 1B zh→vi** (trần 20 B; 11/09 Jiutian-MT 35,34 BLEU/82,68 COMET) và *Video Subtitle
  Translation* (**không vi**). Không hệ nào tải về được, bảng gộp 14 sub-task ⇒ không dùng cho ta.

## 3. Phép so đề xuất (⛔ chưa chạy)

1. Nguồn zh **thật**: `bo_cap_co_nhan.json` (24) + `l_ocr_gt_v2.json` (33) + chạy lại faster-whisper
   large-v3 beam 5 VAD trên 4 clip `Desktop\TEST VIDEO` ⇒ ~400 đoạn.
2. Paired **≈300 đoạn/hệ** để bắt 1 điểm MQM (α .05, power .8). n=12/24 chỉ thăm dò.
3. **Lớp thứ hai bắt buộc** (MetricX AUC lật nghĩa zh→vi **0,61**): (a) back-translation vi→zh bằng model
   KHÁC rồi MetricX chiều vi→zh; (b) **nhãn người 60 đoạn** ở chỗ hai hệ lệch nhất. Thêm: đếm Hán sót,
   kiểm `do_dai_toi_da`.
4. Ghim trước: `dich_thuat.py:201` có `temperature=0.2`, đường lồng tiếng `giai_doan_noi_dung.py:216`
   **không truyền temperature** ⇒ mặc định máy chủ; không ghim thì bench vô nghĩa.
5. Ba nhánh: (A) lời nhắc hiện tại · (B) +glossary +tên riêng +OpenCC · (C) Hy-MT2 dịch thô rồi `ltt-3.8`
   nắn cho vừa miệng. So A↔B trước.

## 4. Hai khuyến nghị

**1. Sửa lời nhắc `ltt-3.8` trước** — không tốn VRAM, không thêm dòng THIRD_PARTY_METRICS, không thêm hàng
đợi, và **chưa có số nào** nói nó yếu zh→vi: đổi model trước khi đo là sửa thứ chưa biết có hỏng.



**2. Hy-MT2-1.8B Q4 là model duy nhất đáng thử** — Apache-2.0 **cả mã lẫn trọng số** (đã đọc nguyên văn,
khác Hunyuan-MT/HY-MT1.5), vừa chỗ trống thật, llama.cpp đã hỗ trợ, Terminology sẵn, kèm IFMTBench
(CC-BY-4.0). Bản 7B mạnh hơn rõ nhưng hết chỗ.

## 5. Điều tôi KHÔNG biết

- **Không có số zh→vi riêng cho ứng viên nào.** ZH⇔XX là trung bình 32 hướng, Tencent tự đo bằng
  XCOMET-XXL/CometKiwi — hai bộ đo `THIRD_PARTY_METRICS §2` đã loại vì NC ⇒ chỉ là thứ tự sơ bộ.
- Hy-MT2 ăn phụ đề không dấu câu / lỗi ASR / tiếng mạng đến đâu: FLORES-200 là văn Wikipedia sạch.
- Nó có giữ `do_dai_toi_da` và trả JSON theo **mã đoạn** không — issue mở #13 (bám lệnh), #12 (lỗi `[`/`]`),
  #9/#11 (vLLM chết; ta dùng llama.cpp).
- VRAM thật khi Hy-MT2 (1,1 GB) + MetricX (2,4 GB) cùng trên 5060 Ti (biên 2,9 GB) — phải đo.
- Hunyuan Community License có chặn ta không: tuỳ có khách EU/UK/Hàn — câu hỏi của chủ dự án.
- Glossary zh→vi quy mô sản phẩm: repo tìm được đều nhỏ hoặc **không khai giấy phép dữ liệu** ⇒ §18 chưa dùng.
