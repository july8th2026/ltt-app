"""
nghe_thu.py — NGHE THỬ một giọng trước khi dùng nó.

🔴 VÌ SAO ĐÂY LÀ P0 CHỨ KHÔNG PHẢI MỘT THỨ TRANG TRÍ.

   Trang Giọng liệt kê hai mươi cái tên kèm ba nhãn (giới · vùng · phong cách).
   Không có gì trong đó trả lời được câu hỏi duy nhất mà người chọn giọng thật
   sự hỏi: **giọng này nghe như thế nào.** Cho tới lúc này, cách duy nhất để
   biết là tạo một lượt đọc thật — tức **trả tiền để xem mình có muốn mua không**.

⭐ BA CÁCH LÀM, VÀ VÌ SAO CHỌN CÁCH THỨ BA.

   ① *Sinh ngay khi bấm, đồng bộ.* Đơn giản nhất, nhưng mỗi cú bấm là một lượt
      chiếm GPU — và nó đi **vòng qua** chốt `admission_resource="vieneu_gpu"`
      (một suất) mà manifest dựng lên để ba cửa job/sync/stream không đè nhau.
      Hai mươi thẻ giọng trên một trang là một lời mời tự DoS.

   ② *Đưa qua hàng đợi job.* Đúng về tài nguyên, sai về trải nghiệm: nghe thử
      mà phải chờ xếp hàng rồi hỏi lại trạng thái thì không ai bấm lần thứ hai.

   ③ **Dựng sẵn một lần, phục vụ như tệp tĩnh.** Mỗi giọng có đúng một tệp cho
      một phiên bản tham số. Lượt nghe thứ nhất và lượt thứ mười nghìn tốn như
      nhau: không GPU, không hàng đợi, không tính tiền.

   Cái giá của ③ là một khoảng *"chưa có"* lúc đầu — và nó được **nói ra** chứ
   không giấu (xem `co_san`). Một nút phát không kêu tệ hơn hẳn một dòng chữ
   "đang chuẩn bị".

⛔ KHÔNG TÍNH TIỀN NGHE THỬ. Đây là vật liệu để chọn hàng, không phải hàng.
   Và vì nó dựng đúng một lần cho mỗi giọng, chi phí thật là hữu hạn và đã biết:
   hai mươi giọng mẫu nhân một câu ngắn.

⚠️ VÒNG ĐỜI. Tệp nghe thử **không** mang `job_id` trong khoá, nên
   `platform_core/job_content.py` không dọn nó — đúng ý muốn: nó thuộc về
   *giọng*, không thuộc về một lượt chạy, và nó phải sống đúng bằng giọng đó.
   Cùng lý do `tham_chieu.khoa_nguon` nằm ngoài tầm dọn.
"""
from __future__ import annotations

import hashlib
import logging
import re

from platform_core.i18n import N_

log = logging.getLogger(__name__)


#: Câu đọc thử. **Cố định**, và cố định là một tính chất chứ không phải sự lười:
#: hai giọng chỉ so sánh được với nhau khi chúng đọc **cùng một câu**. Cho khách
#: tự nhập câu nghe thử là bỏ mất đúng cái làm phép so sánh có nghĩa — và mở lại
#: chính lỗ chi phí mà cách ③ vừa đóng.
#:
#: Nội dung chọn có chủ ý: một lời chào (ngữ điệu mở), một câu có **số** và
#: **đơn vị** (nơi phép chuẩn hoá lộ ra), một câu kết ngắn (nghe được đuôi câu).
CAU_NGHE_THU = N_('Xin chào, đây là giọng đọc của tôi. '
                  'Hôm nay là ngày mùng hai tháng chín. '
                  'Rất vui được đồng hành cùng bạn.')

