# VẬN HÀNH THẬT — chương trình nghiệm thu thường trực

> **Gọi nó thế nào.** Nói *"check plan vận hành thật trong hệ thống LTTSTUDIOSAPP
> và triển khai"* là đủ. Phiên nhận việc đọc tệp này trước, rồi theo §2.
>
> Đây **không** phải một plan dùng một lần. Nó là chương trình chạy lại **sau mỗi
> lần nâng cấp** và **mỗi khi cần audit**.

---

## 1. Nó đo cái gì — và **không** đo cái gì

Giả lập người dùng thật gọi vào **production**, đi xuyên
`API → job → admission → hàng đợi → runtime → GPU → stream → credit → sổ sách`.

⛔ **Nó KHÔNG phải bộ đo hiệu năng.** Đừng chấm nó bằng tok/s. Thứ nó đo là
**hàng đợi, công bằng, và sổ sách** — ba thứ chỉ lộ ra khi hệ **đầy**.

⛔ **Unit test không phải bằng chứng nghiệm thu production.** Ngày 13/09/2026,
**ba** bản vá liên tiếp của sự cố L-08 qua sạch **mọi** phép kiểm trong cây rồi
hoá ra cả ba **chưa từng chạm vào một lượt thật** — chúng gắn vào một cánh cửa
mà lưu lượng không đi qua. Khoảng cách giữa "test xanh" và "chạy đúng" là cả một
lớp lỗi, và chương trình này sinh ra để đứng đúng vào khoảng đó.

⭐ Bằng chứng nó có ích: trong lượt chạy đầu tiên (13/09) nó tìm ra **hai lỗi
   production** mà không unit test nào trong kho bắt được, vì cả hai chỉ hiện khi
   hệ **đang đầy** — xem `ltt_llm_dual/SO_LOI_DO_TAI.md` mục L-11 và L-12.

### Câu hỏi trung tâm

Hệ có **sáu suất** (3 mỗi model, hai card độc lập). Mọi kịch bản xoay quanh ranh
giới ấy: *sáu người đầu chạy — còn người thứ bảy thì sao?*

## 2. Chạy thế nào

```bash
# 0. LUÔN LUÔN trước: có phiên khác đang giữ máy không
py tools\cua_so_yen.py trang-thai

# 1. Nền phải sạch, và production phải RẢNH (xem §5)
# 2a. Tầng DỊCH VỤ (qua máy A + Cloudflare) — GuideLLM, chạy trong WSL
wsl bash tools/do_thong_luong/chay_guidellm.sh ltt-3.8 700 256 12
wsl bash tools/do_thong_luong/chay_guidellm.sh ltt-3.5 700 256 12

# 2b. Tầng ENGINE (thẳng máy B) — bench.py, chỉ stdlib, chạy TRÊN máy B
python bench.py --kich-ban c1    --ra ket_c1.jsonl     # một lượt đơn, có cho_ranh()
python bench.py --kich-ban c4    --ra ket_c4.jsonl     # bốn lượt đồng thời
python bench.py --kich-ban whale --ra ket_whale.jsonl  # prefill khổng lồ + ba minnow lệch giờ
```

⛔ **Hai chân chạy NỐI TIẾP, không song song** — cùng bắn vào một 3090 thì cả hai
   số đều vô nghĩa (`BO_DO_CHUAN.md` §6, §9.3). Thứ tự đã dùng: engine trước,
   dịch vụ sau.

🔑 **Nguồn chân lý về bộ đo là `docs/ltt_llm_dual/BO_DO_CHUAN.md`** — nó ghi
công cụ nào cho tầng nào, bốn lần bộ đo tự viết nói dối về production, và luật
phân loại *"hỏi nó trả lời câu gì, đừng nhìn tên nó"* (bộ đo thông lượng ⇒ xoá;
đầu dò trạng thái và bộ dựng tình huống ⇒ giữ).

