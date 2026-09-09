"""
ban_doc_dai.py — dựng một bản đọc dài từ nhiều lượt sinh, có thể ĐỌC TIẾP.

## Vì sao có tệp này, khi `/v1/speech-dai` đã ghép được rồi

`/v1/speech-dai` sinh **và** ghép trong MỘT lượt gọi HTTP. Đúng cho một bài vừa
phải, và nó vẫn là đường của bài vừa phải. Nhưng nó có ba trần mà không trần nào
được khai ra, và cả ba chỉ lộ ra ở tài liệu dài:

    ① BỘ NHỚ   — mọi đoạn nằm trong RAM sidecar cùng lúc (xem `noi_dai.ghep_tep`)
    ② THỜI GIAN — một lượt HTTP duy nhất, `timeout=1800`. Một cuốn sách vượt qua.
    ③ HẠT       — một đoạn hỏng ở phút thứ 18 làm hỏng cả lượt, và lượt sau
                  sinh lại từ đoạn 1.

⭐ Ba trần ấy là cùng MỘT nguyên nhân: **không có gì được ghi lại giữa chừng**.
   Cả bài là một giao dịch. Nên tệp này không tối ưu hoá phép ghép — nó chỉ làm
   một việc: **cho từng đoạn một chỗ đứng riêng trên đĩa**.

## Bản kế hoạch nằm ở đâu — và vì sao KHÔNG có bảng CSDL nào

Câu trả lời rõ ràng là một bảng `voice_render_segment` với trạng thái từng đoạn.
Ta **không** làm thế, và lý do không phải lười:

    · phép chia đoạn là TẤT ĐỊNH — cùng văn bản + cùng trần ⇒ cùng danh sách
    · nên "đoạn thứ i là gì" không cần lưu, nó tính lại được
    · và "đoạn thứ i xong chưa" đã có một nguồn chân lý rồi: **tệp có tồn tại
      trong kho không**

Một bảng trạng thái song song với kho là hai nguồn chân lý cho cùng một câu hỏi,
và chúng sẽ lệch: job chết sau khi `put` mà trước khi `commit` thì bảng nói
"chưa" trong khi tệp nói "rồi". Kho tự nó đã là bản kế hoạch.

⇒ Không bảng mới, không migration, không thứ hai để đồng bộ.

## 🔴 KHOÁ THEO `job_id`, VÀ ĐÓ LÀ MỘT ĐÁNH ĐỔI CÓ CHỦ Ý

Khoá đoạn là `voice/seg/{owner}/{job_id}/{i}.wav`, **không** phải một hàm băm
của nội dung. Băm nội dung sẽ cho tái dùng giữa các job khác nhau (khách sửa
một chữ rồi đọc lại thì 79 đoạn kia dùng lại được) — hấp dẫn hơn hẳn.

Nhưng `platform_core/job_content.py` nhận diện tệp của một job bằng cách tìm
**`/{job_id}/` như một đoạn đường dẫn**. Một khoá theo băm nội dung thì không
khớp, và hệ quả đã được ghi lại ngay trong `jobs.py`: tệp **không bao giờ bị
dọn**, trong khi vòng bảo trì vẫn chạy, vẫn báo thành công. Một rò rỉ hoàn toàn
im lặng — đủ giấy tờ nói đã dọn, không tệp nào bị xoá.

⇒ Tái dùng giữa các job là việc CÓ THẬT nhưng nó cần chính sách lưu giữ riêng.
  Mở nó trước khi có chính sách ấy là chọn một tính năng và trả bằng một rò rỉ.

⭐ Và khoá theo `job_id` vẫn đủ cho hai thứ quan trọng nhất, vì nền tảng giữ
   NGUYÊN `job_id` qua các lần thử lại (`job_runner._chay_handler` lấy lại đúng
   hàng `Job` cũ):

       · một đoạn hỏng   -> lần thử sau đọc tiếp từ đoạn ấy
       · máy chủ khởi động lại giữa chừng -> y hệt

   Tức "đừng render lại cả tài liệu" và "đừng bắt đầu lại từ đoạn 1 sau khi
   reboot" đều có, mà không thêm một hàng CSDL nào.
"""
from __future__ import annotations

