"""
test_849 — nút Dừng phải ăn ở **MỌI** biên trạng thái, không chỉ lúc đang phát.

Hạng mục P10 ghi rõ: *"tra tấn: … **huỷ ở từng biên trạng thái**"*. Một lượt V3
đi qua nhiều biên, và chỉ một trong số đó có người canh:

```
STREAMING  ->  TOOL_REQUESTED  ->  AWAITING_APPROVAL  ->  TOOL_RUNNING
                                        (nguoi bam Duyet)
                                -> WAITING_BACKGROUND  ->  TOOL_RESULT_READY
                                        (job xong, dong_bo danh thuc)
```

## 🔴 Vì sao biên "đang chờ" mới là biên đáng ngờ

`LUOT.dung()` làm hai việc, và **cả hai đều trượt** khi lượt đang chờ:

```
ex.status in ("streaming", "queued")  ->  lat CSDL      # vong da xong -> KHONG lat
dang_chay.yeu_cau_dung(ex.id)         ->  co trong RAM  # luong da thoat -> KHONG tim thay
```

Luồng nền gọi `dang_chay.ket_thuc()` ở `finally` khi vòng kết thúc, nên sổ
`_SO` không còn khoá ấy. Và lần chạy tiếp gọi `dang_chay.bat_dau()`, hàm này
**ghi đè** một `LuotDangChay` mới — tức một `threading.Event` **mới, đã xoá**.

⇒ Giả thuyết: bấm Dừng lúc chờ duyệt là một **no-op im lặng**, và lượt vẫn chạy
  tiếp khi được duyệt — tiêu thêm tiền sau khi người dùng bảo dừng.

## ⭐ Máy trạng thái ĐÃ có chỗ cho việc này

`dieu_phoi.py` khai `AWAITING_APPROVAL -> CANCELLED` và
`WAITING_BACKGROUND -> CANCELLED` là chuyển **hợp lệ**. Chỗ để ghi nhận đã có
sẵn; chỉ là không ai ghi vào đó.

⛔ Nên bản vá đúng **không** phải thêm một cột hay một cờ mới. Nó là dùng đúng
   cái chuyển trạng thái đã khai — và khi ấy `nen_chay_tiep` tự đúng theo, vì
   `CANCELLED` không thuộc `CHO_DUOC`.

## ⚠️ Mỗi mệnh đề ở đây đi kèm một ĐỐI CHỨNG

Bẫy 31 hình thái 3: một phép kiểm có thể xanh vì **chính mã đang kiểm** làm cho
tập hợp rỗng. `nen_chay_tiep` trả `False` vì **bốn** lý do khác nhau; một phép
kiểm chỉ đòi `False` sẽ xanh ngay cả khi nút Dừng chẳng làm gì, miễn là có một
phiếu chưa quyết còn treo.

⇒ Nên mỗi ca huỷ đều có một ca **không huỷ** chạy trên cùng dữ liệu, và ca ấy
  phải ra `True`. Không có nó thì màu xanh không nói lên điều gì.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import dieu_phoi as DP
from apps.chatltt.services import luot as LUOT
from apps.chatltt.services import luot_v3 as V3
from apps.chatltt.services import luu_run as LR
from apps.chatltt.services import su_kien as S

U = "u-chu"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    gen = get_session()
    s = next(gen)
    yield s
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


def _dung_lai_canh(db, trang_thai: str):
    """Dựng một run V3 **thật** đang đứng ở `trang_thai`, kèm execution đầu.

    Trả `(run_row, ex)`. Không có phiếu duyệt và không có job nào treo — nên
    `nen_chay_tiep` chỉ còn phụ thuộc **đúng một** thứ: trạng thái của run.
    Đó là điều làm cho các phép kiểm dưới đây có nghĩa.
    """
    from apps.chatltt.services import hoi_thoai as H

    hoi = H.tao_hoi_thoai(db, user_id=U, model_alias="ltt_llm")
    tin = H.them_thong_diep(db, user_id=U, conv_id=hoi.id, role="assistant",
                            blocks=[], status="queued")
    db.commit()

    run_row = LR.mo_run(db, user_id=U, conv_id=hoi.id, message_id=tin.id)
    run_row.trang_thai = trang_thai
    ex = S.mo_execution(db, message=tin, tool_name="chat", mode="stream")
    ex.run_id = run_row.id
    db.commit()
    return run_row, ex


# ── 0. Đối chứng: bộ dựng có thật sự dựng được một run CHẠY TIẾP ĐƯỢC không ──

@pytest.mark.parametrize("tt", sorted(DP.CHO_DUOC))
def test_DOI_CHUNG_khong_huy_thi_chay_tiep_duoc(db, tt):
    """🔴 Không có phép kiểm này thì mọi màu xanh dưới đây là xanh rỗng.

    Nếu `nen_chay_tiep` trả `False` sẵn trên dữ liệu này — vì thiếu một hàng,
    vì sai chủ sở hữu, vì bất cứ lý do nào **không phải** nút Dừng — thì các ca
    huỷ bên dưới xanh mà chẳng chứng minh gì.
    """
    run_row, _ex = _dung_lai_canh(db, tt)
    assert V3.nen_chay_tiep(db, user_id=U, run_id=run_row.id) is True, (
        f"bo dung khong tao duoc mot run chay tiep duoc o {tt} — "
        "moi phep kiem huy duoi day se xanh rong")


# ── 1. Mệnh đề trung tâm: Dừng ở biên CHỜ phải chặn được lần chạy tiếp ──────

@pytest.mark.parametrize("tt", sorted(DP.CHO_DUOC))
def test_dung_o_bien_cho_thi_KHONG_chay_tiep_nua(db, tt):
    """⛔ Người dùng bảo dừng ⇒ lượt không được tự chạy tiếp và tiêu thêm tiền.

    Đây là mệnh đề mà P10 đòi, và nó được phát biểu ở tầng **quyết định** chứ
    không ở tầng cờ: câu hỏi không phải *"cờ nào đã được đặt"* mà *"lượt này
    còn được phép chạy tiếp không"*.
    """
    run_row, ex = _dung_lai_canh(db, tt)
    LUOT.dung(db, user_id=U, execution_id=ex.id)
    assert V3.nen_chay_tiep(db, user_id=U, run_id=run_row.id) is False, (
        f"bam Dung o {tt} roi ma luot van chay tiep duoc")


@pytest.mark.parametrize("tt", sorted(DP.CHO_DUOC))
def test_dung_ghi_CANCELLED_vao_dung_cho_may_trang_thai_da_khai(db, tt):
    """⭐ Và nó phải ghi vào **chỗ đã có sẵn**, không vào một cờ mới.

    `dieu_phoi.py` đã khai `AWAITING_APPROVAL -> CANCELLED` và
    `WAITING_BACKGROUND -> CANCELLED`. Dùng đúng chỗ ấy thì mọi thứ đọc trạng
    thái run — kể cả thứ chưa viết — tự đúng theo. Thêm một cờ song song thì
    mỗi người đọc phải nhớ hỏi thêm một câu, và sẽ có người quên.
    """
    run_row, ex = _dung_lai_canh(db, tt)
    LUOT.dung(db, user_id=U, execution_id=ex.id)
    db.refresh(run_row)
    assert run_row.trang_thai == DP.CANCELLED


# ── 2. Đừng phá đường cũ ───────────────────────────────────────────────────

def test_run_DANG_CHAY_khong_bi_dung_bien_thanh_CANCELLED_oan(db):
    """⚠️ Bản vá chỉ được chạm các biên **CHỜ**.

    Một run đang ở `TOOL_RUNNING` có luồng thật đang chạy; đường dừng của nó là
    cờ trong tiến trình + phép kiểm ở `dong_su_kien`. Lật thẳng trạng thái ở
    đây là ghi đè lên thứ luồng ấy sắp ghi, và hai người ghi một ô thì ô ấy
    nói dối một trong hai.
    """
    run_row, ex = _dung_lai_canh(db, DP.TOOL_RUNNING)
    LUOT.dung(db, user_id=U, execution_id=ex.id)
    db.refresh(run_row)
    assert run_row.trang_thai == DP.TOOL_RUNNING


def test_luot_KHONG_phai_V3_van_dung_duoc_nhu_cu(db):
    """⛔ `LUOT.dung` dùng chung với đường chat thường (không có run).

    Đường suy biến phải giữ nguyên: `ex.run_id is None` thì không được nổ.
    """
    from apps.chatltt.services import hoi_thoai as H

    hoi = H.tao_hoi_thoai(db, user_id=U, model_alias="ltt_llm")
    tin = H.them_thong_diep(db, user_id=U, conv_id=hoi.id, role="assistant",
                            blocks=[], status="queued")
    db.commit()
    ex = S.mo_execution(db, message=tin, tool_name="chat", mode="stream")
    db.commit()
    assert ex.run_id is None

    ra = LUOT.dung(db, user_id=U, execution_id=ex.id)
    assert ra["status"] == "cancelled"


def test_khong_phai_chu_thi_khong_dung_duoc_run_nguoi_khac(db):
    """🔴 Bánh cóc IDOR: bản vá mở thêm một đường GHI, nên phải kiểm lại quyền.

    Trước bản vá, `dung()` chỉ ghi vào `ChatlttExecution` — và nó đã kiểm chủ sở
    hữu của hàng ấy. Sau bản vá nó ghi thêm vào `ChatlttRun`, một bảng **khác**.
    Cùng một phép kiểm quyền không tự nối sang bảng mới.
    """
    run_row, ex = _dung_lai_canh(db, DP.AWAITING_APPROVAL)
    from apps.chatltt.services import hoi_thoai as H

    with pytest.raises(H.KhongTimThay):
        LUOT.dung(db, user_id="u-nguoi-khac", execution_id=ex.id)
    db.refresh(run_row)
    assert run_row.trang_thai == DP.AWAITING_APPROVAL


# ── 3. Biên trong vòng lặp: bộ điều phối phải hỏi `nen_dung` ────────────────

def test_dieu_phoi_dung_giua_hai_vong(db):
    """Biên thứ ba: giữa hai vòng của chính bộ điều phối.

    ⭐ Ca này **đã** có người canh (`dieu_phoi.py` hỏi `nen_dung()`), nên nó là
      một phép kiểm **bánh cóc**, không phải một phát hiện. Nó ở đây để bản vá
      cho hai biên kia không lỡ tay gỡ mất biên này.
    """
    goi = {"lan": 0}

    def goi_model(_m, _t):
        goi["lan"] += 1
        return [{"type": "response.delta", "text": "xin chao"},
                {"type": "response.completed", "finish_reason": "stop"}]

    run = DP.chay(messages=[{"role": "user", "content": "chao"}], tools=[],
                  goi_model=goi_model, chay_tool=lambda *a, **k: None,
                  nen_dung=lambda: True)
    assert run.trang_thai == DP.CANCELLED
    assert goi["lan"] == 0, "da bao dung ma van goi model"
# ── 4. Huỷ rồi thì THẺ DUYỆT phải biến mất, không đứng đó chờ vô nghĩa ──────

def _xin_mot_phieu(db, run_row, step_id="st-1"):
    # ⛔ `step_id` phai KHAC nhau giua hai run: `xin_duyet` khu trung theo no va
    #    tra ve dung phieu cu neu trung — dung phep kiem "hai run" se do vi mot
    #    ly do khong lien quan gi toi ban va.
    from apps.chatltt.services import duyet as D

    return D.xin_duyet(db, user_id=U, run_id=run_row.id, step_id=step_id,
                       tool_name="image.ltt", doi_so={"prompt": "mot con meo"},
                       policy_class="PAID", bao_gia_credit=8,
                       phien_ban_gia="thu-v0", bam_trung="b-1")


def test_DOI_CHUNG_chua_huy_thi_phieu_VAN_hien(db):
    """🔴 Không có dòng này thì phép kiểm dưới xanh trên hư không.

    `dang_cho` trả rỗng vì **ba** lý do khác nhau (không có phiếu · đã quyết ·
    hết hạn). Một phép kiểm chỉ đòi rỗng sẽ xanh kể cả khi bản vá chẳng làm gì.
    """
    run_row, _ex = _dung_lai_canh(db, DP.AWAITING_APPROVAL)
    _xin_mot_phieu(db, run_row)
    db.commit()
    from apps.chatltt.services import duyet as D
    assert len(D.dang_cho(db, user_id=U, run_id=run_row.id)) == 1


def test_huy_run_thi_phieu_duyet_KHONG_con_hien(db):
    """⛔ Trạng thái đúng mà giao diện sai thì người dùng vẫn gặp một sản phẩm hỏng.

    ## Cái hụt mà bản vá "huỷ ở biên chờ" để lại

    Sau khi huỷ, `ChatlttRun.trang_thai == CANCELLED` — đúng. Nhưng
    `ChatlttApproval.quyet_dinh` vẫn là `CHO`, nên thẻ duyệt **vẫn hiện**. Người
    dùng bấm "Duyệt", `_quyet` chạy trót lọt, rồi `nen_chay_tiep` trả `False` và
    **không có gì xảy ra** — không kết quả, không lời giải thích.

    ⭐ Vá ở phía ĐỌC chứ không phía GHI, theo đúng lý lẽ đã viết trong bản vá
      kia: một cờ song song thì **mỗi** người đọc phải nhớ hỏi thêm một câu, và
      sẽ có người quên. Lọc một lần trong `dang_cho` thì mọi người đọc — kể cả
      người chưa được viết — tự đúng theo.
    """
    run_row, ex = _dung_lai_canh(db, DP.AWAITING_APPROVAL)
    _xin_mot_phieu(db, run_row)
    db.commit()

    LUOT.dung(db, user_id=U, execution_id=ex.id)
    from apps.chatltt.services import duyet as D
    assert D.dang_cho(db, user_id=U, run_id=run_row.id) == []


def test_huy_MOT_run_khong_lam_bien_mat_phieu_cua_run_KHAC(db):
    """⚠️ Đối chứng ngược: một bộ lọc quá tay cũng làm phép kiểm trên xanh.

    Lọc sạch mọi phiếu thì `dang_cho` luôn rỗng, và mệnh đề trên vẫn đạt. Phép
    kiểm này là thứ phân biệt *lọc đúng cái đã huỷ* với *lọc hết*.
    """
    a_run, a_ex = _dung_lai_canh(db, DP.AWAITING_APPROVAL)
    b_run, _b_ex = _dung_lai_canh(db, DP.AWAITING_APPROVAL)
    _xin_mot_phieu(db, a_run, step_id="st-a")
    _xin_mot_phieu(db, b_run, step_id="st-b")
    db.commit()

    LUOT.dung(db, user_id=U, execution_id=a_ex.id)
    from apps.chatltt.services import duyet as D
    assert D.dang_cho(db, user_id=U, run_id=a_run.id) == []
    assert len(D.dang_cho(db, user_id=U, run_id=b_run.id)) == 1
    # ⭐ Và danh sach KHONG loc theo run cung phai con dung mot phieu.
    assert len(D.dang_cho(db, user_id=U)) == 1
