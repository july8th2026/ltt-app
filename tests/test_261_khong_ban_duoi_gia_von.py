"""
test_261 — ⛔ KHÔNG ĐƯỢC BÁN DƯỚI GIÁ VỐN. (MVP đợt 0.2)

Không mạng, không GPU.

⭐ VÌ SAO TỆP NÀY LÀ THỨ QUAN TRỌNG NHẤT CỦA CẢ ĐỢT 0

   Ngày 23/08/2026 đo được: nền tảng bán ảnh ở **45–57 % giá vốn**, cả bốn bậc
   model, suốt 22 ngày. Không ai chọn như vậy. `CREDIT_PER_IMAGE = 5` là một hằng
   số **không có cơ sở chi phí nào** — nó không sai lúc đặt, nó chỉ **không bao giờ
   được nhìn lại**, vì **không có gì để so với**.

   Sửa giá một lần thì chỉ chữa hôm nay. Tệp này chữa cả ngày mai: từ giờ, hạ giá
   xuống dưới giá vốn **phải là một hành động cố ý, có tên và có hạn**.

💡 ĐÂY LÀ CHỖ **TỰ NGHĨ** — ghi rõ vì nó là chỗ yếu nhất.

   Tra ba nguồn (LiteLLM · Lago · OpenMeter): cả ba đều **đo** chi phí và **hiện**
   biên lợi nhuận, nhưng **không nguồn nào chặn** việc đặt giá dưới giá vốn. Lý do
   của họ hợp lý: với một nền tảng thanh toán, bán dưới giá vốn là một **lựa chọn
   kinh doanh hợp lệ** (khuyến mãi, giá thâm nhập).

   Với ta thì khác, và khác ở đúng một điểm: giá dưới giá vốn ở đây **không phải do
   ai chọn**. Nên ta cần thứ họ không cần.
"""
from __future__ import annotations

import datetime as dt

import pytest

from platform_core import gia_von as G
from platform_core.registry import discover