def _phien_ban_tham_so() -> str:
    """`PHIEN_BAN_THAM_SO` của sidecar, hoặc `"?"` nếu không đọc được.

    ⭐ ĐỌC ĐƯỢC, và đó không hiển nhiên: sidecar chạy trong **venv cách ly**,
       nên phần lớn thứ trong `voice_sidecar/` nền tảng không import nổi. Nhưng
       `tham_so.py` có đúng **một** dòng import (`from __future__ import
       annotations`) — nó là một tệp hằng số thuần, cố ý.

    ⛔ Không đọc được thì trả `"?"`, KHÔNG ném và KHÔNG đoán. `"?"` là một giá
       trị ổn định: mọi khoá sinh ra trên một máy thiếu sidecar đều trùng nhau,
       nên chúng không nở ra vô hạn. Và nó **khác** mọi giá trị thật, nên tệp
       dựng trên máy ấy không bao giờ bị nhầm là tệp dựng bằng tham số thật.
    """
    try:
        from voice_sidecar.tham_so import PHIEN_BAN_THAM_SO
        return str(PHIEN_BAN_THAM_SO)
    except Exception as e:  # noqa: BLE001 - thieu sidecar la trang thai binh thuong
        log.debug("khong doc duoc PHIEN_BAN_THAM_SO (%s)", type(e).__name__)
        return "?"


#: 🔴 SUY RA TỪ HAI ĐẦU VÀO, KHÔNG GÕ TAY. Đây là bản vá cho một khớp nối mà
#:    chú thích cũ ở đúng chỗ này đã **mô tả rất chính xác rồi không cưỡng chế**:
#:
#:        "ĐỔI CÂU TRÊN THÌ PHẢI ĐỔI CHUỖI NÀY … Không đổi phiên bản = khách
#:         nghe câu CŨ trong khi mã nói câu mới, và không ai phát hiện ra vì cả
#:         hai đều là tiếng nói bình thường."
#:        "⚠️ Nó cũng phải đổi khi `PHIEN_BAN_THAM_SO` đổi."
#:
#: ⭐ Một chú thích nói "phải nhớ làm X" là một chú thích thừa nhận X sẽ bị
#:    quên. Ở đây cái giá của việc quên đã được viết ra: **hỏng lặng lẽ, và
#:    không có triệu chứng nào để lần**. Nên câu trả lời đúng không phải một
#:    chú thích to hơn, mà là gỡ khả năng quên.
#:
#: ⇒ Hai thứ quyết định nội dung tệp — câu đọc và bộ tham số engine — cùng đi
#:   vào một hàm băm. Đổi bất cứ cái nào thì khoá đổi, tự động, không ai phải
#:   nhớ gì.
#:
#: ⚠️ BĂM `CAU_NGHE_THU` (msgid GỐC), KHÔNG băm `_t(CAU_NGHE_THU)`. Bản dịch
#:    phụ thuộc ngôn ngữ của lượt gọi, nên băm nó sẽ cho **hai khoá khác nhau
#:    cho cùng một giọng** tuỳ ai chạm vào vòng bảo trì trước.
#:
#: ⛔ NHƯNG ĐIỀU ĐÓ PHƠI RA MỘT KHỚP NỐI THỨ HAI, VÀ TÔI ĐỂ NGUYÊN CÓ Ý THỨC:
#:    `dung()` gửi `str(_t(CAU_NGHE_THU))` xuống engine, tức **nội dung âm
#:    thanh phụ thuộc ngôn ngữ**, trong khi khoá thì không. Trên máy chủ hôm
#:    nay vòng bảo trì chạy ngoài mọi request nên nó luôn rơi về ngôn ngữ mặc
#:    định, và hai giá trị trùng nhau. Đó là một sự trùng hợp, không phải một
#:    bảo đảm.
#:
#:    Không vá ở đây vì thêm ngôn ngữ vào khoá làm **mọi** tệp nghe thử hiện có
#:    thành mồ côi, và đó là một thay đổi cần một lượt đo trước. Ghi ra để nó
#:    không lặng lẽ.
PHIEN_BAN: str = "v2-" + hashlib.sha256(
    (CAU_NGHE_THU + "|" + _phien_ban_tham_so()).encode("utf-8")
).hexdigest()[:12]

#: Trần số giọng dựng trong MỘT lượt bảo trì. Bảo trì chạy mỗi giờ; hai mươi
#: giọng mẫu warm đủ trong bảy lượt.
#:
#: ⛔ Có trần vì vòng bảo trì chạy **cùng tiến trình** với worker job. Dựng cả
#:    hai mươi tệp trong một lượt là giữ GPU khoảng một phút liền, và trong
#:    khoảng đó job của khách chờ mà không ai biết vì sao.
MOI_LUOT_TOI_DA = 3


