r"""U-09 — PHIÊN BẢN NGHE THỬ SUY RA, và công cụ dựng hết một lượt.

## Chú thích cũ đã mô tả rất chính xác một thứ nó không cưỡng chế

Ở đúng chỗ `PHIEN_BAN` được gõ tay, chú thích cũ viết:

    "ĐỔI CÂU TRÊN THÌ PHẢI ĐỔI CHUỖI NÀY … Không đổi phiên bản = khách nghe câu
     **cũ** trong khi mã nói câu mới, và không ai phát hiện ra vì cả hai đều là
     tiếng nói bình thường."
    "⚠️ Nó cũng phải đổi khi `PHIEN_BAN_THAM_SO` đổi."

⭐ Một chú thích nói *"phải nhớ làm X"* là một chú thích thừa nhận X sẽ bị quên.
   Và ở đây cái giá của việc quên đã được viết ra bằng chữ: **hỏng lặng lẽ,
   không có triệu chứng nào để lần**.

⇒ Câu trả lời đúng không phải một chú thích to hơn, mà là **gỡ khả năng quên**.
  `PHIEN_BAN` nay là băm của `(CAU_NGHE_THU, PHIEN_BAN_THAM_SO)`.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


# ── 1. Phiên bản SUY RA, không gõ tay ───────────────────────────────────────

def test_PHIEN_BAN_khong_con_la_hang_so_go_tay():
    """⛔ Đọc AST. Một phép khớp chuỗi sẽ báo động trên chính đoạn chú thích
    **trích dẫn** hằng số cũ để giải thích vì sao nó bị bỏ."""
    from apps.ltt_voice import nghe_thu

    cay = ast.parse(pathlib.Path(nghe_thu.__file__).read_text(encoding="utf-8"))
    gan = [n for n in cay.body
           if isinstance(n, (ast.Assign, ast.AnnAssign))
           and "PHIEN_BAN" in ast.unparse(n).split("=")[0]]
    assert gan, "khong tim thay phep gan PHIEN_BAN"
    assert not any(isinstance(getattr(n, "value", None), ast.Constant)
                   for n in gan), (
        "`PHIEN_BAN` van la mot hang so go tay — no se khong doi khi cau doc "
        "thu hoac PHIEN_BAN_THAM_SO doi")


def _van_tay(bang: dict, tham_so: str) -> str:
    """Dựng lại vân tay từ ĐÚNG những đầu vào mà sản phẩm dùng."""
    import hashlib
    return "v2-" + hashlib.sha256(
        ("|".join([f"{lan}={cau}" for lan, cau in sorted(bang.items())]
                  + [tham_so])).encode("utf-8")).hexdigest()[:12]


def test_doi_CAU_NGHE_THU_thi_PHIEN_BAN_DOI():
    """🔴 Đây là mệnh đề chính. Không có nó thì khách nghe câu **cũ** trong khi
    mã nói câu mới — và cả hai đều là tiếng nói bình thường, nên không ai phát
    hiện ra.

    ⚠️ VIẾT LẠI 2026-09-10 (Q121), và lý do đáng ghi. Bản cũ chốt **công thức**:
       `PHIEN_BAN == bam(CAU_NGHE_THU, tham_so)`. Khi nghe thử có thêm câu thứ
       hai theo làn (`CAU_THEO_LAN`), công thức đổi và phép kiểm đỏ — nhưng nó
       đỏ vì **tập hợp rộng ra**, không vì một hồi quy.

    ⛔ Và cách "sửa" hiển nhiên — gõ lại công thức mới — sẽ giữ nguyên điểm yếu
       gốc: nó chốt *cách tính*, không chốt *điều phải đúng*. Ngày thêm làn thứ
       ba nó lại đỏ y hệt.

    ⭐ Nên bản này chốt MỆNH ĐỀ và bất biến với số làn: **đổi câu của BẤT KỲ làn
       nào thì vân tay phải đổi.** Nó khó xanh hơn bản cũ, không dễ hơn — bản cũ
       chỉ canh một câu, bản này canh mọi câu.
    """
    from apps.ltt_voice import nghe_thu

    ts = nghe_thu._phien_ban_tham_so()
    goc = dict(nghe_thu.CAU_THEO_LAN)
    assert nghe_thu.PHIEN_BAN == _van_tay(goc, ts), (
        "PHIEN_BAN khong phai bam cua (moi cau theo lan, tham_so)")

    assert nghe_thu.CAU_NGHE_THU in goc.values(), (
        "cau tieng Viet khong con nam trong bang — cap nhat phep kiem nay")

    for lan in goc:
        doi = dict(goc, **{lan: goc[lan] + " "})
        assert _van_tay(doi, ts) != nghe_thu.PHIEN_BAN, (
            f"doi cau lan {lan!r} KHONG lam doi khoa — tep nghe thu cu se duoc "
            f"phuc vu mai mai")


def test_doi_PHIEN_BAN_THAM_SO_thi_PHIEN_BAN_DOI():
    """⚠️ Vế thứ hai, và nó là vế **không ai từng cưỡng chế**: cùng một câu
    sinh bằng hai bộ tham số engine là hai tệp âm thanh khác nhau."""
    import hashlib

    from apps.ltt_voice import nghe_thu

    bang = dict(nghe_thu.CAU_THEO_LAN)
    a = _van_tay(bang, "ltt-voice-2026-08-30a")
    b = _van_tay(bang, "ltt-voice-2026-12-01z")
    assert a != b


def test_bam_MSGID_GOC_chu_khong_bam_ban_DICH():
    """⛔ Bản dịch phụ thuộc ngôn ngữ của lượt gọi. Băm nó cho **hai khoá khác
    nhau cho cùng một giọng**, tuỳ ai chạm vào vòng bảo trì trước."""
    from apps.ltt_voice import nghe_thu

    cay = ast.parse(pathlib.Path(nghe_thu.__file__).read_text(encoding="utf-8"))
    gan = next(n for n in cay.body
               if isinstance(n, (ast.Assign, ast.AnnAssign))
               and "PHIEN_BAN" in ast.unparse(n).split("=")[0]
               and "sha256" in ast.unparse(n))
    ma = ast.unparse(gan)
    # `CAU_THEO_LAN` chua chinh `CAU_NGHE_THU` (msgid goc) — chap nhan ca hai
    # ten, vi cai phai chot la "bam msgid GOC", khong phai ten bien nao.
    assert "CAU_NGHE_THU" in ma or "CAU_THEO_LAN" in ma, ma
    assert "_t(" not in ma and "_t (" not in ma, (
        "dang bam ban DICH — khoa se doi theo ngon ngu")


def test_thieu_sidecar_van_cho_MOT_phien_ban_ON_DINH():
    """⛔ `"?"` là một giá trị **ổn định**, không phải một lỗi.

    Nếu nhánh lùi trả một thứ đổi mỗi lượt (thời gian, uuid) thì mỗi lần khởi
    động lại sinh một khoá mới, và kho nở ra vô hạn những tệp không ai đọc.
    """
    from apps.ltt_voice import nghe_thu

    a = nghe_thu._phien_ban_tham_so()
    b = nghe_thu._phien_ban_tham_so()
    assert a == b and a, "gia tri tham so KHONG on dinh giua hai luot goi"


def test_khoa_mau_MANG_phien_ban():
    from apps.ltt_voice import nghe_thu
    assert nghe_thu.PHIEN_BAN in nghe_thu.khoa_mau("Minh Duc")


# ── 2. Công cụ dựng hết một lượt ────────────────────────────────────────────

CC = GOC / "tools/dung_nghe_thu.py"


def test_cong_cu_TON_TAI_va_bien_dich_duoc():
    ast.parse(CC.read_text(encoding="utf-8"))


def test_cong_cu_TU_TU_CHOI_khi_may_ban():
    """Một lượt dựng 20 tệp là 20 lượt GPU. Chồng nó lên một lượt gate làm gate
    ra kết quả **sai**, không chỉ chậm."""
    src = CC.read_text(encoding="utf-8")
    assert "_may_ban" in src
    assert "Win32_Process" in src, (
        "phai hoi Win32_Process — `ps` cua Git Bash KHONG thay tien trinh Windows")
    assert "--bo-qua-kiem-may" in src, "phai co duong thoat co y thuc"


def test_cong_cu_KHONG_dung_ca_luot_khi_MOT_giong_hong():
    """⛔ Một giọng hỏng không được làm 19 giọng còn lại không có tệp — đó là
    biến một sự cố nhỏ thành một sự cố lớn."""
    cay = ast.parse(CC.read_text(encoding="utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "main")
    vong = [n for n in ast.walk(ham) if isinstance(n, ast.For)]
    assert any(any(isinstance(t, ast.Try) for t in ast.walk(v)) for v in vong), (
        "vong dung khong bat loi tung giong — mot giong hong se dung ca luot")


def test_cong_cu_THOAT_KHAC_0_khi_co_giong_hong():
    """⛔ In ra rồi thoát 0 là cách một lỗi đi qua một đường ray tự động mà
    không ai thấy. Cùng bài học với `check_ruff` in "dat moc" rồi thoát 1: mã
    thoát là thứ máy đọc, dòng chữ là thứ người đọc."""
    cay = ast.parse(CC.read_text(encoding="utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "main")
    tra = [ast.unparse(n) for n in ast.walk(ham) if isinstance(n, ast.Return)]
    assert any("hong" in t and "1" in t for t in tra), (
        f"`main` khong tra ma thoat khac 0 khi co giong hong: {tra}")


def test_vong_bao_tri_VAN_GIU_tran_ba_giong():
    """⭐ Công cụ này **không** thay vòng bảo trì, và trần 3/giờ ở đó phải giữ.

    Trần ấy đúng cho vòng bảo trì vì nó chạy **cùng tiến trình** với worker
    job. Gỡ nó "vì nay đã có công cụ" là bỏ đi lý do nó tồn tại — hai thứ giải
    hai bài toán khác nhau: *dựng bao nhiêu* và *dựng lúc nào*.
    """
    from apps.ltt_voice import nghe_thu
    assert nghe_thu.MOI_LUOT_TOI_DA <= 3


@pytest.mark.parametrize("co", ["--tat-ca", "--bo-qua-kiem-may"])
def test_cong_cu_khai_du_hai_co(co):
    """DOC AST, KHONG IMPORT.

    Kho nay da tra gia mot lan: mot module trong `tools/` doi `sys.stdout`
    thanh mot `TextIOWrapper`, va khi no bi thu gom rac no dong luon buffer
    that — lam vo phien pytest o mot cho khong lien quan gi toi no. Bai hoc da
    ghi lai: **doc AST thay vi import** khi chi can biet mot tep khai gi.
    """
    cay = ast.parse(CC.read_text(encoding="utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "main")
    co_khai = {c.value for n in ast.walk(ham)
               if isinstance(n, ast.Call)
               and ast.unparse(n.func).endswith("add_argument")
               for c in n.args if isinstance(c, ast.Constant)}
    assert co in co_khai, f"`main` khong khai co `{co}` (co: {sorted(co_khai)})"
