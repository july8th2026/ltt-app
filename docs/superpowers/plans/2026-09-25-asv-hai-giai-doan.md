# ASV — tách **HAI GIAI ĐOẠN** (chủ dự án chốt 25/09/2026)

> Thay thứ tự 12 bước một mạch. ⛔ Tệp nào khác mô tả thứ tự khác là **cũ**.
> Luật làm việc: `docs/00_LTT_OPERATING_CONTRACT.md`. Gate: **một lần, một cấp,
> CUỐI PLAN** (chốt 25/09) — ⛔ không gate giữa phiên.

## 0. Chốt của chủ dự án

> **Giai đoạn 1**: xử lý **toàn bộ** vấn đề voice → ra MP4 tiếng Việt khớp hình.
> **Giai đoạn 2**: có MP4 full rồi mới xử lý hình ảnh nâng cao, **trên tệp đã xong**.
> ⇒ **Cắt cảnh nằm SAU render**, ⛔ không phải trước dịch.
> *"Chặng 1→3 ra được MP4 chuyển voice là quan trọng nhất."*

## 1. 🔑 Vì sao đúng — bằng chứng trong chính kho

`apps/auto_scan_video/ban_do_thoi_gian.py` mở đầu:

> *"cảnh bị cắt **biến mất khỏi bản ra**, nên giây 120 của nguồn có thể là giây 74
> của bản ra — hoặc **không tồn tại** … sai số đó **tích luỹ** theo từng cảnh bị cắt."*

⇒ Kho **đã biết** vấn đề và giải bằng một **lớp đổi mốc**. Thứ tự mới **xoá sự ghép
nối** thay vì quản lý nó: cắt trên MP4 hoàn thiện thì hình và tiếng bị cắt **cùng
nhau**, sai số **⛔ không thể sinh ra**.

⭐ Lợi ích thứ hai: **hai preset dùng chung y hệt đường voice**; khác biệt preset co
thành một bước hậu kỳ ⇒ xoá cả lớp lỗi phụ-thuộc-preset. (25/09: `lat_guong` và
`dien_nen` bị từ chối ở **ba tầng** dưới `giu_hinh`.)

## 2. ⚠️ Cái giá — ĐO TRƯỚC KHI HỨA

🔴 **`ban_do_thoi_gian` có MƯỜI người dùng**, ⛔ không xoá được dễ:

```
bien_tap · che_do_render · giai_doan_ban_dung · giai_doan_qc · giai_doan_qc_ai
giai_doan_thoi_gian · loi · phu_de · qc            (+ chinh no)
```

⇒ Đây là **tái cấu trúc**, ⛔ **KHÔNG phải một lần xoá tệp**. Điều phối đã nói hớ
*"trở thành thừa"* trước khi `grep` — ghi lại để ⛔ không ai lặp.

## 3. 🔴 Cắt cảnh CÓ THOẠI — ba phương án, cần chủ dự án chốt

`ban_bien_tap.py:157,199-234`: quyết định cắt **có** xét `_co_thoai`, ⛔ nhưng chỉ
**nâng ngưỡng** (`NGUONG_BO_CO_THOAI` > `NGUONG_BO`) ⇒ **vẫn cắt được cảnh có thoại**.

Dưới thứ tự mới ta **đã tổng hợp giọng xong** rồi mới vứt. Hai hệ quả:

| | |
|---|---|
| lãng phí máy | dưới giá phẳng là chi phí của **ta**, ⛔ không phải của khách |
| 🔴 **cụt tiếng** | cắt giữa một câu đang nói. Thứ tự cũ ⛔ không gặp vì cắt **trước** khi có tiếng |

```
A  CAM cat canh co thoai        don gian nhat · mat mot phan kha nang cat
B  chi cat o RANH GIOI CAU      giu duoc kha nang cat · CAN moc cau (ta DA CO)
C  chap nhan lang phi            re nhat de lam · dat nhat khi chay · VAN cut tieng
```

⭐ **Điều phối nghiêng về B**: ta **đã có mốc câu** từ bước nắn thời lượng, nên cái
giá là *dùng lại dữ liệu đã có*, ⛔ không phải *dựng cơ chế mới*. ⛔ **Chưa chốt** —
chờ số đo phương án A mất bao nhiêu % khả năng cắt.

## 4. Demucs ba lớp — cơ chế LẤY ĐƯỢC, mặc định thì KHÔNG

**Nguồn:** `C:\Cut_only ver2` (bot của chủ dự án, chạy ổn định lâu).

```
bot_gui.py:909-913          thanh truot gain moi stem, thang 0,0-2,0, buoc 0,05
configs/pipeline2_*.yaml    cong thuc that:
        vocals_gain: 1.0    drums_gain: 0.7-0.8
        bass_gain:   0.0    other_gain: 0.0
```

