# Ngân sách thời gian cho voice tiếng Việt — thiết kế

> Chủ dự án duyệt 25/09/2026. Đường **architectural** của `superpowers:brainstorming`.
> Plan triển khai viết sau, ⛔ chưa chạm mã khi spec này chưa được duyệt.

## 1. Vấn đề

Hệ có **hai** định nghĩa "khe thời gian của một đoạn", và cái **quyết định tiêu
tiền LLM** dùng cái chặt hơn:

```
nan_cho_vua.khe_cua:136        ket - bat              chi phan DANG NOI
thoi_gian.ngan_sach_doan:82    moc[i+1] - moc[i]      TOI LUC DOAN SAU BAT DAU
                                                       (muon 70% khoang lang)
```

⇒ Bậc thang sửa chữa phán *"⛔ không vừa"* cho những đoạn **vốn đã vừa** nếu tính cả
khoảng lặng phía sau. Mỗi phán quyết sai là **một lượt gọi LLM**.

**Đo được trên worker production 25/09, phim 275 s:**
```
voice_synthesis  1.610,6 s tuong  ·  24,9 s CPU   <- 27 phut, may gan nhu RANH
49 luot goi may B trong 22,5 phut                  <- ~27 s/luot, NOI TIEP
```
`24,9 s` CPU trên `1.610 s` tường ⇒ nó **⛔ không tính, nó CHỜ**.

### 1b. Vì sao khe chặt từng ĐÚNG, và vì sao nay ⛔ không còn đúng

Docstring `khe_cua` nêu hai lý do:
1. giữ hai pha độc lập (pha lập kế hoạch chạy **sau**);
2. *"khe gốc cũng là thứ khán giả thấy: **câu thoại phải khớp với cái miệng đang
   nhép** trên màn hình"*.

🔴 **Lý do 2 là lý lẽ của LỒNG TIẾNG KHỚP MÔI.** Hợp đồng sản phẩm chốt **22/09** là
**một giọng THUYẾT MINH** (`ban_ghi.py:47`, `cao_do.py:58`). ⇒ Lý do ấy **chết trước
khi** khuyết tật này bị phát hiện — một câu giải thích sống lâu hơn điều kiện sinh
ra nó.

⭐ Lý do 1 cũng tan: kiến trúc **hai giai đoạn** (chốt 25/09) bỏ cắt cảnh khỏi Giai
đoạn 1 ⇒ trục nguồn **bằng** trục bản ra ⇒ `ngan_sach_doan` ⛔ không cần lớp đổi mốc.

## 2. Quyết định

### 2a. Biên tràn — ✅ chủ dự án chốt

> **Tới lúc đoạn sau bắt đầu, chừa 30 %** — đúng công thức bộ lập kế hoạch
> (`TY_LE_MUON_KHOANG_LANG = 0.7`).

Phần 30 % chừa lại để bản lồng tiếng còn nhịp nghỉ, **và** để một dao động nhỏ của
máy sinh tiếng ⛔ không tràn sang câu sau.

### 2b. Cách nối — ✅ chủ dự án chốt: **phương án B**

`nan_cho_vua` gọi **chính** `thoi_gian.ngan_sach_doan`. **Một phép tính, hai người
gọi.** ⛔ Không dựng mô-đun thứ ba cho một hàm bốn dòng; ⛔ không để người gọi "nhớ
truyền đúng" (thứ hỏng im lặng).

🔴 **Đoạn cuối phim ⛔ không có "đoạn sau".** `thoi_gian` giải bằng cách lấy tới hết
nguồn. `nan_cho_vua` **phải xử đúng như thế** — nếu ⛔ không, đoạn cuối có ngân sách
`0` và **LUÔN** bị gọi LLM.

⚠️ **Chưa xác minh**: `nan_cho_vua` hiện nhận **một đoạn** (`m: dict`); để biết đoạn
sau bắt đầu lúc nào nó cần **cả danh sách**. Đổi chữ ký là đổi mọi người gọi ⇒ đọc
`giai_doan_giong.py` trước khi chốt cách truyền.

## 3. Luật gom lô — làm rõ, ⛔ không đổi

Hệ **đã** đúng; ghi ra để ⛔ không ai "tối ưu" nhầm chiều:

```
GOM LO     viec dong nhat, doc lap, mot loi KHONG dau doc ca lo
           -> dich (`long_tieng.chia_lo`): DUNG, dang lam
TUNG DOAN  chi phi tinh theo doan, mot loi KHONG duoc lan
           -> sua cau (nac 2): DUNG, dang lam
           ⛔ "mot cau hong lam hong hoa don cua ca tram cau con lai"
```