def _slug(ten: str) -> str:
    """Tên giọng thành một đoạn đường dẫn an toàn.

    ⛔ Tên preset có dấu tiếng Việt và khoảng trắng (`"Minh Đức"`), và nó đi vào
       **khoá kho** rồi vào **URL**. Không chuẩn hoá thì một khoá hợp lệ trên
       máy này là một khoá hỏng trên kho khác, và một URL phải mã hoá phần trăm
       ở mọi chỗ nó xuất hiện.

    ⭐ Nhưng KHÔNG bỏ dấu: `"Minh Đức"` và `"Minh Duc"` phải là hai slug khác
       nhau nếu engine có cả hai. Giữ dấu, chỉ thay thứ không an toàn.
    """
    s = (ten or "").strip()
    s = re.sub(r"\s+", "-", s)
    # ⚠️ Dải chữ có dấu viết bằng **mã điểm**, không bằng ký tự `À-ỹ` gõ thẳng.
    #    Hai lý do, và lý do thứ hai mới là lý do thật:
    #      ① không phụ thuộc bảng mã của chính tệp này;
    #      ② `tools/check_i18n.py` đếm mọi chuỗi có dấu tiếng Việt mà không bọc
    #         `_()`. Một bảng ký tự regex **không phải câu giao diện**, nhưng
    #         luật trừ của nó chỉ tha chuỗi không có chữ ASCII nào — và chuỗi
    #         này có `A-Za-z`. Viết bằng mã điểm là cách đúng để nó không kêu:
    #         bỏ dấu khỏi *mã nguồn*, không bỏ dấu khỏi *hành vi*.
    #    U+00C0 la chu A hoa co dau huyen, U+1EF9 la chu y co dau nga - dung
    #    bang dai chu co dau cua tieng Viet.
    s = re.sub(r"[^0-9A-Za-z\u00C0-\u1EF9_\-]", "", s)
    return s or "khong-ten"


def khoa_mau(ten: str) -> str:
    """Khoá kho cho một giọng DỰNG SẴN.

    Tiền tố `voice/mau/` là tiền tố **thứ ba** của app, và nó có luật đọc riêng:
    giọng dựng sẵn không thuộc về ai, nên tệp nghe thử của nó đọc được cho mọi
    khách đã đăng nhập. Xem `routes/_p_audio.py`.
    """
    return f"voice/mau/{_slug(ten)}/{PHIEN_BAN}.wav"


def khoa_rieng(owner_id: str, public_id: str) -> str:
    """Khoá kho cho một giọng NHÂN BẢN của khách.

    ⭐ Nằm trong đúng thư mục giọng đó (`voice/{uid}/{public_id}/`) để dùng lại
       nguyên phép kiểm sở hữu đã có — phép kiểm ấy dựa vào **hình dạng khoá**,
       và thêm một thư mục thứ tư là thêm một luật thứ tư sẽ lệch.

    ⛔ Tên tệp bắt đầu bằng `preview-` chứ không phải một tên tuỳ ý: cửa đọc mở
       theo **TÊN TỆP**, vì cùng thư mục đó còn chứa `repr-*.npz` — biểu diễn
       người nói, thứ `tables.py` nói thẳng là *"KHÔNG BAO GIỜ ra ngoài"*.
    """
    return f"voice/{owner_id}/{public_id}/preview-{PHIEN_BAN}.wav"


#: Bộ nhớ đệm `khoá -> (lúc, có)`.
#:
#: 🔴 VÌ SAO CẦN, và nó không lộ ra trên máy dev.
#:
#:    `LocalStorage.exists` là một `stat()` — rẻ tới mức vô hình. `R2Storage.exists`
#:    là một **HEAD qua mạng**. Màn Giọng dựng hai mươi thẻ, nên hỏi thẳng kho ở
#:    mỗi lượt dựng trang là **hai mươi lượt gọi mạng cho một trang** trên
#:    production, và không một phép kiểm nào trên máy dev nhìn thấy điều đó.
#:
#: ⚠️ Cái giá của đệm: một tiến trình khác vừa dựng xong tệp thì tiến trình này
#:    còn nói "chưa có" tối đa `DEM_TTL_S` giây. Hệ quả là một dòng *"đang chuẩn
#:    bị"* thừa trong một phút, và nó tự lành. Đổi lại đúng chiều.
_DEM: dict = {}
DEM_TTL_S = 60.0


