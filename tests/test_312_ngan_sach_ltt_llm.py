"""Ngân sách `ltt_llm`: **một nguồn chân lý**, và không nơi nào được lệch nó.

🔴 VÌ SAO BỘ KIỂM NÀY TỒN TẠI

Ngày 30/08 một triệu chứng duy nhất — *"trả lời dài thì im lặng"* — bắt truy qua
bốn tầng tham số ở bốn nơi. Thủ phạm: cửa stream mượn ngân sách 1.024 của cửa
đồng bộ. Cùng buổi còn phát hiện `LTT_LLM_MAX_INPUT_TOKENS` tồn tại ở **ba nguồn
bất đồng** (mặc định trong mã 90.000 · registry dịch vụ 90.000 · tiến trình đang
chạy 65.000) mà **không phép kiểm nào phát hiện**.

⭐ Nên bộ kiểm này không kiểm "mã có chạy không" — nó kiểm **các con số có còn
   đồng ý với nhau không**. Đó là thứ duy nhất chặn được lớp lỗi đó tái phát.

⚠️ Nhóm `TestDoiChieuMayB` gọi máy B thật nên **tự bỏ qua** khi không có mạng
   LAN. Bỏ qua là chấp nhận được; **lệch thì phải đỏ**.
"""
from __future__ import annotations

import os

import pytest

from apps.ltt_llm import ngan_sach


class TestNguonChanLy:
    """Ba con số gõ tay, phần còn lại phải là dẫn xuất."""

    def test_tran_vao_la_dan_xuat_khong_phai_go_tay(self):
        assert ngan_sach.TOKEN_VAO_TRAN == (
            ngan_sach.CUA_SO_MODEL - ngan_sach.TOKEN_RA_TRAN - ngan_sach.LE)

    def test_vao_cong_ra_khong_vuot_cua_so_model(self):
        """Vào và ra chia nhau **một** cửa sổ. Tổng vượt là model tự cắt ngữ cảnh."""
        assert (ngan_sach.TOKEN_VAO_TRAN + ngan_sach.TOKEN_RA_TRAN
                <= ngan_sach.CUA_SO_MODEL)

    def test_cong_bo_cho_client_thap_hon_tran_that(self):
        """Client phải nén **trước** khi chạm trần, không phải lúc đã chạm.

        Lệ 8% là cho lệch tokenizer: client đếm bằng bộ đếm của nó, model đếm
        bằng bộ của Qwen — hai số không bao giờ khớp.
        """
        assert ngan_sach.CONG_BO_CHO_CLIENT < ngan_sach.TOKEN_VAO_TRAN

    def test_body_toi_thieu_du_cho_tran_vao(self):
        """⛔ Trần body từng chặn hội thoại dài ở ~64.000 token trong khi ta tưởng
        đang chạm trần token của máy B. Hai trần không liên quan mà cái nhỏ thắng."""
        assert ngan_sach.BODY_BYTES_TOI_THIEU >= (
            ngan_sach.TOKEN_VAO_TRAN * 4), "body phai du cho tran vao"


class TestMacDinhTheoCua:
    """Mặc định phải **mang tên cửa** — đây là điều kiện để lỗi 30/08 không lặp."""

    def test_moi_cua_deu_co_mac_dinh(self):
        for cua in ("sync", "stream", "job"):
            assert ngan_sach.mac_dinh_cho(cua) > 0

    def test_ten_cua_sai_thi_NEM_chu_khong_tra_bua(self):
        """Lỗi 30/08 sống được vì một mặc định chung chung trả về số của cửa khác."""
        with pytest.raises(KeyError):
            ngan_sach.mac_dinh_cho("khong_co_cua_nay")

    def test_cua_stream_RONG_HON_cua_dong_bo(self):
        """Cửa đồng bộ nhỏ vì trần 100 giây của Cloudflare; cửa stream không bị.

        Đây chính là bất đẳng thức đã bị vi phạm suốt nhiều ngày.
        """
        assert ngan_sach.mac_dinh_cho("stream") > ngan_sach.mac_dinh_cho("sync")

    def test_mac_dinh_khong_vuot_tran(self):
        for cua in ngan_sach.CAC_CUA:
            assert ngan_sach.mac_dinh_cho(cua) <= ngan_sach.TOKEN_RA_TRAN

    def test_mac_dinh_stream_khong_kich_tran(self):
        """Kịch trần bắt khách có sẵn số dư gấp nhiều lần nhu cầu thật (giữ trước
        rồi mới hoàn), và một ví mỏng sẽ bị từ chối oan."""
        assert ngan_sach.mac_dinh_cho("stream") < ngan_sach.TOKEN_RA_TRAN


