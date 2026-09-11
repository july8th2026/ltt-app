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


#: 🔴 CÂU NGHE THỬ THEO **LÀN CỦA GIỌNG**, KHÔNG THEO NGÔN NGỮ GIAO DIỆN.
#:
#:    Tới 2026-09-10 `dung()` gọi `str(_t(CAU_NGHE_THU))` — tức nó đọc câu **đã
#:    dịch sang ngôn ngữ của tiến trình đang chạy**. Ba thứ hỏng cùng lúc:
#:
#:      ① Một giọng làn `vi` có thể được dựng bằng câu tiếng Anh, chỉ vì lượt
#:         bảo trì tình cờ chạy dưới một ngữ cảnh tiếng Anh. Nghe thử khi ấy
#:         không còn trả lời câu nó sinh ra để trả lời — *"giọng này đọc tiếng
#:         Việt nghe thế nào"*.
#:      ② `khoa_mau()` **không mang ngôn ngữ** trong khoá, nên tệp dựng đầu tiên
#:         thắng và mọi khách sau đó nghe nó — kể cả khách đang xem trang tiếng
#:         Việt. Một trạng thái quyết định bởi *lượt chạy nào tới trước*.
#:      ③ Và nó **không so sánh được**: hai giọng dựng ở hai lượt bảo trì khác
#:         ngữ cảnh sẽ đọc hai câu khác nhau, trong khi toàn bộ lý do câu này cố
#:         định là để hai giọng so được với nhau.
#:
#: ⭐ Nên câu phụ thuộc **làn**, thứ thuộc về chính giọng và không đổi theo ai
#:    đang xem. Cùng nội dung có chủ ý ở cả hai làn: một lời chào, một câu có
#:    **số** và **đơn vị** (nơi phép chuẩn hoá lộ ra), một câu kết ngắn.
#:
#: ⚠️ Vẫn bọc `N_()` cho `CAU_NGHE_THU` để bộ trích i18n không kêu, nhưng **cố ý
#:    không gọi `_()`** khi dùng: bản dịch của câu này không được phép đổi thứ
#:    engine đọc. Đây là dữ liệu vào của model, không phải chữ trên màn hình.
CAU_THEO_LAN = {
    "vi": CAU_NGHE_THU,
    "en": ("Hello, this is my reading voice. "
           "Today is the second of September. "
           "I am glad to be here with you."),
}


def cau_cho_lan(lan: str) -> str:
    """Câu nghe thử của một làn. Làn lạ ⇒ câu tiếng Việt.

    ⛔ Lối lui là `vi` chứ không phải ném: nghe thử là **vật liệu chọn hàng**,
       và `dung()` đã có hợp đồng "không bao giờ hỏng vì một tệp nghe thử". Một
       giọng chưa rõ làn nay bị `lan_ngon_ngu.quyet_dinh` chặn ở cửa nộp — đó
       mới là chỗ nói câu đó, không phải ở đây.
    """
    return str(CAU_THEO_LAN.get(str(lan or "").strip().lower(), CAU_NGHE_THU))

#: 🔴 ĐỔI CÂU TRÊN THÌ PHẢI ĐỔI CHUỖI NÀY.

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
#: ⭐ KHỚP NỐI THỨ HAI MÀ CHÚ THÍCH CŨ Ở ĐÂY MÔ TẢ — NAY ĐÃ GỠ (Q121).
#:
#:    Chú thích cũ viết: *"`dung()` gửi `str(_t(CAU_NGHE_THU))` xuống engine,
#:    tức nội dung âm thanh phụ thuộc ngôn ngữ, trong khi khoá thì không … Đó là
#:    một sự trùng hợp, không phải một bảo đảm."* Đúng, và nó đã tự nói rằng bản
#:    vá sẽ phải đến.
#:
#: ⇒ Bản vá không phải là *thêm ngôn ngữ vào khoá* (chi phí: mồ côi mọi tệp
#:   hiện có) mà là **bỏ phụ thuộc ngôn ngữ khỏi nội dung**: `dung()` nay chọn
#:   câu theo **LÀN CỦA GIỌNG** (`cau_cho_lan`), thứ thuộc về chính giọng và
#:   không đổi theo ai đang xem. Hết khớp nối, và khoá không phải dài thêm.
#:
#: ⛔ NHƯNG THẾ THÌ HÀM BĂM PHẢI THẤY **MỌI** CÂU, không chỉ câu tiếng Việt.
#:    Băm riêng `CAU_NGHE_THU` nghĩa là sửa câu tiếng Anh **không** đổi khoá ⇒
#:    khách nghe câu EN cũ mãi mãi — đúng cái bẫy im lặng mà cả khối này dựng ra
#:    để chặn, chỉ khác làn.
#:
#: ⚠️ ĐÁNH ĐỔI CỦA CÁCH NÀY, nói thẳng: thêm một làn thứ ba sẽ đổi khoá của
#:    **cả** hai làn cũ và bắt dựng lại toàn bộ. Đó là chiều sai RẼ: dựng thừa
#:    một lượt (vài chục giây GPU, một lần) đổi lấy việc không bao giờ phục vụ
#:    một tệp cũ. Chiều ngược lại — khoá theo từng làn — gọn hơn nhưng bắt
#:    `khoa_mau()` biết làn, tức đổi hình dạng khoá ở bốn nơi gọi. Không đáng.
PHIEN_BAN: str = "v2-" + hashlib.sha256(
    ("|".join([f"{lan}={cau}" for lan, cau in sorted(CAU_THEO_LAN.items())]
              + [_phien_ban_tham_so()])).encode("utf-8")
).hexdigest()[:12]