def co_san(khoa: str) -> bool:
    """Tệp nghe thử đã dựng chưa. **Có đệm** — xem `_DEM`.

    ⚠️ Trả `False` khi kho ném **bất cứ lỗi gì**, không chỉ khi thiếu tệp. Một
       kho hỏng và một tệp chưa dựng phải dẫn tới cùng một hành vi ở giao diện
       (nói "chưa có"), vì cả hai đều nghĩa là *không phát được* — và một nút
       phát không kêu là thứ tệ nhất trong ba khả năng.

    ⛔ Chỉ đệm câu trả lời **True**. Một `False` bị đệm là một tệp vừa dựng xong
       mà trang vẫn giấu; một `True` bị đệm sai chỉ xảy ra khi có ai xoá tệp
       dưới chân ta, và lúc đó cửa audio trả 404 — thấy được, sửa được. Hai
       hướng sai này không cân nhau, nên đệm cũng không cân.
    """
    import time

    from platform_core.storage import get_storage

    gio = time.monotonic()
    luc = _DEM.get(khoa)
    if luc is not None and (gio - luc) < DEM_TTL_S:
        return True
    try:
        co = bool(get_storage().exists(khoa))
    except Exception as e:  # noqa: BLE001 - kho co the nem nhieu loai loi
        log.warning("khong hoi duoc kho ve %s: %s", khoa, e)
        return False
    if co:
        _DEM[khoa] = gio
    return co


def dung(khoa: str, *, ref_b64=None, preset=None) -> bool:
    """Sinh MỘT tệp nghe thử rồi cất vào kho. Trả `True` nếu vừa dựng xong.

    ⛔ Không ném ra ngoài. Người gọi là vòng bảo trì và đuôi của job ghi danh —
       cả hai đều **không được** hỏng vì một tệp nghe thử. Một giọng không nghe
       thử được vẫn là một giọng dùng được.
    """
    import io

    from platform_core.i18n import _ as _t
    from platform_core.storage import get_storage

    from . import features

    if co_san(khoa):
        return False
    try:
        wav, _ = features.goi_cong(str(_t(CAU_NGHE_THU)),
                                   ref_b64=ref_b64, preset=preset)
        get_storage().put(khoa, io.BytesIO(wav), content_type="audio/wav")
        log.info("da dung nghe thu: %s (%d byte)", khoa, len(wav))
        return True
    except Exception as e:  # noqa: BLE001 - xem docstring
        log.warning("khong dung duoc nghe thu %s: %s", khoa, e)
        return False


def con_thieu_mau() -> list:
    """Những giọng dựng sẵn chưa có tệp nghe thử."""
    from . import giong_mau
    return [g for g in giong_mau.DANH_SACH if not co_san(khoa_mau(g.ma))]


def duong_cho_trang(*, duong_audio: str, owner_id: str,
                    ma_mau=(), rieng=()) -> dict:
    """`{public_id: url}` cho mọi giọng một trang sắp dựng.

    🔴 **MỘT thẩm quyền duy nhất dựng đường nghe thử.** Đây là bài học đã trả
       giá ở `du_an.duong_tieng()`: trước đó **năm** chỗ tự ghép URL bằng
       `if k.audio_key`, và sửa cho đúng nghĩa là phải nhớ đủ năm. Màn Giọng và
       màn Tạo tiếng nói đều cần đường này; hai bản ghép là hai bản sẽ lệch.

    ⭐ Giọng **không có tệp** thì **không có khoá trong dict** — không phải một
       chuỗi rỗng, không phải một URL trỏ vào hư không. Khuôn mẫu hỏi
       `ma in duong` và hiện *"đang chuẩn bị"*; một URL 404 sẽ cho ra một nút
       phát bấm được mà không kêu, tức đúng thứ tệ nhất.
    """
    ra: dict = {}
    for ma in ma_mau:
        khoa = khoa_mau(ma)
        if co_san(khoa):
            ra[ma] = f"{duong_audio}/{khoa}"
    for pid in rieng:
        khoa = khoa_rieng(owner_id, pid)
        if co_san(khoa):
            ra[pid] = f"{duong_audio}/{khoa}"
    return ra


