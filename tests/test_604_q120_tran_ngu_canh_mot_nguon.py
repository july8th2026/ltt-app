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


def _so_q_cao_nhat(van: str) -> int:
    """Số hiệu quyết định LỚN NHẤT đang có trong tài liệu."""
    so = [int(m) for m in re.findall(r"^### Q(\d+) —", van, flags=re.M)]
    assert so, "khong tim thay muc `### Q<n> —` nao"
    return max(so)


def test_q120_ton_tai_va_q116_da_thay():
    van = QD.read_text(encoding="utf-8")
    assert "### Q120 —" in van
    dau_q116 = van.index("### Q116 —")
    dong_q116 = van[dau_q116:van.index("\n", dau_q116)]
    assert "ĐÃ THAY" in dong_q116 and "Q120" in dong_q116

    # 🔴 HEADER MỤC 1 PHẢI ĐẨY SỐ THEO QUYẾT ĐỊNH MỚI NHẤT — và chốt bằng
    #    **số cao nhất đang có**, không bằng hằng `"đến Q120"` gõ tay.
    #
    # ⛔ Bản cũ viết `assert "đến Q120" in …`. Nó đỏ ngày 2026-09-10 khi Q121
    #    được thêm — tức nó bắt được **việc đúng đang xảy ra**, không bắt được
    #    một hồi quy. Và cách "sửa" hiển nhiên (đổi thành `"đến Q121"`) chỉ dời
    #    quả bom sang Q122.
    #
    # ⭐ Đây là hạng lỗi đã có tên trong dự án: *chốt TẬP HỢP, đừng chốt SỐ
    #    LƯỢNG*. Mệnh đề thật là "header nói đúng mốc trên", và nó bất biến với
    #    việc có bao nhiêu quyết định.
    cao_nhat = _so_q_cao_nhat(van)
    header = van[:van.index("### Q1")]
    assert f"đến Q{cao_nhat}" in header, (
        f"header muc 1 con dung o mot moc cu: tai lieu da co Q{cao_nhat}")


def test_khong_con_quy_tac_hien_hanh_nao_noi_cap_65000():
    """Nhắc lịch sử (nhật ký, changelog, Q116 gốc) thì được; luật hiện hành thì không."""
    van = QD.read_text(encoding="utf-8")
    # ⛔ CẮT TỚI MỤC `### Q` KẾ TIẾP, không cắt tới hết mục 1. Từ 2026-09-10 có
    #    Q121 nằm giữa Q120 và `## 2.`, nên lát cắt cũ **nuốt luôn quyết định
    #    sau** — và một lát cắt rộng ra làm phép kiểm DỄ xanh hơn, tức nó âm
    #    thầm thôi đo Q120. Cùng hạng lỗi "phạm vi phép đo rộng hơn lời tuyên bố".
    dau = van.index("### Q120 —")
    sau = re.search(r"^(### Q\d+ —|## \d+\. )", van[dau + 10:], flags=re.M)
    q120 = van[dau:dau + 10 + sau.start()] if sau else van[dau:]
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
