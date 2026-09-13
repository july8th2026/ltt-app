"""
engine/error_context.py

Module theo dõi lỗi chi tiết theo từng file và stage.
Giúp debug dễ dàng hơn khi biết chính xác file nào gây lỗi ở bước nào.
"""

from __future__ import annotations

import os
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any
import json


def _shorten_detail(detail: str, max_len: int = 72) -> str:
    """Rút gọn đường dẫn tuyệt đối dài trong chuỗi detail của PROCESSING SUMMARY.
    Giữ nguyên phần text prefix, chỉ rút gọn phần path."""
    if len(detail) <= max_len:
        return detail
    # Tìm absolute path nhúng trong chuỗi (Windows: X:\ hoặc Unix: /)
    path_match = re.search(r'([A-Za-z]:[/\\]|(?<!\w)/)[^\s]+', detail)
    if path_match:
        path = path_match.group(0)
        norm = path.replace("\\", "/")
        parts = norm.rstrip("/").split("/")
        if len(parts) >= 3:
            short_path = ".../" + "/".join(parts[-2:])
            detail = detail[:path_match.start()] + short_path
    if len(detail) > max_len:
        detail = detail[:max_len - 3] + "..."
    return detail


class FileErrorContext:
    """
    Context manager để track lỗi khi xử lý file.
    Tự động log file name, stage, và error detail.
    """
    
    def __init__(self, filepath: str | Path, stage: str, job_id: str = ""):
        self.filepath = Path(filepath)
        self.stage = stage
        self.job_id = job_id
        self.start_time = None
        self.error_occurred = False
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error_occurred = True
            self._log_error(exc_type, exc_val, exc_tb)
            # Không suppress exception, để nó propagate lên
        return False
    
    def _log_error(self, exc_type, exc_val, exc_tb):
        """Log chi tiết lỗi khi xử lý file"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        error_detail = {
            "timestamp": datetime.now().isoformat(),
            "job_id": self.job_id,
            "stage": self.stage,
            "file": {
                "path": str(self.filepath),
                "name": self.filepath.name,
                "exists": self.filepath.exists(),
                "size_bytes": self.filepath.stat().st_size if self.filepath.exists() else 0,
                "parent": str(self.filepath.parent),
            },
            "error": {
                "type": exc_type.__name__ if exc_type else "Unknown",
                "message": str(exc_val),
                "traceback": "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            },
            "elapsed_seconds": round(elapsed, 2)
        }
        
        # Print to stderr with clear formatting
        print("\n" + "=" * 80, flush=True)
        print(f"❌ FILE ERROR DETECTED", flush=True)
        print("=" * 80, flush=True)
        print(f"Stage:    {self.stage}", flush=True)
        print(f"File:     {self.filepath.name}", flush=True)
        print(f"Path:     {self.filepath}", flush=True)
        print(f"Exists:   {error_detail['file']['exists']}", flush=True)
        if error_detail['file']['exists']:
            print(f"Size:     {error_detail['file']['size_bytes']:,} bytes", flush=True)
        print(f"Error:    {error_detail['error']['type']}: {error_detail['error']['message']}", flush=True)
        print(f"Elapsed:  {elapsed:.2f}s", flush=True)
        print("=" * 80 + "\n", flush=True)
        
        # Also log as JSON for machine parsing
        print(f"ERROR_DETAIL_JSON: {json.dumps(error_detail, ensure_ascii=False)}", flush=True)


class StageValidator:
    """
    Validator để kiểm tra file inputs trước mỗi stage.
    Fail fast nếu thiếu file quan trọng.
    """
    
    def __init__(self, job_id: str = ""):
        self.job_id = job_id
        self.validations: List[Dict] = []
    
    def validate_file_exists(self, filepath: str | Path, stage: str, required: bool = True) -> bool:
        """
        Kiểm tra file tồn tại.
        
        Args:
            filepath: Đường dẫn file
            stage: Stage đang thực hiện
            required: True = bắt buộc phải có, False = optional
        
        Returns:
            True nếu file tồn tại hoặc không bắt buộc
        
        Raises:
            FileNotFoundError nếu file bắt buộc không tồn tại
        """
        filepath = Path(filepath)
        exists = filepath.exists()
        
        validation = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "file": str(filepath),
            "filename": filepath.name,
            "required": required,
            "exists": exists,
            "passed": exists or not required
        }
        self.validations.append(validation)
        
        if required and not exists:
            error_msg = (
                f"VALIDATION FAILED [{stage}]\n"
                f"  Missing required file: {filepath.name}\n"
                f"  Full path: {filepath}\n"
                f"  Parent dir exists: {filepath.parent.exists()}"
            )
            print(f"\n{'=' * 80}", flush=True)
            print(f"❌ {error_msg}", flush=True)
            print(f"{'=' * 80}\n", flush=True)
            raise FileNotFoundError(error_msg)
        
        if not exists and not required:
            print(f"⚠️  [{stage}] Optional file not found: {filepath.name}", flush=True)
        
        return exists
    
    def validate_dir_has_files(
        self, 
        dirpath: str | Path, 
        stage: str,
        extensions: List[str] | None = None,
        min_files: int = 1
    ) -> List[Path]:
        """
        Kiểm tra thư mục có đủ files với extensions cần thiết.
        
        Args:
            dirpath: Đường dẫn thư mục
            stage: Stage đang thực hiện
            extensions: List các extension cần tìm (e.g., ['.mp4', '.avi'])
            min_files: Số file tối thiểu cần có
        
        Returns:
            List các file tìm được
        
        Raises:
            FileNotFoundError nếu không đủ files
        """
        dirpath = Path(dirpath)
        
        if not dirpath.exists():
            error_msg = (
                f"VALIDATION FAILED [{stage}]\n"
                f"  Directory not found: {dirpath.name}\n"
                f"  Full path: {dirpath}"
            )
            print(f"\n{'=' * 80}", flush=True)
            print(f"❌ {error_msg}", flush=True)
            print(f"{'=' * 80}\n", flush=True)
            raise FileNotFoundError(error_msg)
        
        # Tìm files
        found_files: List[Path] = []
        if extensions:
            for ext in extensions:
                # Case-insensitive search
                found_files.extend(dirpath.glob(f"*{ext}"))
                found_files.extend(dirpath.glob(f"*{ext.upper()}"))
        else:
            # Tất cả files
            found_files = [f for f in dirpath.iterdir() if f.is_file()]
        
        # Remove duplicates
        found_files = list(set(found_files))
        
        validation = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "dir": str(dirpath),
            "extensions": extensions,
            "min_files": min_files,
            "found_files": len(found_files),
            "passed": len(found_files) >= min_files
        }
        self.validations.append(validation)
        
        if len(found_files) < min_files:
            ext_str = f" with extensions {extensions}" if extensions else ""
            error_msg = (
                f"VALIDATION FAILED [{stage}]\n"
                f"  Directory: {dirpath.name}\n"
                f"  Expected: At least {min_files} files{ext_str}\n"
                f"  Found: {len(found_files)} files\n"
                f"  Full path: {dirpath}"
            )
            print(f"\n{'=' * 80}", flush=True)
            print(f"❌ {error_msg}", flush=True)
            if found_files:
                print(f"\n  Files found:", flush=True)
                for f in found_files[:5]:  # Show first 5
                    print(f"    - {f.name}", flush=True)
                if len(found_files) > 5:
                    print(f"    ... and {len(found_files) - 5} more", flush=True)
            print(f"{'=' * 80}\n", flush=True)
            raise FileNotFoundError(error_msg)
        
        print(f"✓ [{stage}] Found {len(found_files)} files in {dirpath.name}", flush=True)
        return found_files
    
    def get_summary(self) -> str:
        """Tạo summary của tất cả validations"""
        if not self.validations:
            return "No validations performed"
        
        total = len(self.validations)
        passed = sum(1 for v in self.validations if v["passed"])
        failed = total - passed
        
        lines = [
            f"\nVALIDATION SUMMARY:",
            f"  Total checks: {total}",
            f"  Passed: {passed}",
            f"  Failed: {failed}"
        ]
        
        if failed > 0:
            lines.append("\n  Failed validations:")
            for v in self.validations:
                if not v["passed"]:
                    lines.append(f"    [{v['stage']}] {v.get('file') or v.get('dir')}")
        
        return "\n".join(lines)



#: Hook tuỳ chọn cho tầng App: `(stage, detail) -> None`, gọi ở đầu mỗi giai đoạn.
#: `apps/video_assembly/services/dung_video.py` đặt nó rồi gỡ trong `finally`.
#: `None` = hành vi y hệt bản gốc.
MOC_NGOAI: "Optional[Callable[[str, str], None]]" = None


class ProcessingTracker:
    """
    Tracker để theo dõi progress qua các stages.
    Giúp biết job đang ở stage nào khi timeout/error.
    """
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.stages: List[Dict] = []
        self.current_stage: Optional[str] = None
        self.start_time = datetime.now()
    
    def start_stage(self, stage: str, detail: str = ""):
        """Bắt đầu một stage mới.

        ⛔ SAI LECH CO CHU DICH so voi ban goc — hai dong `MOC_NGOAI` duoi day.

        🔴 Vi sao. `ctx.progress()` cua nen tang **tu no** kiem `JOB_CANCELLED`
           roi nem `JobCancelled` (`job_runner.py:112-116`) — tuc huy hop tac di
           NHO tren callback tien do. App nao goi tien do thua thi huy nhanh;
           thua thi huy cham.

           Do: `video_assembly` chi co **3** moc thang tren `est_duration_s=900`
           => ~300 giay moi moc. Mot lenh huy phai cho toi 5 phut, va trong 5
           phut do job van giu lease **8 GB VRAM**. Runner nay co **14** loi goi
           `start_stage`; moc vao day thi con ~64 giay.

        ⚠️ Hook la bien MO-DUN, khong phai tham so — nen no khong an toan neu hai
           job cua CUNG mot App chay song song trong CUNG mot tien trinh. Hom nay
           dieu do khong xay ra (worker chay mot job mot luc, va App khai
           `admission_slots=1`), nhung neu mot ngay nao do doi thi cho nay phai
           doi theo: chuyen hook thanh tham so cua `__init__`.
        """
        if MOC_NGOAI is not None:
            try:
                MOC_NGOAI(stage, detail)
            except Exception:
                # ⛔ NEM LAI. Ngoai le o day gan nhu chac chan la `JobCancelled`
                #    — dung thu ta muon truyen len. Nuot no la bien mot lenh huy
                #    thanh mot job chay tiep tren card.
                raise
        self.current_stage = stage
        stage_info = {
            "stage": stage,
            "detail": detail,
            "start_time": datetime.now(),
            "end_time": None,
            "elapsed_seconds": None,
            "status": "running"
        }
        self.stages.append(stage_info)
        
        print(f"\n{'─' * 80}", flush=True)
        print(f"▶️  STAGE: {stage}", flush=True)
        if detail:
            print(f"   {detail}", flush=True)
        print(f"{'─' * 80}\n", flush=True)
    
    def complete_stage(self, stage: str):
        """Đánh dấu stage hoàn thành"""
        for s in self.stages:
            if s["stage"] == stage and s["status"] == "running":
                s["end_time"] = datetime.now()
                s["elapsed_seconds"] = (s["end_time"] - s["start_time"]).total_seconds()
                s["status"] = "completed"
                
                print(f"✓ COMPLETED: {stage} ({s['elapsed_seconds']:.1f}s)", flush=True)
                break
    
    def fail_stage(self, stage: str, error: str):
        """Đánh dấu stage thất bại"""
        for s in self.stages:
            if s["stage"] == stage and s["status"] == "running":
                s["end_time"] = datetime.now()
                s["elapsed_seconds"] = (s["end_time"] - s["start_time"]).total_seconds()
                s["status"] = "failed"
                s["error"] = error
                
                print(f"✗ FAILED: {stage} ({s['elapsed_seconds']:.1f}s)", flush=True)
                print(f"  Error: {error}", flush=True)
                break
    
    def get_progress_summary(self) -> str:
        """Tạo summary của tiến độ"""
        total_elapsed = (datetime.now() - self.start_time).total_seconds()
        
        lines = [
            f"\nPROCESSING SUMMARY (Job {self.job_id}):",
            f"  Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)",
            f"  Stages completed: {sum(1 for s in self.stages if s['status'] == 'completed')}/{len(self.stages)}",
            ""
        ]
        
        for i, s in enumerate(self.stages, 1):
            status_icon = {
                "completed": "✓",
                "failed": "✗",
                "running": "⏳"
            }.get(s["status"], "?")
            
            elapsed = s.get("elapsed_seconds", 0) or 0
            stage_line = f"  {i}. {status_icon} {s['stage']}: {elapsed:.1f}s"
            
            if s.get("detail"):
                stage_line += f" - {_shorten_detail(s['detail'])}"
            
            lines.append(stage_line)
            
            if s["status"] == "failed" and s.get("error"):
                lines.append(f"      Error: {s['error']}")
        
        return "\n".join(lines)


# Helper functions for easy usage

def validate_input_structure(input_dir: Path, job_id: str = "") -> StageValidator:
    """
    Validate cấu trúc thư mục đầu vào chuẩn:
    - input_dir/VIDEO/ (phải có ít nhất 1 video)
    - input_dir/VOICE/ (phải có ít nhất 1 audio)
    - input_dir/transcript.json (optional)
    
    Returns:
        StageValidator instance với kết quả validation
    """
    validator = StageValidator(job_id)
    
    print(f"\n{'=' * 80}", flush=True)
    print("🔍 VALIDATING INPUT STRUCTURE", flush=True)
    print(f"{'=' * 80}", flush=True)
    print(f"Input dir: {input_dir}", flush=True)
    
    # Check VIDEO folder
    video_dir = input_dir / "VIDEO"
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
    try:
        video_files = validator.validate_dir_has_files(
            video_dir,
            stage="INPUT_VALIDATION",
            extensions=video_extensions,
            min_files=1
        )
        print(f"  ✓ VIDEO: {len(video_files)} files", flush=True)
    except FileNotFoundError:
        print(f"  ✗ VIDEO: Directory missing or empty", flush=True)
        raise
    
    # Check VOICE folder
    voice_dir = input_dir / "VOICE"
    audio_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']
    try:
        voice_files = validator.validate_dir_has_files(
            voice_dir,
            stage="INPUT_VALIDATION",
            extensions=audio_extensions,
            min_files=1
        )
        print(f"  ✓ VOICE: {len(voice_files)} files", flush=True)
    except FileNotFoundError:
        print(f"  ✗ VOICE: Directory missing or empty", flush=True)
        raise
    
    # Check transcript.json (optional)
    transcript_file = input_dir / "transcript.json"
    has_transcript = validator.validate_file_exists(
        transcript_file,
        stage="INPUT_VALIDATION",
        required=False
    )
    if has_transcript:
        print(f"  ✓ TRANSCRIPT: Found", flush=True)
    else:
        print(f"  ⚠️  TRANSCRIPT: Not found (will use Whisper)", flush=True)
    
    print(f"{'=' * 80}\n", flush=True)
    
    return validator


# Example usage in docstring
"""
USAGE EXAMPLE:

# 1. Validate inputs at start
validator = validate_input_structure(Path(input_dir), job_id="job_123")

# 2. Process files with error context
for video_file in video_files:
    with FileErrorContext(video_file, "VIDEO_ENCODE", job_id="job_123"):
        process_video(video_file)  # If error, auto-logged with file details

# 3. Track progress through stages
tracker = ProcessingTracker("job_123")
tracker.start_stage("WHISPER", "Transcribing audio files")
try:
    do_whisper()
    tracker.complete_stage("WHISPER")
except Exception as e:
    tracker.fail_stage("WHISPER", str(e))
    raise

# 4. At end, print summary
print(tracker.get_progress_summary())
print(validator.get_summary())
"""