| tầng | công cụ | ở đâu |
|---|---|---|
| **serving** (cổng D/E/F) | **GuideLLM 0.7.3** + cầu `Idempotency-Key` | `tools/do_thong_luong/chay_guidellm.sh` · `cau_idem.py` |
| **engine** (máy B) | `bench.py` · `llama-batched-bench` | `docs/ltt_llm_dual/artifacts/bench/bench.py` |
| **trạng thái** (lease · credit · residency) | đầu dò riêng — GuideLLM không biết lược đồ của ta | `tools/soi_lease_tien.py`, `dem_lease.py`, … |

## 2b. ⛔ BỘ ĐO LÀ THỨ MƯỢN, KHÔNG PHẢI THỨ TỰ XÂY

Chủ dự án chốt **14/09/2026**: *"bộ đo có sẵn trong hệ thống đã sử dụng và pass —
xóa đo tự vẽ trùng lặp."*

Ngày 13–14/09 tôi đã dựng một bộ đo riêng (`tools/nghiem_thu_van_hanh/`, sáu
module, bốn tệp test). **Nó đã bị xoá.** Lý do không phải nó xấu mã — mà là:

| | |
|---|---|
| một lượt chạy của nó sinh **bốn lỗi (V-01…V-04), cả bốn là lỗi của chính nó** | mỗi lỗi bộ đo tốn một lượt chạy production để phát hiện |
| nó **trùng** bộ đo chuẩn ở phần cốt lõi | hai bộ đo cùng trả lời một câu là hai bộ đo có thể mâu thuẫn |
| bộ chuẩn đã **chạy thật, đã đóng 14 cổng, có bản ghi** | thứ đã chứng minh thắng thứ mới viết |

⇒ **Cần đo thêm một đại lượng thì thêm một kịch bản vào công cụ của tầng ấy**
  (§2a/§2b, §6), không mở một bộ đo thứ hai. Luật này áp cho mọi phiên sau.

⚠️ Và đây là lần **thứ hai** cùng một sai lầm ở cùng dự án: 13/09 đã xoá sáu
   script tự viết vì y hệt lý do (`BO_DO_CHUAN.md` §7), rồi 14/09 tôi dựng lại
   một bộ mới. Tệp `BO_DO_CHUAN.md` đã tồn tại sẵn và tôi không đọc nó trước khi
   viết dòng mã đầu tiên.

### Nợ đã ghi, KHÔNG tự ý trả bằng một bộ đo mới

`bench.py` đo **engine máy B** qua llama-swap loopback (`:8280`). Nó **không** đi
qua `API → admission → hàng đợi → credit` của máy A. Tầng ấy hiện đo bằng
**test trong cây** (`tests/test_1240`…`test_1250`) cộng ba lượt nghiệm thu
production đã ghi ở §7. Muốn đo tầng ấy bằng tải thật thì **đề xuất thành một
kịch bản của `bench.py`**, và chỉ làm khi chủ dự án chốt.

## 3. Tài liệu con

| | |
|---|---|
| **Bộ đo — NGUỒN CHÂN LÝ** | `docs/ltt_llm_dual/BO_DO_CHUAN.md` |
| Bảng cổng A…Q, cổng nào đóng/hoãn và vì sao | `docs/ltt_llm_dual/BANG_DOI_SOAT.md` |
| **Đường đi một lượt, ai gác chặng nào** | `docs/ltt_llm_dual/BAN_DO_DUONG_DI.md` |
| Sổ lỗi của hệ con | `docs/ltt_llm_dual/SO_LOI_DO_TAI.md` |
| Số suất · pool KV · ngưỡng whale | `apps/ltt_llm/ngan_sach.py` |

🔑 **Đừng gõ lại một con số nào vào tệp này.** Đó chính xác là cơ chế đã làm
bảng ở kho này nói sai năm lần, và ngày 13/09 làm ~40 tài liệu khai sai số suất
suốt hai ngày mà không ai biết.

