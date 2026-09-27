"""Vong lap sua kich ban, va luat tien cua no.

LUAT TIEN (chu du an chot 26/09, Q-7): 2 luot dau moi KICH BAN mien phi, luot
3 tro di thu credit. Dem theo KICH BAN -- khong theo user, khong theo ngay.

BO DEM PHAI NAM TRONG CSDL. Bo dem trong phien nghia la khach mo tab moi la
duoc 2 luot mien phi nua, tuc LLM mien phi vo han. Day khong phai lo hong ly
thuyet: no la duong lach re nhat ma bat ky khach nao cung tim ra.

`verdict="rejected"` KHONG hoan credit. Hoan thi khach bam rejected moi lan
cung dat duoc dieu tren.
"""
from __future__ import annotations

from sqlalchemy import func, select, text

from platform_core.i18n import _ as _t
from apps.prompt_ai_ommi.tables import OmmiBrief, OmmiIteration

#: So luot dau mien phi MOI KICH BAN. Doi so nay la doi gia san pham => hoi chu
#: du an truoc, va ghi vao `docs/NHAT_KY.md`.
LUOT_MIEN_PHI = 2

#: Do dai toi thieu cua NOI DUNG BRIEF (ky tu), rieng cho luot iterate.
#: ⛔ KHONG phai tran so CANH kich ban (`project_schema.MAX_SCENES`) va
#: cung KHONG phai tran KHUNG HINH storyboard (`storyboard.MAX_KHUNG_HINH`,
#: 60) -- ba dai luong nay tung dung chung mot con so `20`/`60` roi lech
#: nhau, nen dat ten rieng thay vi go tay `20` tai cho dung.
# ⭐ Hang so nay da doi nha sang `project_schema` (canh `MAX_SCENES`) vi SAU
#    cho trong app khai cung nguong nay — trong do co mot cho o CUA va mot
#    cho o WORKER (bat bien B-6). Giu ten cu o day de cho goi khong doi.
from apps.prompt_ai_ommi.project_schema import TOI_THIEU_KY_TU_BRIEF

_PHAN_QUYET = {"kept", "rejected"}


def con_mien_phi(brief) -> int:
    """So luot mien phi con lai. Khong bao gio am."""
    return max(0, LUOT_MIEN_PHI - int(getattr(brief, "free_iterations_used", 0) or 0))


def bao_gia(db, brief) -> dict:
    """Gia cho luot TIEP THEO. `authoritative` de frontend khong tu tinh lai."""
    from platform_core.registry import credit_for

    free = con_mien_phi(brief) > 0
    gia = 0 if free else credit_for(
        "prompt_ai_ommi.generate",
        {"operation": "iterate", "scene_count": int(brief.target_scenes or 6)})
    return {"credit": gia, "was_free": free, "free_left": con_mien_phi(brief),
            "authoritative": True}


def _khoa_brief(db, brief_id: str) -> None:
    """Khoa TUAN TU moi `mo_luot` cua MOT brief trong transaction hien tai.

    Cung mot bai voi `credit._khoa_so_du_user`: `con_mien_phi` la mot phep DOC
    ROI GHI tren `free_iterations_used`. Khong khoa thi hai request song song
    (hai tab, bam nut hai lan) cung doc duoc `free_iterations_used == 1`, cung
    tinh `free=True`, va ca hai cung duoc mien phi -- lam 2 luot dau THANH 3
    luot mien phi cho MOT brief. `pg_advisory_xact_lock` giu khoa den khi
    commit/rollback nen request thu hai phai xep hang, doc `free_iterations_used`
    SAU khi request dau da ghi va commit.

    Chi ap dung cho PostgreSQL, giong nguyen ban credit.py: SQLite (test/don
    may) tuan tu hoa ghi o muc tep va test chay don luong, khong co race de chan.
    """
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
                   {"k": f"ommi_iterate:{brief_id}"})


def _seq_ke_tiep(db, brief_id: str) -> int:
    lon_nhat = db.execute(
        select(func.max(OmmiIteration.seq))
        .where(OmmiIteration.brief_id == brief_id)).scalar()
    return int(lon_nhat or 0) + 1


