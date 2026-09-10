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
    ("apps.ltt_voice.giong_mau", "loc"),
    ("apps.ltt_voice.giong_mau", "tim"),
    ("apps.ltt_voice.giong_mau", "hop_le"),
    ("apps.ltt_voice.giong_mau", "DANH_SACH"),
    ("apps.ltt_voice.giong_mau", "NHAN_GIOI"),
    ("apps.ltt_voice.giong_mau", "NHAN_VUNG"),
    ("apps.ltt_voice.giong_mau", "NHAN_PHONG_CACH"),
}