#: Bán dưới giá vốn **được phép** — nhưng phải ký tên và có hạn.
#:
#: Khoá = "<app>/<tool>/<model>". Mỗi mục: `ly_do` (vì sao chấp nhận lỗ),
#: `chu` (ai quyết), `han_ra_lai` (ngày phải xem lại).
#:
#: ⛔ Danh sách này **không phải chỗ để làm cho test xanh**. Mỗi dòng ở đây là một
#:    khoản lỗ trên mỗi đơn hàng, và nó lớn dần theo doanh số.
#: ⏳ Các mục dưới đây là **khoản lỗ đang chạy thật**, khai ra ngày 23/08/2026.
#:    Bậc `pro` đã được ĐÓNG cùng ngày (chủ dự án chốt) nên nó không còn ở đây —
#:    đóng một bậc là cách xử lý dứt điểm hơn miễn trừ, và danh sách này ngắn đi
#:    chính là dấu hiệu việc đó đã làm thật.
#:    Chúng ở đây để khoản lỗ **được ghi nhận** thay vì vô hình — không phải để
#:    test xanh. Hạn 15/09: quá ngày đó mà chưa chốt giá thì test đỏ trở lại.
LO_CO_CHU_DICH: dict[str, dict] = {
    "taoanh/image.batch_generate/gemini-2.5-flash-image": {
        "ly_do": "Gia hien tai dat truoc khi co bang gia von; do 23/08 moi biet "
                 "no duoi gia von. Cho chu du an chot boi so (hoa von / bien 40% / "
                 "dong bac pro) — xem PHAN_TICH_MVP_2026-08-23.md muc 2.3.",
        "chu": "chu du an",
        "han_ra_lai": "2026-09-15",
    },
    "taoanh/image.batch_generate/gemini-3.1-flash-image": {
        "ly_do": "Gia hien tai dat truoc khi co bang gia von; do 23/08 moi biet "
                 "no duoi gia von. Cho chu du an chot boi so (hoa von / bien 40% / "
                 "dong bac pro) — xem PHAN_TICH_MVP_2026-08-23.md muc 2.3.",
        "chu": "chu du an",
        "han_ra_lai": "2026-09-15",
    },
    "taoanh/image.batch_generate/gemini-3.1-flash-lite-image": {
        "ly_do": "Gia hien tai dat truoc khi co bang gia von; do 23/08 moi biet "
                 "no duoi gia von. Cho chu du an chot boi so (hoa von / bien 40% / "
                 "dong bac pro) — xem PHAN_TICH_MVP_2026-08-23.md muc 2.3.",
        "chu": "chu du an",
        "han_ra_lai": "2026-09-15",
    },
    "taoanh/image.generate/gemini-2.5-flash-image": {
        "ly_do": "Gia hien tai dat truoc khi co bang gia von; do 23/08 moi biet "
                 "no duoi gia von. Cho chu du an chot boi so (hoa von / bien 40% / "
                 "dong bac pro) — xem PHAN_TICH_MVP_2026-08-23.md muc 2.3.",
        "chu": "chu du an",
        "han_ra_lai": "2026-09-15",
    },
    "taoanh/image.generate/gemini-3.1-flash-image": {
        "ly_do": "Gia hien tai dat truoc khi co bang gia von; do 23/08 moi biet "
                 "no duoi gia von. Cho chu du an chot boi so (hoa von / bien 40% / "
                 "dong bac pro) — xem PHAN_TICH_MVP_2026-08-23.md muc 2.3.",
        "chu": "chu du an",
        "han_ra_lai": "2026-09-15",
    },
    "taoanh/image.generate/gemini-3.1-flash-lite-image": {
        "ly_do": "Gia hien tai dat truoc khi co bang gia von; do 23/08 moi biet "
                 "no duoi gia von. Cho chu du an chot boi so (hoa von / bien 40% / "
                 "dong bac pro) — xem PHAN_TICH_MVP_2026-08-23.md muc 2.3.",
        "chu": "chu du an",
        "han_ra_lai": "2026-09-15",
    },
    "thumbnail/image.thumbnail/gemini-2.5-flash-image": {
        "ly_do": "Gia hien tai dat truoc khi co bang gia von; do 23/08 moi biet "
                 "no duoi gia von. Cho chu du an chot boi so (hoa von / bien 40% / "
                 "dong bac pro) — xem PHAN_TICH_MVP_2026-08-23.md muc 2.3.",
        "chu": "chu du an",
        "han_ra_lai": "2026-09-15",
    },
    "thumbnail/image.thumbnail/gemini-3.1-flash-image": {
        "ly_do": "Gia hien tai dat truoc khi co bang gia von; do 23/08 moi biet "
                 "no duoi gia von. Cho chu du an chot boi so (hoa von / bien 40% / "
                 "dong bac pro) — xem PHAN_TICH_MVP_2026-08-23.md muc 2.3.",
        "chu": "chu du an",
        "han_ra_lai": "2026-09-15",
    },
    "thumbnail/image.thumbnail/gemini-3.1-flash-lite-image": {
        "ly_do": "Gia hien tai dat truoc khi co bang gia von; do 23/08 moi biet "
                 "no duoi gia von. Cho chu du an chot boi so (hoa von / bien 40% / "
                 "dong bac pro) — xem PHAN_TICH_MVP_2026-08-23.md muc 2.3.",
        "chu": "chu du an",
        "han_ra_lai": "2026-09-15",
    },
}


