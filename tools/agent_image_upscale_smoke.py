"""Real GPU smoke for Agent image.upscale using isolated temporary storage."""
from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.upscalevideo.jobs import handle
from platform_core.storage import LocalStorage, set_storage


class Context:
    job_id = "image-upscale-smoke"
    def progress(self, percent, message):
        print(f"{percent:3d}%")
    def is_cancelled(self):
        return False


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tmp" / "plenx-workflow-empty.png"
    if not source.is_file():
        raise SystemExit(f"Missing source image: {source}")
    with tempfile.TemporaryDirectory(prefix="ltt_agent_upscale_smoke_") as directory:
        storage = LocalStorage(directory); set_storage(storage)
        with Image.open(source) as image:
            image = image.convert("RGB"); image.thumbnail((64, 64))
            payload = io.BytesIO(); image.save(payload, "PNG"); payload.seek(0)
            in_size = image.size
        input_key = "agent-assets/smoke-user/input.png"
        storage.put(input_key, payload, "image/png")
        result = handle({"owner_id": "smoke-user", "image_key": input_key,
                         "preset": "fast"}, Context())
        with storage.open(result["image_key"]) as stream, Image.open(stream) as output:
            expected = (in_size[0] * 4, in_size[1] * 4)
            if output.size != expected:
                raise SystemExit(f"Unexpected output size {output.size}; expected {expected}")
        print(f"PASS image.upscale {in_size} -> {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
