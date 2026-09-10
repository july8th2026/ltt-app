"""Ảnh chụp hằng tuần cho máy khách, giữ đúng một bản.

## Vì sao ảnh chụp chứ không phải `vzdump`

Trang bán hứa "sao lưu hằng tuần, giữ 1 bản" từ trước khi có mã nào làm việc đó.
Khi đi làm thật thì `vzdump` không chạy được: nó ghi ra một kho kiểu `dir`, và
kho `dir` duy nhất trên node (`local`) còn **2,2 GiB** — không đủ cho một máy,
nói gì tới mọi máy mỗi tuần.

Ảnh chụp trên LVM-thin thì ngược lại: tạo trong vài giây, và **gần như không tốn
chỗ lúc tạo** — chỉ khối nào bị ghi đè về sau mới chiếm. Đó là thứ dùng được cho
mọi máy hằng tuần với hạ tầng đang có.

## Nhưng phải nói đúng nó là gì

**Ảnh chụp KHÔNG phải bản sao lưu.** Nó nằm trên **cùng kho** với đĩa gốc; pool
hỏng là mất cả hai. Nó cứu khách khỏi *lỗi của chính họ* — xoá nhầm thư mục, một
bản vá làm hỏng máy, một phần mềm cài vào rồi không gỡ được — chứ không cứu khỏi
hỏng phần cứng.

Nên trang bán phải viết đúng như vậy, và nó đã được sửa. Hứa "sao lưu" rồi giao
một ảnh chụp là loại lời hứa mà người ta chỉ phát hiện sai đúng vào lúc mất dữ
liệu, tức lúc tệ nhất có thể.

## Crash-consistent, và điều đó có nghĩa gì

Máy khách không có guest agent (agent là thiết bị virtio, mà virtio treo trên cụm
này — xem `mang.py`). Nên không có ai bảo Windows "xả bộ đệm rồi đứng yên" trước
khi chụp. Ảnh chụp vì thế giống như **rút điện rồi bật lại**: NTFS có nhật ký nên
thường lên bình thường, nhưng một cơ sở dữ liệu đang ghi dở thì không có gì bảo
đảm.

**Đo thật 24/08, và nó rõ hơn mọi lời giải thích:** một tệp được ghi *ba giây
trước* khi chụp đã **không có** trong ảnh — nó còn nằm trong bộ đệm của guest.
Chạy lại đúng phép thử đó kèm `sync` thì tệp còn nguyên. Nghĩa là ảnh chụp giữ
được **những gì đã xuống đĩa**, không phải "mọi thứ tại thời điểm chụp".

Trong thực tế, Windows xả bộ đệm sau vài giây nên khoảng mất là nhỏ. Nhưng đừng
mô tả tính năng này là "khôi phục về đúng phút đó" — nó không phải vậy, và người
duy nhất phát hiện ra sự khác biệt sẽ là người đang cần khôi phục.

## Giữ ĐÚNG một bản, và tạo **xong** trước khi xoá

Tạo bản mới **rồi** mới xoá bản cũ. Ngược lại thì có một khoảng — dài bằng thời
gian tạo — mà khách **không có bản nào**, và đó đúng là khoảng mà một sự cố sẽ
tìm tới.

⚠️ **"Tạo xong", không phải "đã gửi lệnh tạo".** Bản trước VPS V2 gọi `chup_anh()`
   rồi hỏi danh sách ảnh và xoá bản thừa **ngay lập tức** — trong khi `chup_anh`
   chỉ trả về một UPID và Proxmox còn đang làm việc ở nền. Hai hệ quả, và cái thứ
   hai mới là cái đắt:

   1. ảnh mới thường **chưa hiện** trong danh sách, nên lượt dọn không thấy nó và
      không xoá gì — vô hại;
   2. nhưng `bao_tri` vẫn ghi `sao_luu_luc = now` **dù tác vụ sau đó thất bại**.
      Máy khoe "Ảnh chụp gần nhất: hôm nay" cho một bản **không tồn tại**, và
      `den_han_chup` sẽ không chụp lại trong bảy ngày. Khách phát hiện đúng vào
      lúc cần khôi phục.

   ⇒ Từ VPS V2: chờ tác vụ kết thúc OK, **xác minh ảnh có mặt đúng tên**, rồi mới
     dọn bản cũ và mới trả tên về cho người gọi ghi sổ.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from apps.vps.services import tac_vu

log = logging.getLogger(__name__)

#: Bao lâu chụp một lần.
MOI_NGAY = 7

#: Giữ bao nhiêu bản. Một — đúng như trang bán nói.
GIU = 1

#: Tiền tố tên ảnh. Chỉ ảnh mang tiền tố này mới bị dọn: ảnh do chủ nhà tự tạo
#: bằng tay trên Proxmox **không phải việc của vòng bảo trì**, và xoá nhầm một
#: ảnh người khác đang dựa vào là mất dữ liệu của họ.
TIEN_TO = "ltt"

_TEN = re.compile(rf"^{TIEN_TO}[0-9]{{8}}(_[0-9]{{4}})?$")


class SaoLuuError(RuntimeError):
    """Không chụp hoặc không khôi phục được."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ten_anh(luc: datetime | None = None) -> str:
    """Tên ảnh cho một thời điểm.

    Proxmox chỉ nhận `[A-Za-z0-9_-]` và tên phải **bắt đầu bằng chữ**, nên không
    dùng được dạng `2026-08-24`. Kèm giờ-phút để hai lần chụp trong cùng ngày
    (chụp tay rồi chụp theo lịch) không đụng tên nhau.
    """
    luc = luc or _now()
    return f"{TIEN_TO}{luc.strftime('%Y%m%d_%H%M')}"


