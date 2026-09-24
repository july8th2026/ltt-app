"""LTT VOICE — giong noi tieng Viet nhan ban, chay tren may A (Q117/Q118)."""

#: Be mat ma app KHAC duoc phep import tu app nay.
#:
#: ⭐ Ba cai ten, va chung di voi nhau thanh MOT chuoi: doc tham so -> kiem
#:    quyen so huu giong -> sinh mot luot. Auto Scan Video dung chuoi do de sinh
#:    tieng cho **tung doan** ban dich, roi tu so huu tep, khoa va checkpoint.
#:
#: 🔴 `giai_giong` la BAT BUOC, khong phai tien loi. Docstring cua no ghi:
#:    *"Day la cho **quyen so huu** duoc kiem, va no la cho duy nhat."* Mot app
#:    khac goi `goi_cong` ma khong qua `giai_giong` la mo mot duong dung giong
#:    cua nguoi khac — dung bat bien I6/I7 ma ADR-002 vua dong.
#:
#: ⛔ `sidecar_client` co trong danh sach chi de HOI may da san sang chua
#:    (`san_sang()`), khong phai de goi thang. Goi thang la bo qua ca ba tang
#:    kiem o tren.
#:
#: ⛔ KHONG mo `chuan_bi_van_ban` hay cac tham so `temperature`/`top_k`/`top_p`:
#:    cache CUDA graph cua may sinh tieng khoa theo bo tham so do (CLAUDE.md),
#:    va tran 1.500 ky tu moi luot la tran CHAT LUONG cua app nay chu khong phai
#:    mot con so ai cung duoc chinh.
#:
#: Them mot dong vao day la mot QUYET DINH KIEN TRUC: phai sua CA HAI phia, o
#: day va o `APP_DUOC_DUNG_APP` trong `tools/lint_app_contract.py`.
BE_MAT_CONG_KHAI = {
    ("apps.ltt_voice.features", "chuan_hoa"),
    ("apps.ltt_voice.features", "giai_giong"),
    ("apps.ltt_voice.features", "goi_cong"),
    ("apps.ltt_voice", "features"),
    ("apps.ltt_voice", "sidecar_client"),
    ("apps.ltt_voice.tham_so_cong_khai", "TRAN_MOI_LUOT_SINH"),
    #: 🔴 Chuan hoa van ban TRUOC khi doc. Bo qua no la doc ngay thang thanh
    #:    chuoi ky tu, doc URL tung chu cai, va de ky tu vo hinh thanh token la.
    #:    Auto Scan da hong dung nhu vay o ban dau cua pha 12.
    #: ⛔ Chi `chuan_hoa`, KHONG mo `chuan_bi`: ham do vua chuan hoa vua CHIA
    #:    DOAN, va chia mot cau thoai la doi no thanh hai giong doc o giua cau.
    ("apps.ltt_voice.text_pipeline", "chuan_hoa"),
    ("apps.ltt_voice", "text_pipeline"),
    #: 🔑 Liet ke giong cua CHINH chu so huu, cho man tao lan chay cua Auto Scan.
    #:    Ham nay da loc `owner_id`, da xu ly kho giong dung chung, va da bo
    #:    giong khong con `active`. Mo no ra thay vi de app khac tu truy van
    #:    `VoiceRef`: ba phep loc do deu de lam sai, va lam sai phep dau tien
    #:    nghia la mot khach chon duoc giong nhan ban CUA NGUOI KHAC.
    #: ⚠️ Chi DOC. Tao/sua/go giong van chi lam duoc o man cua LTT VOICE.
    ("apps.ltt_voice.doc_man_api", "ma_giong_cua_toi"),

    # ── Catalog giọng mẫu (pha 09 của Auto Scan V4) ─────────────────────────
    #
    # 🔑 Đây là thứ `AUTO_MATCH` **khớp VÀO**. Không có nó thì "tự khớp giọng"
    #    không còn gì để khớp và sẽ thoái hoá thành "lấy giọng mặc định" — đúng
    #    điều `ADR-V4-001` D-V4-04 cấm bằng tên.
    #
    # ⚠️ CHỈ ĐỌC, và ba nhãn đi kèm bốn hàm tra cứu. Tạo/sửa/gỡ giọng vẫn chỉ
    #    làm được ở màn của LTT VOICE. Một app khác đọc được catalog không có
    #    nghĩa nó ghi được vào đó.
    #
    # ⭐ Xuất `loc` chứ không bắt bên gọi tự duyệt `DANH_SACH`: phép lọc là một
    #    quy tắc, và hai bản của một quy tắc là hai bản sẽ lệch nhau.
    # 🔑 Tap LAN giong la tap ngon ngu DICH cua Auto Scan (chot 22/09):
    #    `apps/auto_scan_video/ngon_ngu._kiem` doc no de mot dich khong co
    #    lan giong la loi luc import, khong phai mot lan chay hong o GIONG.
    ("apps.ltt_voice.lan_ngon_ngu", "LAN_HOP_LE"),
    # 🔑 Hai MA LOI cong khai (24/09). Man mot lan chay cua Auto Scan bat loi
    #    **THEO MA** (`auto_scan_video/ma_loi.py` -> `quan_sat.LOI_CO_MA`), dung
    #    vai ma hai hang so nay sinh ra cho: *"khach bat loi theo ma, khong theo
    #    cau chu"*. Xuat MA ra thay vi de ben do go lai chuoi, vi mot ma go lai la
    #    ban thu hai cua cung mot ma va no se lech im lang khi ta doi ten.
    # ⛔ Chi MA: `PhanQuyet`/phep quyet dinh lan giong van thuoc app nay.
    ("apps.ltt_voice.lan_ngon_ngu", "MA_LOI_LECH_LAN"),
    ("apps.ltt_voice.lan_ngon_ngu", "MA_LOI_LAN_KHONG_RO"),
    ("apps.ltt_voice.giong_mau", "loc"),
    ("apps.ltt_voice.giong_mau", "tim"),
    ("apps.ltt_voice.giong_mau", "hop_le"),
    ("apps.ltt_voice.giong_mau", "DANH_SACH"),
    ("apps.ltt_voice.giong_mau", "NHAN_GIOI"),
    ("apps.ltt_voice.giong_mau", "NHAN_VUNG"),
    ("apps.ltt_voice.giong_mau", "NHAN_PHONG_CACH"),
    # 🔑 Kho CHUNG cho làn mà giọng mẫu không phủ (asv-final F-03, 22/09):
    #    20/20 preset là làn `vi`, nên đích `en` của `AUTO_MATCH` chỉ còn kho
    #    chung để khớp vào. Hàm này ĐÃ đi qua cổng license U-05
    #    (`_dieu_kien_kho_chung`), đã bỏ giọng không `active` và giọng chưa rõ
    #    giới, và đã sắp tất định — ba việc app khác không được viết lại.
    # ⚠️ CHỈ ĐỌC, và chỉ ĐỌC giọng ĐÃ ở kho chung (khách đã thấy). Không mở
    #    thêm giọng nào cho ai; dùng giọng vẫn phải qua `giai_giong`.
    ("apps.ltt_voice.tham_chieu", "ung_vien_kho_chung"),

    # ── Nghe thử TRƯỚC KHI chọn (Auto Scan Video V5) ────────────────────────
    #
    # 🔑 Màn chọn giọng của Auto Scan hỏi đúng câu `nghe_thu.py` mở đầu bằng:
    #    *"giọng này nghe như thế nào"*. Ba nhãn (giới · vùng · phong cách)
    #    không trả lời được nó, và cách còn lại là chạy thật một lượt — tức trả
    #    tiền để xem mình có muốn mua không.
    #
    # ⭐ Xuất `duong_cho_trang` VÀ `duong_cho_app_khac`, KHÔNG xuất
    #    `khoa_mau`/`khoa_rieng`/`khoa_chung`. Đây là bài học đã trả giá ở
    #    `du_an.duong_tieng()`: **MỘT thẩm quyền duy nhất dựng đường nghe
    #    thử**. Xuất hàm dựng khoá là mời mỗi bên gọi tự ghép URL — và một bản
    #    ghép là một bản sẽ lệch.
    #
    # ⛔ Và không mở thêm một cửa đọc nào: tệp được phục vụ bởi chính route
    #    `/audio` của LTT VOICE, nơi phép kiểm sở hữu/quyền đọc đã ở sẵn. App
    #    khác chỉ nhận **URL**, không nhận tệp và không nhận khoá.
    #
    # ⚠️ `duong_cho_app_khac` là bề mặt THẬT `apps/auto_scan_video/gia.py`
    #    import qua `try/except` (`891d93db`, nhánh `phien/asv-v4`) —
    #    `INV-BE-MAT-1`: mất nó thì preview giọng của ASV biến mất **im lặng**,
    #    không đỏ ở đâu cả. `duong_cho_trang` chưa có bên gọi ngoài app nhưng
    #    khai ở đây vì nó là hàm mà `duong_cho_app_khac` GỌI LẠI — hai hàm cùng
    #    một hợp đồng, khai riêng một nửa là để nửa kia trôi không ai thấy.
    #
    # ⚠️ Cả hai chỉ hỏi KHO, không chạm CSDL — gọi được ngoài phiên.
    ("apps.ltt_voice.nghe_thu", "duong_cho_trang"),
    ("apps.ltt_voice.nghe_thu", "duong_cho_app_khac"),
}