def _cac_model(tool) -> list[str]:
    """Model mà tool này **thật sự** chạy được, suy từ `params_schema`.

    ⛔ Phải lọc theo `category` của `model_ref`. Lần chạy đầu tôi bỏ qua nó và bánh
    cóc báo nhầm 12 tổ hợp: một tool text khai `category="chat"` nhưng bộ
    lọc của tôi gom cả model **ảnh** của provider `gemini` rồi so giá bán một đoạn
    văn với giá vốn một tấm ảnh.

    Bài học nhỏ mà đắt: một bánh cóc báo nhầm sẽ bị người ta tắt đi, và lúc đó nó
    không còn bảo vệ cả những chỗ nó báo **đúng**.
    """
    from platform_core import providers as P

    ra: list[str] = []
    for spec in (tool.params_schema or {}).values():
        if not isinstance(spec, dict) or spec.get("type") != "model_ref":
            continue
        cat = spec.get("category")
        for pid in (spec.get("providers") or P.provider_ids()):
            for m in P.models_for(pid, cat):
                if getattr(m, "is_active", False) and m.id not in ra:
                    ra.append(m.id)
    return ra


def _gia_ban_mcredit(app, tool, model_id: str) -> int | None:
    """Giá bán MỘT đơn vị đầu ra, milli-credit. `None` nếu không tính được."""
    ham = app.manifest.credit_cost
    if not callable(ham):
        return None
    tham_so = {"model": model_id, "count": 1, "so_anh": 1, "scene_count": 1}
    for ten, spec in (tool.params_schema or {}).items():
        if isinstance(spec, dict) and "default" in spec and ten not in tham_so:
            tham_so[ten] = spec["default"]
    try:
        return int(ham(tham_so)) * G.MCREDIT_MOI_CREDIT
    except Exception:                                        # noqa: BLE001
        return None


def _khao_sat() -> list[tuple[str, int, int]]:
    """[(khoá, giá bán mcredit, giá vốn mcredit)] cho mọi tổ hợp tra được."""
    ra = []
    for app in discover():
        if app.error:
            continue
        for tool in (app.manifest.tools or []):
            for model_id in _cac_model(tool):
                if not G.co_gia(model_id):
                    continue                 # test_260 lo phan nay
                ban = _gia_ban_mcredit(app, tool, model_id)
                if ban is None:
                    continue
                try:
                    von = G.mot_anh(model_id)
                except G.KhongBietGiaVon:
                    continue                 # model khong sinh anh — ngoai pham vi
                ra.append((f"{app.slug}/{tool.name}/{model_id}", ban, von))
    return ra


# ═══════════════════════════ bánh cóc chính ════════════════════════════════
def test_KHONG_TO_HOP_NAO_ban_duoi_gia_von():
    """⛔ Bánh cóc chính. Đỏ nghĩa là: có một tổ hợp app/tool/model mà **mỗi đơn
    hàng làm ta mất tiền**, và mất càng nhiều khi bán càng chạy."""
    xau = []
    for khoa, ban, von in _khao_sat():
        if ban >= von or khoa in LO_CO_CHU_DICH:
            continue
        xau.append(
            f"{khoa}: ban {ban / 1000:.2f} cr < von {von / 1000:.2f} cr "
            f"(= {ban / von:.0%}, lo {(von - ban) / 10:.0f}d/don)")
    assert xau == [], (
        "BAN DUOI GIA VON:\n  " + "\n  ".join(xau) +
        "\n\nSua gia trong manifest, hoac khai vao LO_CO_CHU_DICH kem ly do + chu "
        "+ han_ra_lai neu day la mot lua chon co y.")


def test_co_khao_sat_duoc_it_nhat_mot_to_hop():
    """Bánh cóc cho chính bánh cóc: nếu `_khao_sat()` trả rỗng vì một thay đổi nào
    đó ở registry, test trên sẽ **luôn xanh** và không bảo vệ gì cả."""
    assert len(_khao_sat()) >= 4, "khong khao sat duoc to hop nao — banh coc dang mu"


# ═══════════════════════ miễn trừ phải ký tên và hết hạn ════════════════════
def test_moi_MIEN_TRU_LO_deu_co_ly_do_chu_va_han():
    for khoa, m in LO_CO_CHU_DICH.items():
        assert m.get("ly_do") and len(str(m["ly_do"]).split()) >= 5, f"{khoa}: ly do so sai"
        assert m.get("chu"), f"{khoa}: khong ai chiu trach nhiem"
        dt.date.fromisoformat(str(m.get("han_ra_lai")))