def bao_tri() -> None:
    """Việc định kỳ của app — dựng dần tệp nghe thử còn thiếu.

    🔴 CHẠY DƯỚI LEASE `bao_tri` của nền tảng, nên **đúng một lần trên toàn
       cụm** dù có bao nhiêu tiến trình worker. Đó chính là lý do nó nằm ở hợp
       đồng `AppManifest.bao_tri` chứ không phải trong một vòng lặp tự dựng:
       một vòng tự dựng chạy ở **mọi** tiến trình, và với `LTT_WORKER_POOLS`
       nhiều làn thì cùng một tệp sẽ được sinh N lần trên N card.

    ⚠️ Im lặng khi cổng chưa bật. Đây là việc nền; sủa mỗi giờ trên một máy
       chưa cài engine chỉ làm nhật ký khó đọc.
    """
    # ⭐ ĐẾM MỨC DÙNG TRƯỚC, và **ngoài** cổng `san_sang()` bên dưới.
    #
    #    Thứ tự giọng là chuyện của giao diện; nó vẫn phải đúng trên một máy
    #    chưa cài engine. Đặt phép đếm sau `return` kia là để một kho chạy nhiều
    #    tháng không engine phục vụ mãi mãi một thứ tự bảng chữ cái — hỏng lặng
    #    lẽ, và hỏng theo cách không ai nghĩ tới khi đọc `bao_tri`.
    _dem_muc_dung()

    from . import sidecar_client

    if not sidecar_client.san_sang():
        return
    _doi_chieu_giong_mau()
    thieu = con_thieu_mau()
    if not thieu:
        return
    log.info("nghe thu: con thieu %d giong mau, dung toi da %d luot nay",
             len(thieu), MOI_LUOT_TOI_DA)
    for g in thieu[:MOI_LUOT_TOI_DA]:
        dung(khoa_mau(g.ma), preset=g.ma)


def duong_cho_app_khac(*, owner_id: str, ma_mau=(), rieng=()) -> dict:
    """`duong_cho_trang` cho mot app KHAC, khong bat ho biet duong `/audio` cua ta.

    🔑 Vi sao ton tai thay vi de ben goi tu ghep `f"{MANIFEST.route_prefix}/audio"`:

       Lam the buoc app kia phai doc `MANIFEST` cua ta — tuc phai khai
       `apps.ltt_voice.manifest.MANIFEST` la be mat cong khai. Va mot manifest la
       thu **ca nen tang** doc: xuat no ra cho mot app khac la xuat ca `job_types`,
       `credit_cost`, `bao_tri`, `tables` — moi thu, de lay mot chuoi.

    ⭐ Va no giu nguyen luat cua `duong_cho_trang`: **MOT tham quyen dung duong
       nghe thu**. Ham nay khong tu ghep gi, no goi ham kia.

    ⚠️ Giong khong co tep van **vang mat** khoi dict, khong tra chuoi rong — hop
       dong do khong doi.
    """
    from .manifest import MANIFEST

    return duong_cho_trang(duong_audio=f"{MANIFEST.route_prefix}/audio",
                           owner_id=owner_id, ma_mau=ma_mau, rieng=rieng)


#: Bao lâu mới đối chiếu ảnh chụp giọng mẫu với engine một lần, tính bằng giây.
#:
#: ⚠️ MỘT NGÀY, không phải mỗi giờ. Danh sách preset đi kèm **bản model**, nên
#:    nó chỉ đổi vào ngày nâng engine. Hỏi mỗi giờ là 24 lượt gọi để phát hiện
#:    một thay đổi xảy ra vài tháng một lần.
MOI_LUOT_DOI_CHIEU_S = 86_400
_LUOT_DOI_CHIEU_CUOI = [0.0]


