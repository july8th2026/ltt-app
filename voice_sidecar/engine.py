"""
engine.py — giữ MỘT thực thể VieNeu ấm, và giữ nó đúng.

Ba việc, và cả ba đều có một sự cố thật đứng sau:

  1. **Nạp model một lần, giữ ấm.** TTS là rất nhiều lượt ngắn; nạp lại mỗi lượt
     là trả toàn bộ chi phí nạp cho một câu ba giây.
  2. **Chốt "đang chạy GPU hay CPU" đọc từ SỐ ĐO.** Khuôn tầng 1 chốt 1.6. Sự cố
     23/08 ở máy B: mọi chốt sống/chết đều xanh trong hơn một giờ trong khi model
     bò trên CPU. Một cờ cấu hình không phát hiện được điều đó; `memory_allocated`
     thì có.
  3. **Từ chối khởi động nếu watermark không áp được.** Upstream nuốt lỗi này
     (issue #191) và hậu quả là API nói có dấu trong khi không có. Ta không được
     thừa kế sự im lặng đó.

⛔ MỘT GPU = MỘT VIỆC. `_Cong` là bộ đếm đồng thời **không chờ**: hết chỗ thì ném
   `DangBan` để tầng HTTP trả **429 + Retry-After**, không bao giờ 5xx. Lý do ở
   D-005: máy A coi 5xx là *hỏng* và sẽ cooldown rồi vô hiệu hoá đường gọi.
   Hàng đợi có chờ chỉ được sống ở admission plane của nền tảng (Q114).
"""
from __future__ import annotations

import base64
import io
import logging
import os
import tempfile
import threading
import time

import numpy as np

from . import tham_so

log = logging.getLogger("ltt.voice.engine")


class DangBan(RuntimeError):
    """Hết suất chạy. Ánh xạ ra HTTP 429 + Retry-After."""

    def __init__(self, retry_after_s: float = 5.0):
        super().__init__("Cong giong dang ban.")
        self.retry_after_s = retry_after_s


class LoiEngine(RuntimeError):
    """Engine hỏng thật (khác `DangBan`). Ánh xạ ra HTTP 503."""


# ─────────────────────────────────────────────────────────── biểu diễn giọng ──
#
# Biểu diễn giọng là **hai mảng numpy của ta** (Q117/QĐ-3): `speaker_emb` và
# `codes`. Đóng gói bằng `.npz` nén rồi base64 để đi qua JSON.
#
# ⭐ Vì sao không dùng `voices.json` của VieNeu: nó là định dạng của upstream,
#    và định danh sản phẩm không được cột vào định dạng của một nhà cung cấp.
#    `encode_reference()` trả thẳng hai mảng, nên ta không cần nó.

def dong_goi_ref(speaker_emb, codes) -> str:
    """Hai mảng -> chuỗi base64 (.npz nén)."""
    buf = io.BytesIO()
    np.savez_compressed(
        buf,
        speaker_emb=np.asarray(speaker_emb, dtype=np.float32),
        codes=(np.zeros(0, dtype=np.int64) if codes is None
               else np.asarray(codes, dtype=np.int64)),
    )
    return base64.b64encode(buf.getvalue()).decode("ascii")


def mo_goi_ref(b64: str) -> dict:
    """Chuỗi base64 -> dict `voice` mà `infer(voice=...)` nhận được.

    Trả về đúng hình dạng `{"speaker_emb": ..., "codes": ...}` — cùng hình dạng
    mà `get_preset_voice()` của SDK trả ra, nên hai đường (giọng dựng sẵn và
    giọng nhân bản) đi chung một nhánh mã.
    """
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception as e:  # noqa: BLE001 - dữ liệu ngoài, thông điệp phải rõ
        raise ValueError("ref khong phai base64 hop le") from e
    with np.load(io.BytesIO(raw)) as z:
        emb = np.asarray(z["speaker_emb"], dtype=np.float32)
        codes = np.asarray(z["codes"], dtype=np.int64)
    return {"speaker_emb": emb, "codes": (None if codes.size == 0 else codes)}


# ─────────────────────────────────────────────────────────────── cổng đồng thời ──

