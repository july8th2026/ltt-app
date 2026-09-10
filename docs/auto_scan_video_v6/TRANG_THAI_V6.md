# TRẠNG THÁI CHƯƠNG TRÌNH ASV V6 (98+)

> Nhánh `phien/asv-v6`. Gói yêu cầu gốc:
> `G:\My Drive\AI\A\Auto_Scan_Video_V6_98_Plus` (35 pha, 00–34).
>
> ⛔ **Không deploy cho tới pha 34.** `apps/auto_scan_video/manifest.py` khai
> `enabled=False`, và `/auto-scan-video` trả **404** trên production (cờ
> `LTT_AUTO_SCAN_VIDEO`). Mọi thay đổi ở đây không chạm một khách nào.

## Vì sao tệp này tồn tại

Gói V6 yêu cầu mỗi pha *"đọc STATE/report pha trước"*. Không có tệp ấy thì mỗi
phiên phải suy trạng thái từ `git log` — và `git log` trả lời *"ai đã commit
gì"*, không trả lời *"pha nào đã đóng, pha nào bị chặn và bởi cái gì"*.

⚠️ Bảng dưới là **con trỏ**, không phải bản sao. Số liệu sống ở báo cáo từng
pha; chép lại vào đây là tạo một bản sẽ trôi.

## Bảng pha

| Pha | Tên | Trạng thái | Ghi chú / chặn |
|---|---|---|---|
| 00–07 | nền, hợp đồng, kiến trúc GUI | **CHƯA MỞ** | 06/07 chưa bắt đầu |
| 08 | Durable upload + source preview | **XONG** | `ef7b3425` (08a) + `d78d1804`/`cc9b1e8d` (08b). Xem `PHA08_TAI_LEN.md`. 🔴 Tìm ra đường tải lên 2 GiB **chưa bao giờ chạy được từ giao diện** |
| 09 | Timeline + Scene Browser | **XONG** | `d4066def` — khách XEM được cảnh, và chỉ xem |
| 10 | Core edit controls | **MỘT PHẦN** | `a9cecb42` cắt đầu/cuối. `zoom`/`crop`/`reframe` nằm trong `CAM_TRONG_MVP` — mở chúng cần một ADR, không phải một lượt code |
| 10b | kiểm GUI thật | **XONG** | `395b29dd` — bắt một lỗi bố cục bộ kiểm không thấy |
| 11 | Overlay controls | **XONG** | `efbcfb4a` + `42512fd8` (11a chữ) · `d78d1804` (11b logo, sau khi pha 08 mở đường nhập ảnh). Xem `PHA11_LOP_PHU_CHU.md` |
| 12 | Region editor v2 | **XONG** | `8c4a1d35` (giờ có tác dụng thật) + `8cd5b281` (giao diện đặt giờ) |
| 13–34 | — | **CHƯA MỞ** | |

## Nợ kỹ thuật mở, không thuộc pha nào

| Mục | Hiện trạng | Vì sao chưa đóng |
|---|---|---|
| `test_448` ×7 đỏ | **đúng là đỏ** | Ba nguyên nhân đã tách: trần token · `sqlite3 database is locked` · LUFS T4. Hai cái sau **đã vá có đối chứng**; cái đầu còn là giả thuyết chưa phân biệt được với "chế độ rỗng lưỡng cực" của `ltt_llm`. Xem `CHAN_DOAN_TEST_448.md` |
| Đo `chuyen_loi_thoai` qua `goi_tinh_tien` | **bị chặn** | Cần `LTT_DATABASE_URL` + `LTT_TOKEN_ENCRYPTION_KEY` + `LTT_LLM_BASE_URL` từ `C:\LTTPlatform\secrets\app.env` (ACL chặn — **cố ý**). Đường hợp lệ đã có sẵn: `setup\do_on_dinh_nang_quyen.ps1`. Việc chủ dự án bấm |
| `nghiem_thu_hien_hanh.json` | **không tái sinh được ở độ trung thực đầy đủ** | Chặn cùng chỗ ở trên. ⛔ Không được tái sinh từ **một** lượt xanh (p(hỏng) ≈ ½) cũng không từ một lượt có **thay thế** |
| Xem trước lớp phủ/logo trên khung hình | chưa có | `vung_che` kéo thả được, lớp phủ và logo thì chưa — khách đặt toạ độ bằng số |
| **Resume thật** khi tải lên | chưa có | Hiện là *thử lại cả tệp* 3 lần. Resume theo byte cần multipart upload của R2 + một bản ghi tiến độ |
| `vung_che`/`cat_dau_cuoi` chưa dùng `hinh_hoc` | 2 bản chép còn lại | Đã ghi tên ở `REBASE_MAP_V4.md`; di trú phải đi cùng đối chứng của chính nó |

## Quy tắc riêng của chương trình này

1. **Không hạ mốc bánh cóc** để một lượt gate xanh. Mốc chốt **tập hợp**, và hạ
   nó là bỏ chính câu hỏi nó đang hỏi.
2. **Bằng chứng engine, không phải HTTP 200.** Mỗi tính năng đổi điểm ảnh phải
   có một phép đo trên tệp ra (PSNR/LUFS), và phép đo phải **không mất mát** —
   xem §4 của `PHA11_LOP_PHU_CHU.md` cho một bản đo sai vì `libx264`.
3. **Đối chứng là tiêm bản cũ xem có ĐỎ không**, và bản thật phải xanh trước.
4. **Kiểm trình duyệt thật** sau mỗi thay đổi giao diện, ở **cả** 1280 và 375.
   Ba lần trong chương trình này, lỗi chỉ trình duyệt thấy — và không lần nào
   tràn ngang, nên chốt `overflow` im lặng cả ba.