def _doi_chieu_giong_mau() -> None:
    """Hỏi engine THẬT xem ảnh chụp preset còn đúng không.

    🔴 CÂU NÀY CHÍNH BỘ SINH ẢNH CHỤP ĐÃ BỎ NGỎ, và nó nói ra điều đó:

       *"Ảnh chụp chốt `giong_mau.py` khớp thứ ta đã chụp; nó **không** chốt
       thứ ta đã chụp còn đúng. Hai câu đó tách nhau đúng vào ngày nâng model —
       và đó là ngày duy nhất chúng có thể sai."*
       (`tools/sinh_giong_mau_engine.py`)

    ⭐ VÌ SAO ĐẶT Ở ĐÂY chứ không ở `giong_mau.py`. Cửa `/v1/voices` gọi
       `c.nap()`, tức **nạp model — 19,4 giây khi nguội**. Một trang liệt kê
       giọng gọi thẳng vào đó sẽ treo 19 giây ở lượt đầu mỗi sáng; chính
       `giong_mau.py` từ chối làm vậy vì lý do ấy.

       Nhưng vòng bảo trì này **đã** giữ model ấm để dựng tệp nghe thử. Ở đây
       phép hỏi gần như miễn phí — cùng một model đã nạp, cùng một tiến trình.

    ⛔ CHỈ GHI NHẬT KÝ, KHÔNG NÉM VÀ KHÔNG SỬA GÌ. Lệch danh sách preset là
       chuyện của một lượt nâng engine, và bản sửa đúng là **chạy lại
       `tools/sinh_giong_mau_engine.py` rồi commit phần diff** — một hành động
       có người xem xét. Tự sửa ảnh chụp lúc chạy là để một vòng bảo trì âm
       thầm viết lại một tệp trong git.

    ⚠️ Nuốt mọi lỗi: đây là việc nền chạy dưới lease. Một cổng chậm không được
       phép làm hỏng lượt dựng tệp nghe thử ngay dưới nó.
    """
    import time

    from . import giong_mau, sidecar_client

    if time.time() - _LUOT_DOI_CHIEU_CUOI[0] < MOI_LUOT_DOI_CHIEU_S:
        return
    _LUOT_DOI_CHIEU_CUOI[0] = time.time()
    try:
        that = {str(m.get("id") or m.get("nhan") or "").strip()
                for m in sidecar_client.giong_dung_san()}
    except Exception as e:  # noqa: BLE001 - viec nen, khong duoc lam hong luot chinh
        log.info("doi chieu giong mau: khong hoi duoc cong (%s)", type(e).__name__)
        return
    that.discard("")
    if not that:
        return
    anh_chup = {g.ma for g in giong_mau.DANH_SACH}
    thieu = sorted(anh_chup - that)
    moi = sorted(that - anh_chup)
    if thieu or moi:
        log.warning(
            "GIONG MAU LECH engine: anh chup thua %s, engine co them %s. "
            "Chay `tools/sinh_giong_mau_engine.py` roi commit phan diff.",
            thieu or "-", moi or "-")
    else:
        log.info("doi chieu giong mau: khop (%d giong)", len(that))
#: Bao lâu mới đếm lại mức dùng, tính bằng giây. SÁU GIỜ, không phải mỗi giờ.
#:
#: ⚠️ `bao_tri_moi_giay = 3600`, nên không tiết chế là 24 lượt quét bảng `jobs`
#:    mỗi ngày — để đổi thứ tự một danh sách hai mươi mục. Thứ tự giọng không
#:    cần tươi tới từng giờ; nó chỉ cần **đúng** và **ổn định**.
MOI_LUOT_DEM_S = 21_600
_LUOT_DEM_CUOI = [0.0]


def _dem_muc_dung() -> None:
    """Đếm lại mức dùng thật cho `muc_dung` (U-12).

    ⛔ NUỐT MỌI LỖI, và mở phiên CSDL của chính nó.

       Đây là số liệu **trang trí thứ tự**. Một truy vấn hỏng ở đây không được
       phép làm hỏng lượt dựng tệp nghe thử ngay dưới nó — và `muc_dung.xep`
       với ảnh chụp rỗng vẫn cho ra một thứ tự hợp lệ, nên đường lùi đã có sẵn.
    """
    import time

    from . import muc_dung

    if time.time() - _LUOT_DEM_CUOI[0] < MOI_LUOT_DEM_S:
        return
    _LUOT_DEM_CUOI[0] = time.time()
    try:
        from platform_core.db import get_session
        gen = get_session()
        db = next(gen)
        try:
            muc_dung.lam_moi(db)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
    except Exception as e:  # noqa: BLE001 - viec nen, khong duoc lam hong luot chinh
        log.info("dem muc dung: bo qua luot nay (%s: %s)", type(e).__name__, e)