def cua_ta(ten: str) -> bool:
    return bool(_TEN.match(str(ten or "")))


def den_han_chup(may, *, now: datetime | None = None) -> bool:
    """Máy này tới kỳ chụp chưa?

    Máy chưa có `vmid` (đang tạo) hoặc đã xoá thì không. Máy **bị treo** thì
    **có** — nó còn 7 ngày ân hạn trước khi bị xoá, và mất dữ liệu trong 7 ngày
    đó vì ta ngừng chụp là một cách phạt kèm không ai công bố.
    """
    if not getattr(may, "vmid", None):
        return False
    if str(getattr(may, "trang_thai", "")) in ("da_xoa", "dang_tao"):
        return False
    luc = getattr(may, "sao_luu_luc", None)
    if luc is None:
        return True
    if luc.tzinfo is None:
        luc = luc.replace(tzinfo=timezone.utc)
    return luc <= (now or _now()) - timedelta(days=MOI_NGAY)


#: Chờ tối đa cho một tác vụ chụp/xoá ảnh (giây).
#:
#: Ảnh chụp LVM-thin xong trong vài giây, nhưng một node đang tải nặng có thể
#: chậm hơn nhiều. 10 phút là trần để một lượt bảo trì không đứng lại vì một máy.
HAN_CHUP_S = 10 * 60


class AnhKhongXuatHien(SaoLuuError):
    """Tác vụ báo OK nhưng ảnh **không có mặt** trong danh sách.

    Hiếm, và chính vì hiếm nên nó là loại lỗi không ai kiểm: nếu không hỏi lại,
    ta ghi `sao_luu_luc` cho một bản không tồn tại và khách chỉ biết lúc cần
    khôi phục — tức lúc tệ nhất có thể.
    """


def co_anh(client, vmid: int, ten: str) -> bool:
    """Ảnh mang đúng tên này có thật trên máy chủ không."""
    return any(str(x.get("name")) == ten for x in client.danh_sach_anh(vmid))


def chup_va_don(client, may, *, now: datetime | None = None,
                nhip: tac_vu.Nhip = tac_vu.NHIP_THAT) -> str:
    """Chụp một bản mới, **xác minh nó có thật**, rồi mới xoá bản cũ.

    Trả tên ảnh vừa tạo. Ném `SaoLuuError`/`AnhKhongXuatHien` nếu không tạo được
    — người gọi **không** được ghi `sao_luu_luc` khi có ngoại lệ.

    Bốn bước, và thứ tự của chúng là cả nội dung của hàm:

    1. gửi lệnh chụp;
    2. **chờ tác vụ nền kết thúc và kiểm `exitstatus`** — `chup_anh` chỉ trả UPID;
    3. **hỏi lại danh sách xem ảnh có mặt đúng tên chưa** — tác vụ OK vẫn có thể
       không để lại thứ ta mong đợi, và đây là chỗ duy nhất phát hiện được;
    4. chỉ khi đó mới dọn bản cũ.

    Lỗi lúc **dọn** bản cũ không làm hỏng cả việc: bản mới đã có và đã kiểm, còn
    bản cũ thừa chỉ tốn chỗ chứ không mất gì. Lượt sau dọn tiếp.
    """
    ten = ten_anh(now)
    try:
        upid = client.chup_anh(may.vmid, ten, mo_ta="LTT VPS - anh chup hang tuan")
        tac_vu.cho_xong(client, str(upid), han_s=HAN_CHUP_S, nhip=nhip)
    except tac_vu.TacVuLoi as exc:
        raise SaoLuuError(f"khong chup duoc anh: {exc}") from exc

    if not co_anh(client, may.vmid, ten):
        raise AnhKhongXuatHien(
            f"tac vu bao OK nhung anh {ten!r} khong co trong danh sach")

    cu = sorted((x.get("name") for x in client.danh_sach_anh(may.vmid)
                 if cua_ta(x.get("name"))), reverse=True)
    for thua in cu[GIU:]:
        if thua == ten:
            continue
        try:
            client.xoa_anh(may.vmid, thua)
        except Exception as exc:                 # noqa: BLE001
            # Bắt rộng có chủ ý và CHỈ ở đây: bản mới đã tạo xong VÀ đã xác minh,
            # nên không lý do gì để một lỗi dọn dẹp làm cả lượt bảo trì hỏng.
            log.warning("VPS: khong xoa duoc anh cu %s cua may %s: %s",
                        thua, may.id, exc)
    return ten


