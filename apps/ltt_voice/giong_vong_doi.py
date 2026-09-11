"""
giong_vong_doi.py — VÒNG ĐỜI và XUẤT XỨ NGÔN NGỮ của một Voice Profile.

Tách khỏi `tables.py` (chỉ khai bảng) và `tham_chieu.py` (chạm CSDL/kho) vì đây
là **luật của trạng thái**: một giọng được đi từ đâu tới đâu, và một giá trị
`ngon_ngu` hiện có được sửa khi nào. Cả hai đều là quy tắc thuần, test được mà
không cần CSDL — nên chúng ở một tệp thuần.

⭐ VÌ SAO XUẤT XỨ NGÔN NGỮ LÀ MỘT GIÁ TRỊ, KHÔNG PHẢI MỘT PHÉP ĐOÁN (D003).

   Cột `voice_profile.ngon_ngu` có từ đầu, nhưng cửa ghi danh **chưa bao giờ đặt
   nó** — nên mọi giọng nhân bản, kể cả giọng mà tên hiển thị là tiếng Anh, đều
   mang `ngon_ngu = "vi"` do mặc định của cột (đo 01/09/2026, `test_384`). Đó
   chính là điều một kho giọng production KHÔNG được làm: **khẳng định một ngôn
   ngữ mà nó chưa từng thu thập, rồi coi đó là sự thật.**

   D003 (2026-09-11) chốt ba nguồn, và **chỉ ba**:
     ① `khai_bao`     — khách TỰ NÓI lúc ghi danh. Nguồn đáng tin nhất.
     ② `do_asr`       — máy ĐO bằng ASR sau khi có bản ghi (WS khác). Vì là một
                        PHÉP ĐO, sửa nó đòi bằng chứng cùng cấp — xem
                        `khai_lan_hop_le`.
     ③ `mac_dinh_cu`  — dòng có TRƯỚC tính năng này; `ngon_ngu` của chúng là một
                        MẶC ĐỊNH cột, không phải một khoản khai hay một phép đo.
                        Migration `20260911_1000_voice_ngon_ngu_nguon` đặt giá
                        trị này cho mọi dòng đang có.

⛔ D003 BỎ nhánh "chưa biết" của bản nháp cũ (`chua_biet`, `ngon_ngu=""`). Ghi
   danh RC1 luôn khai một làn — không còn đường nào để lại một giọng không rõ
   làn lúc ghi danh xong; xem `khai_lan_hop_le` bên dưới cho ràng buộc sửa sau.

⛔ KHÔNG SAO CHÉP THUẬT TOÁN ĐỐI CHIẾU CỦA WS01 (`lan_ngon_ngu.py`). Tệp này chỉ
   **lưu** làn nguồn cho đúng, và dùng `lan_ngon_ngu.LAN_HOP_LE` làm thẩm quyền
   cho danh sách làn — việc đối chiếu văn bản với làn vẫn là của WS01.
"""
from __future__ import annotations

from . import lan_ngon_ngu