#: Trần số giọng dựng trong MỘT lượt bảo trì. Bảo trì chạy mỗi giờ; hai mươi
#: giọng mẫu warm đủ trong bảy lượt.
#:
#: ⛔ Có trần vì vòng bảo trì chạy **cùng tiến trình** với worker job. Dựng cả
#:    hai mươi tệp trong một lượt là giữ GPU khoảng một phút liền, và trong
#:    khoảng đó job của khách chờ mà không ai biết vì sao.
MOI_LUOT_TOI_DA = 3

#: Trần số giọng NHÂN BẢN CỦA KHÁCH dựng lại trong MỘT lượt bảo trì — cùng lý
#: do `MOI_LUOT_TOI_DA` ở trên, một hằng số RIÊNG vì đây là một NGUỒN dữ liệu
#: khác (bảng `voice_profile`, không phải `giong_mau.DANH_SACH`) với một nhịp
#: phát sinh khác: giọng mẫu chỉ thiếu tệp sau một lần nâng `PHIEN_BAN`, còn
#: giọng riêng thiếu tệp mỗi khi một khách ĐỔI LÀN
#: (`routes/_p_giong.py:khai_ngon_ngu_giong` → `dung_lai_cho_giong`) — một sự
#: kiện có thể dồn dập hơn nhiều so với một lần nâng engine.
TOI_DA_GIONG_RIENG_MOI_LUOT = 5


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


def dung_lai_cho_giong(db, ho_so) -> None:
    """HUỶ tệp nghe thử ĐANG CÓ của một giọng — để vòng bảo trì dựng lại theo
    làn MỚI (`CAU_THEO_LAN[ho_so.ngon_ngu]`) ở lượt sau (D004).

    🔴 VÌ SAO CẦN, VÀ VÌ SAO KHÔNG THỂ BỎ QUA.

       `khoa_rieng(owner_id, public_id)` KHÔNG mang làn trong khoá — chỉ mang
       `PHIEN_BAN`, một hằng số TOÀN CỤC không phụ thuộc `ngon_ngu` của giọng
       (xem khối chú thích ở `PHIEN_BAN` bên trên). Hệ quả: đổi làn của một
       giọng KHÔNG tự đổi khoá tệp nghe thử của nó — `dung()` sẽ thấy
       `co_san(khoa)` vẫn `True` (tệp làn CŨ còn nằm đúng khoá đó) và không
       dựng lại, nên khách nghe câu của làn cũ mãi mãi dù hồ sơ đã nói làn mới.

    ⛔ KHÔNG gọi engine đồng bộ ở đây — người gọi là một request HTTP
       (`routes/_p_giong.py:khai_ngon_ngu_giong`), và một lượt sinh tiếng nói
       tốn hàng chục giây GPU. Chỉ HUỶ tệp cũ; bước `_dung_giong_rieng_con_thieu`
       của `bao_tri()` (vòng nền, dưới lease) dựng lại tệp mới bằng LÀN MỚI ở
       lượt kế tiếp — đúng cách ③ đầu tệp này giải thích, không phải cách ①
       (sinh ngay, đồng bộ). Xem `_dung_giong_rieng_con_thieu` cho cơ chế đó.

    ⚠️ `db` không dùng tới Ở ĐÂY (chữ ký khớp `giong_vong_doi.khoa_can_xoa(db,
       ho_so)` có chủ ý — hai hàm cùng hình dạng, cùng nhận một hồ sơ và xoá
       khoá kho của nó), nhưng KHÔNG ĐOÁN tên tệp theo kiểu liệt kê: chỉ có
       ĐÚNG MỘT khoá khả dĩ ở phiên bản engine hiện hành
       (`khoa_rieng(owner_id, public_id)`), vì `Storage`
       (`platform_core/storage.py`) không có API liệt-kê-theo-tiền-tố để quét
       những `PHIEN_BAN` cũ hơn. `giong_vong_doi.khoa_can_xoa` (Task 4) đứng
       trước đúng giới hạn này và cũng chỉ tính MỘT khoá cho tệp nghe thử;
       Task 6 (`khoa_can_xoa` → toàn tiền tố) sẽ cần thêm khả năng liệt kê đó
       cho lượt THU HỒI. Đổi làn thì không cần — một giọng chỉ có MỘT bản
       nghe thử sống tại một thời điểm.

    ⛔ KHÔNG NÉM. Người gọi không được hỏng vì một tệp nghe thử không xoá
       được — cùng hợp đồng "không ném" với `dung()`/`co_san()` ở trên.
    """
    khoa = khoa_rieng(str(ho_so.owner_id), str(ho_so.public_id))
    # Đừng để đệm `co_san` nói "có" cho một tệp vừa xoá — xem `_DEM` bên dưới.
    _DEM.pop(khoa, None)
    try:
        from platform_core.storage import get_storage
        get_storage().delete(khoa)
    except Exception as e:  # noqa: BLE001 - xem docstring: khong nem
        log.warning("khong xoa duoc tep nghe thu cu khi doi lan (%s): %s",
                    khoa, e)


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