def anh_moi_nhat(client, vmid: int) -> str:
    """Tên ảnh mới nhất của ta, hoặc chuỗi rỗng."""
    cua = sorted((x.get("name") for x in client.danh_sach_anh(vmid)
                  if cua_ta(x.get("name"))), reverse=True)
    return cua[0] if cua else ""


def doc_duoc(ten: str) -> str:
    """`ltt20260824_1930` → `24/08/2026 19:30`. Tên máy đọc không phải tên khách đọc."""
    if not cua_ta(ten):
        return str(ten or "")
    lo = ten[len(TIEN_TO):]
    ngay = f"{lo[6:8]}/{lo[4:6]}/{lo[0:4]}"
    return f"{ngay} {lo[9:11]}:{lo[11:13]}" if len(lo) >= 13 else ngay


# ── Khôi phục ───────────────────────────────────────────────────────────────
#
# Job type RIÊNG, không dùng chung `vps.control`: khôi phục là thao tác **phá
# huỷ dữ liệu** và nó có trần thời gian khác hẳn (tắt máy + rollback + bật lại).
# Gộp vào một job type là làm mất khả năng đặt hai trần khác nhau và mất luôn
# khả năng đọc log theo loại việc.

JOB_TYPE = "vps.snapshot"

#: Chờ tối đa cho tác vụ rollback (giây). Rollback trên LVM-thin là thao tác
#: siêu dữ liệu — vài giây. Trần rộng để chịu được một node đang tải nặng.
HAN_KHOI_PHUC_S = 10 * 60


def xin_khoi_phuc(db, may, ten: str, *, boi: str, now: datetime | None = None):
    """Khách xin khôi phục về một ảnh chụp. Mở thao tác + nộp job. Trả thao tác.

    **Không chạm Proxmox** — cùng lý do với `dieu_khien.xin`: một lần khôi phục
    đầy đủ (tắt → chờ STOPPED → rollback → chờ → bật lại) vượt trần 100 giây của
    Cloudflare.

    `dien_truoc` ghi lại **ý định điện trước khi khôi phục**, để bước cuối trả
    máy về đúng trạng thái khách đang có. Không ghi thì mọi lần khôi phục đều
    giao lại một máy đang tắt, và khách phải tự bật — trên một máy họ vừa cứu.
    """
    from apps.vps import trang_thai_may as tt
    from apps.vps.services import provisioning, thao_tac

    op = thao_tac.mo(db, may, tt.DANG_KHOI_PHUC, boi=boi,
                     khoa_idem=f"khoi_phuc:{ten}"[:64],
                     dien_mong_doi=str(may.dien_mong_muon or tt.CHAY), now=now)
    op.dien_truoc = str(may.dien_mong_muon or tt.CHAY)
    provisioning.ghi_su_kien(db, may.id, "xin_khoi_phuc", boi=boi,
                             anh=ten, thao_tac_id=op.id)

    from apps.vps.manifest import MANIFEST
    from platform_core import jobs as job_queue
    job_queue.submit(db, user_id=boi, app_slug=MANIFEST.slug,
                     job_type=JOB_TYPE,
                     params={"instance_id": may.id, "viec": "khoi_phuc",
                             "anh": ten, "thao_tac_id": op.id, "boi": boi})
    return op


#: Bước con của một lần khôi phục. Mã, không phải câu — `nhan.BUOC` dịch.
BUOC_TAT_TRUOC = "tat_truoc_khoi_phuc"
BUOC_KHOI_PHUC = "dang_khoi_phuc_anh"
BUOC_BAT_LAI = "bat_lai_sau_khoi_phuc"

#: Bước nào nghĩa là **rollback đã chạy xong**. Dùng khi nối lại sau khi worker
#: chết: chạy rollback lần thứ hai là quay về ảnh chụp một lần nữa và **xoá luôn
#: mọi thứ khách làm sau lần khôi phục đầu**.
BUOC_DA_QUA_ROLLBACK = frozenset({BUOC_BAT_LAI})