import logging
import os

from platform_core.i18n import _ as _t

from . import sidecar_client, text_pipeline
from .features import LoiHaTang

log = logging.getLogger(__name__)

#: Số đoạn gửi sidecar mỗi lượt gọi.
#:
#: ⚠️ KHÔNG phải `TRAN_SO_VAN_BAN_BATCH`. Con số kia là kích thước một lượt gộp
#:    lô trên GPU, và `/v1/lo-ra-tep` tự chia nhóm theo nó ở phía trong. Con số
#:    ở đây là **đơn vị ghi vào kho** — tức khoảng cách giữa hai lần ta có thể
#:    dừng an toàn.
#:
#: ⭐ Nhỏ hơn thì mất ít việc hơn khi hỏng, nhưng nhiều lượt HTTP hơn. 8 là chỗ
#:    một lượt gọi vẫn gói trọn một lượt gộp lô đầy đủ, nên không lượt GPU nào
#:    bị chia đôi vì lý do kế toán.
SO_DOAN_MOI_LO = 8

#: Phần trăm dành cho việc sinh. Hai đầu chừa cho lập kế hoạch và cho phép ghép.
_TD_DAU, _TD_CUOI = 5, 85


def khoa_doan(owner_id: str, job_id: str, i: int) -> str:
    """Khoá kho của đoạn thứ `i`.

    🔴 `{job_id}/` — CÓ dấu gạch chéo sau job id. Cùng cái bẫy `jobs.py` đã ghi:
       `job_content.py` tìm `/{job_id}/` như một ĐOẠN đường dẫn, nên
       `.../{job_id}-0001.wav` không khớp và tệp sẽ không bao giờ bị dọn.
    """
    return f"voice/seg/{owner_id or 'chung'}/{job_id or 'adhoc'}/{i:04d}.wav"


def _bao(ctx, phan_tram: int, loi_nhan: str) -> None:
    """Báo tiến độ. Không có `ctx` (gọi trực tiếp trong test) thì im lặng bỏ qua.

    ⛔ Nuốt mọi lỗi: một lượt báo tiến độ hỏng KHÔNG được phép đánh hỏng một bản
       đọc đã sinh xong. Cùng bài học `nghe_thu.dung` — việc phụ không được
       giết việc chính.
    """
    if ctx is None:
        return
    try:
        ctx.progress(max(0, min(100, int(phan_tram))), loi_nhan)
    except Exception as e:                       # noqa: BLE001
        log.debug("bao tien do that bai: %s", e)


def _cong_gen_s(so_ke, d) -> None:
    """Cộng `gen_s` của một lượt gọi vào sổ kê. **Không bao giờ ném.**

    🔴 GPU-GIÂY PHẢI CỘNG DỒN, KHÔNG PHẢI LẤY LƯỢT CUỐI. Một bài dài là nhiều
       lượt `lo_ra_tep`; mỗi lượt trả `gen_s` của **riêng nó**. Ghi đè thay vì
       cộng sẽ cho ra GPU-giây của lô cuối cùng và gọi nó là của cả bài — một
       con số nhỏ hơn sự thật nhiều lần, và **trông hoàn toàn hợp lý**.

    ⚠️ Lượt thử-lại-từng-đoạn cũng cộng vào, có chủ ý: GPU đã thật sự chạy
       ngần ấy. Số này đo **việc máy đã làm**, không đo việc đáng lẽ phải làm.

    ⛔ Nuốt mọi lỗi. Đây là số liệu vận hành đi kèm một lượt sinh **đã thành
       công**; một `TypeError` ở đây biến một chỉ số thiếu thành một job hỏng
       và một khoản credit phải hoàn.
    """
    if so_ke is None:
        return
    try:
        so_ke["gen_s"] = float(so_ke.get("gen_s") or 0.0) + float(
            (d or {}).get("gen_s") or 0.0)
    except (TypeError, ValueError, AttributeError) as e:  # noqa: BLE001
        log.debug("khong cong duoc gen_s: %s", type(e).__name__)