# ── Trạng thái vòng đời ──────────────────────────────────────────────────────
#
# `dang_ghi_danh` → `active`               (job ghi danh xong, có biểu diễn)
#                 → `loi`                  (job ghi danh hỏng vĩnh viễn)
# `active`        → `disabled`             (khách tắt, ĐẢO NGƯỢC được)
# `disabled`      → `active`               (bật lại)
# `active`/`disabled`/`loi` → `revoked`    (THU HỒI: xoá dữ liệu sinh trắc,
#                                           KHÔNG đảo ngược; giữ lịch sử + bút
#                                           toán)
#
# ⛔ T-07: `dang_ghi_danh` KHÔNG chuyển thẳng sang `revoked`. Đang ghi danh
#    nghĩa là chưa có biểu diễn engine để thu hồi — cửa thu hồi phải chờ job
#    xong (`active`/`loi`) rồi mới thu hồi, không được nhảy cóc qua một trạng
#    thái chưa từng tồn tại đủ để xoá.
#
# ⛔ `revoked` khác `disabled` ở CHIỀU KHÔNG QUAY LẠI ĐƯỢC và ở HỆ QUẢ với dữ
#    liệu: `disabled` chỉ tắt đường dùng, mọi tệp còn nguyên (điều khoản hứa giữ
#    clip gốc để dựng lại giọng khi nâng engine). `revoked` là quyền được xoá của
#    khách — nó **xoá clip nguồn, biểu diễn và tệp nghe thử**, và cố ý phá lời
#    hứa "dựng lại được" đó, vì dữ liệu sinh trắc thuộc về người, không thuộc về
#    ta. Lịch sử lượt tạo và bút toán credit thì GIỮ, để không làm mồ côi tiền đã
#    thu — đúng lý do `tables.py` không có trạng thái `deleted` (xoá cả hàng).
TT_DANG_GHI_DANH = "dang_ghi_danh"
TT_ACTIVE = "active"
TT_DISABLED = "disabled"
TT_REVOKED = "revoked"
#: 🔴 Hỏng ghi danh có một trạng thái RIÊNG. Trước đó một job ghi danh hỏng để lại
#:    giọng ở `dang_ghi_danh` **vĩnh viễn**, và `features.giai_giong` nói mãi câu
#:    *"chưa ghi danh xong, thử lại sau"* — một lời hứa không bao giờ thành. `loi`
#:    là một trạng thái CUỐI hiện được ra giao diện: khách biết cần ghi danh lại.
#:
#: ⚠️ CHUYỂN VÀO `loi` LÀ VIỆC CỦA WORKER — tệp này chỉ **định nghĩa** trạng
#:    thái và luật chuyển; nó không tự đặt được vì nó không chạy trong worker.
TT_LOI = "loi"

TRANG_THAI_HOP_LE = frozenset(
    {TT_DANG_GHI_DANH, TT_ACTIVE, TT_DISABLED, TT_REVOKED, TT_LOI})

#: Chuyển trạng thái CHO PHÉP (spec §6.3). Khai tường minh để một cửa mới không
#: lặng lẽ đưa một giọng đi một đường vô nghĩa (vd `revoked` → `active`: dữ liệu
#: đã xoá, bật lại là bật một cái vỏ rỗng).
_CHUYEN = {
    TT_DANG_GHI_DANH: {TT_ACTIVE, TT_LOI},
    TT_ACTIVE: {TT_DISABLED, TT_REVOKED},
    TT_DISABLED: {TT_ACTIVE, TT_REVOKED},
    TT_LOI: {TT_REVOKED},
    TT_REVOKED: set(),  # cuối đường — không quay lại (INV-THU-HOI-1)
}


def co_the_chuyen(tu: str, den: str) -> bool:
    """Có được chuyển từ trạng thái `tu` sang `den` không.

    Dùng ở cửa thu hồi/tắt để không phụ thuộc vào việc mỗi cửa tự nhớ luật.
    """
    return den in _CHUYEN.get(tu, set())


# ── Làn ngôn ngữ nguồn + xuất xứ (D003) ──────────────────────────────────────

#: Xuất xứ của giá trị `ngon_ngu` — trả lời "vì sao ta tin làn này", và ba giá
#: trị này là **thẩm quyền duy nhất** cho cột `voice_profile.ngon_ngu_nguon`.
NGUON_KHAI_BAO = "khai_bao"        # khách tự khai lúc ghi danh
NGUON_DO_ASR = "do_asr"            # máy ĐO bằng ASR sau khi có bản ghi
NGUON_MAC_DINH_CU = "mac_dinh_cu"  # dòng có trước tính năng này (migration)

NGUON_HOP_LE = (NGUON_KHAI_BAO, NGUON_DO_ASR, NGUON_MAC_DINH_CU)


