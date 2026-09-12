"""
chon_giong.py — để **model tự chọn giọng** trong kho chung cho hợp ngữ cảnh.

## Vì sao tệp này tồn tại

Trước 04/09, ChatLTT chỉ mời `voice_id` — giọng **nhân bản của chính người
dùng**. Đo trên tài khoản kiểm: ô chọn giọng **không hiện ra**, vì tài khoản đó
chưa nhân bản giọng nào. Đó không phải trường hợp hiếm; đó là trạng thái của gần
như **mọi khách mới**. Họ có đúng một giọng mặc định, và không có cách nào biết
nền tảng đang sẵn 20 giọng khác.

⭐ Nên việc cần làm không phải "bắt khách chọn từ một danh sách", mà là **để
   model chọn giúp** — nó vừa đọc câu trả lời, nó biết đó là tin tức hay truyện
   kể, giọng miền nào thì hợp.

## Ba luật của tệp này, và cả ba đều đến từ một phép đo

🔴 **MỘT LƯỢT CHỌN GIỌNG TỐN ĐÚNG 1 CREDIT.** Đo 04/09: `gia_token.tinh()` làm
   **tròn lên**, nên một lượt 700 token vào / 8 token ra vẫn tính tròn 1 credit —
   bằng đúng giá một lượt đọc. Hỏi model mỗi lần "Đọc to" là **nhân đôi giá**.

⭐ Nên giọng được **nhớ theo hội thoại**: lượt tiếng gần nhất đã chọn giọng nào
   thì dùng lại giọng đó. Phụ phí chỉ phát sinh ở lần đầu của mỗi hội thoại, và
   nó cũng hợp lẽ về nội dung — một hội thoại nên có một giọng nhất quán chứ
   không đổi người đọc giữa chừng.

⛔ **CHỌN GIỌNG HỎNG THÌ VẪN PHẢI ĐỌC ĐƯỢC.** Model bận, hết credit, trả về một
   cái tên không có thật — cả ba đều rơi về giọng mặc định. Một tính năng tiện
   nghi không bao giờ được phép chặn tính năng chính. Đây là lý do mọi đường
   trong `chon()` đều kết thúc bằng một `preset` hợp lệ, không đường nào ném.
"""
from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)

#: (không còn hằng số nhãn — xem `mac_dinh()`)

#: Trần ký tự trích cho model xem. Đủ để nhận ra văn phong, không đủ để tốn tiền.
#: ⛔ Đừng gửi cả bài: giá tính theo token vào, và một bài dài biến một lượt
#:    "chọn giọng" 1 credit thành một lượt vài credit.
TRICH_TOI_DA = 600


def _kho_chung(db, user_id: str) -> list:
    """Kho giọng chung, đọc qua **DANH MỤC NỀN TẢNG** — không import `ltt_voice`.

    🔴 Bản đầu của tệp này gọi thẳng `apps.ltt_voice.tham_chieu`, và
       `tools/lint_app_contract.py` chặn ngay: *"app khong duoc goi vao ruot app
       khac"*. Cái chặn đó đúng, và nó đúng vì một lý do cụ thể: `ltt_voice` có
       thể đổi hình dạng nội bộ bất cứ lúc nào, còn `tuy_chon` trong danh mục là
       **mặt đã công bố** cho mọi app dùng chung.

    ⭐ Và đường này rẻ hơn thật: chính danh sách ấy đã đi ra giao diện qua
       `NangLuc.tuy_chon`, nên máy chủ và màn hình đọc **cùng một nguồn**. Hai
       nguồn cho một danh sách là hai nguồn sẽ lệch.

    ⚠️ Danh mục chuẩn hoá về đúng `{value, label}` — nhãn giới/vùng/phong cách
       nằm **trong** `label` (vd `"Adam (Nam · Miền Nam · Tự nhiên)"`). Nên đừng
       tìm khoá `phong_cach` ở đây; nó không đi qua cửa này.
    """
    from apps.chatltt.services import chinh_sach

    for nl in chinh_sach.danh_muc(db, user_id=str(user_id)):
        if getattr(nl, "ten", "") == chinh_sach.NANG_LUC_TIENG:
            return list((getattr(nl, "tuy_chon", None) or {}).get("preset") or [])
    return []