def _sinh_mot_lo(chi_so: list, doan: list, thu_muc: str, *,
                 ref_b64, preset, so_ke: dict | None = None):
    """Sinh một lô đoạn ra tệp tạm. **Hàm sinh**, trả từng `(chi_so, duong)`.

    ⭐ HỎNG CẢ LÔ THÌ THỬ LẠI TỪNG ĐOẠN, và đây không phải sự cẩn thận thừa.

       Một lô là tám đoạn. Nếu một đoạn làm engine ném lỗi thì bảy đoạn kia
       **đã sinh xong trên GPU** cũng mất theo, và lần thử sau của cả job phải
       làm lại cả tám. Chia nhỏ ở đây biến "mất tám" thành "mất một".

    ⚠️ Không thử lại vô hạn và không đổi tham số sinh: `tham_so.py` bị Q119 khoá,
       và một lượt thử thứ hai với cùng đầu vào chỉ có nghĩa vì việc sinh có
       ngẫu nhiên. Hỏng lần hai thì để nó bay lên — nền tảng còn `SO_LAN_THU_JOB`
       lần nữa, và lần ấy sẽ đọc tiếp chứ không làm lại.
    """
    ra_tam = [os.path.join(thu_muc, f"{i:04d}.wav") for i in chi_so]
    try:
        d = sidecar_client.lo_ra_tep([doan[i] for i in chi_so], ra_tam,
                                     ref_b64=ref_b64, preset=preset)
        _cong_gen_s(so_ke, d)
        yield from zip(chi_so, ra_tam)
        return
    except sidecar_client.SidecarBan:
        raise                                    # bận là bận: để job_runner xếp lại
    except Exception as e:                       # noqa: BLE001
        if len(chi_so) == 1:
            raise
        log.warning("lo %d doan hong (%s) — thu lai tung doan",
                    len(chi_so), type(e).__name__)

    # 🔴 SINH RA TỪNG CÁI MỘT, KHÔNG GOM RỒI TRẢ MỘT LẦN — và đây là một lỗi
    #    `tests/test_378` đã bắt được chứ không phải một phòng xa.
    #
    #    Bản đầu gom `xong` rồi `return` cả danh sách. Người gọi cất kho SAU khi
    #    hàm trả về, nên đoạn thứ sáu ném lỗi là bảy đoạn tốt **chưa kịp vào
    #    kho** cũng mất theo — tức bản sửa "thử lại từng đoạn" không cứu được gì
    #    cả, nó chỉ tốn thêm bảy lượt GPU rồi vứt đúng ngần ấy kết quả.
    #
    # ⭐ Là hàm sinh thì mỗi đoạn tới tay người gọi NGAY, và nó vào kho ngay.
    #    Lỗi bay lên ở cuối, sau khi mọi thứ cứu được đã được cứu.
    #
    # ⚠️ Và ĐI HẾT LÔ rồi mới ném: dừng ở đoạn hỏng thì hai đoạn sau nó cũng
    #    mất, dù chúng chẳng liên quan gì. Giữ lỗi ĐẦU TIÊN — nó là lỗi gần
    #    nguyên nhân nhất; những lỗi sau thường là hệ quả.
    loi = None
    for i, duong in zip(chi_so, ra_tam):
        try:
            _cong_gen_s(so_ke, sidecar_client.lo_ra_tep(
                [doan[i]], [duong], ref_b64=ref_b64, preset=preset))
        except sidecar_client.SidecarBan:
            raise
        except Exception as e2:                  # noqa: BLE001
            log.warning("doan %d hong: %s", i, e2)
            loi = loi or e2
            continue
        yield i, duong
    if loi is not None:
        raise loi