def khai_lan_hop_le(lan_moi: str, *, lan_hien: str, nguon_hien: str) -> str:
    """Khách xin sửa làn hiện có sang `lan_moi` — có được không?

    Trả `""` khi được, hoặc một mã lỗi ỔN ĐỊNH (Public API + GUI đọc mã, không
    đọc câu chữ — câu chữ đổi theo ngôn ngữ giao diện):

      `"voice_language_required"`  `lan_moi` không thuộc `lan_ngon_ngu.LAN_HOP_LE`
                                    — không có làn thứ ba, và không có "tự đoán".
      `"voice_language_measured"`  làn hiện tại đến từ một PHÉP ĐO ASR
                                    (`nguon_hien == NGUON_DO_ASR`) và khách xin
                                    đổi sang một làn KHÁC làn đã đo.

    ⭐ VÌ SAO `do_asr` CHẶN CÒN `khai_bao`/`mac_dinh_cu` THÌ KHÔNG.

       `do_asr` là bằng chứng đo được từ chính bản ghi âm — một khoản khai tay
       muốn ghi đè nó phải trả lời được "vì sao phép đo sai", và cửa này không
       phải chỗ trả lời câu đó (đó là việc đo lại, T-04 không mở đường tắt).
       `khai_bao` (khách tự nói) và `mac_dinh_cu` (chưa ai đo, chưa ai khai) thì
       không có bằng chứng nào bị ghi đè — sửa tự do là đúng.

    ⚠️ Khách xin đổi SANG ĐÚNG làn đã đo (`lan_moi == lan_hien` khi `do_asr`) là
       một no-op hợp lệ, không phải một xung đột — trả `""`.
    """
    lan = lan_ngon_ngu.chuan_lan(lan_moi)
    if lan not in lan_ngon_ngu.LAN_HOP_LE:
        return "voice_language_required"
    if nguon_hien == NGUON_DO_ASR and lan != lan_ngon_ngu.chuan_lan(lan_hien):
        return "voice_language_measured"
    return ""


# ── Thu hồi: những khoá kho phải xoá ─────────────────────────────────────────

def khoa_can_xoa(owner_id: str, public_id: str) -> str:
    """TIỀN TỐ kho phải coi là bị xoá khi THU HỒI một giọng (T-07).

    🔴 Task 4 (`db, ho_so -> list[str]`, xem `khoa_da_biet` — hàm CHỊ EM ngay
       dưới đây) chỉ tính được từng khoá NÓ BIẾT (từ `VoiceRef`/`VoiceRepr` +
       một khoá nghe thử suy được). Đó không phải "mọi khoá dưới tiền tố":
       `platform_core.storage` (`Storage`/`LocalStorage`,
       `platform_core/storage.py`) KHÔNG có API liệt-kê-theo-tiền-tố, nên
       không hàm nào ở tầng app này biết chắc CÓ hay KHÔNG một tệp lạ nằm
       cùng thư mục mà không hàng CSDL nào trỏ tới (vd một `preview-*` phiên
       bản engine CŨ, còn sống từ trước một lần nâng cấp).

    ⭐ HÀM NÀY VẪN CÓ ÍCH dù không tự xoá được gì bằng nó một mình:
         ① căn cứ để LOG một cảnh báo vận hành ("dọn tay mọi thứ còn sót dưới
           tiền tố này nếu có"), cho `_thu_hoi_mot` (`routes/_p_giong.py`);
         ② chỗ một backend liệt-kê-được-theo-tiền-tố sau này (R2 có
           `list_objects_v2`, hay `LocalStorage` được thêm một hàm xoá cả thư
           mục) cắm vào mà không đổi chữ ký gọi từ route — xem README của
           Task 6 (task-6-report.md) cho lý do KHÔNG thêm hàm đó vào
           `platform_core/storage.py` ở lượt này (thay đổi tầng nền tảng, cần
           một quyết định riêng, không phải việc âm thầm chèn vào một task app).

    ⛔ THUẦN — không chạm CSDL, không chạm kho. Chỉ nối chuỗi, nên không bao
       giờ ném và không cần `db`.
    """
    return f"voice/{owner_id}/{public_id}/"