def dung(khoa: str, *, ref_b64=None, preset=None, ngon_ngu: str = "") -> bool:
    """Sinh MỘT tệp nghe thử rồi cất vào kho. Trả `True` nếu vừa dựng xong.

    `ngon_ngu` là **làn của giọng** — nó chọn câu đọc. Rỗng ⇒ câu tiếng Việt;
    xem `cau_cho_lan` và khối chú thích ở `CAU_THEO_LAN` để biết vì sao tham số
    này thay cho `_t()`.

    ⛔ Không ném ra ngoài. Người gọi là vòng bảo trì và đuôi của job ghi danh —
       cả hai đều **không được** hỏng vì một tệp nghe thử. Một giọng không nghe
       thử được vẫn là một giọng dùng được.
    """
    import io

    from platform_core.storage import get_storage

    from . import features

    if co_san(khoa):
        return False
    try:
        wav, _ = features.goi_cong(cau_cho_lan(ngon_ngu),
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

    Hai NGUỒN thiếu, hai bước riêng:
      ① giọng MẪU (`con_thieu_mau`, danh mục tĩnh `giong_mau.DANH_SACH`);
      ② giọng NHÂN BẢN CỦA KHÁCH đang thiếu (`_dung_giong_rieng_con_thieu`,
         bảng `voice_profile`) — điển hình sau một lượt ĐỔI LÀN
         (`dung_lai_cho_giong` huỷ tệp cũ, bước này dựng tệp mới ở lượt kế).

    ⛔ Bước ② PHẢI CHẠY DÙ BƯỚC ① KHÔNG CÓ GÌ ĐỂ DỰNG — hai nguồn độc lập
       nhau, và một `return` sớm sau bước ① (bản trước D004) từng khiến giọng
       khách đổi làn không bao giờ có tệp nghe thử lại nếu 20 giọng mẫu đã
       warm sẵn (`thieu` rỗng ⇒ hàm thoát trước khi chạm tới giọng khách).
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
    if thieu:
        log.info("nghe thu: con thieu %d giong mau, dung toi da %d luot nay",
                 len(thieu), MOI_LUOT_TOI_DA)
        for g in thieu[:MOI_LUOT_TOI_DA]:
            # Làn đi theo giọng, lấy từ chính danh mục — không phải từ ngôn
            # ngữ của tiến trình bảo trì, thứ chẳng liên quan gì tới giọng này.
            dung(khoa_mau(g.ma), preset=g.ma, ngon_ngu=g.ngon_ngu)
    _dung_giong_rieng_con_thieu()


def _dung_giong_rieng_con_thieu() -> None:
    """Dựng lại tệp nghe thử còn THIẾU cho giọng NHÂN BẢN của khách — bước ②
    của `bao_tri()`, tách khỏi bước ① (giọng mẫu) vì khác NGUỒN dữ liệu.

    🔴 VÌ SAO BƯỚC NÀY TỒN TẠI (D004).

       `routes/_p_giong.py:khai_ngon_ngu_giong` gọi `dung_lai_cho_giong` để
       HUỶ tệp nghe thử cũ ngay khi một khách đổi làn — nhưng nó KHÔNG dựng
       lại đồng bộ (một request HTTP không được giữ GPU hàng chục giây). Nếu
       không có bước này, tệp bị huỷ đó không bao giờ có ai dựng lại: giọng
       vẫn `active`, vẫn dùng được để đọc, nhưng vĩnh viễn "chưa có nghe thử"
       — một hồi quy im lặng mà chỉ hiện ra khi khách bấm nút phát.

    ⭐ DÙNG LẠI ĐÚNG BỘ DỰNG mà `jobs._ghi_danh` dùng ở đuôi job ghi danh
       (`nghe_thu.dung`) — không phải một đường dựng thứ hai. `ref_b64` ở đây
       không có sẵn như lúc job đang chạy (job vừa nhận nó thẳng từ sidecar),
       nên đọc lại qua `tham_chieu.nap_ref_b64(bieu_dien)` — cùng cách các cửa
       khác lấy biểu diễn từ kho. Khác biệt với `jobs._ghi_danh`: ở đây
       `ngon_ngu=ho_so.ngon_ngu` được truyền TƯỜNG MINH bằng làn HIỆN TẠI
       (có thể vừa đổi) — bước này là bước DUY NHẤT biết một giọng vừa đổi
       làn.

    ⛔ CHỈ giọng CỦA CHÍNH KHÁCH (`dung_chung=False`) và ĐANG `active`. Giọng
       kho chung (`dung_chung=True`) CỐ Ý bị loại: dựng nghe thử cho kho
       chung theo làn là phạm vi của một tính năng CHƯA MỞ (kho chung nhiều
       khách dùng — không phải việc của D004); dựng nhầm ở đây tiêu GPU cho
       một luồng chưa ai gọi tới.

    ⚠️ Bỏ qua giọng CHƯA CÓ biểu diễn đang dùng (`tham_chieu.tim_repr_active`
       trả `None`): không có `ref_b64` thì không dựng được gì, và một hồ sơ
       `active` mà không có `VoiceRepr` là dữ liệu không nên có (`jobs.
       _ghi_danh` chỉ chuyển `active` SAU khi ghi biểu diễn) — phòng thủ ở
       đây rẻ hơn để một dòng dữ liệu lạ làm cả lượt bảo trì ném.

    ⛔ TRẦN `TOI_DA_GIONG_RIENG_MOI_LUOT` — cùng lý do `MOI_LUOT_TOI_DA` của
       giọng mẫu: vòng bảo trì chạy CÙNG tiến trình với worker job, dựng quá
       nhiều trong một lượt giữ GPU trong lúc khách khác đang chờ job của họ.
       Đếm theo số tệp ĐÃ DỰNG THẬT, không theo số hồ sơ đã quét — một hồ sơ
       đã có tệp hoặc thiếu biểu diễn không tốn ngân sách này.
    """
    from sqlalchemy import select

    from . import tham_chieu
    from .tables import VoiceProfile
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        ho_so_list = db.execute(
            select(VoiceProfile).where(
                VoiceProfile.trang_thai == "active",
                VoiceProfile.dung_chung.is_(False),
            ).order_by(VoiceProfile.tao_luc.desc())
        ).scalars().all()

        da_dung = 0
        for ho_so in ho_so_list:
            if da_dung >= TOI_DA_GIONG_RIENG_MOI_LUOT:
                break
            khoa = khoa_rieng(str(ho_so.owner_id), str(ho_so.public_id))
            if co_san(khoa):
                continue
            bieu_dien = tham_chieu.tim_repr_active(db, ho_so.id)
            if bieu_dien is None:
                # Không có gì để dựng — xem docstring. Không tính vào trần.
                continue
            try:
                ref_b64 = tham_chieu.nap_ref_b64(bieu_dien)
            except Exception as e:  # noqa: BLE001 - xem docstring `dung()`
                log.warning(
                    "khong doc duoc bieu dien de dung nghe thu rieng %s: %s",
                    ho_so.public_id, e)
                continue
            dung(khoa, ref_b64=ref_b64, ngon_ngu=str(ho_so.ngon_ngu or ""))
            da_dung += 1
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


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