class _Cong:
    """Bộ đếm suất chạy. KHÔNG chờ — hết chỗ thì ném ngay."""

    def __init__(self, so_suat: int):
        self._sem = threading.BoundedSemaphore(max(1, int(so_suat)))
        self._dang_chay = 0
        self._khoa = threading.Lock()
        #: Thời gian một lượt gần nhất, để `Retry-After` là một con số có căn cứ
        #: chứ không phải một hằng số bịa ra.
        self._giay_gan_nhat = 5.0

    @property
    def dang_chay(self) -> int:
        return self._dang_chay

    def __enter__(self):
        if not self._sem.acquire(blocking=False):
            raise DangBan(retry_after_s=max(1.0, round(self._giay_gan_nhat, 1)))
        with self._khoa:
            self._dang_chay += 1
        self._bat_dau = time.perf_counter()
        return self

    def __exit__(self, *a):
        troi = time.perf_counter() - self._bat_dau
        with self._khoa:
            self._dang_chay -= 1
            # Trung bình trượt nhẹ: một lượt bất thường không kéo lệch hẳn.
            self._giay_gan_nhat = 0.7 * self._giay_gan_nhat + 0.3 * troi
        self._sem.release()
        return False


# ───────────────────────────────────────────────────────────────────── engine ──

class CongGiong:
    """Bọc `Vieneu` ấm. Một thực thể cho cả tiến trình."""

    def __init__(self, *, backend: str = "auto", device: str = "auto",
                 precision: str = "int8", max_batch_size: int = 8,
                 so_suat: int = 1, warmup: bool = True):
        self.backend_xin = backend
        self.device_xin = device
        self.cong = _Cong(so_suat)
        self._khoa_nap = threading.Lock()
        self._tts = None
        self._vram_sau_nap_mb = 0
        self._nap_giay = 0.0
        self.max_batch_size = max(1, int(max_batch_size))
        self._precision = precision
        self._warmup = warmup

    # ── nạp ──────────────────────────────────────────────────────────────────
    def nap(self) -> None:
        if self._tts is not None:
            return
        with self._khoa_nap:
            if self._tts is not None:
                return
            t0 = time.perf_counter()
            from vieneu import Vieneu

            tts = Vieneu(mode="v3turbo", backend=self.backend_xin,
                         device=self.device_xin, precision=self._precision,
                         max_batch_size=self.max_batch_size)

            # 🔴 CHỐT WATERMARK — TỪ CHỐI KHỞI ĐỘNG, KHÔNG GHI LOG RỒI ĐI TIẾP.
            #
            #    `base.py::_init_watermarker` của upstream bắt cả `AttributeError`
            #    rồi đặt `self.watermarker = None` — không một dòng log. Kết quả:
            #    `apply_watermark=True` ở khắp nơi mà không có dấu nào được áp
            #    (upstream #191, gốc là gói PyPI `perth` sai).
            #
            #    Nếu ta cũng chỉ ghi log thì ta thừa kế đúng lỗi đó: một lời hứa
            #    provenance sai còn tệ hơn không hứa.
            if getattr(tts, "watermarker", None) is None:
                raise LoiEngine(
                    "Watermarker khong nap duoc. Goi PyPI `perth` la thu vien "
                    "threading, khong phai watermarker cua Resemble. Chay "
                    "install-vieneu-sidecar.ps1 de go `perth` va cai "
                    "`resemble-perth` (upstream issue 191).")

            self._tts = tts
            self._nap_giay = time.perf_counter() - t0
            self._vram_sau_nap_mb = self._vram_dang_giu_mb()
            log.info("VieNeu san sang: backend=%s device=%s nap=%.1fs vram=%dMB",
                     self.backend_that, self.device_that, self._nap_giay,
                     self._vram_sau_nap_mb)
            if self._warmup:
                self._lam_am()

    def _lam_am(self) -> None:
        """Một lượt sinh ngắn để dựng sẵn CUDA graph và nạp trọn đường đi.

        ⚠️ Không có bước này thì **lượt đầu tiên của khách** phải trả phí capture
           CUDA graph (`cudagraph.py`: warmup 3 lượt + một lần capture). Khách
           không nên là người trả phí khởi động.
        """
        try:
            t0 = time.perf_counter()
            self._tts.infer("Xin chao.", **tham_so.bo_tham_so())
            log.info("Lam am xong trong %.2fs", time.perf_counter() - t0)
        except Exception as e:  # noqa: BLE001 - làm ấm hỏng không nên chặn khởi động
            log.warning("Lam am that bai (van chay tiep): %s", e)

    # ── đo thật, không đọc cấu hình ──────────────────────────────────────────
    @staticmethod
    def _vram_dang_giu_mb() -> int:
        """VRAM tiến trình này đang giữ, theo torch. 0 = không dùng GPU.

        ⭐ Đây là **phép đo**, không phải phép đọc cấu hình. Khuôn tầng 1 chốt 1.6
           tồn tại vì một cờ `device=cuda` vẫn xanh khi model đã rơi về CPU.
        """
        try:
            import torch
            if not torch.cuda.is_available():
                return 0
            return int(torch.cuda.memory_allocated() / (1024 * 1024))
        except Exception:  # noqa: BLE001 - không có torch = đường ONNX
            return 0

    @property
    def backend_that(self) -> str:
        return getattr(self._tts, "backend", "?") if self._tts else "chua_nap"

    @property
    def device_that(self) -> str:
        if not self._tts:
            return "chua_nap"
        dev = getattr(getattr(self._tts, "engine", None), "device", None)
        return str(dev) if dev is not None else self.backend_that

    @property
    def dang_tren_gpu(self) -> bool:
        """CHỐT SỐ ĐO: có đang thật sự giữ VRAM không."""
        return self._vram_dang_giu_mb() > 0

    @property
    def sample_rate(self) -> int:
        return int(getattr(self._tts, "sample_rate", tham_so.SAMPLE_RATE)) \
            if self._tts else tham_so.SAMPLE_RATE

    def co_streaming(self) -> bool:
        """Dò NĂNG LỰC LÚC CHẠY, không đọc `config.yaml`.

        ⛔ `config.yaml` của upstream khai `supports_streaming: false` cho **mọi**
           backbone trong khi `infer_stream` chạy thật trên cả hai engine. Đọc
           trường metadata đó là tự khai sai năng lực của chính mình.
        """
        if not self._tts:
            return False
        eng = getattr(self._tts, "engine", None)
        return callable(getattr(eng, "infer_stream", None))

    # ── sinh tiếng ───────────────────────────────────────────────────────────
    def _voice_arg(self, ref_b64: str | None, preset: str | None):
        if ref_b64:
            return mo_goi_ref(ref_b64)
        if preset:
            return preset
        return None      # -> giọng mặc định của SDK

    def noi(self, text: str, *, ref_b64=None, preset=None) -> tuple:
        """Một lượt sinh, có KIỂM trước khi trả về. Trả `(wav_float32, giay)`.

        🔴 K1 — bốn chốt: toàn vẹn · gần im · lặp đuôi · thời lượng.
           Hỏng thì sinh lại **một lần**; hỏng lần hai thì trả bản thứ hai kèm
           một dòng cảnh báo trong log, chứ không ném.

        ⭐ VÌ SAO TRẢ VỀ CHỨ KHÔNG NÉM khi thử lại vẫn hỏng: `chot_thoi_luong`
           có thể báo động nhầm trên một giọng đọc chậm bất thường, và biến một
           báo động nhầm thành một job hỏng là **trừ credit cho một việc chưa
           từng chạy sai**. Chốt ở đây để *sửa* một lượt hỏng, không để *từ chối*
           phục vụ khách.

        ⚠️ Sinh lại không cần đổi seed: `temperature` 0,8 nên hai lượt cùng
           tham số vốn đã khác nhau. Cache CUDA graph khoá theo
           `(batch, temperature, top_k, top_p)` — giữ nguyên bộ tham số thì
           không tốn thêm graph nào.
        """
        from . import chot_sinh

        self.nap()
        n = len(text or "")
        with self.cong:
            t0 = time.perf_counter()
            wav = np.asarray(
                self._tts.infer(text, voice=self._voice_arg(ref_b64, preset),
                                **tham_so.bo_tham_so()), dtype=np.float32)
            pq = chot_sinh.kiem_het(wav, self.sample_rate, n)

            # Ghi tương quan đuôi cho MỌI lượt, kể cả lượt đạt.
            #
            # ⭐ Đây là cách duy nhất để ngưỡng `0,92` đi từ "mượn của hệ cũ" tới
            #    "đo trên engine của mình". Số nền hiện có mới là 16 lượt (trung
            #    bình 0,031 · cao nhất 0,103 · ngưỡng cách 17 σ); một dòng log
            #    mỗi lượt biến nó thành hàng nghìn mà không tốn gì.
            # ⛔ Đọc qua `so_do()`, KHÔNG đọc thẳng `pq.chan_doan`.
            #
            #    Bản đầu làm `pq.chan_doan.get("tuong_quan")` và dòng log này
            #    **không bao giờ chạy**: `kiem_het` khi ấy chỉ trả chẩn đoán của
            #    chốt hỏng đầu tiên, nên trên một lượt KHOẺ nó trả
            #    `{"chot": "deu_dat"}` — không con số nào.
            #
            #    Triệu chứng trên production: log sạch bong, đọc lên y hệt
            #    "không phát hiện lặp nào", trong khi sự thật là **chưa đo gì**.
            tq = chot_sinh.so_do(pq, "lap_duoi", "tuong_quan")
            if tq is not None:
                log.info("[chot] tuong_quan_duoi=%.4f ky_tu=%d", tq, n)

            if not pq.dat:
                log.warning("[chot] luot 1 HONG: %s | %s", pq.ly_do, pq.chan_doan)
                wav2 = np.asarray(
                    self._tts.infer(text, voice=self._voice_arg(ref_b64, preset),
                                    **tham_so.bo_tham_so()), dtype=np.float32)
                pq2 = chot_sinh.kiem_het(wav2, self.sample_rate, n)
                if pq2.dat:
                    log.info("[chot] sinh lai DAT")
                    wav = wav2
                else:
                    log.error("[chot] sinh lai VAN HONG: %s — tra ban thu hai",
                              pq2.ly_do)
                    wav = wav2 if pq2.nhan else wav
            return wav, time.perf_counter() - t0

    def noi_lo(self, texts: list, *, ref_b64=None, preset=None) -> tuple:
        """Một lô. Trả `(danh_sach_wav, giay)`.

        Dùng `infer_batch` để các chunk chia nhau từng bước forward trên GPU —
        đó là chỗ GPU thật sự thắng CPU (README: *"The GPU win comes from
        batching"*).
        """
        self.nap()
        with self.cong:
            t0 = time.perf_counter()
            wavs = self._tts.infer_batch(
                texts, voice=self._voice_arg(ref_b64, preset),
                batch_size=self.max_batch_size, **tham_so.bo_tham_so())
            return ([np.asarray(w, dtype=np.float32) for w in wavs],
                    time.perf_counter() - t0)

    def phat_dan(self, text: str, *, ref_b64=None, preset=None):
        """Sinh theo frame. Generator các mảng float32.

        Suất chạy được giữ **suốt cả generator** — nhả sớm là để lượt thứ hai
        chen vào giữa lúc lượt đầu còn đang chiếm engine.
        """
        self.nap()
        with self.cong:
            for chunk in self._tts.infer_stream(
                    text, voice=self._voice_arg(ref_b64, preset),
                    **tham_so.bo_tham_so()):
                if chunk is None or len(chunk) == 0:
                    continue
                yield np.asarray(chunk, dtype=np.float32)

    # ── ghi danh ─────────────────────────────────────────────────────────────
    def ghi_danh_kho(self, duong_wav: str, *, denoise: bool = True,
                     so_clip: int = 5) -> dict:
        r"""Ghi danh theo KHO nhiều cửa sổ (K2). Trả cùng hình dạng `ghi_danh`.

        Gộp `speaker_emb` qua cả kho, giữ `ref_codes` của **cửa sổ tốt nhất**.

        🔴 HAI THỨ `prepare_reference` TRẢ VỀ CÓ BẢN CHẤT KHÁC NHAU, và đó là
           toàn bộ thiết kế của hàm này:

             · `speaker_emb` — vector 192 chiều từ bộ mã hoá người nói. Trung
               bình nhiều lượt phát chính là cách mọi hệ nhận dạng người nói ghi
               danh; nó kéo điểm về **trọng tâm giọng** thay vì một lát cắt.
             · `ref_codes`   — chuỗi token codec của một clip. **Không trung
               bình được**: nó là điều kiện âm học theo ngữ cảnh, và trung bình
               hai chuỗi token là tạo ra một chuỗi không tương ứng với âm thanh
               nào cả.

        ⛔ CHUẨN HOÁ SAU KHI CỘNG. Trung bình các vector đơn vị cho một vector
           **ngắn hơn** 1; đưa thẳng vào model là đưa một biên độ chưa từng có
           trong dữ liệu huấn luyện.

        🔴 ĐÃ ĐO 01/09/2026, VÀ NÓ TỆ HƠN RÕ RỆT. ĐỪNG BẬT.

           Kho giọng cũ, cùng bộ câu, cùng sàn người lạ
           (`tools/do_nhan_ban_tu_kho_cu.py`):

               cấu hình      biên tb    lệch     nhận đúng người
               một cửa sổ    +0,4352   0,0441        24/24
               kho 2         +0,1303   0,1096         7/21
               kho 5         +0,1304   0,1112         9/24

           **0/24** giọng tốt lên. Bốn giọng tụt xuống **âm** (`bella_nu` −0,076,
           `bietdoi_girl` −0,093, `hoathinh_female` −0,057,
           `khanh_male_entertainment` −0,014) — bản nhân bản gần một **người
           lạ** hơn gần chính người nói.

        🔴 VÀ `kho 2` GIỐNG HỆT `kho 5` (0,1303 so với 0,1304). Đó là con số
           quan trọng nhất ở đây, vì nó loại một cách giải thích:

           Có thể nghĩ kho tệ vì nó **trộn thêm cửa sổ kém** — kho lấy cửa sổ tốt
           nhất rồi mới tới các cửa sổ hạng dưới. Nếu vậy thì kho 5 phải tệ hơn
           kho 2. Nó không. Toàn bộ thiệt hại xảy ra ở **bước trung bình đầu
           tiên**, và thêm cửa sổ không làm tệ thêm chút nào.

           ⇒ Hỏng nằm ở **phép trung bình**, không ở chất lượng cửa sổ. Trung
             bình hai embedding của **cùng một người** đã đủ làm model đọc ra
             một người khác.

        ⭐ Vì sao lập luận nghe đúng mà kết quả sai — và đây là phần đáng nhớ:

           Trung bình embedding người nói là chuẩn mực ở hệ **nhận dạng**, nơi
           embedding được huấn luyện bằng một hàm mất mát metric nên **trọng tâm
           của một người là một điểm có nghĩa**. Ở đây embedding đi vào một model
           **sinh**, và model ấy chỉ từng thấy embedding của **một lượt phát**.
           Trung bình rơi vào một vùng nó chưa gặp; chuẩn hoá lại chỉ sửa độ
           dài, không sửa hướng — và hướng ấy đọc lên như một người thứ ba, mờ
           hơn cả hai.

        ⛔ "Gộp nhiều clip tham chiếu" là một ý **trực giác mạnh** — hệ cũ làm,
           XTTS làm, mọi tài liệu nhận dạng người nói đều làm. Nên nó sẽ được
           nghĩ lại. Hàm này ở lại **chính vì thế**: để lần sau ai đó muốn thử,
           họ có sẵn đường chạy và sẵn con số nói rằng đã thử rồi.

           Muốn mở lại thì phải là một **cơ chế khác**, không phải chạy lại phép
           cũ: ví dụ chọn cửa sổ theo đồng thuận (lấy cửa sổ gần trọng tâm nhất
           rồi dùng NGUYÊN embedding của nó, không trung bình) — cách đó giữ
           được một embedding thật trong khi vẫn dùng thông tin của cả kho.

        ⚠️ Tốn `so_clip` lần `prepare_reference` — ghi danh chậm hơn chừng ấy lần.
        """
        import soundfile as sf

        from . import chon_doan

        self.nap()
        with self.cong:
            t0 = time.perf_counter()
            wav, sr = sf.read(duong_wav, dtype="float32", always_2d=False)
            if getattr(wav, "ndim", 1) > 1:
                wav = wav.mean(axis=1)
            wav = np.asarray(wav, dtype=np.float32)
            kho = chon_doan.chon_kho(wav, int(sr), so_luong=max(1, int(so_clip)))

            embs, codes_tot, ho_so = [], None, []
            for i, kq in enumerate(kho):
                a = int(kq.bat_dau_s * sr)
                b = min(len(wav), int(kq.ket_thuc_s * sr))
                if b - a < int(0.5 * sr):
                    continue
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                tmp.close()
                try:
                    sf.write(tmp.name, wav[a:b], int(sr))
                    emb, codes = self._tts.encode_reference(tmp.name,
                                                            denoise=denoise)
                finally:
                    try:
                        os.unlink(tmp.name)
                    except OSError:
                        pass
                embs.append(np.asarray(emb, dtype=np.float32).ravel())
                if i == 0:
                    codes_tot = codes
                ho_so.append({"bat_dau_s": kq.bat_dau_s,
                              "ket_thuc_s": kq.ket_thuc_s,
                              "diem_dai_dien": kq.diem_dai_dien})

            if not embs:
                raise LoiEngine("khong cua so nao ghi danh duoc")
            tb = np.mean(np.stack(embs), axis=0)
            chuan = float(np.linalg.norm(tb))
            emb_gop = (tb / chuan if chuan else tb).astype(np.float32)

            return {
                "ref_b64": dong_goi_ref(emb_gop, codes_tot),
                "emb_dim": int(emb_gop.size),
                "so_codes": (0 if codes_tot is None
                             else int(np.asarray(codes_tot).size)),
                "giay": time.perf_counter() - t0,
                "chon_doan": {"da_chon": True, "kieu": "kho",
                              "so_cua_so": len(embs),
                              "goc_giay": round(len(wav) / float(sr), 2),
                              "cua_so": ho_so},
            }

    def ghi_danh(self, duong_wav: str, *, denoise: bool = True) -> dict:
        """Clip tham chiếu -> biểu diễn giọng của TA.

        `encode_reference` trả `(speaker_emb, ref_codes)` dạng numpy; ta đóng gói
        và **sở hữu** chúng. Không gọi `add_voice`/`save_voices` của SDK: chúng
        ghi vào `voices.json` của upstream, tức là để định danh sản phẩm trôi
        theo định dạng của một nhà cung cấp.
        """
        self.nap()
        with self.cong:
            t0 = time.perf_counter()
            # 🔴 CHỌN ĐOẠN TRƯỚC KHI SDK CẮT MÙ.
            #
            #    `prepare_reference` lấy 8 giây ĐẦU và vứt phần còn lại. Ta có
            #    cả clip nên chọn được đoạn đại diện nhất rồi đưa nó đúng đoạn
            #    ấy. Xem `chon_doan.py` cho hàm mục tiêu và nguồn.
            #
            # ⛔ Không bao giờ tệ hơn hôm nay: chọn hỏng thì dùng nguyên tệp gốc,
            #    tức đúng hành vi cũ. Một bước tối ưu KHÔNG được thêm một đường
            #    hỏng mới vào chỗ trước đây vẫn chạy.
            duong_dung, ho_so_chon = self._chon_doan_tham_chieu(duong_wav)
            try:
                emb, codes = self._tts.encode_reference(duong_dung, denoise=denoise)
            finally:
                if duong_dung != duong_wav:
                    try:
                        os.unlink(duong_dung)
                    except OSError:
                        pass
            return {
                "ref_b64": dong_goi_ref(emb, codes),
                "emb_dim": int(np.asarray(emb).size),
                "so_codes": (0 if codes is None else int(np.asarray(codes).size)),
                "giay": time.perf_counter() - t0,
                "chon_doan": ho_so_chon,
            }

    def _chon_doan_tham_chieu(self, duong_wav: str) -> tuple:
        """`(đường dẫn để enroll, hồ sơ chọn)`. Hỏng thì trả nguyên tệp gốc."""
        try:
            import soundfile as sf

            from . import chon_doan

            wav, sr = sf.read(duong_wav, dtype="float32", always_2d=False)
            if getattr(wav, "ndim", 1) > 1:
                wav = wav.mean(axis=1)
            kq = chon_doan.chon(np.asarray(wav, dtype=np.float32), int(sr))
            if not kq.da_chon_that:
                return duong_wav, {"da_chon": False, "ly_do": kq.ly_do}

            a = int(kq.bat_dau_s * sr)
            b = min(len(wav), int(kq.ket_thuc_s * sr))
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tmp.close()
            sf.write(tmp.name, np.asarray(wav[a:b], dtype=np.float32), int(sr))
            return tmp.name, {
                "da_chon": True,
                "bat_dau_s": kq.bat_dau_s, "ket_thuc_s": kq.ket_thuc_s,
                "goc_giay": round(len(wav) / float(sr), 2),
                "diem_dai_dien": kq.diem_dai_dien, "snr_db": kq.snr_db,
                "so_ung_vien": kq.so_ung_vien,
                # Thang nào đã chấm chất lượng. `dnsmos.cham` trả `None` IM
                # LẶNG khi thiếu `onnxruntime`/`scipy`/tệp model, nên không có
                # dòng này thì một lần deploy làm rơi chúng sẽ hạ bộ chọn về
                # SNR mà không gì ở đâu đổi. Xem `KetQuaChon.thang_chat_luong`.
                "thang_chat_luong": kq.thang_chat_luong,
                "ly_do": kq.ly_do,
            }
        except Exception as e:      # noqa: BLE001 - chon hong KHONG duoc lam hong ghi danh
            log.warning("chon doan tham chieu hong, dung nguyen clip: %s", e)
            return duong_wav, {"da_chon": False, "ly_do": f"loi: {type(e).__name__}"}

    # ── công bố ──────────────────────────────────────────────────────────────
    def nang_luc(self) -> dict:
        """Năng lực **đo lúc chạy**, không đọc từ metadata."""
        d = {
            "da_nap": self._tts is not None,
            "backend": self.backend_that,
            "device": self.device_that,
            "tren_gpu": self.dang_tren_gpu,
            "vram_mb": self._vram_dang_giu_mb(),
            "vram_sau_nap_mb": self._vram_sau_nap_mb,
            "nap_giay": round(self._nap_giay, 2),
            "sample_rate": self.sample_rate,
            "streaming": self.co_streaming(),
            "watermark": bool(getattr(self._tts, "watermarker", None)) if self._tts else False,
            "max_batch_size": self.max_batch_size,
            "dang_chay": self.cong.dang_chay,
        }
        d.update(tham_so.cong_bo())
        return d


# ── thực thể dùng chung cho cả tiến trình ────────────────────────────────────
_CONG_GIONG: CongGiong | None = None
_KHOA = threading.Lock()


def lay_cong() -> CongGiong:
    """Thực thể duy nhất. Cấu hình đọc từ môi trường, không hằng số rải rác."""
    global _CONG_GIONG
    if _CONG_GIONG is not None:
        return _CONG_GIONG
    with _KHOA:
        if _CONG_GIONG is None:
            _CONG_GIONG = CongGiong(
                backend=os.environ.get("LTT_VOICE_BACKEND", "auto"),
                device=os.environ.get("LTT_VOICE_DEVICE", "auto"),
                precision=os.environ.get("LTT_VOICE_PRECISION", "int8"),
                max_batch_size=int(os.environ.get("LTT_VOICE_MAX_BATCH", "8")),
                so_suat=int(os.environ.get("LTT_VOICE_MAX_DONG_THOI", "1")),
                warmup=os.environ.get("LTT_VOICE_WARMUP", "1") != "0",
            )
    return _CONG_GIONG