def thi_hanh_khoi_phuc(db, may, client, op, *, ten: str,
                       nhip: tac_vu.Nhip = tac_vu.NHIP_THAT,
                       luu=None, now: datetime | None = None) -> str:
    """Khôi phục tới nơi tới chốn. Trả điện **đo được** cuối cùng.

    ## Vì sao KHÔNG chụp một "ảnh an toàn trước khi khôi phục"

    Hợp đồng cho phép chụp một điểm an toàn trước khi rollback *"nếu hạ tầng đỡ
    được và nó không tạo ra một bảo đảm giả"*. Ở cụm này thì **không**:

    * ảnh nằm **cùng pool** với đĩa gốc, nên nó không cứu được thứ mà khách sợ
      nhất khi bấm nút này (hỏng phần cứng) — gọi nó là "an toàn" là nói quá;
    * đĩa là **nút thắt** của cả sản phẩm (475 GB LVM-thin cho mọi khách). Một
      ảnh thêm cho mỗi lần khôi phục, không nằm trong vòng dọn hằng tuần, là một
      đường rò dung lượng không có ai đóng.

    ⇒ Không chụp. Thay vào đó, đường phá huỷ đã có **hai** rào của chính nó: gõ
      đúng tên máy để xác nhận, và tên ảnh phải khớp chính xác. Xem ADR-04.

    ## Nối lại sau khi worker chết

    `buoc` phân biệt "chưa rollback" với "đã rollback, đang bật lại". Không có
    nó, một lần chạy lại sẽ rollback **lần thứ hai** — xoá sạch mọi thứ khách
    làm sau lần khôi phục đầu. Đây là ca mất dữ liệu, không phải ca phiền toái.
    """
    from apps.vps import trang_thai_may as tt
    from apps.vps.services import thao_tac

    _luu = luu or (lambda: None)

    def ghi(buoc: str) -> None:
        thao_tac.ghi_buoc(None, op, buoc)
        _luu()

    if str(op.buoc or "") not in BUOC_DA_QUA_ROLLBACK:
        # 1) Máy PHẢI tắt trước: Proxmox từ chối rollback một máy đang chạy khi
        #    ảnh không kèm RAM — và ảnh của ta cố ý không kèm RAM.
        if tac_vu.doc_dien(client, may.vmid) != tt.TAT:
            ghi(BUOC_TAT_TRUOC)
            upid = client.tat_cung(int(may.vmid))
            thao_tac.ghi_upid(None, op, str(upid))
            # ⚠️ Bản cũ nuốt lỗi ở đây (`except ProxmoxError: pass`) rồi gọi
            #    rollback ngay dòng sau. Nuốt lỗi tắt máy rồi rollback là đường
            #    ngắn nhất tới một đĩa hỏng.
            tac_vu.cho_va_xac_minh(client, upid, may.vmid, tt.TAT,
                                   han_tac_vu_s=HAN_KHOI_PHUC_S,
                                   han_dien_s=tac_vu.HAN_DIEN_S, nhip=nhip)

        # 2) Ảnh phải còn đó. Hỏi lại ngay trước khi rollback, không tin danh
        #    sách đọc lúc mở trang: giữa hai thời điểm đó có một vòng bảo trì.
        if not co_anh(client, may.vmid, ten):
            raise SaoLuuError(f"anh {ten!r} khong con tren may chu")

        ghi(BUOC_KHOI_PHUC)
        upid = client.khoi_phuc_anh(may.vmid, ten)
        thao_tac.ghi_upid(None, op, str(upid))
        tac_vu.cho_xong(client, str(upid), han_s=HAN_KHOI_PHUC_S, nhip=nhip)

    # 3) Trả máy về đúng trạng thái điện khách đang có trước khi khôi phục.
    #    Ảnh không kèm RAM nên máy khởi động **mới**, không phải tiếp tục.
    dien_dich = str(op.dien_truoc or tt.CHAY)
    if dien_dich == tt.CHAY:
        ghi(BUOC_BAT_LAI)
        upid = client.bat(int(may.vmid))
        thao_tac.ghi_upid(None, op, str(upid))
        dien = tac_vu.cho_va_xac_minh(client, upid, may.vmid, tt.CHAY,
                                      han_tac_vu_s=HAN_KHOI_PHUC_S,
                                      han_dien_s=tac_vu.HAN_DIEN_S, nhip=nhip)
    else:
        dien = tac_vu.doc_dien(client, may.vmid)

    tt.ghi_quan_sat(may, dien, now=now)
    return dien
