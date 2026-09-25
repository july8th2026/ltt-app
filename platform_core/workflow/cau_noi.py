"""Cầu nối job ↔ node (spec §5.8). Tầng nền gọi đúng MỘT hàm ở đây:
`bao_ket_thuc` từ `jobs.complete/fail/cancel`.

⭐ Một attempt = một job: waitpoint + job + node→QUEUED cùng MỘT transaction.
   `jobs.submit` chỉ khử trùng job CHƯA kết thúc; chốt idempotency sau khi job
   xong là transaction này + việc node đã rời READY.
⭐ Không hold riêng: run đã giữ một lần (`tien.py`, `test_965`). Job không có
   hold ⇒ `job_runner._quyet_toan_credit/_hoan_credit` tự bỏ qua.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from platform_core import jobs, registry
from platform_core.job_scheduler import ORIGIN_WORKFLOW
from platform_core.models import (JOB_CANCELLED, JOB_DONE, Artifact, Job,
                                  Waitpoint, WaitpointSignal, WorkflowRun)
from platform_core.workflow import (bien_dich, chinh_sach, cho_doi,
                                    danh_thuc, may_trang_thai, ngon_ngu,
                                    thi_hanh, thu_lai)
from platform_core.workflow import artifact as _artifact
from platform_core.workflow import cong_cu as _nguon
from platform_core.workflow.bien_dich import la_tham_chieu
from platform_core.workflow.chinh_sach import LoiNgonNgu
from platform_core.workflow.cong_cu import CongCu

GIOI_HAN_DAU_RA = 256 * 1024

#: Tiền tố của node APP trong đồ thị đã biên dịch (`bien_dich._node`).
#: Đây là KHÔNG GIAN TÊN DUY NHẤT mà cầu nối job suy được tên ToolSpec từ
#: `type`, vì `app.<tool>` **theo định nghĩa** mang tên tool ở phần đuôi.
TIEN_TO_APP = "app."


class LoiTienTo(ValueError):
    """`type` của node không thuộc không gian tên mà cầu nối job đọc được.

    🔴 VÌ SAO LÀ MỘT NGOẠI LỆ, KHÔNG PHẢI MỘT LÁT CẮT

       Bản cũ viết `str(node["type"])[4:]` — số 4 là độ dài `"app."`. Nó
       đúng cho **một** không gian tên và sai cho mọi không gian khác, và
       cái sai ấy **không ném**: `"ai.llm"` ra `"lm"`, `"core.if"` ra
       `".if"`, rồi registry không thấy và node FAILED với
       `cong_cu_khong_con: 'lm'`. Câu ấy **đổ lỗi cho registry** cho một
       lỗi của chính cầu nối, và người đọc log đi tìm một tool chưa bao giờ
       tồn tại. Làn p7 đã ghi lại cái bẫy này trong `nut_loi/ai_llm.py`
       trước khi nó kịp cắn.

    ⛔ Và **không** thay bằng một số cứng khác. Độ dài đọc từ chính chuỗi
       tiền tố thì không lệch được; một hằng `4` viết tay thì lệch ngay lần
       đầu ai đó đổi `"app."` thành thứ khác.
    """


def _dinh_nghia(loai: str):
    """`NodeDefinition` của một node lõi HOẶC một node piece, hoặc `None`.

    ⚠️ Import CỤC BỘ: `nut_loi` kéo theo `vong_lap` → `bao_gia` →
       `bien_dich`, và một import ở đầu tệp là một vòng chờ xảy ra.

    🔴 SỬA 25/09 (lan wfp): trước đây hàm này CHỈ tra `nut_loi.tat_ca()` —
       một sổ không bao giờ chứa node `piece.*` (nguồn thứ ba, catalog
       runner, spec §4.5). Hệ quả: mọi chỗ gọi `_dinh_nghia` cho một node
       piece (dưới đây, `nop_job`, hai chỗ trong `bao_ket_thuc`) đều nhận
       `None`, `nop_job` rơi xuống nhánh `ten_cong_cu()` cũ và ném
       `LoiTienTo` — dù `_nop_job_connector` (P6) đã sẵn sàng nhận nó.
       `nut.dinh_nghia_piece` là chỗ TRA DUY NHẤT cho nguồn ấy (cùng hàm mà
       `bien_dich`/`bao_gia` dùng — không ba vòng lặp catalog riêng).
    """
    from platform_core.workflow import nut, nut_loi

    nd = nut_loi.tat_ca().get(str(loai))
    if nd is not None:
        return nd
    return nut.dinh_nghia_piece(str(loai))


def ten_cong_cu(loai: str) -> str:
    """Tên ToolSpec của một node `app.<tool>`. Tiền tố khác ⇒ `LoiTienTo`.

    ⚠️ ⛔ **Không tra ngược `job_type → tên tool`** cho `ai.*`, dù nó trông
       thông minh hơn. Đo trên registry hôm nay (19 tool): **ba** `job_type`
       bị hai tool dùng chung (`prompt_ai_ommi.generate`, `taoanh.generate`,
       `upscalevideo.render`). Một tra ngược đúng hôm nay và sai vào đúng
       ngày ai đó thêm tool thứ hai trên `ltt_llm.chat` — im lặng, và nó
       chọn tool nào thì tuỳ thứ tự dict.

    ⇒ Node `ai.*` phải **KHAI** ToolSpec nó bọc. Trường ấy chưa tồn tại trên
      `NodeDefinition`, nên tới ngày có nó, hàm này là chỗ duy nhất phải sửa.
    """
    chuoi = str(loai or "")
    if chuoi.startswith(TIEN_TO_APP):
        ten = chuoi[len(TIEN_TO_APP):]
        if not ten:
            raise LoiTienTo(f"loai node {chuoi!r} khong co ten tool o duoi")
        return ten
    nd = _dinh_nghia(chuoi)
    if nd is not None and nd.ten_toolspec:
        return str(nd.ten_toolspec)
    raise LoiTienTo(
        f"loai node {chuoi!r} khong thuoc khong gian {TIEN_TO_APP!r} va "
        "khong KHAI `ten_toolspec` — cau noi job khong co cach nao biet no "
        "boc ToolSpec nao")


class LoiThamSo(ValueError):
    def __init__(self, ma: str, thong_diep: str):
        super().__init__(f"{ma}: {thong_diep}")
        self.ma = ma


def _bay_gio():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _giai_bieu_thuc_s6(db, run_id: str, bieu_thuc: str, vong=()) -> Any:
    """Tính GIÁ TRỊ THẬT của một chuỗi `{{ ... }}` lúc job chạy — namespace
    `nodes` dựng từ ảnh chụp CSDL của đúng các node đã tham chiếu.

    ⭐ DÙNG LẠI máy đã có, KHÔNG một bộ đọc đường dẫn thứ hai — cùng ba khối
       mà `bien_dich._doi`/`_bieu_thuc_s6_hop_le` (cổng PUBLISH, kiểm HÌNH
       DẠNG) dùng, chỉ khác là hàm này TÍNH GIÁ TRỊ (cần môi trường thật):

         `bien_dich.BOC_BIEU_THUC`    bóc đúng MỘT khối `{{ }}` trọn chuỗi
         `bien_dich.trich_tham_chieu` trích MỌI tham chiếu `nodes.…` (AST)
         `chinh_sach.moi_truong_wf` + `ngon_ngu.tinh` tính bằng ngôn ngữ §6

       Publish (`_doi`) và runtime (hàm này) phải LUÔN khớp nhau vì cùng gọi
       chung `bien_dich.trich_tham_chieu`/ngôn ngữ §6 — không có hai bảng để
       trôi (bài học "hai chỗ khai một điều"). `bien_dich._NAMESPACE_APP_TOOL`
       hẹp cổng publish xuống ĐÚNG namespace `nodes` mà hàm này giải được —
       không rộng hơn, không hẹp hơn (test_4201/test_4202 đo cả hai chiều).

    🔴 CHÚ Ý TÊN KHOÁ khi dựng `{id: {...}}` cho `chinh_sach.moi_truong_wf`:
       BA khoá `status`/`output`/`error` — KHÔNG phải tên cột
       `execution_status`/`output_ref` của `NodeRunSnapshot`. Đọc sai tên
       khoá ở đây là một "chỗ nối hai module vứt trường im lặng" (bài học đã
       lặp lại nhiều lần trong lịch sử kho này) — `chinh_sach._MatNode` đọc
       đúng ba tên này bằng `.get()`, nên gõ sai tên KHÔNG ném lỗi, nó chỉ
       ÂM THẦM làm `output`/`error` biến mất (`_MatNode.get(khoa)` trả
       `None`). `test_4202::test_ten_khoa_status_dung`/`_output_dung`/
       `_error_dung` khoá lại đúng ba tên này bằng ba đường riêng.

    ⚠️ Kiểm `_tran` (output tràn artifact, §5.8) CHỈ khi biểu thức thật sự
       đọc `.output` của node đó — một tham chiếu `nodes.a.status` không bị
       chặn oan vì output (không liên quan) của `a` tràn artifact.
    """
    boc = bien_dich.BOC_BIEU_THUC.match(bieu_thuc.strip())
    if boc is None:
        # Không thể xảy ra với một đồ thị đã qua `_doi` (cổng publish đòi
        # đúng hình dạng này) — nhưng hàm này không được TIN publish đã chạy
        # (Phần B, chủ dự án round 2): một chuỗi `{{ }}` lạ dạng phải NÉM,
        # không được lặng lẽ trả nguyên văn.
        raise LoiThamSo(
            "bieu_thuc_khong_giai_duoc",
            f"gia tri co '{{{{' nhung khong dung dang MOT bieu thuc boc "
            f"tron trong {{{{ }}}}: {bieu_thuc[:200]!r}")
    bt = boc.group(1).strip()
    try:
        refs = bien_dich.trich_tham_chieu(bt)
    except bien_dich.LoiBienDich as loi:
        raise LoiThamSo("bieu_thuc_khong_giai_duoc", str(loi)) from None

    doc_output = {tc.node for tc in refs if tc.loai == "output"}
    anh_map: dict[str, dict] = {}
    for tc in refs:
        if tc.node in anh_map:
            continue
        anh = thi_hanh.anh_chup_hien_tai(db, run_id, tc.node, vong)
        if anh is None:
            continue          # KhongGianNodes tu noi "khong co trong run"
        ra = dict(anh.output_ref or {})
        if (tc.node in doc_output and anh.execution_status == "SUCCEEDED"
                and "_tran" in ra):
            # Output đã tràn ra artifact (§5.8) — CÙNG lý do/mã lỗi với
            # đường tham chiếu đơn cũ bên dưới.
            raise LoiThamSo(
                "dau_ra_tran_artifact",
                f"{tc.node} tran ra artifact {ra['_tran']['artifact_ref']}; "
                "khong doc long duoc")
        anh_map[tc.node] = {
            "status": anh.execution_status,
            "output": {k: x for k, x in ra.items()
                      if not str(k).startswith("_")},
            "error": str(anh.error or ""),
        }
    moi_truong = chinh_sach.moi_truong_wf(nodes=anh_map)
    try:
        return ngon_ngu.tinh(bt, moi_truong)
    except LoiNgonNgu as loi:
        raise LoiThamSo("dau_vao_sai", str(loi)) from None


def giai_tham_so(db, run_id: str, params: dict, vong=()) -> dict:
    def _giai(v: Any) -> Any:
        if isinstance(v, dict):
            return {k: _giai(x) for k, x in v.items()}
        if isinstance(v, list):
            return [_giai(x) for x in v]
        if not isinstance(v, str):
            return v
        tc = la_tham_chieu(v)
        if tc is not None:
            # ⭐ LỐI TẮT — hành vi KHÔNG đổi cho ca đơn (spec cũ, workflow
            #   đang chạy trên production). Không đi qua `_giai_bieu_thuc_s6`.
            nguon, cong = tc
            anh = thi_hanh.anh_chup_hien_tai(db, run_id, nguon, vong)
            if anh is None or anh.execution_status != "SUCCEEDED":
                raise LoiThamSo("dau_vao_sai", f"{nguon} chua SUCCEEDED")
            ra = anh.output_ref or {}
            if "_tran" in ra:
                # Output đã tràn ra artifact (§5.8). Node sau phải nhận cả tệp
                # qua một cổng `artifact_ref`, không phải một khoá con — plan
                # 04 thêm node đọc artifact. Nói thẳng thay vì báo "khong co
                # cong".
                raise LoiThamSo(
                    "dau_ra_tran_artifact",
                    f"{nguon} tran ra artifact {ra['_tran']['artifact_ref']}; "
                    f"khong tra cung duoc cong {cong!r}")
            if cong not in ra:
                raise LoiThamSo("dau_vao_sai", f"{nguon} khong co cong {cong!r}")
            return ra[cong]
        if "{{" not in v:
            return v
        # ⭐ 25/09 (wfb5, round 2): NHÁNH MỚI — `v` không khớp tham chiếu đơn
        #   nhưng có `{{`, ví dụ `{{ nodes.a.output.json.prompt }}` (đường
        #   dẫn LỒNG, publish được từ round 1 của bản vá này).
        ra = _giai_bieu_thuc_s6(db, run_id, v, vong)
        # ⛔ Phần B (chủ dự án round 2) — LƯỚI AN TOÀN CHIỀU SÂU: một giá trị
        #   TRẢ VỀ mà vẫn còn nguyên `{{` nghĩa là chuỗi gốc đã KHÔNG thật sự
        #   được thay — trước bản vá này, nhánh `tc is None: return v` cũ ở
        #   TRÊN đã âm thầm làm đúng việc "trả nguyên văn" cho MỌI `{{ }}`
        #   không khớp `la_tham_chieu` (fail-OPEN trên đường tiền, có TỪ
        #   TRƯỚC wfb5 — không phải lỗi bản vá này sinh ra). Với
        #   `_giai_bieu_thuc_s6` đã viết đúng, nhánh này gần như không bao
        #   giờ kích hoạt (nó luôn NÉM `LoiThamSo` thay vì trả nguyên văn) —
        #   nhưng nếu một đường nào đó sau này khiến nó trả nguyên văn (bug,
        #   hay một `ngon_ngu.tinh` trả về đúng một CHUỖI VĂN BẢN chứa `{{`
        #   như dữ liệu — hiếm, nhưng không thể loại trừ), TỪ CHỐI thay vì
        #   đưa một giá trị mang hình dạng template cho job THẬT tiêu tiền.
        #   `test_4202::test_luoi_an_toan_nem_khi_go` đo bằng tiêm lỗi.
        if isinstance(ra, str) and "{{" in ra:
            raise LoiThamSo(
                "bieu_thuc_khong_giai_duoc",
                f"gia tri sau khi giai bieu thuc van con '{{{{': {ra[:200]!r}")
        return ra
    return _giai(dict(params))


def _khoa_idem(run: WorkflowRun, node: dict, lan: int, cc: CongCu,
               params: dict, vong=()) -> str:
    """Khoá khử trùng của MỘT lượt nộp job.

    🔴 `duong` THAY CHO `node["id"]`, và đó là chỗ nguy hiểm nhất của cả
       việc khoá `node_run` theo đường thi hành.

       Với `node["id"]` trần, một node THÂN `foreach` có tham số không phụ
       thuộc `loop.item` sinh **cùng một `dedupe_key`** ở mọi vòng. Và
       `jobs.submit` khử trùng theo `dedupe_key`: nó **trả lại job của vòng
       1**. Kết quả: `foreach` 5 phần tử chạy **một** job, bốn vòng còn lại
       nhận lại kết quả cũ — không lỗi, không cảnh báo, không ai biết.

       Cả HAI nhánh đều dính: nhánh `side_effect == "none"` vì `lan` giống
       nhau ở mọi vòng, nhánh kia vì `idempotency_fields` đọc cùng `params`.

    ⚠️ THAY, không phải THÊM: với `vong = ()` thì `duong == node["id"]`, nên
       khoá của mọi node ngoài vòng lặp **không đổi một bit** — các job đang
       chạy trên production giữ nguyên khoá của chúng.
    """
    duong = thi_hanh.khoa_node(str(node["id"]), vong)
    if cc.side_effect == "none" or not cc.idempotency_fields:
        goc = [run.id, duong, lan]
    else:
        goc = [run.id, duong,
               {k: params.get(k) for k in cc.idempotency_fields}]
    return hashlib.sha256(json.dumps(goc, sort_keys=True, default=str)
                          .encode()).hexdigest()[:64]


class _NhuCongCu:
    """Bọc một `NodeDefinition` thành đúng HAI thuộc tính mà `_khoa_idem` đọc.

    ⭐ Một lớp bọc bốn dòng thay vì một tham số thứ bảy cho `_khoa_idem`: hàm
       ấy giữ **luật khử trùng**, và luật đó không được rẽ nhánh theo nguồn
       của node. Node piece và node app phải sinh khoá bằng **cùng một** câu.
    """

    __slots__ = ("side_effect", "idempotency_fields")

    def __init__(self, nd):
        self.side_effect = str(getattr(nd, "side_effect", "external"))
        self.idempotency_fields = tuple(
            getattr(nd, "idempotency_key_fields", ()) or ())


def _chu_job(job_type: str) -> str:
    """App nào khai `job_type` này. ⛔ Không hardcode slug trong
    `platform_core/` (Global Constraint) — tra registry, như `tao_run`."""
    slug = registry.job_type_owners().get(job_type)
    if not slug:
        raise LoiTienTo(
            f"khong app nao khai job_type {job_type!r} trong job_types — "
            "worker se khong bao gio nhan job nay")
    return str(slug)


#: Tài nguyên admission của lane connector (spec §11.2): trần **2 suất đồng
#: thời** trên máy A. Máy này là production và mỗi lệnh connector là một tiến
#: trình Node ~400 MB; để nó tự do là để mã của bên thứ ba quyết định tải máy.
TAI_NGUYEN_CONNECTOR = "connector"
#: ⚠️ `admission_slots` la SUC CHUA cua tai nguyen, ⛔ khong phai so suat MOT
#:    job xin. `jobs.claim` so `dang_giu < Job.admission_slots`, nen ghi `1` o
#:    day la khoa lane xuong MOT lenh dong thoi — khong phai "moi job xin 1".
SUAT_CONNECTOR = 2


def _nop_job_connector(db, run: WorkflowRun, node: dict, nd, *, vong=()):
    """Đường nộp job cho node `piece.*` và `connector.*` (plan wf-v2 P6).

    🔴 Vì sao một nhánh RIÊNG chứ không nhét vào `nop_job`: node ở đây
       **không bọc ToolSpec nào**, nên ba thứ mà `nop_job` lấy từ `CongCu`
       (giá, làn, admission) phải lấy từ chỗ khác — `NodeDefinition.gia`
       (`co_dinh`), `nd.job_type`, và một tài nguyên admission cố định. Ép
       chúng qua `nop_job` thì phải dựng một `CongCu` giả, và một `CongCu`
       giả trong đường **giữ tiền** là đúng thứ không nên có.
    """
    nid = node["id"]
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, nid, vong)
    lan = int(anh.attempt_number if anh else 1)
    try:
        params = giai_tham_so(db, run.id, node.get("params") or {}, vong)
    except LoiThamSo as loi:
        may_trang_thai.chuyen_node(
            db, run.id, nid, sang="FAILED", mo_ta="giai tham so",
            error=str(loi), attempt_number=lan, vong=vong)
        return None
    try:
        app_slug = _chu_job(nd.job_type)
    except LoiTienTo as loi:
        may_trang_thai.chuyen_node(
            db, run.id, nid, sang="FAILED", mo_ta="lane connector chua co chu",
            error=f"loi_he_thong: {loi}"[:2000], attempt_number=lan, vong=vong)
        return None
    gia_that = int(nd.gia.so if nd.gia.kieu == "co_dinh" else 0)
    tran = int(node.get("gia_tran", 0))
    if gia_that > tran:
        may_trang_thai.chuyen_node(
            db, run.id, nid, sang="FAILED", mo_ta="vuot tran bao gia",
            error=f"vuot_tran_bao_gia: {gia_that} > {tran}",
            attempt_number=lan, vong=vong)
        return None
    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id=run.owner_id,
                               kind="JOB", required_successes=1)
    cho_doi.chan_node(db, run_id=run.id, node_id=nid, waitpoint_id=wp.id,
                      vong=vong)
    khoa = _khoa_idem(run, node, lan, _NhuCongCu(nd), params, vong)
    tham_so = dict(params)
    tham_so["owner_id"] = run.owner_id
    tham_so["_idem"] = khoa
    # 🔴 SỬA 25/09 (lan wfp): TRƯỚC đây `tham_so` không mang `credential_ref`
    #    của node — `_bi_mat` (`apps/connector_runner/jobs.py`) luôn nhận
    #    ref RỖNG, tức MỌI job piece/connector chạy KHÔNG credential, kể cả
    #    khi node đã gắn một credential thật. Với `connector.youtube.upload`
    #    nó lộ ra ở `LoiHandler("credential_loi: thieu access_token")`
    #    (`_chay_youtube` không có access_token) — job FAILED nhưng vì lý do
    #    SAI (nhìn như "chưa gắn key" dù người soạn ĐÃ gắn).
    #    `connector.THAM_SO_CREDENTIAL` là hợp đồng CHUNG với `jobs.handle`
    #    (`_bi_mat(db, params.get(THAM_SO_CREDENTIAL), ...)`) — cùng một
    #    hằng ở cả hai đầu, không phải chuỗi `"credential"` gõ tay hai nơi.
    from platform_core.workflow.connector import THAM_SO_CREDENTIAL

    tham_so[THAM_SO_CREDENTIAL] = str(node.get("credential_ref") or "")
    # ⭐ Thứ handler cần để gọi runner. Lấy từ ĐỒ THỊ ĐÃ BIÊN DỊCH (`node`),
    #    ⛔ không tra lại catalog lúc chạy: một bản publish phải chạy được
    #    với đúng phiên bản piece nó được biên dịch cùng, kể cả khi catalog
    #    đã đổi sau đó.
    tham_so["_connector"] = {
        "node_type": str(node["type"]),
        "piece": str(node.get("piece") or ""),
        "piece_version": str(node.get("piece_version") or ""),
        "op": str(node.get("op") or "run_action"),
        "name": str(node.get("ten_action") or ""),
        "run_id": run.id,
        "node_id": nid,
    }
    job = jobs.submit(db, user_id=run.owner_id, app_slug=app_slug,
                      job_type=nd.job_type, params=tham_so, dedupe_key=khoa,
                      max_attempts=1, parent_id=wp.id, plan_id=run.id,
                      origin=ORIGIN_WORKFLOW, priority_class="internal",
                      admission_resource=TAI_NGUYEN_CONNECTOR,
                      admission_slots=SUAT_CONNECTOR)
    may_trang_thai.chuyen_node(
        db, run.id, nid, sang="QUEUED", mo_ta="da nop job connector",
        job_id=job.id, attempt_number=lan,
        output_ref={"_gia_that": gia_that}, vong=vong)
    return job.id


def nop_job(db, run: WorkflowRun, node: dict, *,
            cong_cu: Optional[dict[str, CongCu]] = None,
            vong=()) -> Optional[str]:
    from platform_core.workflow.nut import JOB_TYPE_KHONG_TOOLSPEC

    # ⭐ Rẽ theo **BỘ THI HÀNH**, ⛔ không theo tiền tố tên. `piece.*` và
    #    `connector.*` đều không bọc ToolSpec; cái chung của chúng là
    #    `job_type`, không phải cái tên.
    _nd = _dinh_nghia(node.get("type", ""))
    if _nd is not None and _nd.job_type in JOB_TYPE_KHONG_TOOLSPEC:
        return _nop_job_connector(db, run, node, _nd, vong=vong)
    cc_all = _nguon.tat_ca() if cong_cu is None else cong_cu
    nid = node["id"]
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, nid, vong)
    lan = int(anh.attempt_number if anh else 1)
    try:
        ten_cc = ten_cong_cu(node["type"])
    except LoiTienTo as loi:
        # ⛔ Lỗi CỦA TA, không phải của registry — nên mã là `loi_he_thong`
        #    (§5.6) và câu lỗi mang TÊN LOẠI THẬT, không mang một cái đuôi
        #    bị cắt bừa.
        may_trang_thai.chuyen_node(
            db, run.id, nid, sang="FAILED",
            mo_ta="cau noi job khong doc duoc loai node",
            error=f"loi_he_thong: {loi}"[:2000], attempt_number=lan,
            vong=vong)
        return None
    cc = cc_all.get(ten_cc)
    if cc is None:
        # ⭐ F5 (final-review.md): tra `cc_all[...]` bằng tay trước đây ném
        # `KeyError` thẳng vào `mot_vong` khi một tool bị gỡ khỏi registry
        # SAU KHI version đã publish (app tắt cờ, tool đổi tên) — nuốt mất
        # theo từng lượt (`except Exception` ở `mot_vong`), node đứng QUEUED
        # mãi, credit vẫn giữ, cho tới khi `TRAN_RUN` (20h) tự hết hạn. Mọi
        # chỗ từ chối node KHÁC trong hàm này đều xử lý văn minh (`LoiThamSo`,
        # vượt trần báo giá) — chỗ này cũng phải vậy: FAILED có mã lỗi rõ, để
        # run kết thúc ngay trong lượt này thay vì quay vòng đến khi hết hạn.
        may_trang_thai.chuyen_node(
            db, run.id, nid, sang="FAILED", mo_ta="cong cu bien mat khoi registry",
            error=f"cong_cu_khong_con: {ten_cc!r}", attempt_number=lan,
            vong=vong)
        return None
    try:
        params = giai_tham_so(db, run.id, node.get("params") or {}, vong)
    except LoiThamSo as loi:
        # `str(loi)` da la "<ma>: <chi tiet>" (LoiThamSo.__init__) - khong lap
        # lai `loi.ma` lan nua o day (review round 1: ma "dau_vao_sai" bi lap
        # ba lan khi ghep them prefix rieng).
        may_trang_thai.chuyen_node(
            db, run.id, nid, sang="FAILED", mo_ta="giai tham so",
            error=str(loi), attempt_number=lan, vong=vong)
        return None
    gia_that = int(cc.tinh_gia(params))
    tran = int(node.get("gia_tran", 0))
    if gia_that > tran:
        may_trang_thai.chuyen_node(
            db, run.id, nid, sang="FAILED", mo_ta="vuot tran bao gia",
            error=f"vuot_tran_bao_gia: {gia_that} > {tran}",
            attempt_number=lan, vong=vong)
        return None
    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id=run.owner_id,
                               kind="JOB", required_successes=1)
    cho_doi.chan_node(db, run_id=run.id, node_id=nid, waitpoint_id=wp.id,
                      vong=vong)
    tham_so = dict(params)
    tham_so["owner_id"] = run.owner_id           # như submit_child (v1)
    khoa = _khoa_idem(run, node, lan, cc, params, vong)
    tham_so["_idem"] = khoa
    # Làn + admission ĐÚNG con đường canonical (`public_api/invocation.py`
    # `submit()`, dòng ~500-560): làn do `ToolSpec.lane_for` chọn (không cứng
    # `cc.job_type`), `Job.admission_resource/slots` ghi LÚC NỘP qua
    # `registry.admission_luc_nop` — thiếu bước này `jobs.claim()` coi mọi
    # job GPU/LLM là "không giành tài nguyên chia sẻ" và có thể nhận quá số
    # thẻ (multijob 2.3, R20; review round 1, controller-found). `cc.spec`
    # rỗng (CongCu giả trong test cũ) ⇒ giữ hành vi cũ y nguyên: làn =
    # `job_type`, không admission — không tự suy diễn logic của registry ở
    # đây, chỉ gọi thẳng hai hàm đã có.
    if cc.spec is not None:
        lane = cc.spec.lane_for(tham_so)
        # `mac_dinh="internal"`: nhánh này chỉ chạy khi tool KHÔNG khai admission
        # nào cả (không `admission_theo_model`, không bộ ba tĩnh) — bản thân
        # `so_suat` vẫn là 0 trong nhánh đó (xem `admission_luc_nop`), nên nhãn
        # chỉ phục vụ quan sát/gom nhóm, không đổi quyền giành suất. Job này
        # đến từ động cơ workflow (không phải Public API, nơi dùng "api"), nên
        # nhãn "internal" khớp `priority_class="internal"` đã dùng ngay dưới
        # thay vì mượn nhãn "api" của một cửa khác.
        tai_nguyen, so_suat = registry.admission_luc_nop(
            cc.spec, tham_so, mac_dinh="internal")
    else:
        lane, tai_nguyen, so_suat = cc.job_type, "", 0
    job = jobs.submit(db, user_id=run.owner_id, app_slug=cc.app_slug,
                      job_type=lane, params=tham_so, dedupe_key=khoa,
                      max_attempts=3, parent_id=wp.id, plan_id=run.id,
                      origin=ORIGIN_WORKFLOW, priority_class="internal",
                      admission_resource=tai_nguyen, admission_slots=so_suat)
    may_trang_thai.chuyen_node(
        db, run.id, nid, sang="QUEUED", mo_ta="da nop job", job_id=job.id,
        attempt_number=lan, output_ref={"_gia_that": gia_that}, vong=vong)
    return job.id


def bao_ket_thuc(db, job: Job) -> None:
    from platform_core.workflow import tao_run
    if job.job_type == tao_run.DONG_CO_JOB:
        return
    if job.origin != ORIGIN_WORKFLOW or not job.parent_id or not job.plan_id:
        return
    trang_thai = {JOB_DONE: "SUCCEEDED", JOB_CANCELLED: "CANCELLED"}.get(
        str(job.status), "FAILED")
    ket_qua = dict(job.result or {}) if trang_thai == "SUCCEEDED" else {
        "error": str(job.error or "")[:2000],
        "provider_state": str(job.provider_state or "")}
    try:
        with db.begin_nested():
            cho_doi.ghi_tin_hieu(db, job.parent_id, seq=1, status=trang_thai,
                                 ref_id=job.id, result_ref=ket_qua)
    except IntegrityError:
        # `UNIQUE(waitpoint_id, seq)` — tín hiệu đã có: gọi lại luỹ đẳng (job
        # runner gọi trùng, retry hạ tầng). MỌI lỗi khác (FK thiếu, mất kết
        # nối, serialization) phải NỔI LÊN — nuốt hết bằng `except Exception`
        # (review round 1, Important #2) từng khiến job đóng "thành công" mà
        # node đứng QUEUED mãi mãi, không wakeup, không log.
        return
    danh_thuc.hen(db, run_id=job.plan_id, kind="job", due_at=_bay_gio(),
                  node_run_id=job.id)
    tao_run.danh_thuc_dong_co(db)


def ap_ket_qua(db, run: WorkflowRun, node_id: str, *,
               cong_cu: Optional[dict[str, CongCu]] = None,
               vong=()) -> Optional[str]:
    hien = may_trang_thai.trang_thai_node(db, run.id, node_id, vong)
    if hien not in ("QUEUED", "RUNNING"):
        return None
    for wp_id in cho_doi.waitpoint_cua_node(db, run.id, node_id, vong):
        wp = db.get(Waitpoint, wp_id)
        if wp is None or wp.kind != "JOB" or wp.status != "PENDING":
            continue
        sig = db.execute(select(WaitpointSignal).where(
            WaitpointSignal.waitpoint_id == wp_id)).scalars().first()
        if sig is None:
            continue
        wp.status = "COMPLETED"
        anh = thi_hanh.anh_chup_hien_tai(db, run.id, node_id, vong)
        lan = int(anh.attempt_number if anh else 1)
        gia_that = int((anh.output_ref or {}).get("_gia_that", 0)) if anh else 0
        node = _node_cua(db, run, node_id)
        if sig.status == "SUCCEEDED":
            du_lieu = dict(sig.result_ref or {})
            # ⭐ HẬU KIỂM (spec §12.1). `job.status == SUCCEEDED` **không**
            #    đảm bảo kết quả dùng được: ca đã đo trên máy B là HTTP 200,
            #    job SUCCEEDED, `content` RỖNG — "vô hình với quan trắc".
            #    Node nào biết điều đó thì KHAI một `hau_kiem`; cầu nối chỉ
            #    hỏi, ⛔ không tự biết loại node nào cần kiểm gì.
            nd = _dinh_nghia(node["type"])
            kiem = getattr(nd, "hau_kiem", None) if nd is not None else None
            if kiem is not None:
                tt_hk, ma_hk, chi_tiet_hk = kiem(du_lieu,
                                                node.get("params") or {})
                if tt_hk != "SUCCEEDED":
                    # ⛔ KHÔNG ghi `cost_credit`: cùng luật với mọi node
                    #    FAILED (`test_1718::test_job_loi_khong_tinh_tien`).
                    #    Khách không trả tiền cho một câu trả lời rỗng.
                    # ⚠️ Ta VẪN tốn tài nguyên máy B cho lượt ấy. Đó là một
                    #    khoản lỗ có thật, bị chặn trên bởi `retry.max ≤ 5`,
                    #    và nó phải được theo dõi chứ không được quên.
                    #
                    # 🔴 SỬA 24/09 (plan wf-v2 P6): dùng `tt_hk` mà hậu kiểm
                    #    TRẢ VỀ, ⛔ không cứng `"FAILED"`.
                    #
                    #    Bản cũ hỏi node *"kết quả này dùng được không"* rồi
                    #    **vứt câu trả lời đi**, chỉ giữ phần "không". Với
                    #    `ai_loi` thì vô hại — nó luôn trả `FAILED`. Với một
                    #    node `side_effect = irreversible`
                    #    (`connector.youtube.upload`) thì không: hậu kiểm của
                    #    nó trả **ABANDONED** cho một `video_id` rỗng, nghĩa
                    #    là *"có thể đã đăng rồi, ⛔ đừng đăng lại"*. Ép nó
                    #    thành FAILED là mở lại đường thử lại — tức video thứ
                    #    hai trên kênh khách.
                    #
                    #    Đây đúng hạng lỗi "hai chỗ khai một điều, không ai
                    #    bắt khớp": node khai ba giá trị, cầu nối chỉ đọc một.
                    sang_hk = str(tt_hk or "FAILED")
                    may_trang_thai.chuyen_node(
                        db, run.id, node_id, sang=sang_hk,
                        mo_ta="hau kiem ket qua job",
                        error=f"{ma_hk}: {chi_tiet_hk}"[:2000],
                        attempt_number=lan, job_id=sig.ref_id, vong=vong)
                    return sang_hk
            bao = du_lieu.get("credit_cost")      # handler báo giá thật (vd theo token)
            chi_phi = int(bao) if bao is not None else gia_that
            do_dai = len(json.dumps(du_lieu, default=str))
            tran_ref = ""
            if do_dai > GIOI_HAN_DAU_RA:
                # ⭐ Spec §5.8: output quá lớn KHÔNG làm hỏng node — nó ra
                #    artifact và output giữ ref. Plan 01a để FAILED
                #    (`dau_ra_qua_lon`) vì chưa có đường lưu; đây là chỗ trả nợ.
                # ⚠️ `credit_cost` đọc TRƯỚC dòng này: sau khi thay `du_lieu`
                #    bằng ref thì handler coi như không báo giá, và mọi node
                #    tràn sẽ bị thu theo `gia_that`.
                khoa = f"workflow/{run.id}/{node_id}/{lan}.json"
                du_lieu = {"_tran": _artifact.luu_json(
                    db, owner_id=run.owner_id, key=khoa, du_lieu=du_lieu)}
                tran_ref = str(du_lieu["_tran"]["artifact_ref"])
            # M2 (final-review.md): mặc định PHẢI khớp `nop_job` (fail-closed,
            # `0`) — bản cũ mặc định `chi_phi` (fail-OPEN, tức "không trần")
            # khi thiếu `gia_tran`. Không sờ được hôm nay (bộ biên dịch luôn
            # ghi `gia_tran` và `_ban_publish` từ chối version chưa biên
            # dịch), nhưng hai mặc định khác nhau cho CÙNG một luật là đúng
            # hình dạng hai bản sao trôi nhau — sửa cả hai về cùng `0`.
            chi_phi = min(chi_phi, int(node.get("gia_tran", 0)))  # không thu quá trần
            may_trang_thai.chuyen_node(
                db, run.id, node_id, sang="SUCCEEDED", mo_ta="job xong",
                output_ref=du_lieu, cost_credit=chi_phi, attempt_number=lan,
                job_id=sig.ref_id, vong=vong)
            if tran_ref:
                # LINEAGE — `created_by_snapshot_id` phải trỏ vào ảnh chụp
                # ĐANG GIỮ ref, để "tệp này từ đâu ra" trả lời được bằng MỘT
                # cột. Ảnh chụp đó là hàng SUCCEEDED vừa ghi ở trên: mô hình C
                # INSERT một hàng MỚI mỗi lần chuyển, nên lúc `luu_json` chạy
                # nó CHƯA tồn tại (`anh` khi đó còn là hàng QUEUED/RUNNING).
                moi = thi_hanh.anh_chup_hien_tai(db, run.id, node_id, vong)
                if moi is not None:
                    db.get(Artifact, tran_ref).created_by_snapshot_id = moi.id
            run.actual_cost = int(run.actual_cost or 0) + chi_phi
            db.flush()
            return "SUCCEEDED"
        mo_ho = (sig.result_ref or {}).get("provider_state") == jobs.PROVIDER_AMBIGUOUS
        from platform_core.workflow.nut import JOB_TYPE_KHONG_TOOLSPEC

        nd_loi = _dinh_nghia(node.get("type", ""))
        if nd_loi is not None and nd_loi.job_type in JOB_TYPE_KHONG_TOOLSPEC:
            # ⭐ `side_effect` đọc từ `NodeDefinition`, ⛔ không từ một
            #    `CongCu` không tồn tại. Với `connector.youtube.upload`
            #    (`irreversible`) thì một lượt MƠ HỒ phải ra **ABANDONED**:
            #    "mất kết nối giữa chừng" không chứng minh video chưa lên,
            #    nó chỉ chứng minh ta không biết — và thử lại là đăng hai lần.
            return _chot_that_bai(db, run, node_id, sig=sig, lan=lan,
                                  vong=vong, node=node,
                                  side_effect=str(nd_loi.side_effect),
                                  mo_ho=mo_ho)
        cc_all = _nguon.tat_ca() if cong_cu is None else cong_cu
        try:
            ten_cc = ten_cong_cu(node["type"])
        except LoiTienTo as loi:
            # Cùng lỗi, cùng mã, cửa thứ hai: job ĐÃ kết thúc nhưng cầu nối
            # không đọc nổi loại node. Không chốt trạng thái ở đây là để
            # node đứng QUEUED tới khi `TRAN_RUN` (20 giờ) hết hạn.
            may_trang_thai.chuyen_node(
                db, run.id, node_id, sang="FAILED",
                mo_ta="cau noi job khong doc duoc loai node",
                error=f"loi_he_thong: {loi}"[:2000], attempt_number=lan,
                job_id=sig.ref_id, vong=vong)
            return "FAILED"
        cc = cc_all.get(ten_cc)
        if cc is None:
            # F5 (final-review.md) — cùng lý do với `nop_job`: tool bị gỡ
            # khỏi registry giữa lúc publish và lúc job này kết thúc. Tra
            # `side_effect` bằng tay ném `KeyError` ở đây thì job ĐÃ kết thúc
            # (job runner đã gọi `bao_ket_thuc`) nhưng node không bao giờ
            # chốt trạng thái — cùng cái bẫy 20h, chỉ khác cửa vào. FAILED có
            # mã rõ, không đoán `side_effect` khi không còn ToolSpec nào để
            # đọc nó.
            may_trang_thai.chuyen_node(
                db, run.id, node_id, sang="FAILED", mo_ta="job ket thuc",
                error=f"cong_cu_khong_con: {ten_cc!r}", attempt_number=lan,
                job_id=sig.ref_id, vong=vong)
            return "FAILED"
        return _chot_that_bai(db, run, node_id, sig=sig, lan=lan, vong=vong,
                              node=node, side_effect=str(cc.side_effect),
                              mo_ho=mo_ho)
    return None


def _chot_that_bai(db, run: WorkflowRun, node_id: str, *, sig, lan: int,
                   vong, node: dict, side_effect: str, mo_ho: bool):
    """Nhánh KHÔNG-thành-công của `ap_ket_qua`, tách ra để **một** luật
    ABANDONED/CANCELLED/FAILED + retry phục vụ cả node app lẫn node connector.

    ⛔ Hai bản sao của luật này là đúng hình dạng "hai chỗ khai cùng một điều,
       không ai bắt khớp" — và chỗ chúng lệch nhau sẽ là chỗ một node
       `irreversible` bị thử lại.
    """
    if True:
        sang = "ABANDONED" if (mo_ho and side_effect == "irreversible") else (
            "CANCELLED" if sig.status == "CANCELLED" else "FAILED")
        # Ba mã riêng (spec §5.6 `NodeError.ma`) — review round 1: CANCELLED
        # từng bị gắn nhầm mã `provider_loi` (mã của FAILED).
        ma = {"ABANDONED": "ket_qua_mo_ho", "CANCELLED": "bi_huy"}.get(
            sang, "provider_loi")
        chi_tiet = str((sig.result_ref or {}).get("error", ""))
        # ⭐ Retry CẤP NODE (spec §5.6) — chỉ xảy ra ở ĐÂY, tức khi job đã kết
        #    thúc ERROR và retry của chính job đã cạn. `thu_lai` không có bộ
        #    đếm riêng: nó đọc `settings.retry`, hỏi `jobs.gian_cach_retry` về
        #    giãn cách, và hẹn một wakeup. `KHONG_THU_LAI` (ABANDONED/CANCELLED)
        #    thắng `settings.retry`, không phải ngược lại.
        node = _node_cua(db, run, node_id)
        if thu_lai.quyet_dinh(sang=sang, node=node, lan=lan) == "RETRY_SCHEDULED":
            han = thu_lai.hen(db, run_id=run.id, node=node, lan=lan,
                              vong=vong)
            may_trang_thai.chuyen_node(
                db, run.id, node_id, sang="RETRY_SCHEDULED",
                mo_ta="job ket thuc, con luot thu lai",
                error=f"{ma}: {chi_tiet}"[:2000],
                attempt_number=lan + 1, job_id=sig.ref_id, vong=vong,
                output_ref={thu_lai.KHOA_HAN: han.isoformat()})
            return "RETRY_SCHEDULED"
        may_trang_thai.chuyen_node(
            db, run.id, node_id, sang=sang, mo_ta="job ket thuc",
            error=f"{ma}: {chi_tiet}"[:2000],
            attempt_number=lan, job_id=sig.ref_id, vong=vong)
        return sang
    return None


def _node_cua(db, run: WorkflowRun, node_id: str) -> dict:
    from platform_core.models import WorkflowVersion
    g = db.get(WorkflowVersion, run.version_id).graph
    return next(n for n in g["nodes"] if n["id"] == node_id)


__all__ = ["GIOI_HAN_DAU_RA", "SUAT_CONNECTOR", "TAI_NGUYEN_CONNECTOR",
           "TIEN_TO_APP", "LoiThamSo", "LoiTienTo", "ap_ket_qua",
           "bao_ket_thuc", "giai_tham_so", "nop_job", "ten_cong_cu"]
