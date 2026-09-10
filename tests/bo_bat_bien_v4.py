"""Bo BAT BIEN V4 — chay sau moi lan sua, va truoc khi dong mot pha.

`V4_TEST_REVIEW_PROTOCOL.md` tang 2 doi mot bo nhanh phu it nhat muoi hai bat
bien. Tep nay la **ban khai** cua bo do: dau la bat bien, dau la tep chung minh
no, va vi sao chia lam hai vong.

## Hai vong, vi mot con so do duoc

    VONG NHANH  ~12,5 giay   chay sau MOI lan sua
    VONG DU     ~80 giay     chay truoc khi dong mot pha

Do that (2026-09-03, may nay):

    test_400  1,8s   test_401  0,6s   test_404  1,2s   test_416  0,5s
    test_421  3,2s   test_425  0,2s   test_426  4,1s   test_427  0,6s
    test_428  1,3s
    ────────────────────────────────────────────────────────────────
    test_417  65,9s  <- MOT tep chiem 84% thoi gian cua ca bo

⚠️ `test_417` phu **vo hieu ha nguon**, mot bat bien bat buoc cua tang 2. No
   khong bi loai; no bi tach. Ly do la mot bai hoc cu cua kho nay: mot bo kiem
   80 giay khong duoc chay sau moi lan sua, no duoc chay **mot lan cuoi ngay**,
   va luc do no bao mot loi da nam trong muoi lan sua.

   Mot bo 12 giay duoc chay that. Do la ca khac biet.

⛔ Va chieu nguoc lai phai noi thang: **vong nhanh KHONG phai bang chung day du.**
   Dong mot pha ma chi chay vong nhanh la bo qua vo hieu ha nguon — dung cho ma
   pha 16 cua V2 tim ra mot khiem khuyet that (mot giai doan chay lai nhung cac
   giai doan an theo no van giu ket qua cu, va lan chay ket thuc voi mot ban
   long tieng tron lan hai lan chay).
"""
from __future__ import annotations

#: Bat bien tang 2 -> tep chung minh no. Khoa la ten trong
#: `V4_TEST_REVIEW_PROTOCOL.md`; gia tri la tep test that.
#:
#: ⚠️ **`V4_TEST_REVIEW_PROTOCOL.md` KHONG co trong kho** (do 2026-09-06). No
#:    duoc nhac o ba ban bao cao va o chinh docstring nay, nhung khong tep nao
#:    ton tai. Tuc "khoa la ten trong protocol" hien la mot rang buoc **khong ai
#:    kiem duoc** — khac han rang buoc hai chieu BAT_BIEN <-> VONG_DU ma
#:    `test_428` cuong che that.
#:
#: ⭐ Ghi ra thay vi im lang them khoa: mot rang buoc chi ton tai trong mot cau
#:    van la thu se bi vi pham ma khong ai biet, va nguoi doc sau xung dang biet
#:    khoa nao co goc ro rang va khoa nao do mot phien tu dat.
#:
#: ⭐ Ban do nay la mot rang buoc HAI CHIEU: xoa mot tep thi mot bat bien mat
#:    nguoi chung minh, va `test_428` do. Them mot bat bien ma khong co tep thi
#:    cung do.
BAT_BIEN: dict[str, str] = {
    "queue SSOT":                "tests/test_400_asv_bat_bien_thi_hanh.py",
    "one billing owner":         "tests/test_400_asv_bat_bien_thi_hanh.py",
    "owner isolation":           "tests/test_401_asv_ranh_gioi_va_artifact.py",
    "credential scope":          "tests/test_404_pham_vi_khoa_api.py",
    "artifact promotion":        "tests/test_401_asv_ranh_gioi_va_artifact.py",
    "fingerprint/cache":         "tests/test_416_asv_van_tay_engine.py",
    "cancellation":              "tests/test_400_asv_bat_bien_thi_hanh.py",
    "downstream invalidation":   "tests/test_417_asv_vo_hieu_ha_nguon.py",
    "no orphan child":           "tests/test_400_asv_bat_bien_thi_hanh.py",
    "provider ambiguity":        "tests/test_400_asv_bat_bien_thi_hanh.py",
    "no private AI client":      "tests/test_421_asv_tach_khoi_di_san.py",
    "heavy-model test isolation": "tests/test_428_asv_v4_rao_chan_nang.py",
    # V4 them ba cai nua, deu la hop dong chu khong phai hanh vi runtime.
    "product contract frozen":   "tests/test_425_asv_v4_hop_dong_san_pham.py",
    "capability inventory true": "tests/test_426_asv_v4_kiem_ke_nang_luc.py",
    "no second queue/scheduler": "tests/test_427_asv_v4_kien_truc.py",
    # 🔴 Hai cai duoi them 2026-09-06, va ca hai la BAT BIEN SAN PHAM chu
    #    khong phai chi tiet cai dat — do la tieu chuan de vao bang nay.
    #
    #    "busy is not failure": mot tin hieu BAN tu mot tai nguyen dung chung
    #    khong duoc bien thanh that bai cuoi cung. Vi pham no thi job hong, va
    #    `giong_noi.MayBan` ghi thang hau qua: **TRU CREDIT cho viec chua tung
    #    chay**. Da vi pham that tren duong AI cho toi 06/09.
    #
    #    "repair smallest safe scope": mot doan bi bao hong phai duoc lam lai o
    #    giai doan SOM NHAT sua duoc no, va **chi doan do**. Vi pham theo mot
    #    chieu la dich lai ca phim de sua mot cau; theo chieu kia la doc lai mot
    #    cau dich sai va giao dung y sai do.
    "busy is not failure":       "tests/test_434_asv_v4_ranh_gioi_ai.py",
    "repair smallest safe scope": "tests/test_454_asv_v4_vong_sua.py",
}

#: Chay sau MOI lan sua. ~12,5 giay.
VONG_NHANH: tuple[str, ...] = (
    "tests/test_400_asv_bat_bien_thi_hanh.py",
    "tests/test_401_asv_ranh_gioi_va_artifact.py",
    "tests/test_404_pham_vi_khoa_api.py",
    "tests/test_416_asv_van_tay_engine.py",
    "tests/test_421_asv_tach_khoi_di_san.py",
    "tests/test_425_asv_v4_hop_dong_san_pham.py",
    "tests/test_426_asv_v4_kiem_ke_nang_luc.py",
    "tests/test_427_asv_v4_kien_truc.py",
    "tests/test_428_asv_v4_rao_chan_nang.py",
    # Do 2026-09-06: test_434 ~1,0s | test_454 ~2,0s. Du re cho vong NHANH, va
    # ca hai phu bat bien san pham nen chung thuoc ve cho duoc chay that.
    "tests/test_434_asv_v4_ranh_gioi_ai.py",
    "tests/test_454_asv_v4_vong_sua.py",
)

#: Chay TRUOC KHI DONG MOT PHA. ~80 giay. Vong nhanh + phan cham.
VONG_DU: tuple[str, ...] = VONG_NHANH + (
    "tests/test_417_asv_vo_hieu_ha_nguon.py",
)


def lenh(vong: tuple[str, ...]) -> str:
    return "python -m pytest " + " ".join(vong) + " -q"
