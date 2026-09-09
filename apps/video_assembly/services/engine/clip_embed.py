from ..tuong_thich.dll_fix import fix_torch_dll
fix_torch_dll()

import torch, open_clip
from PIL import Image
from ..tuong_thich.log import info, warn


_DEFAULT_CLIP_CFG = {
    "model": "ViT-B-32",
    "pretrained": "laion2b_s34b_b79k",
}


class ClipEmbedder:
    def __init__(self, cfg: dict):
        # ✅ Robust: avoid KeyError if 'clip' is missing in cfg
        ccfg = cfg.get("clip")
        if not isinstance(ccfg, dict):
            warn("clip_embed_missing_clip_cfg", err="cfg['clip'] missing; using defaults", default=_DEFAULT_CLIP_CFG)
            ccfg = dict(_DEFAULT_CLIP_CFG)
        else:
            merged = dict(_DEFAULT_CLIP_CFG)
            merged.update(ccfg)
            ccfg = merged

        # [ĐA GPU 2026-09] Trước đây chỉ đặt "cuda" (= cuda:0) nên MỌI job CLIP
        # đều đổ vào card 0 bất kể gpu_arbiter cấp card nào — card 1 nằm không.
        # Nay pin đúng card đã được cấp: "cuda:<idx>".
        if torch.cuda.is_available():
            try:
                from gpu_arbiter import current_gpu
                self.gpu_index = int(current_gpu())
            except Exception:
                self.gpu_index = 0
            self.device = f"cuda:{self.gpu_index}"
        else:
            self.gpu_index = -1
            self.device = "cpu"

        # [2026-08] Truoc day tat cuDNN de ne loi nap DLL (Error code 127) tren
        # cau hinh cu. Da kiem tra tren may hien tai: torch 2.11.0+cu128,
        # cudnn 9.19 available=True, sm_120 -> workaround khong con can va dang
        # lam CLIP cham di dang ke. Bat lai, van co duong lui neu loi.
        if self.device.startswith("cuda"):
            try:
                if torch.backends.cudnn.is_available():
                    torch.backends.cudnn.enabled = True
                    torch.backends.cudnn.benchmark = True   # anh cung kich thuoc -> chon thuat toan nhanh nhat
                    info("cudnn_enabled", version=torch.backends.cudnn.version())
                else:
                    torch.backends.cudnn.enabled = False
                    info("cudnn_disabled", reason="cuDNN not available")
            except Exception as _e:
                torch.backends.cudnn.enabled = False
                info("cudnn_disabled", reason=f"probe failed: {_e}")

        # Log GPU info if available — đọc thông tin của ĐÚNG card được cấp,
        # không phải card 0 (hai card giống hệt nhau nên log card 0 sẽ gây hiểu nhầm
        # là job đang chạy ở đó).
        if self.gpu_index >= 0:
            gpu_name = torch.cuda.get_device_name(self.gpu_index)
            gpu_memory = torch.cuda.get_device_properties(self.gpu_index).total_memory / 1024**3
            info("gpu_detected", name=gpu_name, gpu_index=self.gpu_index,
                 vram_gb=round(gpu_memory, 2))

        model_name = ccfg.get("model") or _DEFAULT_CLIP_CFG["model"]
        pretrained = ccfg.get("pretrained") or _DEFAULT_CLIP_CFG["pretrained"]

        # ✅ Safe init
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained
        )
        self.model = self.model.to(self.device)
        self.tokenizer = open_clip.get_tokenizer(model_name)

        info("clip_embed_init",
             device=self.device,
             model=model_name,
             pretrained=pretrained,
             gpu_enabled=self.device.startswith("cuda"))

    def embed_clips(self, clips: list[dict], batch_size: int = 32):
        """
        Embed clips with GPU batch processing for 10-15x speedup.

        Args:
            clips: List of clip dicts with "frame" path
            batch_size: Batch size for GPU processing (32 optimal for RTX 3060)

        [Phase 8] try/finally bao quanh batch loop để empty_cache() chạy cả khi
        exception (CUDA OOM, decode error...). Trước đây nếu encode_image() raise,
        tensor `x` còn alloc trên GPU → batch tiếp theo / engine retry vẫn OOM.
        """
        total = len(clips)
        try:
            with torch.no_grad():
                for i in range(0, total, batch_size):
                    batch = clips[i:i+batch_size]

                    # Load and preprocess batch
                    images = []
                    for c in batch:
                        try:
                            img = Image.open(c["frame"]).convert("RGB")
                            images.append(self.preprocess(img))
                        except Exception as e:
                            warn("clip_load_failed", frame=c.get("frame"), error=str(e))
                            # Use black image as fallback
                            images.append(torch.zeros(3, 224, 224))

                    if not images:
                        continue

                    x = None
                    feats = None
                    try:
                        # Batch encode on GPU
                        x = torch.stack(images).to(self.device)
                        feats = self.model.encode_image(x)
                        feats = feats / feats.norm(dim=-1, keepdim=True)

                        # Assign to clips
                        for j, c in enumerate(batch):
                            c["feat"] = feats[j].cpu()
                    finally:
                        # [Phase 8] Always free GPU memory, ngay cả khi encode raise
                        try:
                            del x, feats, images
                        except Exception:
                            pass
                        if self.device.startswith("cuda"):
                            try:
                                torch.cuda.empty_cache()
                            except Exception:
                                pass

                    # Progress logging every 10 batches
                    if (i // batch_size) % 10 == 0 or i + batch_size >= total:
                        info("clip_embed_progress",
                             processed=min(i + batch_size, total),
                             total=total,
                             batch_size=batch_size,
                             device=self.device)
        finally:
            # [Phase 8] Cuối cùng dọn lần nữa để ngăn leak khi raise giữa loop
            if self.device.startswith("cuda"):
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass

        info("clip_embed_done",
             clips=total,
             batch_size=batch_size,
             device=self.device)

    def embed_texts(self, segments: list[dict], batch_size: int = 64):
        """
        Embed text segments with GPU batch processing.

        Args:
            segments: List of segment dicts with "text" field
            batch_size: Batch size for GPU (64 optimal for text)

        [Phase 8] Cleanup CUDA cache on exception path (giống embed_clips).
        """
        total = len(segments)
        texts = [s.get("text", "") for s in segments]

        try:
            with torch.no_grad():
                all_feats = []

                for i in range(0, total, batch_size):
                    batch_texts = texts[i:i+batch_size]

                    toks = None
                    feats = None
                    try:
                        # Tokenize and encode batch on GPU
                        toks = self.tokenizer(batch_texts).to(self.device)
                        feats = self.model.encode_text(toks)
                        feats = feats / feats.norm(dim=-1, keepdim=True)
                        all_feats.append(feats.cpu())
                    finally:
                        try:
                            del toks, feats
                        except Exception:
                            pass
                        if self.device.startswith("cuda"):
                            try:
                                torch.cuda.empty_cache()
                            except Exception:
                                pass

                    # Progress logging
                    if (i // batch_size) % 10 == 0 or i + batch_size >= total:
                        info("text_embed_progress",
                             processed=min(i + batch_size, total),
                             total=total,
                             batch_size=batch_size,
                             device=self.device)

                # Concatenate all batches
                all_feats = torch.cat(all_feats, dim=0)

            # Attach per segment
            for i, s in enumerate(segments):
                s["feat"] = all_feats[i]
        finally:
            if self.device.startswith("cuda"):
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass

        info("text_embed_done",
             segments=total,
             batch_size=batch_size,
             device=self.device)
