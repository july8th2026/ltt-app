"""apps/ltt_llm — model ngôn ngữ của nhà, bán ra ngoài qua `/api/v1`. (H38)"""

#: Be mat ma app KHAC duoc phep import tu app nay.
#:
#: ⭐ `ngan_sach` la **mot nguon chan ly** cho moi ngan sach token cua model nha
#:    (CLAUDE.md, muc don tham so 30/08): ba so go tay, con lai deu dan xuat.
#:    Auto Scan Video goi model qua `platform_core/llm/dieu_phoi.py`, nen no can
#:    dung con so do — va cach sai la go lai mot con so thu hai vao ma cua no.
#:
#: 🔴 Vi sao dieu do quan trong hon ve be ngoai: CLAUDE.md ghi mot loi da xay ra
#:    that — cua stream muon ngan sach 1.024 cua cua dong bo, va **moi cau tra
#:    loi dai cut o dung 1.024 token, im lang**. Mot con so bi nhan ban la mot
#:    con so se lech, va lech kieu do khong lam do phep kiem nao ca.
#:
#: ⛔ Chi `ngan_sach` — khong phai `features`, `executor` hay `gia`. Mot app khac
#:    duoc biet ngan sach la bao nhieu; no khong duoc biet model nay chay the nao.
#:    Them mot dong vao day la mot QUYET DINH KIEN TRUC: phai sua CA HAI phia,
#:    o day va o `APP_DUOC_DUNG_APP` trong `tools/lint_app_contract.py`.
BE_MAT_CONG_KHAI = {
    ("apps.ltt_llm", "ngan_sach"),
}