class TestKhongConChongCheo:
    """Không nơi nào được **định nghĩa lại** con số của `ngan_sach`."""

    def test_manifest_chi_la_bi_danh(self):
        from apps.ltt_llm import manifest
        assert manifest.CUA_SO_NGU_CANH == ngan_sach.CUA_SO_MODEL
        assert manifest.MAX_TOKENS_TRAN == ngan_sach.TOKEN_RA_TRAN
        assert manifest.LE_NGU_CANH == ngan_sach.LE

    def test_features_chi_la_bi_danh(self):
        from apps.ltt_llm import features
        assert features.KY_TU_MOI_TOKEN == ngan_sach.KY_TU_MOI_TOKEN
        assert features.SYNC_MAX_TOKENS_MAC_DINH == ngan_sach.mac_dinh_cho("sync")

    def test_executor_KHONG_con_mac_dinh_chung_chung(self):
        """`default_max_tokens` là cái tên đã gây ra lỗi; nó phải biến mất."""
        from apps.ltt_llm.executor import EXECUTOR
        assert not hasattr(EXECUTOR, "default_max_tokens")
        assert EXECUTOR.mac_dinh_cho("stream") == ngan_sach.mac_dinh_cho("stream")

    def test_khong_con_hang_so_token_go_tay_trong_duong_sinh(self):
        """Quét mã: không tệp nào được gán lại các con số này."""
        import pathlib
        import re
        goc = pathlib.Path(__file__).resolve().parents[1]
        cam = re.compile(
            r"^\s*(MAX_TOKENS_TRAN|CUA_SO_NGU_CANH|LE_NGU_CANH|"
            r"MAC_DINH_TOKEN_RA_STREAM|KY_TU_MOI_TOKEN)\s*=\s*[0-9]", re.M)
        pham = []
        for tep in (goc / "server" / "api" / "streaming.py",
                    goc / "server" / "api" / "chat.py",
                    goc / "apps" / "ltt_llm" / "manifest.py",
                    goc / "apps" / "ltt_llm" / "features.py"):
            if tep.exists() and cam.search(tep.read_text(encoding="utf-8")):
                pham.append(tep.name)
        assert not pham, f"cac tep con go tay hang so ngan sach: {pham}"