def khoa_da_biet(db, ho_so) -> list[str]:
    """Mọi khoá `platform_core.storage` mà TA BIẾT CHẮC phải xoá khi THU HỒI
    `ho_so` — không phải "mọi khoá dưới tiền tố" (đó là `khoa_can_xoa`, hàm
    chị em ngay trên; đọc docstring của nó để biết vì sao hai hàm tách nhau).

    Gom TỪ DỮ LIỆU chứ không đoán tên tệp:
      · clip nguồn      — `storage_key` của mọi `VoiceRef` của giọng này;
      · biểu diễn engine — `storage_key` của mọi `VoiceRepr` (chứa `speaker_emb`,
                          thứ `tables.py` nói thẳng là "KHÔNG BAO GIỜ ra ngoài");
      · tệp nghe thử     — khoá HIỆN HÀNH suy được từ `(owner_id, public_id)`
                          (`nghe_thu.khoa_rieng`). Chỉ MỘT phiên bản — một
                          bản nghe thử của một `PHIEN_BAN` engine cũ hơn (nếu
                          còn sót từ trước một lần nâng cấp) sẽ KHÔNG bị liệt
                          ở đây, vì không có cách liệt kê nó (xem `khoa_can_xoa`).

    ⛔ Tệp KẾT QUẢ (`voice/out/{uid}/{job_id}/…`) KHÔNG nằm ở đây: nó thuộc về
       một LƯỢT TẠO, có `job_id`, và đã được `job_content.py` dọn theo hạn 30
       ngày. Thu hồi một giọng không được xoá các bản thu âm khách đã tải về là
       sản phẩm của họ.

    Trả về danh sách khoá (có thể có trùng nếu hai ref cùng khoá — người gọi tự
    khử trùng khi xoá).
    """
    from . import nghe_thu  # lazy: tránh vòng import ở tầng module
    from .tables import VoiceRef, VoiceRepr
    from sqlalchemy import select

    khoa: list[str] = []
    try:
        for r in db.execute(
                select(VoiceRef.storage_key)
                .where(VoiceRef.profile_id == int(ho_so.id))).scalars():
            if r:
                khoa.append(str(r))
        for r in db.execute(
                select(VoiceRepr.storage_key)
                .where(VoiceRepr.profile_id == int(ho_so.id))).scalars():
            if r:
                khoa.append(str(r))
    except Exception:  # noqa: BLE001 - đọc khoá để xoá; hỏng thì vẫn xoá được
        import logging                                 # phần đã gom, đừng dừng
        logging.getLogger(__name__).warning(
            "khong doc het duoc khoa kho de thu hoi %s", ho_so.public_id,
            exc_info=True)
    # Tệp nghe thử riêng — cùng thư mục giọng, tên `preview-*`.
    khoa.append(nghe_thu.khoa_rieng(str(ho_so.owner_id), str(ho_so.public_id)))
    return khoa


# ── Bảo trì: dọn hồ sơ TREO ở `dang_ghi_danh` (review round 2, IMPORTANT B) ──

#: Bao lâu thì một hồ sơ còn `dang_ghi_danh` bị coi là TREO. Rộng hơn NHIỀU so
#: với `max_runtime_s["ltt_voice.enroll"] = 300` (5 phút, `manifest.py`) nhân
#: `SO_LAN_THU_JOB` (5, `tham_so_cong_khai.py`) cộng giãn cách giữa các lượt
#: thử lại — đủ để không bắt nhầm một lượt vẫn đang thử lại hợp lệ, nhưng vẫn
#: đủ hẹp để một hồ sơ THẬT SỰ mồ côi không sống hàng ngày trời.
PHUT_TREO_GHI_DANH = 60