## 4. Đọc kết quả — bốn ngăn

Mỗi phát hiện vào **đúng một** ngăn, **trước** khi sửa bất cứ gì:

| ngăn | xử |
|---|---|
| **lỗi hệ thống** | vào `SO_LOI_DO_TAI.md`, gom lại sửa **một lượt** |
| **lỗi bộ đo** | sửa ngay, chạy lại đúng kịch bản ấy |
| **nhiễu** | chạy lại, **không diễn giải** |
| **hệ đúng, kỳ vọng SAI** | sửa **kỳ vọng**, ghi rõ vì sao |

⭐ Ngăn thứ tư dễ bỏ sót nhất và đã xuất hiện thật: một prompt 195.696 token bị
từ chối, suýt ghi thành *"221K không với tới được"* — trong khi nền tảng khai
**171.458** và từ chối là **đúng**.

## 5. ⛔ Luật phối hợp — đọc trước khi gửi request đầu tiên

**Production là tài nguyên dùng chung, và `cua_so_yen` KHÔNG bảo vệ nó.** Khoá ấy
chỉ khoá lệnh nặng CPU/gate. Hai phiên có thể cùng xanh ở `cua_so_yen` mà vẫn
phá phép đo của nhau.

Đo được ngày 13/09: một lượt đo bão hoà chạy trúng cửa sổ deploy của phiên khác
⇒ cả sáu job chết cùng một khắc, và suýt bị đọc thành *"6 job đồng thời làm sập
hệ"*. Lượt đo ấy phải vứt.

⇒ **Trước khi vào cửa sổ đo: `ListAgents`, nhắn mọi phiên đang sống, chờ họ xác
  nhận.** Báo cả lúc **xong**. Giao ước đi hai chiều — bên đo báo trước, bên
  deploy cũng báo trước.

⚠️ Đề xuất đã ghi cho integrator: thêm tài nguyên khoá thứ ba `production_dang_dung`
   để deploy và đo **loại trừ nhau bằng cơ chế thay vì bằng lời hứa**. Chưa làm.

## 6. Mở rộng — ba luật không được vi phạm

Thêm kịch bản là thêm **một nhánh** vào công cụ đã có của đúng tầng ấy (§2a/§2b),
**không** mở một bộ đo mới — §2b và `BO_DO_CHUAN.md` §7. Ba luật dưới đây giữ cho
chương trình còn nghĩa sau mười lần mở rộng.

### Luật 1 — kịch bản phải CÓ KHẢ NĂNG HỎNG theo một cách nói lên điều gì đó

Khai rõ **điều gì làm nó đỏ**. Một kịch bản không thể đỏ thì không chứng minh gì
— sổ tay dự án gọi đó là **cửa giả**. Cột "đỏ khi" trong ma trận là bắt buộc; ô
trống nghĩa là kịch bản chưa dùng được.

### Luật 2 — mỗi ngưỡng phải có NGUỒN

Ba nguồn hợp lệ: một **hằng số trong mã**, một **câu trong spec**, hoặc một
**phép đo đã có**. Không có nguồn thì ghi *"chốt sau lượt đầu"* — **đừng bịa một
con số đẹp**.

⚠️ Ngưỡng sai còn tệ hơn không có ngưỡng, vì nó **xanh vĩnh viễn**.

### Luật 3 — mỗi phép đo phải có ĐỐI CHỨNG

Một con số không có đối chứng không phải phát hiện.

🔴 Ngày 13/09 tôi báo *"slot nhả sau 20,8 s — ĐẠT"*. Sai: `max_tokens=2048` sinh
xong trong ~20 s, nên máy B rảnh ở giây 20,8 **dù có cắt hay không**. Phép đo mù
đúng ở chiều nó định đo. Bản sửa: chạy **một lượt trọn vẹn không cắt** trước để
lấy `T_tròn`, rồi mới cắt — kết luận chỉ có nghĩa khi `T_nhả << T_tròn`.