class TestDoiChieuMayB:
    """Số của ta phải khớp số máy B **đang thực thi**, không phải số ta tưởng.

    ⛔ Đây là phép kiểm mà nếu có từ đầu thì mâu thuẫn 90.000-vs-65.000 đã lộ ra
       ngay, thay vì phải truy nửa đêm qua bốn tầng.
    """

    @staticmethod
    def _health():
        import json
        import urllib.request
        goc = os.environ.get("LTT_LLM_GATEWAY_URL", "http://192.168.2.66:8299")
        token = os.environ.get("LTT_LLM_TOKEN", "")
        if not token:
            pytest.skip("khong co LTT_LLM_TOKEN — bo qua doi chieu may B")
        req = urllib.request.Request(f"{goc}/health",
                                     headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:                                  # noqa: BLE001
            pytest.skip(f"khong goi duoc may B: {type(exc).__name__}")

    def test_tran_vao_khop_may_B(self):
        tran = self._health().get("tran", {})
        assert tran.get("input_tokens") == ngan_sach.TOKEN_VAO_TRAN, (
            f"may B dang thuc thi {tran.get('input_tokens')} nhung ta tinh "
            f"{ngan_sach.TOKEN_VAO_TRAN} — mot trong hai noi sai")

    def test_tran_ra_khop_may_B(self):
        tran = self._health().get("tran", {})
        assert tran.get("output_tokens") == ngan_sach.TOKEN_RA_TRAN

    def test_dong_thoi_cua_ta_khong_vuot_may_B(self):
        """Cho nhiều việc song song hơn máy B phục vụ được thì phần dôi ra chắc
        chắn ăn 429/503 — không phải lỗi của bên nào, là hai trần không biết nhau."""
        gh = self._health().get("gioi_han", {})
        assert gh.get("max_dong_thoi") == ngan_sach.DONG_THOI_MAY_B, (
            f"may B phuc vu {gh.get('max_dong_thoi')} luot cung luc nhung ta "
            f"khai {ngan_sach.DONG_THOI_MAY_B}")


class TestDoiChieuNenTang:
    """Trần của **nền tảng** phải đủ rộng cho ngân sách của **app**.

    ⚠️ `platform_core` KHÔNG được import `apps.ltt_llm` (app phụ thuộc nền tảng,
       không phải chiều ngược lại). Nên hai bên giữ số riêng, và **bộ kiểm này là
       chỗ duy nhất bắt chúng phải đồng ý**.

    ⛔ Đây chính là cặp đã lệch ngày 30/08: nền tảng chặn body ở 256 KB trong khi
       app cần ~433 KB cho `TOKEN_VAO_TRAN`, nên hội thoại dài bị chặn ở khoảng
       64.000 token và ta tưởng đang chạm trần của máy B.
    """

    def test_tran_body_cua_nen_tang_du_cho_tran_vao_cua_app(self):
        from platform_core.public_api.config import load_public_api_config
        cfg = load_public_api_config()
        assert cfg.max_body_bytes >= ngan_sach.BODY_BYTES_TOI_THIEU, (
            f"nen tang cho {cfg.max_body_bytes} byte nhung app can it nhat "
            f"{ngan_sach.BODY_BYTES_TOI_THIEU} de chua {ngan_sach.TOKEN_VAO_TRAN} "
            f"token — dat LTT_PUBLIC_API_MAX_BODY_BYTES cho du")

    def test_dong_thoi_khai_o_app_khop_hang_so_may_B(self):
        """Ai đặt trần đồng thời cho `text.chat` phải đọc `DONG_THOI_MAY_B` trước."""
        assert ngan_sach.DONG_THOI_MAY_B >= 1


class TestDoiChieuKhoMayB:
    """Mã nguồn của máy B nằm cùng kho này (`llm_gateway/`), nên drift bắt được
    ngay lúc commit chứ không đợi tới lúc chạy.

    ⛔ `KY_TU_MOI_TOKEN` là **phép ước token**, khai ở cả hai kho. Lệch nhau là
       tiền ta giữ trước lệch tiền máy B tính — và **không có gì báo**.
    """

    @staticmethod
    def _hang_so(ten: str, tep: str) -> float:
        import pathlib
        import re
        goc = pathlib.Path(__file__).resolve().parents[1]
        van = (goc / tep).read_text(encoding="utf-8")
        m = (re.search(rf"^{ten}\s*=\s*([0-9_.]+)", van, re.M)
             or re.search(rf"{ten}\s*([0-9_.]+)", van))
        assert m, f"khong tim thay {ten} trong {tep}"
        return float(m.group(1).replace("_", ""))

    def test_uoc_token_khop_giua_hai_kho(self):
        b = self._hang_so("KY_TU_MOI_TOKEN", "llm_gateway/ngan_sach.py")
        assert b == ngan_sach.KY_TU_MOI_TOKEN, (
            f"may B uoc {b} ky tu/token con ta uoc {ngan_sach.KY_TU_MOI_TOKEN} — "
            f"tien giu truoc se lech tien B tinh")

    def test_tran_ra_khop_mac_dinh_trong_ma_may_B(self):
        b = self._hang_so(r'_int\("LTT_LLM_MAX_OUTPUT_TOKENS", ',
                          "llm_gateway/config.py")
        assert b == ngan_sach.TOKEN_RA_TRAN

    def test_tran_vao_khop_mac_dinh_trong_ma_may_B(self):
        """⛔ Đây là cặp đã lệch: mã B mặc định 90.000 còn ta tính 96.256."""
        b = self._hang_so(r'_int\("LTT_LLM_MAX_INPUT_TOKENS", ',
                          "llm_gateway/config.py")
        assert b == ngan_sach.TOKEN_VAO_TRAN, (
            f"ma may B mac dinh {b} nhung ta tinh {ngan_sach.TOKEN_VAO_TRAN}")
