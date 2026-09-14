"""test_1239 — SÀN `max_tokens` theo (model x mức suy nghĩ). L-02, 13/09/2026.

## Lỗi mà bộ này canh

Model nhà trả về **rỗng** (`content` = "", `finish_reason` = "length") ở khoảng
một nửa số lượt khi `max_tokens` thấp. Nguyên nhân không phải model hỏng: phần
**suy nghĩ** tiêu cùng một ngân sách với phần trả lời, nên một trần thấp bị
tiêu hết vào suy nghĩ và không còn chữ nào cho câu trả lời. Khách vẫn bị tính
tiền cho token đã sinh.

Chặn ở cửa vào rẻ hơn nhiều lần so với giải thích sau khi đã thu tiền.

## ⛔ Vì sao phải chốt, chứ không chỉ để mã chạy đúng

Ba mệnh đề dưới đây **không** được mã nào cưỡng chế nếu bộ này biến mất:

1. Sàn nằm ở `ngan_sach.py`, enum mức nằm ở `manifest.py`, enum model nằm ở
   `platform_core/llm/canonical.py` — **ba tệp**. Thêm một mức hay một model ở
   một nơi mà quên nơi kia thì lượt hợp lệ rơi vào nhánh mặc định im lặng.
2. Sàn phải **≤ mặc định của mọi cửa**. Vi phạm ⇒ khách không khai
   `max_tokens` bị từ chối **mọi lượt** — trần nằm dưới sàn, đúng hình dạng lỗi
   `test_448` đã bắt ở tầng khác.
3. Sàn phải theo **model**, không phải một bảng chung. Đo 13/09 cho cùng một câu
   hỏi ở `max_tokens=1500`: `ltt-3.5` tiêu low 206 / medium 377, `ltt-3.8` tiêu
   63 ở mọi mức. Một bảng chung lấy số của model tốn nhất sẽ **phạt oan** lượt
   hợp lệ của model kia.
"""
import pytest

from apps.ltt_llm import features
from apps.ltt_llm.manifest import MANIFEST
from apps.ltt_llm.ngan_sach import (NGHI_MAC_DINH, SAN_TOKEN_RA_THEO_NGHI,
                                    TOKEN_RA_MAC_DINH, san_token_ra)
from platform_core.llm.canonical import MODEL_HOP_LE


def _enum_muc() -> list:
    return list(MANIFEST.tools[0].params_schema["reasoning_effort"]["values"])


def _xin(model, max_tokens, effort=None):
    p = {"model": model, "max_tokens": max_tokens,
         "messages": [{"role": "user", "content": "2+2?"}]}
    if effort is not None:
        p["reasoning_effort"] = effort
    return p


# ── 1. Ba tệp phải khai cùng một tập ────────────────────────────────────────

@pytest.mark.parametrize("muc", _enum_muc())
def test_moi_muc_trong_enum_deu_co_san(muc):
    """Mức nào khách gửi được thì mức đó phải có sàn ĐO ĐƯỢC, không rơi mặc định.

    Nếu một mức mới thêm vào enum mà quên bảng sàn, `san_token_ra` vẫn trả về
    một số (sàn của `NGHI_MAC_DINH`) — **không lỗi, không cảnh báo**. Bộ này là
    thứ duy nhất phát hiện ra.
    """
    for model, bang in SAN_TOKEN_RA_THEO_NGHI.items():
        assert muc in bang, f"{model} thieu san cho muc {muc!r}"


@pytest.mark.parametrize("model", MODEL_HOP_LE)
def test_moi_model_ban_ra_deu_tra_loi_duoc(model):
    """Model nào bán ra thì `san_token_ra` phải trả số dương, không ném.

    ⭐ KHÔNG đòi model phải có mặt trong bảng: một model mới **không** thừa
       hưởng hình phạt của model tốn nhất cho tới khi ai đó đo nó. Điều bộ này
       cưỡng chế chỉ là: không có model nào làm hàm ném ra ngoài.
    """
    for muc in _enum_muc():
        s = san_token_ra(model, muc)
        assert isinstance(s, int) and s > 0


def test_nghi_mac_dinh_khop_manifest():
    """`NGHI_MAC_DINH` và `default` của manifest là HAI chỗ khai một điều.

    Lệch nhau ⇒ sàn áp cho một mức, còn máy B chạy một mức khác.
    """
    assert NGHI_MAC_DINH == MANIFEST.tools[0].params_schema[
        "reasoning_effort"]["default"]


def test_model_la_le_tra_ve_san_nhe_chu_khong_nem():
    """Model lạ ⇒ sàn nhẹ. `kiem_tham_so` đã chặn enum model TRƯỚC hàm này, nên
    một `KeyError` ở đây chỉ có thể thành 500 cho lượt lẽ ra chỉ cần 400."""
    assert san_token_ra("model-chua-ton-tai", "low") > 0
    assert san_token_ra(None, None) > 0
    assert san_token_ra("ltt-3.5", "muc-la") == san_token_ra(
        "ltt-3.5", NGHI_MAC_DINH)


# ── 2. Sàn không được cao hơn trần của bất kỳ cửa nào ───────────────────────