def mac_dinh(db, user_id: str) -> str:
    """Giọng lùi về: **phần tử đầu** của kho chung.

    ⛔ Không gõ cứng `"Adam"`. Ảnh chụp preset của engine nằm trong git và **sẽ
       đổi** khi engine nâng cấp; một cái tên gõ cứng ở đây trở thành một
       `preset` không tồn tại, và lỗi đó chỉ lộ ra lúc chạy thật.

    🔴 VÀ KHÔNG DÒ CHỮ TRÊN NHÃN. Bản đầu tìm nhãn `"Tự nhiên"` trong `label` —
       `tools/check_i18n.py` kêu, và nó kêu đúng vào một khuyết tật thật:
       `label` đi qua `_()`, nên một bản dịch sang tiếng Anh sẽ làm phép so
       chuỗi trượt và giọng mặc định lặng lẽ đổi **theo ngôn ngữ giao diện**.

    ⭐ Nên thứ tự được quyết ở nguồn (`tham_chieu.tuy_chon_preset` xếp giọng
       trung tính lên đầu), còn ở đây chỉ lấy phần tử đầu. Một quyết định nằm ở
       **dữ liệu** thì không có bản dịch nào làm nó lệch được.
    """
    kho = _kho_chung(db, user_id)
    return str(kho[0]["value"]) if kho else ""


def hop_le(db, user_id: str, ten: str) -> bool:
    """Tên này có thật trong kho chung không.

    ⛔ Kiểm bằng **danh sách nền tảng vừa trả**, không bằng một bảng chép lại.
       Đây là chỗ chặn một cái tên model bịa ra đi thẳng vào `infer(voice=...)`.
    """
    if not ten:
        return False
    return any(str(g.get("value")) == str(ten) for g in _kho_chung(db, user_id))


def giong_da_dung(db, *, conv_id: str, user_id: str) -> Optional[str]:
    """Giọng đã dùng ở lượt tiếng gần nhất của hội thoại này, nếu có.

    ⭐ Nhớ ở đây thay vì thêm một cột: `ChatlttExecution.usage` là JSON và đã có
       đường ra giao diện sẵn. Thêm cột cho một thứ suy được từ dữ liệu đã có là
       thêm một migration và một chỗ nữa để lệch.
    """
    from apps.chatltt.services import chinh_sach
    from apps.chatltt.tables import ChatlttExecution

    hang = (db.query(ChatlttExecution)
            .filter(ChatlttExecution.conversation_id == str(conv_id),
                    ChatlttExecution.user_id == str(user_id),
                    ChatlttExecution.tool_name == chinh_sach.NANG_LUC_TIENG)
            .order_by(ChatlttExecution.id.desc())
            .limit(12).all())
    for ex in hang:
        ten = ((ex.usage or {}).get("giong") or {}).get("preset")
        if ten and hop_le(db, user_id, ten):
            return str(ten)
    return None


def _loi_nhac(db, user_id: str, trich: str) -> list:
    """Lượt hỏi model. Ngắn có chủ ý — xem luật giá ở đầu tệp."""
    kho = _kho_chung(db, user_id)
    danh_sach = "\n".join(f"- {g['value']}: {g['label']}" for g in kho)
    return [{
        "role": "user",
        "content": (
            "Chọn MỘT giọng đọc hợp nhất với đoạn văn bản dưới đây.\n\n"
            f"Các giọng có sẵn:\n{danh_sach}\n\n"
            "Quy tắc: tin tức/thông báo hợp giọng phong cách Tin tức; truyện, "
            "tâm sự, mô tả hợp Kể chuyện; hội thoại thường hợp Tự nhiên. Nếu văn "
            "bản nhắc tới một vùng miền thì ưu tiên giọng vùng đó.\n\n"
            f"Văn bản:\n{trich}\n\n"
            "TRẢ LỜI: chỉ đúng một tên giọng, không giải thích, không dấu câu."
        ),
    }]


