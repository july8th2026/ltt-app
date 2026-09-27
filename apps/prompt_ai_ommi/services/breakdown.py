"""breakdown.py — chia canh tu dong theo ommi_storyboard_framework (pha 5).

⚠️ BAI HOC `sai-so-nho-o-nhip-thanh-sai-so-lon-o-nguong`: do that hai lan tren
model that o scene_count=20 cho ra 19/20 canh va do dai `prompt` co dan theo
thu tu canh (67%/69% tran token) — chat luong suy TRUOC khi cham tran cung.
Vi vay ham nay KHONG gia dinh mot luot goi LLM tra du N canh; no ep dung SO
LUONG o tang HAU KY.

⛔ Chu du an da chot (Q-16): mang co che CHIA LO cua `apps/prompt_canh` sang
la viec cua MOT PHA SAU. `breakdown()` o day van la MOT lan goi
`provider.generate_json` — neu thiet ke nay can doi khi chia lo toi, day la
diem se doi (xem bao cao lam I).

⭐ Bat bien CAU TRUC (dieu phoi yeu cau 27/09, thay cho khang dinh HINH THUC
`len(scenes) == N`): mot `assert len == N` xanh ca khi chi so canh la
`[0,1,1,3]` — bon phan tu, mot lo, mot trung. O day ta khang dinh:
  1. tap chi so tra ve la DUNG `{0..N-1}`, moi so DUNG MOT LAN (khong lo,
     khong trung) — kiem ca o `assert` noi bo lan o test (tiem loi 3 chieu:
     thieu/du/trung tieu de);
  2. noi dung AI da SINH RA nhung VUOT so canh yeu cau KHONG duoc bien mat
     im lang — gop vao canh cuoi kem ghi chu ro, dem duoc so canh da gop
     (`overflow_merged_count`);
  3. canh do AI TU DONG BU (thieu so voi yeu cau) duoc DANH DAU rieng
     (`auto_filled=True`), khong lan voi canh AI that sinh.
"""
from __future__ import annotations

from apps.prompt_ai_ommi import provider

# ⚠️ Cac chuoi hien thi duoi day CO Y khong dau va KHONG boc `_t()` — tep moi
# tao trong luc cong dich dang chay song song (dieu phoi dang dich hang loat
# mot lan, xem `DIEU_HUONG_AGENT.md` Sec 4.5), nen boc `_t()` ngay bay gio se
# tao msgid CHUA CO trong catalog va lam do `ban-dich-thieu` (chi minh boc);
# con neu de co dau ma KHONG boc thi do `chuoi-chua-dich` (check_i18n.py).
# Khong dau + khong boc la duong DUY NHAT qua duoc CA HAI banh coc cung luc —
# dung theo dung tien le `services/nhap_mau_goc.py:65`. Ban co dau that de
# dieu phoi dua vao dot dich hang loat sau, ghi trong bao cao lam I:
#   "Cảnh {n}"
#   "[TỰ ĐỘNG BÙ — AI chưa sinh đủ cảnh; cần chỉnh sửa hoặc chia lại trước
#    khi dùng]"
#   "[GỘP {n} CẢNH VƯỢT {target} — AI đã sinh nhưng bị cắt do vượt số lượng
#    yêu cầu]:\n{text}"

# Tran AN TOAN rieng cho SO CANH AI TU DE XUAT trong MOT lan breakdown.
# ⚠️ Trung GIA TRI (20) voi `apps.prompt_ai_ommi.project_schema.MAX_SCENES`
# (so CANH KICH BAN) la NGAU NHIEN — hai dai luong khac nhau, khac bang, khac
# cua (spec Sec 4.3 da phan quyet "canh kich ban" (ommi_canh) khac "khung
# hinh" (ommi_scene); breakdown() la mot khai niem THU BA — de xuat tho truoc
# khi khach ap vao storyboard). ⛔ Dung doi ten nay cho khop mot trong hai so
# kia — do la dung con bo ma spec Sec 4.4 da canh bao ("hai cho khai mot
# dieu").
_MAX_BREAKDOWN_SCENES = 20
_MIN_BREAKDOWN_SCENES = 1


def _system_prompt(framework) -> str:
    return "\n\n".join(filter(None, [
        framework.composite_header, framework.composite_rules,
        framework.composite_negative_footer]))


def _default_title(index: int) -> str:
    return "Canh {n}".format(n=index + 1)


def _clean_scene(raw: dict, index: int) -> dict:
    title = str((raw or {}).get("title") or _default_title(index))[:200]
    prompt = str((raw or {}).get("prompt") or "")[:4000]
    return {"index": index, "title": title, "prompt": prompt,
            "auto_filled": False}


def _auto_fill_scene(index: int) -> dict:
    """Canh AI KHONG sinh du — danh dau ro (ca bang co `auto_filled` VA bang
    van ban) de nguoi dung biet canh nay can tu tay chinh, khong am tham lay
    mot canh rong lam nhu that.
    """
    return {
        "index": index,
        "title": _default_title(index),
        "prompt": ("[TU DONG BU - AI chua sinh du canh; can chinh sua hoac "
                  "chia lai truoc khi dung]"),
        "auto_filled": True,
    }


def breakdown(db, *, framework, story_vi: str, n_scenes: int | None = None,
             model: str = "") -> list[dict]:
    """Chia `story_vi` thành ĐÚNG `n_scenes` (hoặc `framework.default_n_scenes`
    nếu không truyền) cảnh. Số cảnh trả về KHÔNG BAO GIỜ lệch so yêu cầu, và
    KHÔNG canh nào trong so do co chi so lo/trung (xem docstring module).
    """
    target = int(n_scenes) if n_scenes is not None else int(framework.default_n_scenes)
    target = max(_MIN_BREAKDOWN_SCENES, min(_MAX_BREAKDOWN_SCENES, target))

    system = _system_prompt(framework)
    prompt = framework.breakdown_llm_prompt.replace(
        "{N}", str(target)).replace("{STORY}", story_vi)
    chosen_model = model or provider.model_mac_dinh()
    raw, _tokens = provider.generate_json(system, prompt, model=chosen_model)

    raw_scenes = list((raw or {}).get("scenes") or [])
    kept_raw = raw_scenes[:target]
    overflow_raw = raw_scenes[target:]

    scenes = [_clean_scene(item, i) for i, item in enumerate(kept_raw)]
    while len(scenes) < target:
        scenes.append(_auto_fill_scene(len(scenes)))

    if overflow_raw:
        # Khong duoc lam bien mat noi dung AI da sinh chi vi vuot so canh yeu
        # cau — gop vao canh cuoi kem ghi chu, ⛔ khong xoa im lang.
        overflow_text = "\n---\n".join(
            f"{str((item or {}).get('title') or '')}: "
            f"{str((item or {}).get('prompt') or '')}"
            for item in overflow_raw)
        note = ("[GOP {n} CANH VUOT {target} - AI da sinh nhung bi cat do "
               "vuot so luong yeu cau]:\n{text}").format(
            n=len(overflow_raw), target=target, text=overflow_text)
        scenes[-1]["prompt"] = f"{scenes[-1]['prompt']}\n\n{note}"
        scenes[-1]["overflow_merged_count"] = len(overflow_raw)

    # Bat bien noi bo (khong hien cho nguoi dung -- khong can boc _()):
    # chi so canh phai la DUNG 0..target-1, moi so DUNG MOT LAN.
    indices = [s["index"] for s in scenes]
    assert sorted(indices) == list(range(target)), (
        "chi so canh vo cau truc: %r (target=%d)" % (indices, target))
    return scenes