## 7. Lịch sử chạy

Mỗi lượt thêm **một dòng**. Không xoá dòng cũ — so sánh giữa các lượt chính là
thứ một chương trình audit cần.

| ngày | commit production | kết quả | lỗi tìm ra |
|---|---|---|---|
| 2026-09-13 | `3c827ce3` → `08362209` | 9/11 đúng · L-08 đóng (643 s → **0,7 s**) | **L-11**, **L-12** |
| 2026-09-14 | `1235f876` | quét bão hoà 1/3/6/9 hai model, **8/8 mức 0 lỗi** · L-12 xác nhận vá | — (không lỗi mới) |

### Lượt 14/09 — số đo, bằng GuideLLM 0.7.3 qua máy A + Cloudflare

12 request mỗi mức · prompt 256 tok · `output_tokens=700` · `stream=false`.

| streams | `ltt-3.8` tok ra/s | trễ mdn | | `ltt-3.5` tok ra/s | trễ mdn |
|---:|---:|---:|---|---:|---:|
| 1 | **63,4** | 11,0 s | | 63,9 | 4,6 s |
| 3 | 104,3 | 14,4 s | | 119,0 | 6,1 s |
| 6 | 114,9 | 38,7 s | | 125,9 | 14,5 s |
| 9 | 106,5 | 39,4 s | | 136,9 | 22,3 s |

⭐ **Đối chứng (Luật 3):** `ltt-3.8` C1 = **63,4** tok/s, so với **63,39** đo
   13/09 bằng cùng công cụ (`BO_DO_CHUAN.md` §10). Trùng tới chữ số thứ ba ⇒
   phép đo lặp lại được, và mọi con số khác trong bảng đứng trên nền ấy.

✅ **Câu hỏi trung tâm đã có câu trả lời đo được.** Ở mức 6 và 9 — tức gấp đôi
   và gấp ba số suất của một card — **không một lượt nào bị từ chối**: 0 lỗi,
   0 × `429`. Thứ dâng lên là **độ trễ** (`ltt-3.8`: 14,4 → 38,7 s, ×2,7), còn
   thông lượng **chững** (104 → 115 → 107). Đó đúng là hình dạng của một hàng
   đợi hấp thụ tải, không phải của một cửa đuổi khách. **L-12 vá đúng.**

⚠️ **Hai điều tệp này KHÔNG được đọc thành nhiều hơn nó đo:**

1. **Đồng thời đo được ở mức 9 là 6,30 (3.8) / 5,55 (3.5), không phải 9.** Đó là
   **hiện vật của đoạn lên-xuống**: 12 request với 9 luồng chỉ đủ ~1,3 đợt, nên
   trung bình bị đoạn khởi động và đoạn cạn kéo xuống. Nó **không** nói "hệ giữ
   đồng thời ở 6". Muốn con số ấy có nghĩa thì phải nâng số request — một lượt
   đo khác.
2. **Hai cột KHÔNG trừ được cho nhau.** `ltt-3.5` chạy với `reasoning_effort=none`
   (bắt buộc: sàn `medium` của nó là **1024** > 700), còn `ltt-3.8` chạy ở mặc
   định. Đề bài khác nhau ⇒ chỉ đọc theo **chiều dọc** trong từng model.

## 8. Ngoài phạm vi

- Trộn tải ảnh / voice / Auto Scan Video — chốt **chỉ LLM**. Tranh chấp LLM ↔ ảnh
  đã do cổng I và N đo riêng.
- Cổng M — dư ở biên Cloudflare, **không sửa được ở tầng mã**.
- Cổng L (đa tệp) — thuộc Spec 2, chưa tồn tại.
- Cổng Q (soak) — spec không định nghĩa; chủ sản phẩm chốt bỏ qua 13/09.