⇒ ✅ **Cơ chế đã có lời giải**: `htdemucs` **4 stem** + gain riêng + trộn lại.
⛔ **KHÔNG cần mô hình mới.**

🔴 **NHƯNG mặc định của họ ⛔ KHÔNG chuyển sang ta được** — mục tiêu **ngược nhau**:

```
Cut_only:  GIU giong, BO nhac      -> vocals 1,0 · other 0,0  (vut het hieu ung)
ASV     :  BO giong goc, GIU nhac + tieng dong -> gan nhu NGUOC LAI
```

⇒ Lấy **cơ chế + đặc tả giao diện**; **mặc định phải tự đo trên phim của ta**.
⚠️ Ánh xạ 4 stem → 3 lớp người dùng (`voice` · `hiệu ứng` · `nhạc nền`) **chưa xác
minh** — `other` chứa những gì phải nghe thử, ⛔ đừng đoán.

⚠️ **`D:\FULL AUTO VIDEO\DUNGVIDEO-FULL\engine\audio\demucs_post.py` ⛔ KHÔNG phải
lời giải này** — nó chạy `--two-stems vocals` (**2** lớp) và tự khai *"Does NOT
change gain/loudness"*. ⛔ Đừng lẫn hai kho.

⭐ Đáng lấy từ `DUNGVIDEO-FULL`: `engine/subtitle/{ass_builder,burner}.py` (đốt phụ
đề ASS) · `ffmpeg_gpu.py` (*"libass. Đừng đổi."*) · `gpu_arbiter.py` · và **cách suy
ra** timeout `1800 s` (*"87 segments ~20min trên CUDA; > 30 phút = chắc chắn hang"*)
— ⛔ chép **cách suy ra**, ⛔ đừng chép con số.

## 5. QC — trả lời câu hỏi *"ổn định rồi thì thôi kiểm?"*

```
qc co hoc      co hinh? co tieng? CO TEP GIAO?     RE    -> LUON BAT
qc_do_luong    ASR vong lai + cham giong           DAT   -> bat/tat duoc
qc_ai          model doc ban dich soi loi nghia    DAT   -> bat/tat duoc
```

🔴 **Giữ cổng rẻ, ⛔ không thương lượng.** 25/09 có một lượt `done` + QC `đạt` +
**⛔ không tệp nào** — và luật thu tiền khi ấy là `{done}` ⇒ **thu 50 credit cho hàng
rỗng** (`N-57`). ⭐ Tắt cổng cơ học khi *"hệ thống đã ổn định"* chính là bỏ đi thứ
báo cho ta biết mình **đã thôi ổn định**.

⇒ Hai cổng đắt **bật/tắt được**, ⛔ nhưng phải ghi **cái giá**: lỗi loại nào sẽ đi
thẳng tới khách.

## 6. Thứ tự — **bước XOÁ mã đi trước bước THÊM mã**

```
B0  CHOT THIET KE      ADR + phuong an cat canh        -> chu du an duyet
B1  GO CAT KHOI GD1    tai cau truc ban_do_thoi_gian   -> test nham xanh
B2  DEMUCS BA LOP      co che tu Cut_only, mac dinh TU DO
B3  ⭐ NGHIEM THU GD1   phim that -> MP4 tieng Viet     -> CHU DU AN XEM VA GAT
B4  LAP GIAI DOAN 2    ma DA CO, chi doi cho cam
B5  WEBUI              dac ta da co tu anh chup
B6  CHAY THAT WORKER   mo lai o day, KHONG som hon
```

**Song song, ⛔ không chặn ai:** `N-57` giao hàng rỗng · đối chiếu `4,228` vs `3,35`
(ngân sách độ dài câu dịch) · `N-59` hàng rào thứ hai (`LTT_FFMPEG` vào MACHINE Path).

**⛔ DỪNG tới B6:** chạy ASV trên worker thật · nối thêm tính năng GĐ2 vào chuỗi cũ.

## 7. Nghiệm thu — ⛔ *"làm xong"* KHÔNG phải tiêu chí

| bước | phép kiểm |
|---|---|
| B1 | một lượt fixture ra MP4 đúng **và** ⛔ không còn nhánh preset trong bộ lập kế hoạch |
| B2 | kéo **từng** thanh trượt ⇒ **nghe được** khác biệt; ba lớp tách đúng |
| B3 | phim thật ⇒ MP4 tiếng Việt, **đủ độ dài gốc**, khớp hình — chủ dự án gật |
| B4 | thao tác trên MP4 đã xong, **⛔ không đụng** một mẫu tiếng nào |
| B6 | chạy qua **bảng kiểm môi trường** lượt 25/09 đã lập (PATH · quyền · biến) |