def _hoi_model(db, *, user_id: str, alias: str, trich: str) -> Optional[str]:
    """Hỏi model một câu, gom chữ, trả tên giọng. `None` khi không dùng được.

    ⛔ KHÔNG NÉM. Mọi hỏng hóc ở đây — model bận, hết credit, luồng vỡ, model
       bịa một cái tên — đều chỉ là "không chọn được", và bên gọi rơi về mặc
       định. Xem luật thứ ba ở đầu tệp.
    """
    from apps.chatltt.services import chinh_sach
    from platform_core.runtime_noi_bo import luong as L

    chu = []
    try:
        for sk in L.mo_luong(db, user_id=user_id,
                             tool_name=chinh_sach.NANG_LUC_TEXT,
                             params={"model": alias, "max_tokens": 24,
                                     "messages": _loi_nhac(db, user_id, trich)},
                             cua=chinh_sach.CUA, tien_to=chinh_sach.TIEN_TO):
            if sk.get("type") == "response.delta":
                chu.append(sk.get("text") or "")
            elif sk.get("type") == "response.failed":
                log.info("chon giong: model tu choi (%s)", sk.get("code"))
                return None
    except Exception as e:                                      # noqa: BLE001
        log.info("chon giong: khong hoi duoc model (%s)", type(e).__name__)
        return None

    ra = "".join(chu).strip().strip('."\'`').strip()
    if hop_le(db, user_id, ra):
        return ra
    # ⭐ Model hay trả kèm chữ thừa ("Giọng: Minh Đức"). Dò từng tên trong kho
    #    thay vì bỏ cuộc — nhưng CHỈ chấp nhận tên có thật, không tự sửa lỗi
    #    chính tả: một cái tên gần đúng đi vào `infer(voice=...)` là một lỗi
    #    engine, không phải một giọng khác.
    for g in _kho_chung(db, user_id):
        if str(g["value"]).lower() in ra.lower():
            return str(g["value"])
    log.info("chon giong: model tra ve %r — khong khop giong nao", ra[:60])
    return None


def chon(db, *, user_id: str, conv_id: str, text: str,
         alias: str = "") -> dict:
    """Giọng cho lượt đọc này. **Luôn** trả về một `preset` dùng được.

    Trả `{"preset", "nguon", "ton_credit"}` với `nguon` ∈ `nho | model | mac_dinh`:

      · `nho`      — dùng lại giọng của lượt tiếng trước trong hội thoại (0 credit)
      · `model`    — model vừa chọn (**1 credit**)
      · `mac_dinh` — không chọn được, rơi về giọng lùi (0 credit)

    ⭐ `ton_credit` được trả ra để bên gọi **nói cho khách biết trước khi thu**.
       Một phụ phí không được nêu là một phụ phí sẽ bị coi là lỗi tính tiền.
    """
    # ⛔ BAT LOI O CA HAI TANG, VA DO KHONG PHAI THUA.
    #
    #    `_hoi_model` da tu bat loi cua no. Nhung `chon()` duoc goi thang tu cua
    #    BAO GIA cua khach — mot ngoai le lot qua day la HTTP 500 tren mot thao
    #    tac ma khach chi dinh xem gia. Phep kiem `test_635` chot dung menh de
    #    nay bang cach cho `_hoi_model` nem, va ban dau no DO: ham nay dang tin
    #    vao mot bao dam nam trong mot ham khac.
    #
    # ⭐ Tin vao mot bao dam o noi khac la dung, cho toi khi ai do sua noi khac.
    try:
        cu = giong_da_dung(db, conv_id=conv_id, user_id=user_id)
        if cu:
            return {"preset": cu, "nguon": "nho", "ton_credit": 0}

        trich = (text or "").strip()[:TRICH_TOI_DA]
        if trich:
            ten = _hoi_model(db, user_id=user_id,
                             alias=alias or "", trich=trich)
            if ten:
                return {"preset": ten, "nguon": "model", "ton_credit": 1}
    except Exception as e:                                      # noqa: BLE001
        log.warning("chon giong hong (%s) — lui ve giong mac dinh",
                    type(e).__name__)

    try:
        lui = mac_dinh(db, user_id)
    except Exception:                                           # noqa: BLE001
        # Khong doc noi ca danh muc: tra rong. `preset` la tham so TUY CHON,
        # nen cua tieng se dung giong mac dinh cua chinh no — van doc duoc.
        log.exception("khong doc duoc kho giong chung")
        lui = ""
    return {"preset": lui, "nguon": "mac_dinh", "ton_credit": 0}
