"""
api_pool.py — cấp phát API key (H8). App xin key ở đây theo (provider, category,
model); nền tảng chọn key khả dụng, đếm tải (rpm/tpm/token) và đánh dấu lỗi để tự
nghỉ/tắt.

KHÁC hàng đợi job: một API key CHIA SẺ được cho nhiều request đồng thời, nên
KHÔNG cần khoá độc quyền (`FOR UPDATE`) — chỉ chọn theo priority rồi cập nhật
trạng thái. Không tự commit (caller quyết định transaction).

Pha 2 thêm:
- **Telemetry rpm/tpm/token** — cửa sổ cố định 60s ngay trong hàng: allocator bỏ
  qua key đã chạm `rpm_limit`/`tpm_limit` trong cửa sổ hiện tại, tự reset khi quá
  hạn. `danh_dau_thanh_cong(..., tokens=)` kế toán token.
- **Cascade đa-provider** — `chon_key(category=..., thu_tu_provider=[...])` gom key
  MỌI provider phục vụ category, nên một provider cạn key KHÔNG làm chết cả loại.

Phân loại lỗi (học BOT GEMINI, đã kiểm chứng ở đó):
- 401/403 → auth_error; cooldown ngắn, DISABLE sau `AUTH_DISABLE_THRESHOLD` lần
  liên tiếp (chống một key hỏng làm chết mọi request);
- 429     → cooldown theo retry-after (mặc định `DEFAULT_COOLDOWN_S`);
- 4xx khác → LỖI CỦA TA (bad request) → KHÔNG phạt key;
- 5xx/mạng → error; sang trạng thái error sau nhiều lần.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from platform_core.models import (APIKEY_ACTIVE, APIKEY_COOLDOWN,
                                  APIKEY_DISABLED, APIKEY_ERROR, ApiKey)

AUTH_DISABLE_THRESHOLD = 5
DEFAULT_COOLDOWN_S = 60
ERROR_TO_STATUS_THRESHOLD = 5
WINDOW_S = 60          # cửa sổ đo rpm/tpm (giây)


class ThieuKeyError(Exception):
    """Không có API key khả dụng cho yêu cầu — app phải báo lỗi rõ, không gọi API."""


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _cuon_cua_so(key: ApiKey, now: datetime) -> None:
    """Reset cửa sổ đếm khi đã quá `WINDOW_S`. Gọi trước khi đọc/tăng bộ đếm."""
    ws = _aware(key.window_start)
    if ws is None or (now - ws).total_seconds() >= WINDOW_S:
        key.window_start = now
        key.window_requests = 0
        key.window_tokens = 0


def _cua_so_hieu_luc(key: ApiKey, now: datetime) -> tuple[int, int]:
    """`(window_requests, window_tokens)` HIỆU LỰC tại `now` — **không ghi gì**.

    Cùng phép tính với `_cuon_cua_so`, khác đúng một điều: nó không chạm đối
    tượng. Cần bản không-ghi vì `_ung_vien` chỉ đang **lọc**, và một phép lọc
    không được để lại khoá hàng — xem `_ghi_so_pool`.
    """
    ws = _aware(key.window_start)
    if ws is None or (now - ws).total_seconds() >= WINDOW_S:
        return 0, 0
    return int(key.window_requests or 0), int(key.window_tokens or 0)


def _dinh_muc_con(key: ApiKey, w_req: int, w_tok: int) -> bool:
    """True nếu key CÒN quota trong cửa sổ hiện tại.

    `w_req`/`w_tok` là số ĐÃ cuộn cửa sổ (`_cua_so_hieu_luc`), truyền vào chứ
    không đọc từ `key`: bên gọi có thể chưa ghi việc cuộn xuống đối tượng.
    """
    if key.rpm_limit and w_req >= key.rpm_limit:
        return False
    if key.tpm_limit and w_tok >= key.tpm_limit:
        return False
    return True


#: ── 🔴 SỔ CỦA POOL KHOÁ ĐI Ở GIAO DỊCH RIÊNG (L-01) ─────────────────────────
#:
#: Chú thích đầu tệp này nói: *"một API key CHIA SẺ được cho nhiều request đồng
#: thời, nên KHÔNG cần khoá độc quyền (`FOR UPDATE`)"*. Câu ấy đúng về **ý định**
#: và sai về **cơ chế**: không xin `FOR UPDATE` không có nghĩa là không có khoá.
#: Trên PostgreSQL, một `UPDATE` thường **cũng** lấy khoá hàng độc quyền, và khoá
#: đó sống **tới khi giao dịch commit**.
#:
#: Hậu quả đo được 12/09/2026: `chon_key` tăng bộ đếm rồi chỉ `flush()`, còn giao
#: dịch nghiệp vụ thì commit **sau khi model trả lời** — giữa hai mốc là 3-20
#: giây gọi máy B. Production có **đúng một** hàng khoá `ltt_llm` và **cả hai**
#: model đi qua nó, nên một lượt LTT-3.8 chặn một lượt LTT-3.5 dù hai GPU hoàn
#: toàn rời nhau. Đo: lượt thứ hai chờ **2,015 s** ở `chon_key` trong khi lượt
#: thứ nhất giữ 2,0 s. Sổ lỗi: `docs/ltt_llm_dual/SO_LOI_DO_TAI.md` §L-01.
#:
#: ⇒ Sổ của pool khoá (ai được cấp, bao nhiêu lượt, sức khoẻ) **không thuộc** giao
#:   dịch nghiệp vụ. Nó có giao dịch của chính nó: mở, ghi, commit ngay — khoá
#:   hàng sống vài mili giây thay vì vài chục giây.
#:
#: ⛔ CHỈ PostgreSQL. Cùng khuôn `admission._khoa_resource`: SQLite khoá **cả
#:    CSDL** khi ghi, nên một kết nối thứ hai ở đó là một đường tự khoá mình.
#:    Đường cũ giữ nguyên từng byte cho SQLite và cho mọi `db` giả trong test.
_COT_SO_POOL = frozenset({
    "last_used_at", "total_requests", "window_start", "window_requests",
    "window_tokens", "total_tokens", "total_success", "status", "cooldown_until",
    "error_count", "auth_error_count", "health_score", "total_failed",
    "last_error",
})


def _ghi_rieng_duoc(db: DbSession) -> bool:
    """`db` có phải một phiên PostgreSQL thật không (⇒ ghi sổ pool ở giao dịch riêng).

    ⛔ Hai đường "không phải" ở đây được bắt **hẹp và có tên**, không bằng một
       `except Exception`. Bắt rộng ở đúng chỗ này là tự bịt mắt: một lỗi cấu
       hình thật (engine sai, driver thiếu) sẽ lặng lẽ thành "à thôi, đi đường
       SQLite" — tức sổ pool quay về ghi trong giao dịch nghiệp vụ và L-01 sống
       lại mà không một dòng log nào nói tại sao.
    """
    from sqlalchemy.exc import UnboundExecutionError

    lay = getattr(db, "get_bind", None)
    if lay is None:
        return False        # `db` giả trong test — đi đường cũ, từng byte
    try:
        bind = lay()
    except UnboundExecutionError:
        return False        # phiên chưa gắn engine nào
    dialect = getattr(bind, "dialect", None)
    return getattr(dialect, "name", "") == "postgresql"


def _ghi_so_pool(db: DbSession, key: ApiKey, cau_set: str, tham_so: dict,
                 cot_doi: Sequence[str]) -> None:
    """Chạy `UPDATE api_keys SET <cau_set> WHERE id=...` ở GIAO DỊCH RIÊNG.

    `cot_doi` là các cột câu lệnh chạm tới; chúng được `expire` khỏi đối tượng
    trong phiên của bên gọi, nên lần đọc sau lấy giá trị mới bằng một `SELECT`
    thuần — không phải bằng một `UPDATE` thứ hai (thứ sẽ khoá lại đúng hàng ta
    vừa cố gỡ).
    """
    from sqlalchemy import text

    la = [c for c in cot_doi if c not in _COT_SO_POOL]
    if la:
        raise ValueError(f"cot khong nam trong so pool: {la}")

    # `get_bind()` trả `Engine` HOẶC `Connection` (phiên đã gắn sẵn kết nối).
    # Cần `Engine` để mở một kết nối **thứ hai**; `Connection.engine` trả nó,
    # và `Engine.engine` trả chính nó — nên một dòng phục vụ cả hai.
    from sqlalchemy.engine import Connection

    bind = db.get_bind()
    engine = bind.engine if isinstance(bind, Connection) else bind
    with engine.connect() as con:
        con.execute(text(f"UPDATE api_keys SET {cau_set} WHERE id = :_id"),
                    {**tham_so, "_id": key.id})
        con.commit()
    db.expire(key, list(cot_doi))


#: ── PHẠM VI CẤP KHOÁ (H43/Q120, O15) ────────────────────────────────────────
#:
#: 🔴 VÌ SAO PHẢI CÓ, VÀ VÌ SAO NÓ TỪNG LÀ MỘT LỖ.
#:
#:    `ApiKey.owner_user_id` tồn tại từ migration đầu tiên của bảng này
#:    (`20260731_1600_them_bang_api_keys.py:24`, có index) và được `tao_key()`
#:    ghi. Nhưng **không nơi nào ĐỌC nó** — `_ung_vien` lọc theo enabled/status/
#:    categories/supported_models/rpm/tpm và không hề lọc theo chủ sở hữu. Nghĩa
#:    là một khoá RIÊNG của khách sẽ được cấp cho lượt gọi của bất kỳ ai.
#:
#: ⭐ Hôm nay điều đó **chưa** rò rỉ, và nói cho đúng thì phải nói rõ vì sao:
#:    không đường ghi nào trong kho đặt `owner_user_id`. Trang admin
#:    (`server/admin.py:734`) không truyền tham số đó, hai công cụ nạp khoá cũng
#:    không. Nên mọi dòng đang tồn tại đều mang chuỗi rỗng.
#:
#: ⇒ Định nghĩa rỗng = POOL NỀN TẢNG là **thiết lập** ngữ nghĩa cho một cột chưa
#:   có ngữ nghĩa, không phải diễn giải lại một cột đang có. Không dòng nào đổi
#:   hành vi, nên hợp đồng O15 ("tương thích ngược") được giữ nguyên vẹn.
PHAM_VI_POOL = "platform_pool"     # khoá của nền tảng, dùng chung
PHAM_VI_RIENG = "user_owned"       # khoá do chính người dùng cung cấp
PHAM_VI_HOP_LE = frozenset({PHAM_VI_POOL, PHAM_VI_RIENG})


class PhamViError(ValueError):
    """Yêu cầu cấp khoá có phạm vi không hợp lệ. Fail-closed."""


def _ung_vien(db: DbSession, now: datetime, *, providers: Optional[Sequence[str]],
              category: Optional[str], model: Optional[str],
              pham_vi: str = PHAM_VI_POOL,
              owner_user_id: str = "") -> list:
    """Gom key khả dụng (tự hồi cooldown + cuộn cửa sổ). Lọc provider/category/model
    và bỏ key đã chạm rpm/tpm. KHÔNG sắp xếp — caller quyết thứ tự.

    🔑 Phép lọc chủ sở hữu chạy **trong câu truy vấn**, trước mọi phép xếp hạng.
       Đặt nó ở đây chứ không ở chỗ gọi vì một lý do: chủ sở hữu hiệu lực phải
       được biết **TRƯỚC KHI CHỌN** (Prompt 07 mục 3). Lọc sau khi chọn nghĩa là
       đã có một lượt chọn sai xảy ra rồi mới sửa, và một ngày nào đó ai đó sẽ
       quên bước sửa.
    """
    stmt = select(ApiKey).where(ApiKey.enabled.is_(True))
    if providers:
        stmt = stmt.where(ApiKey.provider.in_(list(providers)))

    if pham_vi == PHAM_VI_RIENG:
        # ⛔ KHÔNG BAO GIỜ rơi về pool nền tảng. Khách chọn khoá riêng là để
        #    hạn mức và hoá đơn thuộc về họ; lặng lẽ dùng khoá nhà là tiêu tiền
        #    của nền tảng cho một yêu cầu đã nói rõ không muốn thế.
        stmt = stmt.where(ApiKey.owner_user_id == owner_user_id)
    else:
        # Pool nền tảng KHÔNG bao giờ chạm khoá riêng của ai (I7).
        stmt = stmt.where(ApiKey.owner_user_id == "")

    rows = db.execute(stmt).scalars().all()

    # 🔴 MỘT PHÉP LỌC KHÔNG ĐƯỢC ĐỂ LẠI KHOÁ HÀNG (L-01).
    #
    #    Bản trước gán thẳng lên đối tượng ở đây — tự hồi cooldown và cuộn cửa
    #    sổ — cho **mọi** ứng viên, kể cả những key rốt cuộc không được chọn.
    #    Mỗi lần gán là một hàng `dirty`, và `autoflush` biến nó thành `UPDATE`
    #    ngay ở câu truy vấn kế tiếp ⇒ khoá hàng độc quyền sống tới hết giao
    #    dịch nghiệp vụ, tức suốt cả lượt gọi model.
    #
    #    Trên PostgreSQL ta chỉ **tính**; việc ghi thuộc về `chon_key`, nó ghi
    #    đúng một hàng (hàng được chọn) trong giao dịch của riêng sổ pool.
    chi_doc = _ghi_rieng_duoc(db)

    out = []
    for k in rows:
        _cd = _aware(k.cooldown_until)
        het_cooldown = bool(k.status == APIKEY_COOLDOWN and _cd and _cd <= now)
        if het_cooldown and not chi_doc:
            # Đường cũ (SQLite, `db` giả): ghi ngay tại đây, từng byte như trước.
            k.status = APIKEY_ACTIVE
            k.cooldown_until = None
        if not (k.status == APIKEY_ACTIVE or het_cooldown):
            continue
        if category and k.categories and category not in k.categories:
            continue
        if model and k.supported_models and model not in k.supported_models:
            continue
        if chi_doc:
            w_req, w_tok = _cua_so_hieu_luc(k, now)
        else:
            _cuon_cua_so(k, now)
            w_req, w_tok = int(k.window_requests or 0), int(k.window_tokens or 0)
        if not _dinh_muc_con(k, w_req, w_tok):
            continue          # đã chạm rpm/tpm trong cửa sổ này -> tạm bỏ
        out.append(k)
    return out


def chon_key(db: DbSession, *, category: Optional[str] = None,
             model: Optional[str] = None,
             thu_tu_provider: Optional[Sequence[str]] = None,
             loai_tru: Optional[Sequence[str]] = None,
             pham_vi: str = PHAM_VI_POOL,
             owner_user_id: str = "") -> ApiKey:
    """Chọn một API key khả dụng cho `category` (tuỳ `model`), CASCADE nhiều provider.

    `thu_tu_provider`: thứ tự ưu tiên provider (vd ["gemini","apiai"]); None = xét
    mọi provider. Xếp: provider theo thứ tự cho trước → `priority` cao → `health`
    cao → ít tải nhất (cửa sổ) → ít dùng nhất. Raise `ThieuKeyError` nếu cạn.

    `loai_tru`: id các key **đã thử và hỏng trong chính lượt gọi này**. Xem
    `thu_lan_luot()` để biết vì sao cần.
    """
    if pham_vi not in PHAM_VI_HOP_LE:
        raise PhamViError(f"pham vi cap khoa khong hop le: {pham_vi!r}")
    owner_user_id = (owner_user_id or "").strip()
    if pham_vi == PHAM_VI_RIENG and not owner_user_id:
        # Fail-closed. Xin khoá riêng mà không nói của ai thì câu trả lời đúng là
        # từ chối — nếu đoán, đường đoán an toàn nhất vẫn là cấp một khoá của
        # người khác hoặc của nền tảng, tức đúng hai thứ bất biến I7 cấm.
        raise PhamViError("pham vi user_owned bat buoc phai co owner_user_id")

    order = [(p or "").strip().lower() for p in (thu_tu_provider or []) if p]
    bo_qua = {str(x) for x in (loai_tru or [])}
    now = _bay_gio()
    ung_vien = _ung_vien(db, now, providers=(order or None),
                         category=category, model=model,
                         pham_vi=pham_vi, owner_user_id=owner_user_id)
    if bo_qua:
        ung_vien = [k for k in ung_vien if k.id not in bo_qua]
    if not ung_vien:
        raise ThieuKeyError(
            f"khong co API key kha dung: pham_vi={pham_vi} "
            f"providers={order or 'moi'} category={category} model={model}")

    def _rank_prov(p: str) -> int:
        if not order:
            return 0
        try:
            return order.index(p)
        except ValueError:
            return len(order)

    ung_vien.sort(key=lambda k: (_rank_prov(k.provider), -k.priority,
                                 -k.health_score, _cua_so_hieu_luc(k, now)[0],
                                 k.total_requests))
    chon = ung_vien[0]

    if not _ghi_rieng_duoc(db):
        # Đường cũ — SQLite và `db` giả trong test. Từng byte như trước.
        chon.last_used_at = now
        chon.total_requests += 1
        _cuon_cua_so(chon, now)  # bảo đảm cửa sổ hợp lệ trước khi tăng
        chon.window_requests += 1
        db.flush()
        return chon

    # ── PostgreSQL: một câu, giao dịch riêng, commit ngay (L-01) ─────────────
    #
    # ⭐ Cuộn cửa sổ và tự hồi cooldown làm **trong chính câu lệnh**, không làm
    #    trong Python rồi ghi đè. Hai cái lợi, và cái thứ hai mới là cái chính:
    #      1. nguyên tử — hai lượt đồng thời không đọc rồi cùng ghi đè nhau;
    #      2. `total_requests = total_requests + 1` cộng vào giá trị **thật đang
    #         nằm trong hàng**, chứ không vào giá trị phiên này đọc được lúc
    #         nào đó. Gỡ khoá đi thì hai lượt song song KHÔNG còn xếp hàng, nên
    #         một phép `đọc rồi ghi` ở Python sẽ bắt đầu mất lượt đếm.
    #
    # ⚠️ Chỉ hàng ĐƯỢC CHỌN được hồi cooldown, khác bản trước (hồi mọi ứng
    #    viên). Có chủ ý: một hàng ta không dùng thì không có lý do gì để ghi
    #    vào, và nó sẽ được hồi đúng ở lượt nó được chọn.
    moc = now - timedelta(seconds=WINDOW_S)
    het_cd = ("status = :cd_status AND cooldown_until IS NOT NULL "
              "AND cooldown_until <= :now")
    moi = "window_start IS NULL OR window_start < :moc"
    _ghi_so_pool(
        db, chon,
        "last_used_at = :now, "
        "total_requests = total_requests + 1, "
        f"window_start   = CASE WHEN {moi} THEN :now ELSE window_start END, "
        f"window_requests = CASE WHEN {moi} THEN 1 ELSE window_requests + 1 END, "
        f"window_tokens  = CASE WHEN {moi} THEN 0 ELSE window_tokens END, "
        f"status         = CASE WHEN {het_cd} THEN :cd_active ELSE status END, "
        f"cooldown_until = CASE WHEN {het_cd} THEN NULL ELSE cooldown_until END",
        {"now": now, "moc": moc,
         "cd_status": APIKEY_COOLDOWN, "cd_active": APIKEY_ACTIVE},
        ("last_used_at", "total_requests", "window_start", "window_requests",
         "window_tokens", "status", "cooldown_until"))
    return chon


def lay_key(db: DbSession, provider: str, *, category: Optional[str] = None,
            model: Optional[str] = None,
            loai_tru: Optional[Sequence[str]] = None,
            pham_vi: str = PHAM_VI_POOL,
            owner_user_id: str = "") -> ApiKey:
    """Chọn key cho MỘT provider cụ thể (tương thích Pha 1). Nội bộ gọi `chon_key`
    với thứ tự provider = [provider], nên rpm/tpm/telemetry áp dụng như nhau."""
    provider = (provider or "").strip().lower()
    return chon_key(db, category=category, model=model,
                    thu_tu_provider=[provider], loai_tru=loai_tru,
                    pham_vi=pham_vi, owner_user_id=owner_user_id)


def thu_lan_luot(db: DbSession, *, provider: Optional[str] = None,
                 category: Optional[str] = None, model: Optional[str] = None,
                 so_lan: int = 3,
                 pham_vi: str = PHAM_VI_POOL,
                 owner_user_id: str = ""):
    """Sinh lần lượt các key khả dụng, **không bao giờ trả lại key đã thử**.

        for key in api_pool.thu_lan_luot(db, provider="gemini", category="image"):
            try:
                return goi_nha_cung_cap(key)
            except LoiCoTheThuLai as e:
                api_pool.danh_dau_loi(db, key, http_status=e.status)
        raise RuntimeError("het key")

    ⛔ VÌ SAO CẦN — KHOẢNG TRỐNG THẬT SO VỚI LiteLLM Router.

       Hôm nay **không có chuỗi thử lại nào**. `apps/taoanh/jobs.py` lấy key **một
       lần** trước vòng lặp ảnh; key đó cạn hạn mức ở ảnh thứ hai thì **cả job
       hỏng**, dù tài khoản còn ba key Gemini khác đang rảnh. Khách mất một job vì
       hết quota của *một tài khoản*, không phải vì hết quota.

       LiteLLM Router loại deployment vừa hỏng khỏi **các bước sau của cùng một
       request**, và loại trừ **tích luỹ** qua từng bước — nên nó không bao giờ
       quay lại thứ vừa chết.

    ⭐ RANH GIỚI PHẢI GIỮ (D-042): đây là dự phòng ở tầng **TÀI KHOẢN**, không phải
       tầng **sản phẩm**. Khách gọi `gemini-3-pro-image` thì vẫn nhận đúng model
       đó — ta chỉ đổi **khoá nào** của Gemini phục vụ lượt gọi. Đừng dùng hàm này
       để nhảy sang một model khác: đó là đánh tráo sản phẩm.

    ⚠️ Bên gọi **phải** gọi `danh_dau_loi()` khi một key hỏng. Không gọi thì key đó
       vẫn `active`, và lượt sau lại chọn đúng nó — vòng lặp này chỉ tránh lặp
       *trong một lượt*, nó không thay việc ghi nhận sức khoẻ.
    """
    da_thu: list[str] = []
    for _ in range(max(1, int(so_lan))):
        try:
            key = (lay_key(db, provider, category=category, model=model,
                           loai_tru=da_thu, pham_vi=pham_vi,
                           owner_user_id=owner_user_id)
                   if provider else
                   chon_key(db, category=category, model=model, loai_tru=da_thu,
                            pham_vi=pham_vi, owner_user_id=owner_user_id))
        except ThieuKeyError:
            return          # het key kha dung -> dung, khong nem
        da_thu.append(key.id)
        yield key


def danh_dau_thanh_cong(db: DbSession, key: ApiKey, *, tokens: int = 0) -> None:
    """Kế toán một lượt thành công. Ghi ở **giao dịch riêng** trên PostgreSQL.

    ⛔ Vì sao hàm này cũng phải đi đường riêng, không chỉ `chon_key`: ở
       `dieu_phoi.goi` nó chạy **ngay sau** lượt gọi model rồi hàm trả về, còn
       commit thì xảy ra mãi ở cửa (`_finish_chat`). Để nó ghi qua phiên nghiệp
       vụ là dời chỗ nghẽn của L-01 chứ không gỡ: lượt kế tiếp sẽ đứng ở đây
       thay vì ở `chon_key`.
    """
    if not _ghi_rieng_duoc(db):
        # Đường cũ — SQLite và `db` giả trong test. Từng byte như trước.
        key.total_success += 1
        key.error_count = 0
        key.auth_error_count = 0
        key.health_score = min(100, key.health_score + 5)
        if tokens:
            now = _bay_gio()
            _cuon_cua_so(key, now)
            key.window_tokens += int(tokens)
            key.total_tokens += int(tokens)
        if key.status == APIKEY_ERROR:
            key.status = APIKEY_ACTIVE
        db.flush()
        return

    now = _bay_gio()
    dat = ["total_success = total_success + 1",
           "error_count = 0",
           "auth_error_count = 0",
           "health_score = LEAST(100, health_score + 5)",
           "status = CASE WHEN status = :er THEN :ac ELSE status END"]
    cot = ["total_success", "error_count", "auth_error_count", "health_score",
           "status"]
    tham: dict = {"er": APIKEY_ERROR, "ac": APIKEY_ACTIVE}
    if tokens:
        moi = "window_start IS NULL OR window_start < :moc"
        dat += [
            f"window_start    = CASE WHEN {moi} THEN :now ELSE window_start END",
            f"window_requests = CASE WHEN {moi} THEN 0 ELSE window_requests END",
            f"window_tokens   = CASE WHEN {moi} THEN :tok "
            f"                       ELSE window_tokens + :tok END",
            "total_tokens = total_tokens + :tok"]
        cot += ["window_start", "window_requests", "window_tokens", "total_tokens"]
        tham |= {"now": now, "moc": now - timedelta(seconds=WINDOW_S),
                 "tok": int(tokens)}
    _ghi_so_pool(db, key, ", ".join(dat), tham, cot)


def danh_dau_loi(db: DbSession, key: ApiKey, *, http_status: Optional[int] = None,
                 retry_after_s: Optional[int] = None, message: str = "") -> None:
    """Phạt một key theo phân loại lỗi. Ghi ở **giao dịch riêng** trên PostgreSQL.

    ⛔ Cũng phải đi đường riêng vì cùng lý do với `danh_dau_thanh_cong`: ở
       `dieu_phoi.goi` nó chạy rồi `continue` sang provider kế, và ở
       `luong_vlm.LuongMo.hong()` nó chạy giữa lúc luồng đang vỡ — cả hai chỗ
       đều còn cách điểm commit rất xa.

    ⚠️ Các ngưỡng (`AUTH_DISABLE_THRESHOLD`, `ERROR_TO_STATUS_THRESHOLD`) vẫn
       tính từ giá trị phiên này đọc được, y như bản trước. Đường ghi đổi, phép
       tính **không** đổi — đây không phải chỗ để sửa kèm một thứ khác.
    """
    now = _bay_gio()
    s = http_status
    moi: dict = {"total_failed": int(key.total_failed or 0) + 1,
                 "last_error": (message or "")[:500]}

    if s in (401, 403):
        moi["auth_error_count"] = int(key.auth_error_count or 0) + 1
        moi["health_score"] = max(0, int(key.health_score or 0) - 10)
        if moi["auth_error_count"] >= AUTH_DISABLE_THRESHOLD:
            moi["status"] = APIKEY_DISABLED    # hỏng thật -> tắt hẳn, chờ admin
        else:
            moi["status"] = APIKEY_COOLDOWN    # có thể chỉ trục trặc tạm
            moi["cooldown_until"] = now + timedelta(seconds=DEFAULT_COOLDOWN_S)
    elif s == 429:
        cd = int(retry_after_s) if retry_after_s else DEFAULT_COOLDOWN_S
        moi["status"] = APIKEY_COOLDOWN
        moi["cooldown_until"] = now + timedelta(seconds=cd)
        moi["health_score"] = max(0, int(key.health_score or 0) - 5)
    elif s is not None and 400 <= s < 500:
        # Bad request CỦA TA — không phải lỗi của key. KHÔNG phạt.
        pass
    else:
        # 5xx hoặc lỗi mạng.
        moi["error_count"] = int(key.error_count or 0) + 1
        moi["health_score"] = max(0, int(key.health_score or 0) - 10)
        if moi["error_count"] >= ERROR_TO_STATUS_THRESHOLD:
            moi["status"] = APIKEY_ERROR

    if not _ghi_rieng_duoc(db):
        # Đường cũ — SQLite và `db` giả trong test.
        for ten, gt in moi.items():
            setattr(key, ten, gt)
        db.flush()
        return

    _ghi_so_pool(db, key, ", ".join(f"{c} = :{c}" for c in moi), dict(moi),
                 tuple(moi))


def rpm(key: ApiKey, *, now: Optional[datetime] = None) -> int:
    """Số request trong cửa sổ 60s hiện tại (0 nếu cửa sổ đã cũ)."""
    now = now or _bay_gio()
    ws = _aware(key.window_start)
    if ws is None or (now - ws).total_seconds() >= WINDOW_S:
        return 0
    return key.window_requests


def tpm(key: ApiKey, *, now: Optional[datetime] = None) -> int:
    """Số token trong cửa sổ 60s hiện tại (0 nếu cửa sổ đã cũ)."""
    now = now or _bay_gio()
    ws = _aware(key.window_start)
    if ws is None or (now - ws).total_seconds() >= WINDOW_S:
        return 0
    return key.window_tokens


def pham_vi_cua(key: ApiKey) -> str:
    """Phạm vi thực tế của một khoá, suy từ DỮ LIỆU chứ không từ lời gọi."""
    return PHAM_VI_RIENG if (key.owner_user_id or "").strip() else PHAM_VI_POOL


def mo_ta_an_toan(key: ApiKey) -> dict:
    """Mô tả một khoá cho log/telemetry/màn admin — KHÔNG BAO GIỜ có bí mật.

    ⛔ Không có `credential`, không có `credential_enc`. `key_preview` do
       `secretbox.preview()` sinh ra và vốn được thiết kế để in ra được; mọi thứ
       còn lại ở đây là siêu dữ liệu.

    ⭐ Có hàm này để nơi gọi khỏi phải tự dựng một dict — và mỗi lần tự dựng là
       một cơ hội cho `credential` lọt vào một dòng log. Bất biến I16 nói "không
       bí mật thô nào bị ghi lại"; cách giữ nó là làm cho đường đúng thành đường
       sẵn có.

    `chu_so_huu` rút gọn còn 8 ký tự: đủ để đối chiếu hai dòng log với nhau,
    không đủ để dùng làm định danh ở chỗ khác.
    """
    chu = (key.owner_user_id or "").strip()
    return {
        "key_id": key.id,
        "provider": key.provider,
        "pham_vi": pham_vi_cua(key),
        "chu_so_huu": (chu[:8] + "…") if chu else "",
        "preview": key.key_preview or "",
        "status": key.status,
        "health": key.health_score,
        "rpm": rpm(key),
        "tpm": tpm(key),
    }