def don_ghi_danh_treo(db) -> int:
    """AN TOÀN CUỐI CÙNG cho T-14 (review round 2, IMPORTANT B): dọn những hồ
    sơ mắc kẹt ở `dang_ghi_danh` mà KHÔNG CÒN JOB NÀO đang chạy/chờ để hoàn
    tất nó, bất kể vì sao job đó biến mất.

    🔴 VÌ SAO CẦN, DÙ `jobs.handle` ĐÃ CÓ AN TOÀN CUỐI RIÊNG (IMPORTANT 1/A,
       Task 6 review round 1+2).

       An toàn cuối của `handle()` chỉ chạy khi CHÍNH job đó ném một exception
       mà tiến trình worker BẮT ĐƯỢC trong cùng lời gọi `ham(params, ctx)`. Có
       những đường một lượt thử KHÔNG BAO GIỜ chạm khối `except` đó:
         · orphan reaper (`platform_core/job_runner.py`) — một job `running`
           lâu không đập nhịp (worker chết cứng, mất điện, OOM-killer) bị coi
           là mồ côi và `fail()` TỪ MỘT TIẾN TRÌNH KHÁC, không chạy lại
           handler của lượt đã chết;
         · runtime watchdog (`_canh_gio`/`_het_gio`) — job vượt
           `max_runtime_s` bị GIẾT tiến trình, không handler nào kịp chạy tới
           một dòng Python nào, kể cả một khối `except`.
       Cả hai đường đều có thể tiêu HẾT `SO_LAN_THU_JOB` lượt mà không một
       lượt nào từng thực thi `handle()`'s `except Exception`.

    ⛔ CHỈ đụng vào một hồ sơ khi CHẮC CHẮN không còn job nào đang tham chiếu
       nó — một hồ sơ vừa nộp job (`tao_giong`) vài giây trước, còn nằm trong
       `queued`, KHÔNG được đặt `loi` chỉ vì nó cũng đang `dang_ghi_danh` (đó
       là lý do có cả ngưỡng `PHUT_TREO_GHI_DANH` LẪN phép kiểm job đang sống
       — một mình ngưỡng thời gian không đủ, vì `bao_tri()` chạy mỗi GIỜ và
       một hồ sơ mới nộp có thể trùng đúng lúc lượt bảo trì chạy).

    Trả về SỐ HỒ SƠ vừa đặt `loi`, để nơi gọi (`nghe_thu.bao_tri`) ghi log.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from .tables import VoiceProfile

    han = datetime.now(timezone.utc) - timedelta(minutes=PHUT_TREO_GHI_DANH)
    ung_vien = db.execute(
        select(VoiceProfile.id, VoiceProfile.public_id)
        .where(VoiceProfile.trang_thai == TT_DANG_GHI_DANH,
              VoiceProfile.tao_luc < han)
    ).all()
    if not ung_vien:
        return 0

    con_job = _cac_public_id_con_job_enroll(db, [pid for _id, pid in ung_vien])

    so_dat = 0
    for prof_id, public_id in ung_vien:
        if public_id in con_job:
            continue
        ket = db.execute(
            VoiceProfile.__table__.update()
            .where(VoiceProfile.id == prof_id,
                  VoiceProfile.trang_thai == TT_DANG_GHI_DANH)
            .values(trang_thai=TT_LOI))
        so_dat += int(ket.rowcount or 0)
    return so_dat


def _cac_public_id_con_job_enroll(db, public_ids) -> set:
    """Trong `public_ids`, cái nào còn một job `ltt_voice.enroll` ĐANG CHỜ
    (`queued`) hoặc ĐANG CHẠY (`running`) tham chiếu tới.

    ⚠️ LỌC JSON BẰNG PYTHON, KHÔNG BẰNG SQL. `Job.params` khai kiểu `JSON`
       (không phải `JSONB`), và cú pháp truy vấn vào trong nó KHÁC NHAU giữa
       PostgreSQL (production) và SQLite (test) — một truy vấn JSON viết cho
       một bên sẽ xanh ở bên đó và đỏ ở bên kia. Cùng bài học đã ghi ở
       `du_an.py` (`⚠️ Lọc JSON bằng PYTHON, không bằng SQL`): lọc theo cột có
       CHỈ MỤC (`app_slug`/`job_type`/`status`) ở SQL trước, rồi lọc khoá JSON
       trong Python trên một tập đã bị chặn nhỏ (chỉ job `queued`/`running`
       của đúng job_type này — không phải toàn bộ lịch sử job).

    ⚠️ `params["voice_id"]` — ĐÚNG khoá `routes/_p_giong.py::tao_giong` đặt
       khi nộp job (`params = {"owner_id": ..., "voice_id": ho_so.public_id,
       ...}`), không phải `"public_id"`.
    """
    if not public_ids:
        return set()
    from sqlalchemy import select

    from platform_core.models import JOB_QUEUED, JOB_RUNNING, Job

    hang = db.execute(
        select(Job.params).where(
            Job.app_slug == "ltt_voice",
            Job.job_type == "ltt_voice.enroll",
            Job.status.in_((JOB_QUEUED, JOB_RUNNING)))
    ).scalars().all()
    muon = set(public_ids)
    ra: set = set()
    for params in hang:
        pid = str((params or {}).get("voice_id") or "")
        if pid in muon:
            ra.add(pid)
    return ra