🔑 **"Từng đoạn" ⛔ KHÔNG có nghĩa "nối tiếp".** ⛔ Nhưng song song hoá ⛔ **không
phải** thuốc ở đây: trần thật là **≤ 2 request đồng thời mỗi model**, và các bước có
khai đều `tai_nguyen_suat=1` ⇒ **một job `llm_remote` một lúc trên toàn nền tảng**.
49 lượt song song hết mức vẫn ~11 phút.

⇒ ⭐ **Thuốc là làm cho 49 lượt ĐỪNG XẢY RA**, ⛔ không phải làm chúng nhanh hơn.

### 3b. 🔴 Khuyết tật đi kèm: `voice_synthesis` ⛔ không khai `llm_remote`

```
pipeline.py:259  EDIT_PLAN        tai_nguyen="llm_remote"  suat=1
pipeline.py:282  CONTENT_PROCESS  tai_nguyen="llm_remote"  suat=1
pipeline.py:440  QC_AI            tai_nguyen="llm_remote"  suat=1
                 VOICE_SYNTHESIS  ⛔ KHONG KHAI — ma goi 49 lan
```
⇒ 49 lượt ấy chạy **ngoài toàn bộ cơ chế đếm suất**. Bản khai giả định nó gọi
*"thỉnh thoảng"*. **49 lần ⛔ không phải thỉnh thoảng.**

## 4. 🔴 Mốc thời gian — ĐO trước khi tin ngân sách

Ngân sách **đứng trên** mốc từng từ. Sửa công thức mà mốc vào sai chỉ là **đổi một
loại sai này lấy một loại sai khác**.

`N-59` (25/09): sidecar WhisperX **chết sau 4 giây** vì ⛔ không thấy `ffmpeg` dưới
`LocalSystem`; hệ **lui về faster-whisper**; giai đoạn **vẫn báo `succeeded`**.
⇒ **Mốc từng từ chưa bao giờ được căn cưỡng bức trên production.** Có mốc, ⛔ nhưng
là mốc thô — và ⛔ không ai biết.

⇒ **Phép đo bắt buộc**, trên phim thật, ba đường:
```
faster-whisper tho    <- thu production DANG chay
WhisperX da can       <- sau ban va N-59
CapCut ASR            <- `D:\Viral\resources\app-src\capcut_asr.py` (bot cua chu du an)
```
⭐ Chủ dự án nhận xét CapCut làm việc này **rất tốt** ⇒ nó là **ứng viên engine thật**,
⛔ không phải ý tưởng suông.

## 5. Nghiệm thu — ⛔ "làm xong" KHÔNG phải tiêu chí

| # | phép kiểm |
|---|---|
| 1 | Đoạn **cuối phim** có ngân sách **> 0** và ⛔ không bị gọi LLM vô cớ |
| 2 | Một đoạn vừa-nếu-tính-khoảng-lặng ⇒ `VUA`, ⛔ **không** vào nấc 2 |
| 3 | `nan_cho_vua` và `thoi_gian` cho **cùng một con số** trên cùng dữ liệu — ghim bằng phép kiểm, ⛔ không bằng giao ước |
| 4 | Số lượt LLM trên phim thật: **trước → sau**, đo được |
| 5 | `voice_synthesis` khai `llm_remote`, và bộ nạp job tính đúng suất |
| 6 | Bảng so **ba đường ASR**: lệch mốc từng từ, trên cùng phim |

⚠️ **⛔ Không hứa con số cho (4).** Giả thuyết là ngân sách sai gây ra phần lớn 49
lượt. Nếu đo ra chỉ giảm `49 → 40` thì gốc nằm chỗ khác và **phải tìm tiếp**, ⛔ không
được coi là đã xong.

## 6. Rủi ro

| rủi ro | xử |
|---|---|
| Đổi chữ ký `nan_cho_vua` lan ra mọi người gọi | đọc `giai_doan_giong.py` trước; ⛔ không đổi nếu truyền được cách khác |
| Đoạn cuối ngân sách `0` ⇒ luôn gọi LLM | phép kiểm (1) chặn |
| Hai pha lệch nhau lần nữa | phép kiểm (3) — **một phép tính**, ⛔ không hai bản khai |
| Mốc ASR sai làm ngân sách vô nghĩa | §4 đo trước khi tin |
| Bản dịch **ngắn đi** vì ít bị ép rút gọn | ⭐ đây là **lợi**, ⛔ không phải rủi ro: `len_ratio < 0,85` từng kéo chrF++ từ **49,85** xuống **39,31** |