@pytest.mark.parametrize("cua,mac_dinh", sorted(TOKEN_RA_MAC_DINH.items()))
def test_san_khong_cao_hon_mac_dinh_cua(cua, mac_dinh):
    """🔴 TRẦN KHÔNG ĐƯỢC NẰM DƯỚI SÀN.

    Khách không khai `max_tokens` thì cửa điền mặc định của chính nó. Mặc định
    ấy mà thấp hơn sàn ⇒ **mọi** lượt không khai đều bị 400, ngay cả lượt hoàn
    toàn hợp lệ. Hiện `sync` = 1024 và sàn cao nhất cũng = 1024: sát đúng một
    token, nên hạ mặc định một chút là vỡ.
    """
    cao_nhat = max(s for bang in SAN_TOKEN_RA_THEO_NGHI.values()
                   for s in bang.values())
    assert cao_nhat <= mac_dinh, (
        f"cua {cua!r} mac dinh {mac_dinh} < san cao nhat {cao_nhat}: "
        f"luot khong khai max_tokens se bi tu choi het")


# -- 3. Cua vao thuc su dung san cua DUNG model -----------------------------

def _cua(p):
    """Dung thu tu ma `server/api/chat.py` goi: hinh dang truoc, san sau."""
    sach = features.kiem_tham_so(p)
    features.kiem_san_token_ra(sach)
    return sach


def test_kiem_tham_so_KHONG_duoc_ap_san():
    """CHOT THU TU, o tang cau truc.

    `kiem_tham_so` chay TRUOC 413 o cua dong bo. Gop san vao no => mot hoi thoai
    65K token xin tran thap nhan **400 thay vi 413**, va Codex/Claude Code mat
    duong tu nen hoi thoai. Phep kiem nay do ngay khi ai do gop lai cho gon.

    `tests/test_259_cua_dong_bo.py` chot cung mot dieu o tang HTTP that. Hai
    tang vi mot minh tang nao cung bi di vong qua duoc.
    """
    features.kiem_tham_so(_xin("ltt-3.5", 1, "medium"))     # khong duoc nem


def test_cua_vao_tu_choi_tran_duoi_san():
    _san = san_token_ra("ltt-3.5", "medium")
    with pytest.raises(features.ThamSoSai) as e:
        _cua(_xin("ltt-3.5", _san - 1, "medium"))
    noi = str(e.value)
    assert "reasoning_effort='none'" in noi, (
        "thong bao phai chi ra LOI RA: ha max_tokens la nut SAI, "
        "tat suy nghi moi la nut dung")
    assert str(_san) in noi


def test_cua_vao_nhan_dung_tai_san():
    _cua(_xin("ltt-3.5", san_token_ra("ltt-3.5", "medium"), "medium"))


def test_san_theo_model_khong_phat_oan_model_re():
    """MENH DE TRUNG TAM: cung `max_tokens`, cung muc, hai model KHAC ket qua.

    Xoa bang theo model va thay bang mot bang chung thi phep kiem nay do --
    dung nhu no phai the. Do 13/09: `ltt-3.8` tra loi DUNG o `max_tokens=100`
    voi `low` (63 token ra), nen tu choi no la tu choi mot luot hop le.
    """
    mt = san_token_ra("ltt-3.8", "low")
    assert mt < san_token_ra("ltt-3.5", "low"), (
        "phep kiem nay chi co nghia khi hai model co san KHAC nhau")
    _cua(_xin("ltt-3.8", mt, "low"))                        # nhan
    with pytest.raises(features.ThamSoSai):
        _cua(_xin("ltt-3.5", mt, "low"))                    # tu choi


def test_san_khong_phat_luot_100_token_cua_model_chua_thay_hong():
    """`max_tokens=100` la mot luot BINH THUONG, khong phai luot sai.

    Hang chuc phep kiem khap kho gui dung con so ay. San cua `ltt-3.8` dat theo
    "cho chac" (256) se bien tat ca thanh 400 -- mot cai phanh dat duoi nhu cau
    that, thu da ghi la *te hon khong co phanh*. Do duoc la 63 token.
    """
    for muc in _enum_muc():
        _cua(_xin("ltt-3.8", 100, muc))


def test_none_bi_TU_CHOI_va_loi_noi_ro_dung_cai_gi_thay_the():
    """`none` DA BI BO 14/09/2026 — va ca nay la ban viet lai, khong phai ban xoa.

    ⛔ Ban cu khang dinh dieu NGUOC LAI: *"loi ra `none` phai that su di duoc o
       mot tran ma `medium` tu choi"*. No dung khi `none` con trong hop dong.
       Chot 14/09 go `none` vi do duoc no lam sap chat luong dau ra: 2 token
       thay vi ~1180 tren cung mot de bai sinh dai. Giu ca cu la giu mot phep
       kiem luon do; xoa han la mat mot mat cua hop dong.

    ⭐ Nen menh de doi chieu: `none` phai bi TU CHOI, va loi phai **chi duong**
       — mot loi chi noi "sai" bat khach doan tiep la loi chua hanh dong duoc.
    """
    for m in ("ltt-3.5", "ltt-3.8"):
        thap = san_token_ra(m, "low")
        with pytest.raises(features.ThamSoSai) as e:
            _cua(_xin(m, thap, "none"))
        loi = str(e.value)
        assert "none" in loi, loi
        assert "low" in loi, f"loi khong chi duong sang muc thay the: {loi}"

    # doi chung: ba muc con lai VAN di duoc, neu khong thi ca tren vo nghia
    # (mot `kiem_tham_so` tu choi TAT CA cung lam no xanh).
    for muc in ("low", "medium", "xhigh"):
        _cua(_xin("ltt-3.5", san_token_ra("ltt-3.5", muc), muc))
