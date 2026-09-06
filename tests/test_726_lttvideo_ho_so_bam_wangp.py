"""Hồ sơ LTT phải bám mặc định của WanGP — và mọi chỗ lệch phải **có tên**.

⭐ Vì sao cần phép kiểm này. Ngày 06/09 hồ sơ mang `1280x720` / `20 bước` trong
   khi WanGP đặt `832x480` / `30 bước`. Cả 53 phép kiểm của `lttvideo` đều xanh.
   Không phép kiểm nào **đo được câu hỏi đang quan trọng nhất** — "ta có đang
   chạy đúng như WanGP không" — nên hồ sơ trôi khỏi WanGP mà cổng vẫn báo PASS.

⛔ Chốt theo **TẬP HỢP CÓ TÊN**, không theo **số lượng**. Một phép kiểm dạng
   "không quá 2 khoá lệch" cho phép đổi khoá này lấy khoá kia mà vẫn xanh.

Dữ liệu đối chiếu là hai tệp cấu hình của chính WanGP tại SHA ghim, lấy từ
volume C-CLOUD và để ở `tests/fixtures/wangp_factory/`. Chúng là **bằng chứng**,
không phải bản chép tay — nên chúng không trôi được như một bảng markdown.
"""
from __future__ import annotations

import json
import pathlib

GOC = pathlib.Path(__file__).parent.parent
KHO = GOC / "tests" / "fixtures" / "wangp_factory"
HO_SO = GOC / "apps" / "lttvideo" / "ho_so_data" / "ltt.video.chuan.v1.json"

MODEL = "t2v_2_2"
I2V = False  # `t2v_2_2` khong phai i2v — quyet dinh hai dong hard-code duoi day

#: Khoá thời-chạy của WanGP, cố ý KHÔNG đưa vào hồ sơ.
#: `seed` nằm đây vì người dùng đổi được nó (`KHOA_NGUOI_DUNG_DOI_DUOC`).
KHOA_CO_Y_BO = frozenset({"client_id", "config", "output_filename", "seed"})

#: Khoá hồ sơ thêm vào, không phải của `_settings.json`.
KHOA_CO_Y_THEM = frozenset({"model_type", "settings_version"})

#: Chỗ hồ sơ ĐƯỢC PHÉP lệch giá trị so với WanGP. Rỗng là đúng: ta chạy y
#: nguyên WanGP. Thêm một khoá vào đây là một QUYẾT ĐỊNH, và nó phải kèm lý do.
LECH_DUOC_DUYET: dict[str, str] = {}


def _factory() -> dict:
    """Dựng lại `wgp.get_factory_settings("t2v_2_2")` — bốn tầng, đúng thứ tự.

    Neo vào mã nguồn tại SHA ghim:
      ① `wgp.py:2568`  models/_settings.json -> primary_settings
      ② `wgp.py:3217`  prompt / resolution / flow_shift ghi de cung
      ③ `wan_handler.py:1253`  sample_solver = "unipc"
      ④ `wgp.py:3313`  model_def["settings"] = moi khoa ngoai "model"
    """
    d = json.loads((KHO / "models_settings.json").read_text(encoding="utf-8"))

    # ② — chép nguyên điều kiện của WanGP, kể cả khi nó trông thừa với một model
    d["resolution"] = "1280x720" if "720" in MODEL else "832x480"
    d["flow_shift"] = 7.0 if "720" not in MODEL and I2V else 5.0
    if not d.get("prompt"):
        d["prompt"] = _PROMPT_MAC_DINH

    # ③
    d["sample_solver"] = "unipc"

    # ④
    dn = json.loads((KHO / "defaults_t2v_2_2.json").read_text(encoding="utf-8"))
    dn.pop("model", None)
    d.update(dn)
    return d


#: `wgp.get_default_prompt(i2v=False)` — nguyên văn.
_PROMPT_MAC_DINH = (
    "A large orange octopus is seen resting on the bottom of the ocean floor, "
    "blending in with the sandy and rocky terrain. Its tentacles are spread out "
    "around its body, and its eyes are closed. The octopus is unaware of a king "
    "crab that is crawling towards it from behind a rock, its claws raised and "
    "ready to attack. The crab is brown and spiny, with long legs and antennae. "
    "The scene is captured from a wide angle, showing the vastness and depth of "
    "the ocean. The water is clear and blue, with rays of sunlight filtering "
    "through. The shot is sharp and crisp, with a high dynamic range. The "
    "octopus and the crab are in focus, while the background is slightly "
    "blurred, creating a depth of field effect."
)


def _ho_so() -> dict:
    return json.loads(HO_SO.read_text(encoding="utf-8"))


def test_khong_lech_gia_tri_nao_ngoai_danh_sach_duoc_duyet():
    """Đây là phép kiểm đáng lẽ phải bắt được `1280x720` / `20 bước`."""
    f, t = _factory(), _ho_so()
    lech = {k: (f[k], t[k]) for k in set(f) & set(t) if f[k] != t[k]}
    la = {k: v for k, v in lech.items() if k not in LECH_DUOC_DUYET}
    assert not la, (
        "hồ sơ lệch WanGP ở khoá chưa được duyệt: "
        + "; ".join(f"{k}: WanGP={a!r} LTT={b!r}" for k, (a, b) in sorted(la.items()))
    )


def test_bo_khoa_nao_la_co_y_chu_khong_phai_bo_sot():
    f, t = _factory(), _ho_so()
    assert set(f) - set(t) == KHOA_CO_Y_BO


def test_them_khoa_nao_la_co_y():
    f, t = _factory(), _ho_so()
    assert set(t) - set(f) == KHOA_CO_Y_THEM


def test_route_lay_do_phan_giai_tu_danh_sach_cua_wangp():
    """Route gửi `resolution` như khoá người-dùng-đổi-được ⇒ nó GHI ĐÈ hồ sơ.

    Chữa hồ sơ mà quên chỗ này thì độ phân giải cũ quay lại qua cửa trước, lặng
    lẽ, trong khi hồ sơ trông vẫn đúng. Nên chốt luôn cả hai đầu.
    """
    from apps.lttvideo.routes import _DO_PHAN_GIAI

    # nhóm `# 480p` của Wan2GP/shared/resolutions.py:DEFAULT_RESOLUTION_CHOICES
    cua_wangp_480p = {"832x624", "624x832", "720x720", "832x480", "480x832"}
    ngoai = set(_DO_PHAN_GIAI.values()) - cua_wangp_480p
    assert not ngoai, f"độ phân giải không có trong nhóm 480p của WanGP: {sorted(ngoai)}"


def test_do_phan_giai_16_9_khop_dung_mac_dinh_cua_wangp():
    from apps.lttvideo.routes import _DO_PHAN_GIAI

    assert _DO_PHAN_GIAI["16:9"] == _factory()["resolution"]


def test_hang_so_gia_bi_danh_dau_la_chua_do_lai():
    """Hằng số giá đo ở profile 4 / 720p / 20 bước — cả ba nay đều đã đổi.

    Cờ này đỏ cho tới khi `E1` đo lại. Một con số sai mà **im lặng** nguy hiểm
    hơn một con số sai mà **ồn ào**.
    """
    from apps.lttvideo import cost

    assert hasattr(cost, "DA_DO_LAI_SAU_KHI_DOI_THAM_SO")
