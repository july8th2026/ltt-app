"""
runner.py — vòng thi hành một job: dựng workflow → xếp hàng → chờ → lấy ảnh → đẩy R2.

⭐ ĐỌC TRẠNG THÁI TỪ `/history`, KHÔNG TỪ WEBSOCKET. Lý do ở `comfy.py`: ComfyUI
   gửi `progress`/`executing` **chỉ tới client đã gửi prompt**, nên websocket không
   giúp gì cho việc lạ, và với việc của ta thì `/history` là đủ.

⭐ HÌNH DẠNG `/history` (đọc từ `execution.py:1282`, không suy đoán):

       {"<prompt_id>": {
           "status": {"status_str": "success" | "error",
                      "completed": bool, "messages": [...]},
           "outputs": {"<node_id>": {"images": [{filename, subfolder, type}]}},
           "meta": {...}}}

   ⛔ Mục lịch sử **xuất hiện cả khi hỏng**. Thấy có mục ≠ thành công — phải đọc
   `status.status_str`. Đây đúng là cái bẫy "phán quyết không đọc thứ nó vừa in ra".

⛔ HẾT GIỜ THÌ PHẢI HUỶ ĐÚNG PROMPT CỦA MÌNH. `interrupt()` không có `prompt_id`
   sẽ giết lượt đang chạy — trên máy B đó có thể là lượt video 70 phút của dự án
   khác. `ComfyClient.interrupt` bắt buộc truyền id để không ai lỡ tay.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from . import jobs as J
from . import ngan_sach as NS
from . import theo_doi_luot
from .comfy import ComfyClient, ComfyError, ComfyRejected, prompt_id_for
from .storage_io import HttpFetcher, RefSpec, StorageIOError, day_ket_qua, tai_refs
from .workflows import WorkflowError, kiem_node, nap, thay

log = logging.getLogger("render_gateway.runner")

#: Mã lỗi là HỢP ĐỒNG với máy A — đừng đổi chuỗi, máy A phân nhánh theo chúng.
E_BAD_REQUEST = "bad_request"
E_WORKFLOW = "workflow_invalid"
E_REF = "ref_invalid"
E_COMFY_DOWN = "comfy_unavailable"
E_COMFY_REJECT = "comfy_rejected"
E_OOM = "oom"
E_TIMEOUT = "timeout"
E_STORAGE = "storage_failed"
#: Cau hinh vuot vung DA DO. Tu choi co chu y, khong phai loi he thong (D-024).
E_NGOAI_VUNG = "config_unmeasured"
E_INTERNAL = "internal"

#: Nhận diện OOM từ thông điệp của ComfyUI/torch. Không dựa vào mã lỗi vì ComfyUI
#: gói mọi thứ vào `status.messages` dạng văn bản.
_DAU_HIEU_OOM = ("out of memory", "outofmemory", "cuda error: out of memory",
                 "allocate", "not enough memory")


@dataclass
class RenderRequest:
    job_id: str
    template: str                      # tên file trong render_gateway/workflows/
    values: dict[str, Any]             # giá trị cho các thẻ `@ten`
    refs: list[RefSpec] = field(default_factory=list)
    put_urls: list[str] = field(default_factory=list)
    image_keys: list[str] = field(default_factory=list)
    content_type: str = "image/png"
    #: Tên thẻ nhận tên tệp ảnh tham chiếu, theo thứ tự: `["ref1", "ref2"]`.
    ref_slots: list[str] = field(default_factory=list)


class Runner:
    def __init__(self, comfy: ComfyClient, store: J.JobStore, fetcher: HttpFetcher, *,
                 input_dir: Path, timeout_s: float = 900.0,
                 poll_s: float = 2.0,
                 sleep: Callable[[float], None] = time.sleep,
                 now: Callable[[], float] = time.monotonic,
                 workflow_dir: Optional[Path] = None,
                 doc_vram_mb: Optional[Callable[[], Optional[int]]] = None,
                 doc_ram_gb: Optional[Callable[[], Optional[float]]] = None):
        # Hai nguồn đo tiêm được: test không được phụ thuộc vào card của máy đang
        # chạy test, và cũng không được chờ `nvidia-smi` thật.
        self.doc_vram_mb = doc_vram_mb
        self.doc_ram_gb = doc_ram_gb
        self.comfy = comfy
        self.store = store
        self.fetcher = fetcher
        self.input_dir = input_dir
        self.timeout_s = timeout_s
        self.poll_s = poll_s
        self._sleep = sleep
        self._now = now
        self.workflow_dir = workflow_dir

    # ── công khai ────────────────────────────────────────────────────────────
    def _doc_vram(self) -> Optional[int]:
        """VRAM đang dùng, `nvidia-smi`. Tiêm được để test không cần GPU."""
        if self.doc_vram_mb is not None:
            return self.doc_vram_mb()
        from .busy import vram_dung_mb_qua_smi
        return vram_dung_mb_qua_smi()

    def _doc_ram_gb(self) -> Optional[float]:
        """RAM còn trống, lấy từ ComfyUI `/system_stats`.

        ⭐ Cùng nguồn với `BusyWatcher._tai_nguyen`, và cùng lý do: con số RAM ở
           đó **không** bị giới hạn theo tiến trình nên nó đúng, khác hẳn con số
           VRAM của cùng endpoint (mù với tiến trình khác trên Windows/WDDM).
        """
        if self.doc_ram_gb is not None:
            return self.doc_ram_gb()
        try:
            st = self.comfy.system_stats()
            gia_tri = (st.get("system") or {}).get("ram_free")
            return float(gia_tri) / (1024 ** 3) if gia_tri else None
        except Exception:                                       # noqa: BLE001
            return None

    def run(self, req: RenderRequest) -> J.Job:
        """Chạy một job tới khi xong. Không bao giờ ném — mọi lỗi thành trạng thái."""
        pid = prompt_id_for(req.job_id)
        job, la_moi = self.store.create_or_get(req.job_id, pid)
        if not la_moi:
            # Idempotency: cùng `job_id` thì trả lại đúng job cũ, không vẽ lần hai.
            return job
        try:
            return self._chay(req, job)
        except Exception as e:                                    # noqa: BLE001
            log.exception("job %s hong ngoai du kien", req.job_id)
            return self.store.fail(req.job_id, E_INTERNAL, str(e)) or job

    # ── các bước ─────────────────────────────────────────────────────────────
    def _chay(self, req: RenderRequest, job: J.Job) -> J.Job:
        self.store.set_status(req.job_id, J.PREPARING)

        # ① Dựng workflow trên CPU. Mọi thứ sai ở đây phải lộ ra TRƯỚC khi tiêu GPU.
        try:
            mau = nap(req.template, thu_muc=self.workflow_dir)
        except WorkflowError as e:
            return self.store.fail(req.job_id, E_WORKFLOW, str(e)) or job

        # ② Ảnh tham chiếu: tải về `input` của ComfyUI rồi gắn tên vào thẻ.
        gia_tri = dict(req.values)
        if req.refs:
            try:
                ten_files = tai_refs(self.fetcher, req.refs, job_id=req.job_id,
                                     input_dir=self.input_dir)
            except StorageIOError as e:
                return self.store.fail(req.job_id, E_REF, str(e)) or job
            for slot, ten in zip(req.ref_slots, ten_files):
                gia_tri[slot] = ten

        try:
            wf = thay(mau, gia_tri)
        except WorkflowError as e:
            return self.store.fail(req.job_id, E_WORKFLOW, str(e)) or job

        # ③ Kiểm node trước khi gửi — "thứ gì CPU trả lời được thì không hỏi GPU".
        try:
            kiem_node(wf, self.comfy.object_info_keys())
        except WorkflowError as e:
            return self.store.fail(req.job_id, E_WORKFLOW, str(e)) or job
        except ComfyError as e:
            return self.store.fail(req.job_id, E_COMFY_DOWN, str(e)) or job

        # ③c NGÂN SÁCH TOKEN — chặn cấu hình ngoài vùng đã đo (D-024).
        #
        # ⚠️ ĐÂY KHÔNG PHẢI CHỐT DUY NHẤT, và đừng tưởng nó là. `chay_baseline.py`
        #    — đúng cái đường đã làm sập máy B hôm 22/08 — gọi thẳng
        #    `ComfyClient.queue_prompt`, **KHÔNG đi qua Runner**. Nó có chốt RIÊNG,
        #    cùng gọi `ngan_sach.kiem_workflow`. Thêm một đường vào ComfyUI mới thì
        #    phải thêm chốt ở đó nữa; `tests/test_245` có test đếm các đường đó.
        #    Đọc từ `wf` (workflow ĐÃ DỰNG), không từ tham số của bên gọi:
        #    `chay_baseline.py` đưa ảnh tham chiếu qua giá trị thẻ chứ không qua
        #    `req.refs`, nên đếm theo tham số sẽ ra 0 và cấu hình nguy hiểm đi lọt.
        try:
            NS.kiem_workflow(wf)
        except (NS.NgoaiVungDaDo, ValueError) as e:
            return self.store.fail(req.job_id, E_NGOAI_VUNG, str(e)) or job

        # ③b IDEMPOTENCY XUYÊN TIẾN TRÌNH — hỏi ComfyUI trước khi xếp hàng.
        #
        # ⛔ SỰ CỐ THẬT 2026-08-21: bản đầu bỏ qua bước này. Cổng khởi động lại (hoặc
        #    một tiến trình khác chạy cùng `job_id`) sẽ **xếp hàng lại một job đã
        #    xong** — vừa trả về kết quả cũ vừa đốt thêm 100 giây GPU cho không.
        #    `JobStore` chỉ nhớ trong tiến trình; `/history` của ComfyUI là bộ nhớ
        #    duy nhất sống sót qua khởi động lại. Thiết kế ở `KE_HOACH_H37.md` §3 đã
        #    hứa điều này ("kết quả cũ vẫn tra được trong /history") — nhưng mã thì
        #    chưa làm.
        try:
            if self.comfy.da_xong(job.prompt_id):
                log.info("job %s da chay xong tu truoc — lay lai ket qua, KHONG ve lai",
                         req.job_id)
                return self._lay_ket_qua(req, job)
        except ComfyError:
            pass          # không hỏi được thì cứ chạy đường thường

        # ④ Xếp hàng, rồi chờ. Một lần thử lại DUY NHẤT nếu OOM, sau khi nhả VRAM.
        for lan in (1, 2):
            try:
                self.comfy.queue_prompt(wf, prompt_id=job.prompt_id)
            except ComfyRejected as e:
                return self.store.fail(req.job_id, E_COMFY_REJECT, str(e)) or job
            except ComfyError as e:
                return self.store.fail(req.job_id, E_COMFY_DOWN, str(e)) or job

            self.store.set_status(req.job_id, J.GENERATING)

            # ── LẤY MẪU TRONG LÚC CHẠY, không chỉ chờ kết quả ───────────────
            # Trước đây đường này **không lấy mẫu nào**, trong khi
            # `deploy/chay_baseline.py` lấy ~198 mẫu mỗi job. Tức là bộ đo canh
            # cẩn thận còn thứ khách dùng chạy mù — và đó đúng là chỗ tệ nhất để
            # mù, vì "model chỉ thường trú một phần" **vẫn cho ra ảnh đúng**, chỉ
            # chậm 3–10 lần, và mọi chốt sống/chết vẫn xanh (P6, D-051).
            with theo_doi_luot.NguoiTheoDoi(
                    doc_vram=self._doc_vram,
                    doc_ram_trong_gb=self._doc_ram_gb) as td:
                ket, thong_diep = self._cho(job.prompt_id)

            tt = td.tom_tat()
            if tt.so_mau:
                self.store.set_status(req.job_id, J.GENERATING,
                                      do_duoc=tt.as_dict())
            for cb in tt.canh_bao:
                log.warning("job %s: %s", req.job_id, cb)

            if ket == "success":
                break
            if ket == "timeout":
                self._huy_an_toan(job.prompt_id)
                return self.store.fail(req.job_id, E_TIMEOUT,
                                       f"qua {self.timeout_s:.0f} giay") or job
            if ket == "down":
                return self.store.fail(req.job_id, E_COMFY_DOWN, thong_diep) or job
            # ket == "error"
            if _la_oom(thong_diep) and lan == 1:
                log.warning("job %s OOM, nha VRAM roi thu lai mot lan", req.job_id)
                try:
                    self.comfy.free()
                except ComfyError:
                    pass
                continue
            ma = E_OOM if _la_oom(thong_diep) else E_COMFY_REJECT
            return self.store.fail(req.job_id, ma, thong_diep) or job

        # ⑤ Lấy ảnh và đẩy lên R2.
        return self._lay_ket_qua(req, job)

    def _lay_ket_qua(self, req: RenderRequest, job: J.Job) -> J.Job:
        """Tải ảnh từ ComfyUI rồi đẩy lên R2. Dùng chung cho cả đường chạy mới lẫn
        đường lấy lại kết quả cũ (idempotency)."""
        self.store.set_status(req.job_id, J.SAVING)
        try:
            refs = self.comfy.images_of(job.prompt_id)
            if not refs:
                return self.store.fail(
                    req.job_id, E_COMFY_REJECT,
                    "ComfyUI bao thanh cong nhung khong co anh nao trong outputs") or job
            data = [self.comfy.download(r) for r in refs]
        except ComfyError as e:
            return self.store.fail(req.job_id, E_COMFY_DOWN, str(e)) or job

        try:
            so = day_ket_qua(self.fetcher, data, req.put_urls,
                             content_type=req.content_type)
        except StorageIOError as e:
            return self.store.fail(req.job_id, E_STORAGE, str(e)) or job

        if so < len(data):
            log.warning("job %s: sinh %d anh nhung chi co %d ve PUT — bo phan du",
                        req.job_id, len(data), so)
        return self.store.set_status(req.job_id, J.COMPLETED,
                                     image_keys=list(req.image_keys[:so])) or job

    def _cho(self, prompt_id: str) -> tuple[str, str]:
        """Chờ ComfyUI xong. Trả `("success"|"error"|"timeout"|"down", thong_diep)`."""
        het = self._now() + self.timeout_s
        loi_lien_tiep = 0
        while self._now() < het:
            try:
                # ⛔ HAI điều kiện, không phải một: có bản ghi `success` **và** không
                #    còn trong hàng đợi. Chỉ đọc bản ghi là chưa đủ — một prompt
                #    ĐANG CHỜ vẫn trả về `success` nếu id đó đã từng chạy (ta tự đặt
                #    id theo `job_id` nên nó lặp lại). Đo thật trên máy B 21/08.
                if self.comfy.da_xong(prompt_id):
                    return "success", ""
                muc = self.comfy.history(prompt_id)
                loi_lien_tiep = 0
            except ComfyError as e:
                # Một cú vấp mạng không phải là máy chủ chết. Ba cú liên tiếp thì là.
                loi_lien_tiep += 1
                if loi_lien_tiep >= 3:
                    return "down", f"ComfyUI khong tra loi 3 lan lien tiep: {e}"
                self._sleep(self.poll_s)
                continue
            if muc:
                st = muc.get("status") or {}
                # Bản ghi có, nhưng KHÔNG phải success ⇒ hỏng thật, dừng ngay.
                if st.get("status_str") and str(st["status_str"]) != "success":
                    return "error", _gop_thong_diep(st)
            self._sleep(self.poll_s)
        return "timeout", ""

    def _huy_an_toan(self, prompt_id: str) -> None:
        try:
            self.comfy.interrupt(prompt_id)
        except (ComfyError, ValueError) as e:
            log.warning("khong huy duoc prompt %s: %s", prompt_id, e)


# ── tiện ích ─────────────────────────────────────────────────────────────────
def _gop_thong_diep(status: dict) -> str:
    ra = []
    for m in (status.get("messages") or []):
        ra.append(str(m))
    return (" | ".join(ra) or "ComfyUI bao loi khong kem thong diep")[:500]


def _la_oom(thong_diep: str) -> bool:
    t = (thong_diep or "").lower()
    return any(d in t for d in _DAU_HIEU_OOM)