def dung(doan: list, *, thu_muc: str, owner_id: str = "", job_id: str = "",
         ref_b64=None, preset=None, ctx=None, so_moi_lo: int | None = None):
    """Dựng bản đọc dài. Trả `(duong_tep_ra, ho_so_ghep)`.

    `thu_muc` là thư mục tạm do người gọi sở hữu và dọn — ở đây không xoá gì,
    vì một hàm vừa tạo tệp vừa quyết định lúc nào xoá chúng là một hàm hai chủ.
    """
    if not doan:
        raise LoiHaTang(_t("Không có đoạn nào để đọc."))

    from platform_core.storage import get_storage
    st = get_storage()
    n = len(doan)
    moi_lo = max(1, int(so_moi_lo or SO_DOAN_MOI_LO))

    # ── 1. KIỂM KHO TRƯỚC KHI SINH BẤT CỨ GÌ ────────────────────────────────
    #
    # Đây là toàn bộ phép "đọc tiếp". Không cờ, không bảng trạng thái: tệp có
    # trong kho nghĩa là đoạn ấy xong, và đó là nguồn chân lý duy nhất.
    duong = [None] * n
    con_lai = []
    for i in range(n):
        p = st.local_path(khoa_doan(owner_id, job_id, i))
        if p:
            duong[i] = p
        else:
            con_lai.append(i)

    da_co = n - len(con_lai)
    if da_co:
        log.info("job %s: doc tiep — %d/%d doan da co trong kho",
                 job_id[:8] if job_id else "?", da_co, n)
    _bao(ctx, _TD_DAU, _t("Chuẩn bị {n} đoạn").format(n=n))

    # ── 2. sinh phần còn thiếu, GHI VÀO KHO SAU MỖI LÔ ──────────────────────
    #
    # ⭐ Sổ kê GPU-giây. Nó đi **cùng** vòng sinh chứ không đo lại sau, vì
    #    không có cách nào đo lại: `gen_s` chỉ tồn tại trong phản hồi của từng
    #    lượt `lo_ra_tep`, và phản hồi ấy không được lưu ở đâu.
    _so_ke: dict = {"gen_s": 0.0}
    for k in range(0, len(con_lai), moi_lo):
        lo = con_lai[k:k + moi_lo]
        for i, tam in _sinh_mot_lo(lo, doan, thu_muc,
                                   ref_b64=ref_b64, preset=preset,
                                   so_ke=_so_ke):
            khoa = khoa_doan(owner_id, job_id, i)
            # Luồng tệp, KHÔNG `read()`: `LocalStorage.put` dùng
            # `shutil.copyfileobj`, nên đưa nó một handle là chép theo khối.
            # Đọc cả tệp vào bộ nhớ ở đây là dựng lại đúng cái trần mà cả tệp
            # này sinh ra để gỡ.
            with open(tam, "rb") as f:
                st.put(khoa, f, content_type="audio/wav")
            duong[i] = st.local_path(khoa) or tam
        xong = da_co + k + len(lo)
        _bao(ctx, _TD_DAU + (_TD_CUOI - _TD_DAU) * xong // max(1, n),
             _t("Đã đọc {a}/{b} đoạn").format(a=xong, b=n))

    thieu = [i for i, d in enumerate(duong) if not d]
    if thieu:
        raise LoiHaTang(_t("Thiếu {n} đoạn sau khi sinh.").format(n=len(thieu)))

    # ── 3. ghép ─────────────────────────────────────────────────────────────
    _bao(ctx, _TD_CUOI, _t("Đang ghép {n} đoạn").format(n=n))
    ra = os.path.join(thu_muc, "tieng.wav")
    ho_so = sidecar_client.ghep_tep(
        duong, ra, so_cau=[text_pipeline.dem_cau(t) for t in doan])
    if not os.path.isfile(ra):
        raise LoiHaTang(_t("Ghép xong nhưng không thấy tệp kết quả."))
    # ⛔ `ho_so` đến từ `ghep_tep`, và `ghep_tep` KHÔNG chạy model — nó không
    #    biết gì về GPU-giây. Cộng sổ kê vào đây là chỗ duy nhất con số ấy còn
    #    sống sót ra khỏi hàm này.
    #
    # ⚠️ Ghi ĐÈ chứ không `setdefault`: nếu ngày nào `ghep_tep` bắt đầu trả một
    #    khoá `gen_s` của riêng nó, hai nguồn sẽ tranh nhau — và nguồn đúng cho
    #    câu hỏi "bài này tốn bao nhiêu GPU" là sổ kê của vòng SINH.
    ho_so = dict(ho_so or {})
    ho_so["gen_s"] = round(float(_so_ke.get("gen_s") or 0.0), 3)
    return ra, ho_so
