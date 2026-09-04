"""
test_604 — Q120 (H43 Phase 03): trần đầu vào công bố là số DẪN XUẤT, một nguồn.

Chốt ba điều, vì mâu thuẫn Q116↔mã đã sống hai tuần mà không phép kiểm nào thấy:

  1. `QUYET_DINH_NEN_TANG.md` có Q120 và Q116 được đánh dấu ĐÃ THAY (giao thức §6).
  2. Không tài liệu ĐANG HIỆU LỰC nào (CLAUDE/AGENTS/QUYET_DINH mục Q120,
     `docs/CHATLTT/`) còn nói "cap 65000" như quy tắc hiện hành.
  3. Con số client nhìn thấy ở catalog/executor đúng bằng `ngan_sach.CONG_BO_CHO_CLIENT`
     (đã có `test_334`; ở đây chốt thêm đường CLIENT NỘI BỘ: `danh_muc` chiếu đúng số đó).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QD = ROOT / "docs" / "QUYET_DINH_NEN_TANG.md"


def test_q120_ton_tai_va_q116_da_thay():
    van = QD.read_text(encoding="utf-8")
    assert "### Q120 —" in van
    dau_q116 = van.index("### Q116 —")
    dong_q116 = van[dau_q116:van.index("\n", dau_q116)]
    assert "ĐÃ THAY" in dong_q116 and "Q120" in dong_q116
    assert "đến Q120" in van[:van.index("### Q1")]      # header mục 1 đã đẩy số


def test_khong_con_quy_tac_hien_hanh_nao_noi_cap_65000():
    """Nhắc lịch sử (nhật ký, changelog, Q116 gốc) thì được; luật hiện hành thì không."""
    van = QD.read_text(encoding="utf-8")
    q120 = van[van.index("### Q120 —"):van.index("## 2. Ràng buộc bất biến")]
    # Q120 phải trỏ về tên HẰNG trong mã, không gõ lại con số làm luật.
    assert "CONG_BO_CHO_CLIENT" in q120 and "TOKEN_VAO_TRAN" in q120
    assert "ngan_sach.py" in q120
    for ten in ("CLAUDE.md", "AGENTS.md"):
        assert not re.search(r"cap\s*`?65[.,]?000", (ROOT / ten).read_text(encoding="utf-8"))
    for tep in (ROOT / "docs" / "CHATLTT").rglob("*.md"):
        for i, dong in enumerate(tep.read_text(encoding="utf-8").splitlines(), 1):
            if "65.000" in dong or "65000" in dong:
                assert "Q116" in dong or "Q120" in dong or "đã thay" in dong.lower(), \
                    f"{tep.name}:{i} nhắc 65K mà không nói nó là lịch sử"


def test_danh_muc_chieu_dung_tran_cong_bo_cua_ngan_sach():
    from apps.ltt_llm import ngan_sach
    from platform_core.runtime_noi_bo.danh_muc import danh_muc

    ds = danh_muc(None, user_id="u", cho_phep={"text.chat"})
    assert [n.ten for n in ds] == ["text.chat"]
    n = ds[0]
    assert n.models["ltt_llm"]["constraints"]["context_window"] == ngan_sach.CONG_BO_CHO_CLIENT
    assert n.models["ltt_llm"]["constraints"]["max_output_tokens"] == ngan_sach.TOKEN_RA_TRAN
    # Không alias nào mang id nội bộ, và số vision nhỏ hơn số text (F-02).
    assert all("id" not in m for m in n.models.values())
    assert (n.models["ltt_llm_vision"]["constraints"]["context_window"]
            < n.models["ltt_llm"]["constraints"]["context_window"])