def test_MIEN_TRU_LO_qua_han_lam_test_DO():
    hom_nay = dt.date.today()
    qua_han = [k for k, m in LO_CO_CHU_DICH.items()
               if dt.date.fromisoformat(str(m["han_ra_lai"])) < hom_nay]
    assert qua_han == [], f"mien tru lo qua han, phai xem lai: {qua_han}"


def test_MIEN_TRU_chi_tro_toi_to_hop_CO_THAT():
    """Một miễn trừ trỏ vào tổ hợp không còn tồn tại là rác — và nó che mất việc
    danh sách này lẽ ra phải ngắn đi."""
    co_that = {k for k, _b, _v in _khao_sat()}
    thua = sorted(set(LO_CO_CHU_DICH) - co_that)
    assert thua == [], f"mien tru tro toi to hop khong ton tai: {thua}"


# ═══════════════════════ model nhà: nơi phép tính đảo chiều ═════════════════
def test_model_NHA_lai_dam_o_cung_muc_gia():
    """Cùng một giá bán, cùng một khách — khác nhau ở chỗ ảnh được vẽ ở đâu.

    Đây là lý do H37 không phải một tính năng thêm mà là **lối thoát của bài toán
    đơn vị kinh tế**: ở giá hoà vốn của Gemini, model nhà cho biên > 90 %."""
    von_gemini = G.mot_anh("gemini-2.5-flash-image")
    von_nha = G.mot_anh("hidream-o1")
    assert von_nha < von_gemini
    bien = (von_gemini - von_nha) / von_gemini
    # Ngưỡng 0,89 chứ không 0,90: số thật là 89,8 %. Đặt ngưỡng cao hơn số đo được
    # là ép số liệu cho vừa một câu chữ đã lỡ viết — đúng thứ cả dự án này chống.
    assert bien > 0.89, f"bien chi {bien:.0%} — kiem lai gia von model nha"


@pytest.mark.parametrize("che_do,tham_chieu", [("t2i", False), ("subject", True)])
def test_anhnoibo_ban_TREN_gia_von_o_ca_hai_che_do(che_do, tham_chieu):
    """App bán model nhà phải lãi ở **cả** chế độ, kể cả chế độ đắt gấp đôi."""
    app = [a for a in discover() if a.slug == "anhnoibo"][0]
    ban = int(app.manifest.credit_cost({"count": 1, "mode": che_do})) * G.MCREDIT_MOI_CREDIT
    von = G.mot_anh("hidream-o1", tham_chieu=tham_chieu)
    assert ban > von, f"che do {che_do}: ban {ban} <= von {von}"


# ═══════════════ LTT VOICE — đơn vị "một giây tiếng", không phải "một ảnh" ══
def test_ltt_voice_ban_TREN_gia_von_moi_giay_tieng():
    """🔴 Cho tới 01/09/2026 app này bán mà **không biết mình lãi hay lỗ**.

    `apps/ltt_voice/gia.py` tự thú điều đó ngay trong mã: *"Chưa đối chiếu được
    với giá vốn vì chưa có RTF đo thật (V1)"*. Nghĩa là `MCREDIT_MOI_GIAY = 200`
    là một hằng số **không có cơ sở chi phí nào** — đúng hình dạng của
    `CREDIT_PER_IMAGE = 5`, thứ đã chạy 22 ngày ở 45–57 % giá vốn mà không ai
    thấy, vì **không có gì để so với**.

    ⭐ `_khao_sat()` ở trên không bắt được nó, và không phải vì nó quên: nó gọi
       `G.mot_anh`, và voice **không bán theo ảnh**. Một bánh cóc chỉ bảo vệ
       được thứ nó nhìn thấy, và một đơn vị đo mới thì vô hình với nó cho tới
       khi có người viết phép so cho đúng đơn vị ấy.

    Số đo 01/09 (4 bậc × 3 lượt, đọc `X-Duration-S`/`X-Gen-S` của chính cổng
    giọng): bậc đắt nhất là **câu ngắn** — RTF 0,699, 29,8 W → 2,83 mcredit mỗi
    giây tiếng. Bán 200. Biên hơn 98 %.
    """
    from apps.ltt_voice import gia

    von = G.mot_giay_tieng("ltt-voice-v3turbo")
    ban = gia.MCREDIT_MOI_GIAY
    assert ban > von, (
        f"ban {ban} mcredit/giay tieng <= von {von}. Doi gia trong "
        f"`apps/ltt_voice/gia.py`, hoac do lai bang "
        f"`setup\do_gia_von_voice.ps1` neu phan cung da doi.")


