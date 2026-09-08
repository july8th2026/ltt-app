"""Đếm `AgentWorkflow` / `AgentRun` trên production — chốt `D2`, mở khoá `Q6`.

`D2` là mục **duy nhất** trong `00_TIEN_DO.md §5` được ghi là *"cần người dùng"*:

    "Dem AgentWorkflow/AgentRun trong CSDL production.
     LTT_DATABASE_URL o secrets/ — ACL chan CO Y (W1.5).
     Q6: neu 0 => bo han Plan v1, di tru thanh bai toan RONG."

⭐ Con số này quyết một việc lớn bằng một câu truy vấn: nếu **0**, toàn bộ lớp
   Plan v1 gỡ được mà không cần một dòng mã di trú nào — và `27_29 §27` nói
   thẳng rằng khi ấy "di trú" không còn là một hạng mục.

## ⛔ CHỈ ĐỌC — và đây là chỗ cưỡng chế, không phải chỗ hứa

Công cụ này nối vào **CSDL production đang giữ sổ credit thật**. Nên nó không
"cẩn thận"; nó **không có khả năng** ghi:

    1. moi cau lenh di qua `_chi_doc()` — tu choi bat cu gi khong bat dau
       bang SELECT, va tu choi moi tu khoa ghi du nam o dau trong cau
    2. ket noi mo o `AUTOCOMMIT=False` va KHONG BAO GIO `commit()`
    3. khong import alembic, khong cham `Base.metadata`

⚠️ Vì sao rào 1 quét **cả câu** chứ không chỉ chữ đầu: `SELECT ... ; DROP ...`
   bắt đầu bằng `SELECT`. Một rào chỉ nhìn tiền tố là một rào đọc **thứ đại
   diện** thay vì đọc thứ thật.
"""
from __future__ import annotations

import pathlib
import re
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: Từ khoá ghi. Quét trên **toàn câu**, không chỉ tiền tố.
_CAM = re.compile(
    r"\b(insert|update|delete|drop|truncate|alter|create|grant|revoke|copy|"
    r"vacuum|reindex|call|do)\b", re.I)


def _chi_doc(cau: str) -> str:
    """Trả lại câu nếu nó chắc chắn chỉ đọc. Ngược lại **dừng**."""
    goi = cau.strip().rstrip(";")
    if ";" in goi:
        raise SystemExit(f"⛔ TU CHOI: nhieu cau lenh trong mot chuoi: {cau!r}")
    if not goi.lower().startswith("select"):
        raise SystemExit(f"⛔ TU CHOI: khong bat dau bang SELECT: {cau!r}")
    if _CAM.search(goi):
        raise SystemExit(f"⛔ TU CHOI: co tu khoa ghi trong cau: {cau!r}")
    return goi


def _doc_bi_mat(ten_tep: str) -> str:
    for path in (pathlib.Path(r"C:\LTTPlatform\secrets") / ten_tep,
                 GOC / "secrets" / ten_tep):
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception as loi:                            # noqa: BLE001
            # ⛔ "ACL chan" khac "tep khong co", va cong cu nay ton tai de tra
            #    loi mot cau ve CSDL — nuot loi o day la bit dung cho cau tra
            #    loi hay sai nhat.
            print(f"  (bo qua {path}: {type(loi).__name__})")
            continue
    return ""


def _live_url() -> str:
    for line in _doc_bi_mat("app.env").splitlines():
        if line.strip().startswith("LTT_DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    live = _live_url()
    if not live.startswith(("postgresql", "postgres")):
        print("BO QUA: khong tim thay LTT_DATABASE_URL kieu postgres.")
        return 0

    pw = _doc_bi_mat("postgres-superuser.txt").strip()
    if not pw:
        print("BO QUA: khong doc duoc mat khau superuser.")
        return 0

    ten = live.rsplit("/", 1)[-1].split("?", 1)[0]
    dia_chi = live.partition("://")[2].partition("@")[2].rsplit("/", 1)[0]
    url = f"postgresql+psycopg://postgres:{pw}@{dia_chi}/{ten}"

    import sqlalchemy as sa

    print(f"CSDL: {ten}   (CHI DOC)")
    e = sa.create_engine(url, connect_args={"connect_timeout": 5})
    ra: dict[str, int] = {}
    with e.connect() as c:
        co = {r[0] for r in c.execute(sa.text(_chi_doc(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public'")))}
        for bang in ("agent_workflows", "agent_runs", "agent_workflow_snapshots",
                     "agent_workflow_shares"):
            if bang not in co:
                print(f"  {bang:28s} KHONG CO BANG")
                continue
            n = c.execute(sa.text(_chi_doc(f"SELECT COUNT(*) FROM {bang}"))).scalar()
            ra[bang] = int(n or 0)
            print(f"  {bang:28s} {n}")
        # Doi chung: mot bang CHAC CHAN co du lieu. Neu no cung ra 0 thi con so
        # 0 o tren khong phai phat hien — no la dau hieu ta dang doc nham CSDL.
        for bang in ("users", "jobs", "credit_entries"):
            if bang in co:
                n = c.execute(sa.text(_chi_doc(
                    f"SELECT COUNT(*) FROM {bang}"))).scalar()
                print(f"  [doi chung] {bang:17s} {n}")
    e.dispose()

    tong = sum(ra.values())
    print()
    if not ra:
        print("KET LUAN: khong co bang Agent nao tren production.")
    elif tong == 0:
        print("KET LUAN: TONG = 0 => `Q6` chot duoc: bo han Plan v1, di tru la")
        print("          bai toan RONG (khong can script chuyen doi nao).")
    else:
        print(f"KET LUAN: TONG = {tong} => `Q6` CAN mot script di tru mot lan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