def mo_luot(db, brief, feedback: str, prompt_sent: str) -> OmmiIteration:
    """Tao mot luot VA tang bo dem -- trong CUNG mot transaction.

    Hai viec nay khong duoc tach: mot lan crash giua chung de lai hoac mot
    iteration khong tinh luot (khach duoc them mot luot free), hoac mot luot
    da tinh ma khong co iteration (khach mat mot luot free khong co gi doi
    lai). Caller tu `commit`.

    LUA CHON CO Y (job that bai o worker): bo dem `free_iterations_used` tang
    tai thoi diem NOP (ham nay), khong phai tai thoi diem job THANH CONG. Job
    that bai sau do KHONG duoc hoan lai luot free -- khac voi CREDIT (duong
    tra tien), no duoc `job_runner.py` tu dong hoan qua `credit.hoan()` khi
    job that bai (G-9, ngoai pham vi tep nay). Ly do: cong AI (dung system +
    prompt, goi LLM) da ton chi phi thuc du ket qua co dùng duoc hay khong, va
    hoan lai luot free theo loi worker mo lai dung lo hong B-6 theo huong
    khac -- khach co the co y gui input lam worker tu choi de "cay lai" luot
    free vo han. Neu san pham muon doi lai (hoan luot free khi job that bai vi
    LOI HE THONG, khong phai loi INPUT cua khach), day la cho phai sua, va can
    phan biet ro hai loai loi o worker truoc khi lam.
    """
    _khoa_brief(db, brief.id)
    # Sau khi co khoa: doc lai gia tri MOI NHAT bang mot SELECT tho, khong
    # dung `db.refresh()` -- no VUT thay doi CHUA COMMIT cua chinh phien nay
    # (da do that: hai `mo_luot` lien tiep trong CUNG transaction, `refresh()`
    # giua chung lam mat lan tang dau). `db.execute(select(...))` tu autoflush
    # truoc khi doc, nen thay duoc CA thay doi chua commit cua chinh minh LAN
    # thay doi da commit cua mot phien khac vua xep hang truoc no qua khoa tren.
    moi_nhat = db.execute(
        select(OmmiBrief.free_iterations_used).where(OmmiBrief.id == brief.id)
    ).scalar()
    if moi_nhat is not None:
        brief.free_iterations_used = int(moi_nhat)
    free = con_mien_phi(brief) > 0
    gia = bao_gia(db, brief)
    lt = OmmiIteration(
        owner_id=brief.owner_id,
        brief_id=brief.id, seq=_seq_ke_tiep(db, brief.id),
        feedback=str(feedback or "")[:4000],
        prompt_sent=str(prompt_sent or "")[:60000],
        credit_charged=0 if free else int(gia["credit"]), was_free=free)
    db.add(lt)
    if free:
        brief.free_iterations_used = int(brief.free_iterations_used or 0) + 1
    return lt


def dat_phan_quyet(db, iteration, verdict: str):
    """`kept` | `rejected`. KHONG hoan credit trong ca hai ca."""
    v = str(verdict or "").strip().lower()
    if v not in _PHAN_QUYET:
        raise ValueError(_t('Phán quyết không hợp lệ.'))
    iteration.verdict = v
    return iteration


def chay_iterate(params: dict, ctx=None) -> dict:
    """Than job cho `operation="iterate"`. Goi tu `jobs.handle` (P-4: nhanh
    dispatch trong `jobs.py` la cua lan M -- xem bao cao cuoi lan D).

    PHAI nem exception khi loi -- nen tang dua vao exception de hoan credit
    (G-9). Tra ve em ru la "thanh cong" gia va mat tien hoan cua khach.
    """
    from apps.prompt_ai_ommi import provider
    from apps.prompt_ai_ommi.services.composer import director_prompt

    feedback = str(params.get("feedback") or "").strip()
    if not feedback:
        raise ValueError(_t('Cần nội dung góp ý để sửa kịch bản.'))
    story = str(params.get("story") or "").strip()
    if len(story) < TOI_THIEU_KY_TU_BRIEF:
        raise ValueError(
            _t('Nội dung brief tối thiểu {n} ký tự.').format(n=TOI_THIEU_KY_TU_BRIEF))
    if ctx is not None:
        ctx.progress(15, _t('đang ghép góp ý vào brief'))
    # Gop y di vao brief thay vi mot he thong prompt rieng: mot duong, mot cho sua.
    params = dict(params)
    params["story"] = f"{story}\n\n[GOP Y CAN SUA]\n{feedback}"
    system, prompt = director_prompt(params)
    if ctx is not None:
        ctx.progress(40, _t('AI Director đang sửa kịch bản'))
    model = str(params.get("model") or provider.model_mac_dinh())
    raw, tokens = provider.generate_json(system, prompt, model=model)
    if ctx is not None:
        ctx.progress(90, _t('đang chuẩn hóa kết quả'))
    from apps.prompt_ai_ommi.jobs import _normalize_result
    from apps.prompt_ai_ommi.manifest import _cost
    ket_qua = {
        "operation": "iterate",
        "prompt_package": _normalize_result(raw, params),
        "master_prompt": prompt[:20000], "tokens_used": tokens, "model": model,
        "credit_cost": _cost(params),
    }
    if ctx is not None:
        ctx.progress(100, _t('hoàn tất'))
    return ket_qua