def test_gia_von_voice_doc_bang_DUNG_DON_VI_chu_khong_im_lang_tra_so_khac():
    """⛔ Hỏi giá vốn voice bằng hàm của ảnh phải NÉM, không được trả một con số.

    Đây là điều `mot_anh`/`mot_giay_tieng` cùng chặn qua `mode`. Không có chốt
    này thì một lần gọi nhầm hàm sẽ so **giá một giây tiếng** với **giá một
    ảnh** — hai con số cùng đơn vị milli-credit, cùng kiểu `int`, chênh nhau ba
    bậc, và không có gì trong hệ thống kiểu nào phản đối.
    """
    with pytest.raises(G.KhongBietGiaVon):
        G.mot_anh("ltt-voice-v3turbo")
    with pytest.raises(G.KhongBietGiaVon):
        G.mot_giay_tieng("hidream-o1")


def test_gia_api_CONG_KHAI_co_gia_tieng_va_lay_tu_ham_ra_hoa_don():
    """Chốt 3.6 của khuôn bán model nhà: giá phải lên trang công khai.

    ⭐ `gia.bang_gia()` đã tự viết trong docstring rằng `/gia-api` đọc **hàm
       này**, không gõ lại số — và suốt từ khi viết, **không ai nối dây**. Trang
       giá công khai nói về token và về ảnh, không nói một chữ nào về giọng nói,
       trong khi app giọng nói đang bán thật.

       Đó là đúng thứ tự ngược mà chính hàm `gia_api()` mở đầu bằng cách chê:
       *"muốn biết giá thì phải đăng ký trước… không ai đăng ký một dịch vụ
       tính tiền để xem nó tính bao nhiêu"*. Lặp lại lần thứ ba, với đơn vị đo
       thứ ba.

    ⛔ Phép kiểm này so **giá trị**, không so sự có mặt của khối. Một khối HTML
       có tiêu đề "Giá tạo giọng nói" mà số bên trong gõ tay vẫn qua được nếu
       chỉ kiểm tiêu đề — nên nó lấy `tinh(60)` từ chính module giá rồi tìm
       đúng con số ấy trong trang.
    """
    from fastapi.testclient import TestClient

    from apps.ltt_voice import gia as gia_tieng
    from server.app import create_app

    c = TestClient(create_app(), base_url="https://testserver")
    r = c.get("/gia-api")           # KHÔNG đăng nhập — trang này phải công khai
    assert r.status_code == 200, f"/gia-api tra {r.status_code}"
    t = r.text

    assert gia_tieng.PHIEN_BAN_GIA in t, (
        "trang gia khong noi phien ban gia cua giong noi — mot con so khong co "
        "phien ban thi khong doi soat duoc voi hoa don cu")
    mot_phut = gia_tieng.tinh(60)
    assert f">{mot_phut}<" in t or f"{mot_phut}</strong>" in t, (
        f"khong thay gia mot phut ({mot_phut} credit) trong trang. Neu template "
        f"go tay so thi day la luc no lech.")
