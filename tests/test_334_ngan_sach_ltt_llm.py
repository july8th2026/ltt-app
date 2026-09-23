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
import pathlib

import pytest

from apps.ltt_llm import ngan_sach


class TestNguonChanLy:
    """Ba con số gõ tay, phần còn lại phải là dẫn xuất."""

    def test_tran_vao_la_dan_xuat_khong_phai_go_tay(self):
        assert ngan_sach.TOKEN_VAO_TRAN == (
            ngan_sach.CUA_SO_MODEL - ngan_sach.TOKEN_RA_TRAN - ngan_sach.DEM_UOC)

    def test_vao_cong_ra_khong_vuot_cua_so_model(self):
        """Vào và ra chia nhau **một** cửa sổ. Tổng vượt là model tự cắt ngữ cảnh."""
        assert (ngan_sach.TOKEN_VAO_TRAN + ngan_sach.TOKEN_RA_TRAN
                <= ngan_sach.CUA_SO_MODEL)

    def test_moi_model_deu_chua_tron_mot_luot_sinh_dai_nhat(self):
        """Bat bien nay phai dung cho **moi** model, khong chi model text.

        🔴 VI SAO CAN. `tran_theo_ngu_canh()` — cho kep tran RA cua cua
           stream — dung `CUA_SO_MODEL` (204.800) **vo dieu kien**, khong theo
           model dang goi. Voi `qwen38-vision` (65.536) do la mot cua so gap ba
           lan that.

        ⛔ No van dung, nhung dung **nho mot bat bien o noi khac**:
           `tran_vao_cua()` da tru san `TOKEN_RA_TRAN`, nen dau vao hop le lon
           nhat cua vision la 30.720 va 30.720 + 32.768 = 63.488 <= 65.536.

        ⭐ Do la loai "dung nho hang so ben canh" — nang `TOKEN_RA_TRAN` hay
           ha `LE` mot lan la bien do bien mat, va **khong co gi keu**. Phep kiem
           nay chinh la cai keu.
        """
        # ⛔ DANG THUC, KHONG PHAI `<=`. Ban dau toi viet `<=` va no la mot
        #    TAUTOLOGY: vi `tran_vao_cua` tru dung `TOKEN_RA_TRAN + LE`, tong
        #    luon bang `cua_so - LE`, nen ve trai KHONG BAO GIO vuot. Thu nang
        #    `TOKEN_RA_TRAN` len 40.000: tong van 63.488. Mot phep kiem khong
        #    the do duoc la mot phep kiem khong canh gi.
        #
        # ⭐ Dang thuc moi chot dung thu `tran_theo_ngu_canh()` dang DUA VAO:
        #    dau vao hop le lon nhat cua MOI model da chua san tron mot luot
        #    sinh dai nhat cong `LE`. Bo phan tru do di — theo bat ky chieu nao
        #    — la phep kiem nay do ngay.
        for model_id, cua_so in ngan_sach.CUA_SO_THEO_MODEL.items():
            assert (ngan_sach.tran_vao_cua(model_id) + ngan_sach.TOKEN_RA_TRAN
                    + ngan_sach.DEM_UOC == cua_so), (
                f"{model_id}: vao {ngan_sach.tran_vao_cua(model_id)} + ra "
                f"{ngan_sach.TOKEN_RA_TRAN} + le {ngan_sach.DEM_UOC} != cua so {cua_so}")

    def test_tran_ra_khong_tran_cua_so_cua_model_NHO_NHAT(self):
        """Chay that `tran_theo_ngu_canh()` o bien, tren model cua so be nhat.

        ⛔ Phep kiem tren doc cac HANG SO; phep kiem nay goi chinh cai HAM
           dang dung `CUA_SO_MODEL` vo dieu kien. Hai thu do hong theo hai cach
           khac nhau, nen chung khong thay the nhau duoc.
        """
        be_nhat = min(ngan_sach.CUA_SO_THEO_MODEL, key=ngan_sach.CUA_SO_THEO_MODEL.get)
        cua_so = ngan_sach.CUA_SO_THEO_MODEL[be_nhat]
        vao_toi_da = ngan_sach.tran_vao_cua(be_nhat)
        for vao in (0, 1, vao_toi_da // 2, vao_toi_da - 1, vao_toi_da):
            ra = ngan_sach.tran_theo_ngu_canh(vao)
            assert ra >= 1
            assert vao + ra <= cua_so, (
                f"model {be_nhat}: vao {vao} + tran ra {ra} vuot cua so {cua_so}")

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

    def test_cua_stream_KHONG_co_tran_an_duoi_tran_cong_bo(self):
        """Cửa stream phải mặc định **kịch trần**, không có trần ẩn nào thấp hơn.

        ⛔ Phép kiểm này thay cho một phép kiểm cũ đòi điều NGƯỢC LẠI
           (`stream < TOKEN_RA_TRAN`), viết theo lý do *"kịch trần bắt khách có
           số dư gấp nhiều lần nhu cầu"*. **Phép đo bác bỏ lý do đó**: giá ra 400
           credit/1M token ⇒ giữ trước cho 32.768 token chỉ **13,1 credit**, tức
           1% số dư một tài khoản thường.

        ⛔ Còn cái giá của việc đặt thấp thì đo được và đắt: 30/08 một lượt Codex
           viết ba tệp dừng ở **đúng 8.192 token** ⇒ phản hồi cụt ⇒ Codex vứt ⇒
           **không tệp nào được tạo**. Bất kỳ số nào dưới trần đều chỉ là chỗ để
           cụt lần sau.
        """
        assert ngan_sach.mac_dinh_cho("stream") == ngan_sach.TOKEN_RA_TRAN


class TestKhongConChongCheo:
    """Không nơi nào được **định nghĩa lại** con số của `ngan_sach`."""

    def test_manifest_chi_la_bi_danh(self):
        from apps.ltt_llm import manifest
        assert manifest.CUA_SO_NGU_CANH == ngan_sach.CUA_SO_MODEL
        assert manifest.MAX_TOKENS_TRAN == ngan_sach.TOKEN_RA_TRAN

    def test_features_chi_la_bi_danh(self):
        from apps.ltt_llm import features
        assert features.SYNC_MAX_TOKENS_MAC_DINH == ngan_sach.mac_dinh_cho("sync")

    def test_may_A_khong_uoc_thieu_tool_use_va_tool_result_so_voi_may_B(self):
        """So với phép đo độc lập của gateway, không so A với chính A.

        Hai khối công cụ là hình dạng thật của Claude Code. Trước bản vá, A chỉ
        đọc ``text`` nên bỏ gần hết kết quả công cụ; B đếm đủ và trả 429 sau khi
        A đã cho qua hàng chờ.
        """
        from apps.ltt_llm import features
        from llm_gateway.ngan_sach import do_yeu_cau
        from platform_core.runtime_noi_bo.luong import uoc_tin_nhan

        body = {
            "system": [{"type": "text", "text": "Bạn là coding agent."}],
            "messages": [
                {"role": "assistant", "content": [{
                    "type": "tool_use", "id": "toolu_1", "name": "Read",
                    "input": {"file_path": "src/app.py", "limit": 4000},
                }]},
                {"role": "user", "content": [{
                    "type": "tool_result", "tool_use_id": "toolu_1",
                    "content": [{"type": "text", "text": "x" * 40_000}],
                }]},
            ],
            "tools": [{
                "name": "Read", "description": "Đọc một tệp",
                "input_schema": {"type": "object", "properties": {
                    "file_path": {"type": "string"},
                    "limit": {"type": "integer"},
                }},
            }],
        }
        a = features.uoc_token_vao(uoc_tin_nhan(body))
        b = do_yeu_cau(body).token_van_ban
        assert a >= b, f"máy A giữ {a} nhưng máy B cần ít nhất {b} token"

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
            pytest.skip(
                "khong co LTT_LLM_TOKEN — bo qua doi chieu SONG voi may B "
                "(TestDoiChieuKhoMayB van doi chieu voi MA NGUON cua B, "
                "khong can khoa va khong can mang)")
        req = urllib.request.Request(f"{goc}/health",
                                     headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:                                  # noqa: BLE001
            pytest.skip(f"khong goi duoc may B: {type(exc).__name__}")

    def test_tran_vao_khop_may_B_THEO_MODEL(self):
        """🔵 Phương án C bước 3 (O-02): `/health.tran.input_tokens` là **dict theo
        model**. Bản trước so một số chung với `TOKEN_VAO_TRAN` — đúng cho 3.8, và
        chính vì thế nó không bao giờ thấy 3.5 bị chặn ở trần của 3.8."""
        tran = self._health().get("tran", {}).get("input_tokens")
        assert isinstance(tran, dict), (
            f"may B con tran vao CHUNG ({tran}) — ban cong truoc phuong an C buoc 3")
        for m in ngan_sach.CUA_SO_THEO_MODEL:
            if m in tran:
                assert tran[m] == ngan_sach.tran_vao_cua(m), (
                    f"may B chan {m} o {tran[m]} nhung ta tinh "
                    f"{ngan_sach.tran_vao_cua(m)} — mot trong hai noi sai")

    def test_tran_ra_khop_may_B(self):
        tran = self._health().get("tran", {})
        assert tran.get("output_tokens") == ngan_sach.TOKEN_RA_TRAN

    def test_dong_thoi_cua_ta_khong_vuot_may_B(self):
        """Cho nhiều việc song song hơn máy B phục vụ được thì phần dôi ra chắc
        chắn ăn 429 — không phải lỗi của bên nào, là hai trần không biết nhau.

        Rào của B là `-np` từng model (đọc yaml); máy A không được khai hơn."""
        theo = self._health().get("gioi_han", {}).get("theo_model", {})
        for m, t in theo.items():
            if m not in ngan_sach.HO_SO:
                continue
            ta = ngan_sach.HO_SO[m].seq_cap
            assert ta <= t.get("max_dong_thoi", 0), (
                f"may B phuc vu {t.get('max_dong_thoi')} luot {m} cung luc nhung "
                f"ta khai {ta}")


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
        """Ai đặt trần đồng thời cho `text.chat` phải đọc `HO_SO[m].seq_cap` trước."""
        assert all(1 <= h.seq_cap <= h.np for h in ngan_sach.HO_SO.values())


class TestDoiChieuKhoMayB:
    """Mã nguồn của máy B nằm cùng kho này (`llm_gateway/`), nên drift bắt được
    ngay lúc commit chứ không đợi tới lúc chạy.

    ⛔ Phép ước token (từng là `KY_TU_MOI_TOKEN`, đã gỡ — Task 7) nay là module
       `uoc_token.py` chép ở cả hai kho; `test_1470` so hai bản từng byte.
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

    def test_tran_ra_khop_mac_dinh_trong_ma_may_B(self):
        b = self._hang_so(r'_int\("LTT_LLM_MAX_OUTPUT_TOKENS", ',
                          "llm_gateway/config.py")
        assert b == ngan_sach.TOKEN_RA_TRAN

    def test_tran_vao_may_B_DAN_XUAT_theo_model_khop_ta(self):
        """⛔ Đây là cặp đã lệch hai lần: mã B mặc định 90.000 còn ta tính 96.256;
        rồi B ép 186.368 cho CẢ HAI model (O-02). Phương án C bước 3 gỡ hẳn mặc
        định: B dẫn xuất `-c(yaml) − max_out − DEM_UOC` theo từng model."""
        from llm_gateway.config import DEM_UOC_MAC_DINH
        from llm_gateway.vat_ly import doc_tep, tim_yaml, tran_vao

        max_out = self._hang_so(r'_int\("LTT_LLM_MAX_OUTPUT_TOKENS", ',
                                "llm_gateway/config.py")
        vl = doc_tep(tim_yaml())
        for m in ngan_sach.CUA_SO_THEO_MODEL:
            b = tran_vao(vl[m], int(max_out), DEM_UOC_MAC_DINH)
            assert b == ngan_sach.tran_vao_cua(m), (
                f"ma may B dan xuat {b} cho {m} nhung ta tinh {ngan_sach.tran_vao_cua(m)}")


class TestBanSaoConLai:
    """Ba bản sao trên máy A mà `TestKhongConChongCheo` **không** quét tới.

    Bánh cóc chống-gõ-tay hiện chỉ soi bốn tệp (`streaming`, `chat`, `manifest`,
    `features`) và năm cái tên. Quét lại toàn kho ngày 31/08 (Prompt 01/W4) tìm
    ra ba chỗ nữa giữ bản sao, và **hai trong đó tới tay khách**.

    ⭐ VÀ GÕ TAY Ở ĐÂY LÀ THIẾT KẾ ĐÚNG, đừng "sửa" bằng cách import.
       `platform_core/` và `server/` **không được** phụ thuộc vào `apps/` — đó là
       hợp đồng app của kho này. Nên thứ ghép hai đầu lại phải là **một phép
       kiểm**, không phải một câu `import`. Lớp này chính là cái ghép ấy; trước
       31/08 nó chưa tồn tại.
    """

    @staticmethod
    def _so(ten: str, tep: str) -> int:
        import pathlib
        import re
        goc = pathlib.Path(__file__).resolve().parents[1]
        van = (goc / tep).read_text(encoding="utf-8")
        m = re.search(rf"^{ten}\s*=\s*([0-9_]+)", van, re.M)
        assert m, f"khong tim thay {ten} trong {tep}"
        return int(m.group(1).replace("_", ""))

    def test_vi_du_cho_khach_dung_dung_tran_ra(self):
        """🔴 `examples.py` sinh ra `CLAUDE_CODE_MAX_OUTPUT_TOKENS` trong đoạn
        cấu hình **ta đưa cho khách dán vào máy họ**.

        Lệch ở đây nghĩa là ta phát cho khách một cấu hình sai, và họ sẽ gặp lỗi
        ở máy họ chứ không ở máy ta — kiểu lỗi đắt nhất để lần ra.
        """
        assert self._so("TOKEN_RA_TRAN",
                        "platform_core/public_api/examples.py") == ngan_sach.TOKEN_RA_TRAN

    def test_tran_ra_o_duong_tool_khop(self):
        """`server/api/tools.py:TOKEN_RA_TOI_DA` là trần THẬT trên đường sống
        (dùng làm giá trị lùi khi client không khai `max_tokens`)."""
        assert self._so("TOKEN_RA_TOI_DA",
                        "server/api/tools.py") == ngan_sach.TOKEN_RA_TRAN
        # Task 11 (18/09): chú thích phải dẫn đúng nguồn chân lý, không phải tên
        # nhập lại `MAX_TOKENS_TRAN` của `manifest.py`.
        van = (pathlib.Path(__file__).resolve().parents[1] / "server" / "api"
               / "tools.py").read_text(encoding="utf-8")
        assert "ngan_sach.TOKEN_RA_TRAN" in van

    def test_deploy_ps1_KHONG_chua_so_go_tay(self):
        """🔴 BẢN SAO NGUY HIỂM NHẤT, VÌ NÓ **GHI ĐÈ** CHỨ KHÔNG CHỈ HIỂN THỊ.

        `llm_gateway/deploy/deploy.ps1` từng viết lại `gateway.env` ở **ba** chỗ:
        nhánh migrate (thay dòng cũ), nhánh migrate (thêm nếu thiếu), và nhánh
        sinh mới. Cả ba đều gõ tay con số.

        🔵 Phương án C bước 3: script **không còn gõ số nào** cho trần/slot/bể.
           `max_out`/`DEM_UOC` đọc từ ngan_sach qua `xuat_tham_so_a.py`; `-c`/`-np`
           cổng đọc thẳng từ yaml. Phép kiểm đổi từ "số gõ tay phải đúng" thành
           "không có số gõ tay" — và kiểm luôn rằng script GỌI tệp đọc ngan_sach.

        ⛔ Nên đổi `CUA_SO_MODEL` mà quên tệp này thì máy B **chạy đúng cho tới
           lần deploy kế tiếp**, rồi lặng lẽ lùi về trần cũ. Không lỗi, không
           cảnh báo — chỉ là những yêu cầu lẽ ra vừa lại bắt đầu ăn 413, và
           không ai nối được nó với một lần deploy không liên quan.

        ⭐ Đây đúng lớp khuyết tật "cấu hình trên đĩa ≠ cấu hình đang chạy" mà
           audit 31/08 ghi là D-03-5. Ở đó nó là `llama-swap.yaml` không được
           restart; ở đây nó là `gateway.env` bị viết đè.
        """
        import pathlib
        import re
        goc = pathlib.Path(__file__).resolve().parents[1]
        van = (goc / "llm_gateway" / "deploy" / "deploy.ps1").read_text(
            encoding="utf-8")
        go_tay = re.findall(
            r"LTT_LLM_(?:MAX_INPUT_TOKENS|MAX_OUTPUT_TOKENS|DEM_UOC|MAX_DONG_THOI"
            r"|TOKEN_POOL\w*|RPM)=\d", van)
        assert not go_tay, f"deploy.ps1 con go tay so len may B: {go_tay}"
        # Đối chứng: phép dò phải bắt được đúng dòng cũ.
        assert re.findall(
            r"LTT_LLM_(?:MAX_INPUT_TOKENS|MAX_OUTPUT_TOKENS)=\d",
            "'LTT_LLM_MAX_INPUT_TOKENS=186368'")
        assert "xuat_tham_so_a.py" in van, (
            "deploy.ps1 khong con doc ngan_sach — tham so gateway.env tu dau ra?")
        for so in (ngan_sach.TOKEN_RA_TRAN, ngan_sach.CUA_SO_MODEL):
            assert str(so) not in van, f"deploy.ps1 chua so {so} go tay"

    def test_llama_swap_yaml_khop_cua_so_cua_TUNG_ho_so(self):
        """Tệp thật sự quyết định `-c` của mỗi hồ sơ trên máy B.

        `catalog.py` chỉ **công bố**; `llama-swap.yaml` là thứ **khởi động
        tiến trình**. Hai tệp lệch nhau thì `/v1/models` nói một đằng và model
        chạy một nẻo — và bên sai là bên ta tin.

        🔵 `xfail(strict=True, reason="cho Task 3.3")` đã được **gỡ** ngày
           12/09: Task 3.3 viết lại `llama-swap.yaml` với `-c 221184` cho
           `qwen38-api` và hồ sơ `qwen35-api` mới `-c 262144`, nên cửa sổ thời
           gian "hai bên lệch có chủ ý" đóng lại. Phép kiểm nay **sống**, và nó
           đo đúng điều nó sinh ra để đo.
        """
        import pathlib
        import re
        goc = pathlib.Path(__file__).resolve().parents[1]
        van = (goc / "llm_gateway" / "deploy" / "llama-swap.yaml").read_text(
            encoding="utf-8")
        for ho_so, mong in ngan_sach.CUA_SO_THEO_MODEL.items():
            m = re.search(rf"^  {re.escape(ho_so)}:.*?^\s*-c (\d+)",
                          van, re.S | re.M)
            assert m, f"khong tim thay `-c` cua {ho_so} trong llama-swap.yaml"
            assert int(m.group(1)) == mong, (
                f"llama-swap.yaml khoi dong {ho_so} voi -c {m.group(1)} nhung "
                f"ngan_sach khai {mong}")

    def test_catalog_may_B_KHONG_con_go_cua_so(self):
        """🔵 Phương án C bước 3 (O-16): `catalog.py` từng công bố `max_context` gõ
        tay — bản sao thứ tư của `-c`. Nay `/v1/models` đọc `-c` từ yaml, nên
        catalog **không được** khai lại cửa sổ; và cửa sổ B công bố == của ta."""
        import pathlib
        import re

        from llm_gateway.vat_ly import doc_tep, tim_yaml
        goc = pathlib.Path(__file__).resolve().parents[1]
        van = (goc / "llm_gateway" / "catalog.py").read_text(encoding="utf-8")
        assert not re.search(r"max_context\s*=\s*[0-9]", van), (
            "catalog.py lai go tay cua so ngu canh")
        vl = doc_tep(tim_yaml())
        for m, cua_so in ngan_sach.CUA_SO_THEO_MODEL.items():
            assert vl[m].ctx == cua_so, (m, vl[m].ctx, cua_so)

    def test_KHONG_con_ho_so_vision_rieng_trong_nguon_chan_ly(self):
        """🔴 KẾ THỪA BÁNH CÓC P08 F-02 — nhưng đo **sự vắng mặt** cho đúng.

        Bản cũ của phép kiểm này buộc `CUA_SO_MODEL_VISION` khớp `max_context`
        của hồ sơ `qwen38-vision` trong `catalog.py`. Dual-model 2.6 **gỡ hằng
        ấy**: `qwen38-api` tự nạp mmproj nên không còn model vision riêng (L-14
        hệ quả 4). Nếu chỉ xoá phép kiểm thì cái nó bảo vệ biến mất im lặng.

        ⭐ Nên nó đổi thành một **mệnh đề dương**: nguồn chân lý khai đúng hai
           model nội bộ, và cả hai đều là model thật đang bán. Một hồ sơ vision
           thứ ba lẻn lại vào ⇒ đỏ.
        """
        assert not hasattr(ngan_sach, "CUA_SO_MODEL_VISION"), (
            "CUA_SO_MODEL_VISION quay lai — mot cua so thu hai cho CUNG mot "
            "model la dung khuyet tat F-02")
        assert set(ngan_sach.CUA_SO_THEO_MODEL) == {"qwen38-api", "qwen35-api"}, (
            f"nguon chan ly dang khai {sorted(ngan_sach.CUA_SO_THEO_MODEL)}")

    def test_ho_so_vision_da_bien_mat_khoi_llama_swap_yaml(self):
        """Hồ sơ `qwen38-vision` phải biến mất khỏi **tệp khởi động tiến trình**.

        🔵 `xfail(strict=True, reason="cho Task 3.3")` đã gỡ ngày 12/09 — Task
           3.3 viết lại yaml với đúng hai hồ sơ.

        ⚠️ VÀ PHÉP KIỂM ĐỔI TỪ QUÉT CHUỖI SANG ĐỌC HỒ SƠ. Bản cũ khẳng định
           `"qwen38-vision" not in van` trên **văn bản thô** của cả hai tệp.
           `llama-swap.yaml` nay có một khối *đính chính* giải thích hồ sơ vision
           biến mất vì đâu (và nó là bằng chứng đo được, không phải lời kể), nên
           một phép quét chuỗi sẽ **trừng phạt việc giải thích**: nó ép người sau
           xoá lịch sử để làm cho phép kiểm xanh.

        ⭐ Điều nó ĐO vẫn nguyên, chỉ đúng hơn: hỏi `yaml.safe_load` — tức hỏi
           đúng thứ llama-swap đọc — xem có bao nhiêu hồ sơ và là những hồ sơ nào.
        """
        import pathlib

        import yaml as _yaml
        goc = pathlib.Path(__file__).resolve().parents[1]
        cfg = _yaml.safe_load(
            (goc / "llm_gateway" / "deploy" / "llama-swap.yaml")
            .read_text(encoding="utf-8"))
        ho_so = set(cfg.get("models") or {})
        assert ho_so == set(ngan_sach.CUA_SO_THEO_MODEL), (
            f"llama-swap.yaml mo cac ho so {sorted(ho_so)}, nguon chan ly khai "
            f"{sorted(ngan_sach.CUA_SO_THEO_MODEL)}")
        assert not [t for t in ho_so if "vision" in t], (
            "con mot ho so vision rieng trong llama-swap.yaml")

    def test_ho_so_vision_da_bien_mat_khoi_catalog_cong_B(self):
        """`llm_gateway/catalog.py` không còn `ModelSpec(ten="qwen38-vision")`.

        🔵 `xfail(strict=True, reason="cho Task 4.2")` đã được **gỡ** ngày 12/09:
           Task 4.2 khai lại `catalog.HO_SO` thành đúng hai hồ sơ (`qwen38-api`,
           `qwen35-api`), **cả hai** `co_vision=True` (L-14 hệ quả 4), và sửa
           hàng chục nhánh của `test_250` theo đúng cách — đổi điều chúng khẳng
           định, không thu hẹp cho tới khi xanh. Nhánh "ảnh vào hồ sơ không
           vision ⇒ 413" thành một **mệnh đề dương**:
           `test_MOI_ho_so_dang_mo_deu_NHAN_duoc_anh`.

        Dưới đây là lý do phép kiểm này từng được đánh dấu — giữ lại vì nó giải
        thích vì sao dấu ấy là `xfail(strict=True)` chứ không phải một phép kiểm
        bị xoá:

        ⛔ `xfail(strict=True)` CHO TASK 4.2, KHÔNG PHẢI MỘT PHÉP KIỂM BỊ TẮT —
           và **không phải** một phép kiểm bị thu hẹp cho tới khi nó xanh. Task
           3.3 chỉ sở hữu `llama-swap.yaml`; `catalog.py` là bản **công bố** của
           cổng máy B và nó còn phục vụ hồ sơ vision ở hàng chục nhánh của
           `test_250`. Gỡ nó ở đây là làm một nửa việc của 4.2 trong một commit
           không ai rà.

        ⚠️ HỆ QUẢ ĐANG SỐNG, và nó phải được nói ra chứ không giấu trong một dấu
           `xfail`: từ khi 3.3 deploy yaml, `catalog.py` công bố một model mà
           llama-swap **không còn hồ sơ nào** khởi động nổi. Khách gọi
           `qwen38-vision` sẽ bị llama-swap từ chối, không phải được phục vụ ở
           131K. Hàng rào chặn thiệt hại là `LTT_LLM_MODELS` (fail-closed, Q92):
           tên nào không nằm trong đó thì không mở. ⇒ Task 4.2 phải gỡ hồ sơ khỏi
           `catalog.py` **và** `LTT_LLM_MODELS` của máy B trong cùng một lượt.

        `strict=True` ⇒ ngày `catalog.py` sạch thì đây là XPASS ⇒ ĐỎ ⇒ người làm
        4.2 buộc phải gỡ dấu.
        """
        import pathlib
        goc = pathlib.Path(__file__).resolve().parents[1]
        van = (goc / "llm_gateway" / "catalog.py").read_text(encoding="utf-8")
        assert 'ten="qwen38-vision"' not in van, (
            "catalog.py con khai ModelSpec cho qwen38-vision")

    def test_MOI_alias_tu_khai_context_window(self):
        """🔴 BÁNH CÓC CHO P08 F-03 — cấm rơi về hằng số lùi.

        `server/api/tools.py:_dang_codex` dùng `CUA_SO_CONG_BO_MAC_DINH`
        (60.000) khi model **không tự khai** `constraints.context_window`. Trước
        01/09 không alias nào khai, nên một phản hồi `/api/v1/models` chứa
        **hai con số khác nhau**: phần chữ nói `89K`, trường máy đọc nói `60000`.

        ⭐ Và hằng số lùi ấy nằm cách `TOKEN_RA_TOI_DA` — thứ ĐÃ có bánh cóc —
           đúng 20 dòng trong cùng một tệp. Bánh cóc chỉ bảo vệ thứ nó nhìn thấy.
        """
        from apps.ltt_llm.manifest import MANIFEST
        khai = {}
        for tool in MANIFEST.tools:
            for alias, spec in (getattr(tool, "api_contract", {}) or {}).get("models", {}).items():
                khai[alias] = dict(spec.get("constraints") or {})
        assert khai, "khong doc duoc alias nao tu manifest — phep kiem nay VO"
        for alias, rang_buoc in khai.items():
            assert "context_window" in rang_buoc, (
                f"alias {alias!r} khong tu khai context_window ⇒ no se roi ve "
                f"CUA_SO_CONG_BO_MAC_DINH cua server/api/tools.py, va khach se "
                f"nhan mot con so khong lien quan gi toi model nay")

    #: Trường **bắt buộc** của `ModelInfo` mà `/api/v1/models` phải mang.
    #:
    #: 🔴 Đo 04/09 trên `rust-v0.145.0`, không đoán: `ModelInfo` có 17 trường
    #:    không mang `#[serde(default)]`. Endpoint ta thiếu **tám** — nhưng
    #:    **năm** trong tám là `Option<T>`, và serde tự cho `None`. Ba cái dưới
    #:    đây KHÔNG phải `Option`, nên thiếu chúng là Codex bỏ **cả mục**, im
    #:    lặng, rồi rơi về metadata dự phòng (272.000 ngữ cảnh, KHÔNG nén).
    #:
    #: ⭐ Ranh giới `Option`/không-`Option` đến từ một phép thử BÁC BỎ, không
    #:    từ suy luận: catalog bộ cài cũng thiếu 5 trường mà Codex vẫn chạy
    #:    thật. Nếu "thiếu trường bắt buộc nào cũng chết" thì nó đã phải chết.
    _BAT_BUOC_KHONG_OPTION = ("support_verbosity", "truncation_policy",
                              "experimental_supported_tools")

    def test_models_endpoint_mang_du_truong_Codex_BAT_BUOC(self):
        """🔴 KHUYẾT TẬT SỐNG TRÊN PRODUCTION, tìm ra 04/09.

        `/api/v1/models` thiếu cả ba trường dưới. Khách nào **không** dùng bộ
        cài của ta — cấu hình tay theo tài liệu, hoặc dùng tiện ích VS Code —
        thì Codex không parse nổi một mục nào, rơi về 272.000 ngữ cảnh và
        **không nén**, tức bảo đảm một `413` giữa phiên.

        ⛔ Bộ cài che được lỗi này (`model_catalog_json` thay cả catalog), nên
           nó **không hiện ra** ở bất kỳ phép đo nào đi qua bộ cài. Đó chính là
           lý do phải có phép kiểm riêng cho endpoint.
        """
        import types
        from server.api import tools as sv
        m = types.SimpleNamespace(name="ltt_llm", description="x")
        m.constraints = {"context_window": 156_385, "max_output_tokens": 32_768}
        d = sv._dang_codex(m)
        for truong in self._BAT_BUOC_KHONG_OPTION:
            assert truong in d, (
                f"/api/v1/models thieu {truong!r} — Codex se bo CA MUC va roi ve "
                f"metadata du phong 272.000 ngu canh khong nen")

    def test_models_endpoint_va_bo_cai_noi_CUNG_mot_con_so(self):
        """Ba nơi suy ra ngưỡng nén và trần kết quả tool; ba nơi phải trùng.

        ⛔ Bất biến không phải "mỗi nơi có một con số hợp lệ" — nó là *"ba con
           số ấy là MỘT"*. Hai catalog nói hai ngưỡng nén khác nhau thì hành vi
           của khách phụ thuộc vào việc họ cài bằng cách nào, và đó là loại lỗi
           không ai tái hiện được.
        """
        import json
        import types
        from server.api import tools as sv
        import importlib.util
        import pathlib as _pl
        goc = _pl.Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "cam_cli_doi_chieu_sv", goc / "tools" / "cam_cli.py")
        cc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cc)
        bo_cai = {m["slug"]: m for m in json.loads(cc._catalog_codex())["models"]}
        for slug, bc in bo_cai.items():
            m = types.SimpleNamespace(name=slug, description="x")
            m.constraints = {"context_window": bc["context_window"],
                             "max_output_tokens": ngan_sach.TOKEN_RA_TRAN}
            sv_d = sv._dang_codex(m)
            assert sv_d["truncation_policy"] == bc["truncation_policy"], (
                f"{slug}: may chu {sv_d['truncation_policy']} != bo cai "
                f"{bc['truncation_policy']}")
            assert (sv_d.get("auto_compact_token_limit")
                    == bc.get("auto_compact_token_limit")), (
                f"{slug}: nguong nen may chu {sv_d.get('auto_compact_token_limit')} "
                f"!= bo cai {bc.get('auto_compact_token_limit')}")

    def test_context_window_cua_alias_khop_cua_so_model_that(self):
        """Con số công bố của mỗi alias phải dẫn xuất từ cửa sổ THẬT của model
        nó trỏ tới — không phải từ cửa sổ của model bên cạnh."""
        from apps.ltt_llm.manifest import MANIFEST
        for tool in MANIFEST.tools:
            for alias, spec in (getattr(tool, "api_contract", {}) or {}).get("models", {}).items():
                id_noi_bo = spec["id"]
                mong_doi = ngan_sach.cong_bo_cua(id_noi_bo)
                thay = int((spec.get("constraints") or {})["context_window"])
                assert thay == mong_doi, (
                    f"alias {alias!r} (id {id_noi_bo!r}) cong bo {thay} nhung "
                    f"cua so that cua no cho {mong_doi}")

    def test_hang_so_lui_KHONG_hua_nhieu_hon_model_that(self):
        """Hằng số lùi là lời hứa cho model **chưa tự khai**. Nó không được cao
        hơn con số của model rộng nhất ta thật sự có."""
        lui = self._so("CUA_SO_CONG_BO_MAC_DINH", "server/api/tools.py")
        rong_nhat = max(ngan_sach.cong_bo_cua(m) for m in ngan_sach.CUA_SO_THEO_MODEL)
        assert lui <= rong_nhat, (
            f"hang so lui {lui} hua nhieu hon model rong nhat ({rong_nhat})")

    @pytest.mark.parametrize("model", sorted(ngan_sach.HO_SO))
    def test_registry_provider_khop_HO_SO_tung_model(self, model):
        """`platform_core/providers.py` khai `context_window` + `vision` cho
        TỪNG model nhà, và phải khớp `HO_SO` (Task 5, plan v2 18/09).

        🔴 Bản trước đọc bằng `re.search` ⇒ chỉ **lần xuất hiện đầu** (3.8)
           được đối chiếu; bản sao `-c` của 3.5 (`providers.py:326`) không ai
           canh. Nay hỏi registry theo id, mỗi model một ca.

        ⭐ `vision is True` cho CẢ HAI: `llama-swap.yaml` nạp `--mmproj` cho cả
           `qwen38-api` (mmproj-F16.gguf) lẫn `qwen35-api`; và LTTCODE live L7
           (ảnh, `model: 'ltt-3.8'`) PASS trên production 17/09
           (`D:/LTTCODEAPP/docs/LTTCODE/reports/P03-live-20260917-232947.json`,
           11/11). Cờ `False` của 3.8 là lời khai sai.
        """
        from platform_core import providers
        ids = {m.id for m in providers.models_for("ltt_llm")}
        assert model in ids, f"{model} co trong HO_SO nhung khong co trong registry"
        kn = providers.model_capabilities(model)
        assert kn.get("context_window") == ngan_sach.HO_SO[model].engine_ctx, (
            f"providers khai context_window {kn.get('context_window')} cho {model}"
            f" nhung HO_SO khai {ngan_sach.HO_SO[model].engine_ctx}")
        assert kn.get("vision") is True, f"{model} nap mmproj ma khai vision={kn.get('vision')!r}"

    @pytest.mark.parametrize("model", sorted(ngan_sach.HO_SO))
    def test_registry_provider_nap_model_khop_NAP_KHO_AM_S(self, model):
        """`do_duoc.nap_model_s` trong providers là **bản sao** của
        `ngan_sach.NAP_KHO_AM_S` (`platform_core` không import `apps/`, nên
        phép kiểm này buộc hai đầu). Bản cũ gõ `18` — không khớp số đo 16,3 s
        (`10_BENCHMARK_P3.md` §G4)."""
        from platform_core import providers
        do = providers.model_capabilities(model).get("do_duoc") or {}
        if "nap_model_s" not in do:
            return
        assert do["nap_model_s"] == ngan_sach.NAP_KHO_AM_S[model], (
            f"providers khai nap_model_s {do['nap_model_s']} cho {model} nhung "
            f"NAP_KHO_AM_S khai {ngan_sach.NAP_KHO_AM_S[model]}")

    def test_ASV_viec_anh_GIU_3_5_tuong_minh_khi_3_8_co_vision(self):
        """Hệ quả của cờ `vision` thật trên 3.8: trước Task 5, việc ảnh của
        Auto Scan (`DOC_CANH`, `HO_SO_NOI_DUNG`) rơi về 3.5 **do tình cờ** (3.8
        khai sai không đọc ảnh). Bật cờ đúng mà không chỉ định thì chúng âm thầm
        sang 3.8 — đắt hơn nhiều lần mỗi token (`gia_token.BANG_GIA`), chậm hơn,
        tranh 3090 với job ảnh, và vân tay `EDIT_PLAN` không đổi nên cache không
        vô hiệu. ⇒ ASV phải chỉ định 3.5 cho việc ảnh ở chính `ai.py`."""
        from apps.auto_scan_video import ai
        from platform_core.llm import canonical
        assert ai.MODEL_THI_GIAC_NOI_BO == "ltt-3.5"
        mid_35 = canonical.ALIAS_SANG_ID["ltt-3.5"]
        for t in ai.THAO_TAC:
            if t.can_thi_giac:
                assert ai.model_cho(t) == mid_35, t.ma
            else:
                assert ai.model_cho(t) == canonical.ALIAS_SANG_ID[
                    canonical.model_noi_bo_cua(ai.SLUG)], t.ma


class TestThuLaiKhiParserVo:
    """Nhóm 3: tự thử lại **một lần** khi parser tool-call của llama.cpp vỡ.

    ⛔ Bug thượng nguồn còn mở (ggml-org/llama.cpp#27733, #20260): model sinh
       XONG một lượt hợp lệ rồi phát thừa một mẩu, parser hỏng ở phần đuôi và
       **vứt toàn bộ kết quả**. Khách chỉ thấy "chạy xong rồi không có gì".

    ⭐ Thử lại là hợp lệ vì lỗi **ngẫu nhiên theo lần sinh**, không phải lỗi của
       yêu cầu — nhưng bộ nhận diện phải HẸP, nếu không ta sẽ đốt thêm một lượt
       GPU cho mọi sự cố hạ tầng thật rồi vẫn hỏng y hệt.
    """

    def test_cau_parser_khong_con_la_tin_hieu(self):
        """Task 13: câu chữ parser KHÔNG còn quyết định gì (kể cả telemetry).

        Thử lại chỉ theo mã typed `tool_call_parse_failed` do máy B phát
        (`test_1704::test_chi_tool_call_parse_failed_typed_moi_duoc_retry_mot_lan`).
        """
        from platform_core.llm import luong_vlm
        assert not hasattr(luong_vlm, "_loi_parser_tool_call")
        assert not hasattr(luong_vlm, "_DAU_HIEU_PARSER")

    def test_mo_co_tham_so_chan_thu_lai_vo_han(self):
        """`_da_thu_lai` là thứ giữ cho nó đúng MỘT lần, không thành vòng lặp."""
        import inspect
        from platform_core.llm import luong_vlm
        assert "_da_thu_lai" in inspect.signature(luong_vlm.mo).parameters


# ── Tên model lạ: từ chối, nhưng chỉ đúng chỗ sửa (30/08) ──────────────────

class TestTenModelCuaHangKhac:
    """Codex bịa `gpt-5.6-luna` khi nó thiếu metadata cho `ltt_llm`.

    ⛔ Ta **không** ánh xạ tên đó về `ltt_llm`. Nhận tên sản phẩm của hãng khác
       rồi lặng lẽ phục vụ Qwen là mượn tên hãng — và giấu mất cấu hình sai.
    """

    def test_ten_hang_khac_duoc_chi_dung_cho_sua(self):
        from server.api.streaming import _goi_y_ten_la
        for ten in ("gpt-5.6-luna", "GPT-4o", "claude-sonnet-5", "gemini-3-pro"):
            g = _goi_y_ten_la(ten)
            assert "model_catalog_json" in g, ten
            assert "do not alias" in g, ten

    def test_ten_la_KHONG_phai_ten_hang_thi_khong_them_gi(self):
        from server.api.streaming import _goi_y_ten_la
        assert _goi_y_ten_la("mo-hinh-cua-toi") == ""
        assert _goi_y_ten_la("") == ""

    def test_KHONG_co_tuyen_tuong_thich_nao_muon_ten_hang(self):
        """Bánh cóc: thêm alias `gpt-…`/`claude-3…` vào là gate đỏ."""
        from server.api.streaming import TUYEN_TUONG_THICH, _TIEN_TO_TEN_HANG
        for ten in TUYEN_TUONG_THICH:
            assert not any(ten.lower().startswith(t) for t in _TIEN_TO_TEN_HANG), (
                f"`{ten}` bat dau bang ten hang khac. Tuyen tuong thich phai "
                f"dung ten TA tu dat (vd `ltt-llm-claude-compat`), khong phai "
                f"ten san pham that cua ho.")


# ── Công cụ cắm: hai client, cùng một nguồn chân lý (30/08) ────────────────

class TestCamCliKhopNganSach:
    """`cam_cli.py` chạy trên **máy khách**, nên nó không import được
    `apps.ltt_llm`. Nó gõ lại hai con số — và việc đối chiếu là của TEST.

    🔴 VÌ SAO KHÔNG ĐƯỢC LỆCH. Đây không phải tinh chỉnh, nó là **lỗi tiền**:
       client tưởng cửa sổ rộng hơn thật thì nó **không nén hội thoại kịp**,
       hội thoại vượt trần của ta, khách ăn 413 giữa chừng. Đúng triệu chứng
       "hỏi dài thì im lặng" đã mất nhiều giờ tìm ở phía Codex.
    """

    @staticmethod
    def _cam_cli():
        import importlib.util
        import pathlib
        goc = pathlib.Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "cam_cli_doi_chieu", goc / "tools" / "cam_cli.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _sdk_cli():
        import importlib.util
        import pathlib
        goc = pathlib.Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "sdk_cli_doi_chieu", goc / "sdk" / "ltt_cai_dat_cli.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    #: Bí danh công khai → id nội bộ, để đối chiếu **theo từng model**.
    #:
    #: ⛔ ĐỌC TỪ `canonical.ALIAS_SANG_ID`, KHÔNG GÕ LẠI (D02, dual-model 2.3).
    #:    Bản cũ gõ tay `{"ltt_llm": ..., "ltt_llm_vision": ...}`, nên ngày tên
    #:    công khai bị cắt thì phép kiểm đỏ vì **chính nó** đã cũ — chứ không vì
    #:    bộ cài sai. Một bảng chép tay ở đây là bản chân lý thứ hai cho đúng
    #:    câu hỏi mà `ALIAS_SANG_ID` sinh ra để trả lời.
    @property
    def _THEO_ALIAS(self):
        from platform_core.llm.canonical import ALIAS_SANG_ID
        return dict(ALIAS_SANG_ID)

    def test_cua_so_va_tran_ra_khop_nguon_chan_ly(self):
        cc = self._cam_cli()
        assert cc.CUA_SO_NGU_CANH == ngan_sach.CONG_BO_CHO_CLIENT
        assert cc.TOKEN_RA_TRAN == ngan_sach.TOKEN_RA_TRAN
        assert cc.NEN_HOI_THOAI == ngan_sach.NEN_CHO_CLIENT
        from platform_core.llm.canonical import ALIAS_SANG_ID
        id_35 = ALIAS_SANG_ID["ltt-3.5"]
        assert cc.CUA_SO_NGU_CANH_35 == ngan_sach.cong_bo_cua(id_35)
        assert cc.NEN_HOI_THOAI_35 == ngan_sach.nen_cua(id_35)

    def test_ca_HAI_client_deu_duoc_noi_that_cua_so(self):
        """Codex qua `model_catalog_json`; Claude Code qua biến môi trường.

        ⭐ Hai tên khoá khác nhau, cùng một việc. Bỏ sót một bên là để đúng một
           client rơi lại vào lỗi vừa sửa cho client kia.
        """
        cc = self._cam_cli()
        import json
        cat = json.loads(cc._catalog_codex())
        assert "CLAUDE_CODE_MAX_CONTEXT_TOKENS" in cc.CLAUDE_ENV, \
            "Claude Code khong duoc noi that — no se gia dinh 200k"
        assert {m["slug"] for m in cat["models"]} == set(self._THEO_ALIAS)

    def test_MOI_model_trong_catalog_khai_cua_so_CUA_NO(self):
        """🔴 BÁNH CÓC CHO LỖI "MỘT CON SỐ CHO HAI MODEL", bản bộ cài.

        Trước 03/09 phép kiểm ở đây viết:

            assert all(m["context_window"] == ngan_sach.CONG_BO_CHO_CLIENT
                       for m in cat["models"])

        — tức nó **đòi** cả hai model khai cùng một con số, và `ltt_llm_vision`
        (cửa sổ thật 28.262) bị buộc phải nói 88.555. Phép kiểm không bắt được
        khuyết tật; nó **cưỡng chế** khuyết tật, và sửa mã sẽ làm gate đỏ.

        ⭐ Đây đúng là khuyết tật F-02 mà `cong_bo_cua()` sinh ra để giết. Nó
           chết ở `/api/v1/models` và sống sót ở bộ cài — vì bản vá hôm ấy sửa
           *con số*, còn phép kiểm vẫn giữ nguyên *hình dạng sai*: một hằng số
           cho một vòng lặp trên nhiều model.
        """
        cc = self._cam_cli()
        import json
        for m in json.loads(cc._catalog_codex())["models"]:
            mong = ngan_sach.cong_bo_cua(self._THEO_ALIAS[m["slug"]])
            for truong in ("context_window", "max_context_window"):
                assert m[truong] == mong, (
                    f"{m['slug']}.{truong} = {m[truong]} nhung cua so that cua "
                    f"model nay cho {mong}")
            # ⛔ KHONG kiem `truncation_policy` o day. No la mot ĐẠI LƯỢNG
            #    KHÁC HẲN — trần cho MỘT kết quả tool, không phải cửa sổ — và
            #    dòng cũ ở chỗ này (`limit == mong`) chính là thứ **cưỡng chế**
            #    khuyết tật: nó bắt một kết quả tool được phép nuốt trọn ngữ
            #    cảnh. Bất biến thật ở `test_tran_ket_qua_tool_*` bên dưới.

    def test_tran_ket_qua_tool_KHONG_duoc_bang_ca_cua_so(self):
        """🔴 PHÉP KIỂM CHO KHUYẾT TẬT 04/09 — và cho một lỗ hổng của Codex.

        Bộ cài từng khai `truncation_policy = {"tokens", cả cửa sổ}`, tức
        **một kết quả tool được phép nuốt trọn ngữ cảnh**. Mặc định của chính
        Codex là `TruncationPolicyConfig::bytes(10_000)` với
        `APPROX_BYTES_PER_TOKEN = 4` — tức 2.500 token. Ta rộng hơn 62 lần.

        ⭐ VÌ SAO ĐIỀU ĐÓ NGUY HIỂM chứ không chỉ lãng phí: Codex kiểm ngưỡng
           nén **giữa hai lượt**, KHÔNG kiểm giữa các lần gọi tool trong cùng
           một lượt (openai/codex#16033 — 83 lệnh shell đưa ngữ cảnh 0 → 400K
           trong một lượt; có TODO của chính họ thừa nhận). Khi một lượt phình
           ra thì `truncation_policy` là **hàng phòng thủ duy nhất còn lại**.
           Production đã ăn một kết quả tool **95.901 token trong một lượt**.

        ⛔ Bất biến không phải "limit nhỏ hơn cửa sổ". Nó là: sau một kết quả
           tool lớn nhất, **vẫn phải còn chỗ cho trọn một lượt sinh kế tiếp**.
        """
        cc = self._cam_cli()
        import json
        for m in json.loads(cc._catalog_codex())["models"]:
            tp = m["truncation_policy"]
            assert tp["mode"] == "tokens", (m["slug"], tp)
            assert tp["limit"] != m["context_window"], (
                f"{m['slug']}: tran ket qua tool = ca cua so ngu canh "
                f"({tp['limit']}) — mot ket qua tool duy nhat nuot tron ngu "
                f"canh, va Codex khong kiem nen GIUA cac lan goi tool")
            khoang = m["context_window"] - m.get(
                "auto_compact_token_limit", m["context_window"])
            assert tp["limit"] * 2 <= max(khoang, ngan_sach.TOKEN_RA_TRAN), (
                f"{m['slug']}: tran ket qua tool {tp['limit']} chiem qua nua "
                f"khoang trong {khoang} — hai ket qua lien tiep trong mot luot "
                f"la tran")

    def test_Claude_PHAI_duoc_dat_cua_so_nen_rieng(self):
        """🔴 KHUYẾT TẬT 04/09 TRÊN ĐƯỜNG CLAUDE — cùng họ với Codex, khác tên.

        `CLAUDE_CODE_MAX_CONTEXT_TOKENS` chỉ sửa con số Claude **giả định**. Nó
        **không** đặt ngưỡng nén. Tài liệu chính thức
        (`code.claude.com/docs/en/model-config.md`, mục *Default auto-compact
        thresholds*) nói thẳng:

            "If you don't set an auto-compact window, Claude Code compacts when
             the conversation reaches the model's context limit"
            "Sessions on a model ID Claude Code doesn't recognize, such as an
             LLM gateway alias, compact at the context window Claude Code
             assumes for the ID"

        ⇒ Không đặt `CLAUDE_CODE_AUTO_COMPACT_WINDOW` thì Claude nén ở **đúng
          100%** cửa sổ ta khai (156.385), chừa lại 13.599 trên trần cứng —
          nhỏ hơn một lượt sinh dài nhất (32.768). Và Claude cũng chỉ kiểm
          ngưỡng **giữa hai lượt**.

        ⛔ Đây đúng là hình dạng lỗi đã ăn `413` ở production phía Codex, chỉ
           khác tên khoá. Nó sống được vì `MAX_CONTEXT_TOKENS` **trông như** đã
           giải quyết xong vấn đề.
        """
        cc = self._cam_cli()
        assert "CLAUDE_CODE_AUTO_COMPACT_WINDOW" in cc.CLAUDE_ENV, (
            "bo cai khong dat cua so nen cho Claude — Claude se nen o 100% "
            "cua so khai bao, khong con cho cho mot luot sinh")
        # ⚠️ 18/09 (R-05): AUTO_COMPACT_WINDOW la CUA SO; Claude nen o
        #    cua so - min(maxOut, 20000) - 13000. Diem nen THAT moi phai bang
        #    nguong Codex — phep kiem day du o `test_1440`.
        diem = (cc.CUA_SO_NEN_CLAUDE
                - min(cc.TOKEN_RA_TRAN, cc.CLAUDE_TRU_RA_TOI_DA)
                - cc.CLAUDE_DEM_NEN)
        assert diem <= cc.NEN_HOI_THOAI, (
            f"Claude nen o {diem} > nguong nen Codex {cc.NEN_HOI_THOAI}")
        con = ngan_sach.tran_vao_cua("qwen38-api") - diem
        assert con >= ngan_sach.TOKEN_RA_TRAN, (
            f"nen o {diem} tren tran cung "
            f"{ngan_sach.tran_vao_cua('qwen38-api')} chi chua {con} token — "
            f"nho hon mot luot sinh dai nhat ({ngan_sach.TOKEN_RA_TRAN})")

    #: Sàn cứng của `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, đọc từ tài liệu chính
    #: thức: *"Set the auto-compact window in tokens, from `100000` to
    #: `1000000`"*. Giá trị dưới sàn bị Claude kẹp lên, tức lời hứa của ta im
    #: lặng thành một lời hứa khác.
    _SAN_CUA_SO_NEN_CLAUDE = 100_000

    def test_cua_so_nen_Claude_KHONG_duoi_san_Claude_chap_nhan(self):
        """Một con số bị client kẹp lại là một con số ta không còn kiểm soát."""
        cc = self._cam_cli()
        assert cc.CUA_SO_NEN_CLAUDE >= self._SAN_CUA_SO_NEN_CLAUDE, (
            f"{cc.CUA_SO_NEN_CLAUDE} duoi san {self._SAN_CUA_SO_NEN_CLAUDE} — "
            f"Claude se kep len va bo cai noi mot dang, client lam mot dang")

    def test_tran_ket_qua_MCP_khop_tran_ket_qua_tool_cua_Codex(self):
        """Mặc định `MAX_MCP_OUTPUT_TOKENS` là 25.000 — chiếm 76% khoảng trống.

        Hai kết quả MCP trong **một** lượt là tràn, và Claude không kiểm ngưỡng
        giữa các lần gọi tool. Cùng bài toán với Codex nên cùng con số.
        """
        cc = self._cam_cli()
        assert "MAX_MCP_OUTPUT_TOKENS" in cc.CLAUDE_ENV
        assert cc.TRAN_KET_QUA_TOOL * 2 <= ngan_sach.TOKEN_RA_TRAN, (
            f"hai ket qua tool {cc.TRAN_KET_QUA_TOOL} lien tiep vuot khoang "
            f"trong {ngan_sach.TOKEN_RA_TRAN}")

    def test_hai_bo_cai_khai_CUNG_bo_bien_Claude(self):
        """Bản `sdk` từng **thiếu** hai biến mà bản Windows có — chú thích ngay
        trong tệp ấy ghi lại chuyện đó. Phép kiểm này để nó đừng lặp lại."""
        cc, sdk = self._cam_cli(), self._sdk_cli()
        for ten in ("CUA_SO_NEN_CLAUDE", "TRAN_KET_QUA_TOOL", "NEN_HOI_THOAI"):
            assert getattr(cc, ten) == getattr(sdk, ten), (
                f"{ten}: cam_cli {getattr(cc, ten)} != sdk {getattr(sdk, ten)}")

    def test_hai_bo_cai_khai_CUNG_tran_ket_qua_tool(self):
        """Hai bộ cài là hai tệp; một tệp được sửa còn tệp kia thì không, đó là
        cách khuyết tật vision đã sống nhiều ngày."""
        import json
        cc, sdk = self._cam_cli(), self._sdk_cli()
        a = {m["slug"]: m["truncation_policy"]
             for m in json.loads(cc._catalog_codex())["models"]}
        b = {m["slug"]: m["truncation_policy"]
             for m in json.loads(sdk._catalog())["models"]}
        assert a == b, f"cam_cli {a} != sdk {b}"

    def test_nguong_nen_chua_TRON_mot_luot_sinh_dai_nhat(self):
        """🔴 ĐÂY LÀ PHÉP KIỂM CHO ĐÚNG LỖI PRODUCTION 03/09.

        `413` ở `POST /api/v1/responses`: 101.938 token vào trên trần 96.256.
        Client **có** nén — nó chỉ nén quá muộn, vì khoảng trống từ ngưỡng nén
        lên cửa sổ công bố (25.412 với tỉ lệ `× 0,8` cũ) **nhỏ hơn một lượt
        sinh dài nhất** mà chính ta cho phép (32.768).

        ⛔ Client chỉ kiểm ngưỡng **giữa hai lượt**. Nên bất biến không phải
           "ngưỡng nén nhỏ hơn cửa sổ" — nó là *"cửa sổ trừ ngưỡng nén phải đủ
           cho trọn một lượt nữa"*. Hai câu ấy nghe giống nhau và chỉ một câu
           đúng.
        """
        cc = self._cam_cli()
        import json
        for m in json.loads(cc._catalog_codex())["models"]:
            nen = m.get("auto_compact_token_limit")
            if nen is None:
                # Bỏ hẳn trường là câu trả lời hợp lệ — và chỉ hợp lệ khi nguồn
                # chân lý cũng nói "không có ngưỡng nào giữ được lời hứa".
                assert ngan_sach.nen_cua(self._THEO_ALIAS[m["slug"]]) == 0, (
                    f"{m['slug']} bo truong auto_compact_token_limit trong khi "
                    f"nguon chan ly VAN dinh nghia duoc mot nguong")
                continue
            con = m["context_window"] - nen
            assert con >= ngan_sach.TOKEN_RA_TRAN, (
                f"{m['slug']}: nen o {nen} tren cua so {m['context_window']} chi "
                f"chua {con} token — nho hon mot luot sinh dai nhat "
                f"({ngan_sach.TOKEN_RA_TRAN}). Day dung la cau hinh da an 413.")

    def test_phep_kiem_nay_DO_DUOC_khi_bat_bien_bi_pha(self):
        """⭐ Một chốt chỉ hữu ích nếu chứng minh được nó **đỏ được**.

        🔴 VÀ ĐỐI CHỨNG CŨ ĐÃ TỰ HỎNG Ở 2.6 — ghi lại vì nó dạy đúng điều
           `ngan_sach` vẫn nói mà chưa ai đo. Bản cũ dựng lại công thức hỏng
           bằng `0,8 × cửa sổ **hôm nay**` rồi đòi nó vỡ. Ở cửa sổ 156.385 nó vỡ
           (còn 31.277 < 32.768). Ở cửa sổ 171.458 của hồ sơ 221K nó **không vỡ
           nữa** (còn 34.292 ≥ 32.768) — nên đối chứng chuyển từ "chứng minh
           phép kiểm đỏ được" sang "đỏ vì chính nó đã cũ".

        ⭐ Đó chính là câu `ngan_sach.nen_cua` viết ra mà chưa ai chạy được:
           *"0,8 không sai vì bịa, nó sai vì được chọn ở một cửa sổ rộng rồi
           mang sang một cửa sổ hẹp"*. Nay có số: cùng tỉ lệ, cùng bất biến, chỉ
           đổi cửa sổ — và kết quả lật.

        ⇒ Đối chứng phải **bất biến với cửa sổ**. Hai phần dưới đây làm việc đó:
          một cấu hình hỏng dựng từ chính cửa sổ hôm nay, và **số thật** của sự
          cố 03/09 (không suy lại từ hôm nay, nên nó không lật theo).
        """
        cua_so = ngan_sach.CONG_BO_CHO_CLIENT

        # (1) Đối chứng bất biến với cửa sổ: chừa THIẾU đúng một token.
        nen_hong = cua_so - (ngan_sach.TOKEN_RA_TRAN - 1)
        assert cua_so - nen_hong < ngan_sach.TOKEN_RA_TRAN, (
            "bat bien khong con phan biet duoc cau hinh hong voi cau hinh lanh")

        # (2) Sự cố THẬT 03/09, bằng số của hôm ấy: `413` ở 101.938 token vào
        #     trên trần 96.256, ngưỡng nén `0,8 ×` cửa sổ công bố khi đó.
        cua_so_03_09 = 96_256
        assert cua_so_03_09 - int(cua_so_03_09 * 0.8) < ngan_sach.TOKEN_RA_TRAN

        # (3) Cấu hình THẬT hôm nay thoả.
        assert cua_so - ngan_sach.NEN_CHO_CLIENT >= ngan_sach.TOKEN_RA_TRAN

        # (4) Và ghi lại phát hiện: sau khi hạ cửa sổ công bố ngày 22/09 (L-35,
        #     chia `HE_SO_UOC_TREN_THAT` thay vì bớt 8%), `0,8` LẠI KHÔNG thoả
        #     ở cửa sổ hôm nay — y hệt sự cố 03/09 ở mục (2). Đây KHÔNG phải hồi
        #     quy: nó là đúng bằng chứng cho câu "tỉ lệ không đo được cái cần
        #     đo" — 0,8 đúng/sai tuỳ cửa sổ đang chạy, còn công thức
        #     `cửa sổ − TOKEN_RA_TRAN` (mục 3) đúng ở MỌI cửa sổ.
        assert cua_so - int(cua_so * 0.8) < ngan_sach.TOKEN_RA_TRAN, (
            "cua so da rong lai du muc `0,8` con thoa — doc lai muc (2), va "
            "dung dung `0,8` o bat ky bo cai nao")


# ── Số công bố cho KHÁCH phải khớp số máy chủ thực thi (30/08) ─────────────

class TestExamplesKhopNganSach:
    """`platform_core/public_api/examples.py` là thứ khách **đọc rồi chép**.

    🔴 MỘT CON SỐ GÕ TAY TRONG TÀI LIỆU BÁN HÀNG LÀ MỘT LỜI HỨA.

       Trước 30/08 sáu chỗ nói với khách ba con số khác nhau, và không chỗ nào
       đúng:
         · `examples.py` ×2 và `HUONG_DAN_CAM_CLI.md` ×2 -> `65000`
           (bắt khách tự giới hạn thấp hơn thật 24 nghìn token);
         · mô tả model trong manifest -> `131K`
           (hứa nhiều hơn thật 42 nghìn, rồi khách ăn **413** giữa hội thoại);
         · vision -> `64K`, không khớp gì cả.

    ⚠️ `platform_core` **không được** import `apps` (`test_147_layering`), nên
       hai con số ở `examples.py` là bản sao có chủ ý và việc đối chiếu là của
       phép kiểm này — cùng khuôn đã dùng cho `llm_gateway` và `cam_cli`.
    """

    def test_hai_con_so_cong_bo_khop_nguon_chan_ly(self):
        from platform_core.public_api import examples

        assert examples.CUA_SO_CONG_BO == ngan_sach.CONG_BO_CHO_CLIENT
        assert examples.TOKEN_RA_TRAN == ngan_sach.TOKEN_RA_TRAN
        # ⛔ HAI DONG NAY THIEU CHO TOI 04/09. `NEN_CLIENT` la con so trang
        #    cong khai bao khach dat lam nguong nen — no troi khoi nguon chan
        #    ly thi trang day khach mot nguong sai, va khong gi keu len.
        assert examples.NEN_CLIENT == ngan_sach.NEN_CHO_CLIENT
        assert examples.TRAN_KET_QUA_TOOL == ngan_sach.TOKEN_RA_TRAN // 2

    def test_KHONG_con_so_ngu_canh_go_tay_nao_trong_doan_ma_mau(self):
        """Bánh cóc: mọi đoạn khách chép phải sinh ra từ hằng, không gõ."""
        import re

        from platform_core.public_api import examples

        goc = "https://app.lttstudios.com"
        doan = "\n".join([
            examples.codex_profile(),
            examples.codex_config(goc),
            examples.vscode_codex_config(goc),
            examples.claude_code_env(goc),
            examples.claude_code_settings(goc),
            examples.vscode_claude_settings(goc),
        ])
        cho_phep = {str(ngan_sach.CONG_BO_CHO_CLIENT),
                    str(ngan_sach.TOKEN_RA_TRAN),
                    # Hai con so cua ban 1.6.0 — VAN suy tu SSOT, khong go tay.
                    str(ngan_sach.NEN_CHO_CLIENT),
                    str(ngan_sach.TOKEN_RA_TRAN // 2),
                    # ⚠️ `25000` la HANG SO CUA CLAUDE, khong phai cua ta:
                    #    mac dinh `MAX_MCP_OUTPUT_TOKENS`, doc 04/09 tu
                    #    `code.claude.com/docs/en/env-vars.md`. No duoc phep
                    #    xuat hien vi no khong the troi theo SSOT cua ta —
                    #    nhung no CO THE troi theo Anthropic, nen neu doan mau
                    #    con nhac no thi phai doi chieu lai tai lieu.
                    "25000",
                    "600000",           # stream_idle_timeout_ms
                    "200",              # nhac trong chu thich: "200,000 token"
                    "000", "0", "1", "145", "0.145", "2"}
        so = {m for m in re.findall(r"\b\d{4,}\b", doan)}
        la = so - cho_phep
        assert not la, (
            f"So ngu canh go tay trong doan ma mau: {sorted(la)}. "
            f"Dung `CUA_SO_CONG_BO` / `TOKEN_RA_TRAN`.")

    def test_doan_Codex_khai_catalog_va_doan_Claude_khai_cua_so(self):
        """Thiếu một trong hai là để lại đúng lỗi vừa sửa cho khách tự dính."""
        from platform_core.public_api import examples

        goc = "https://app.lttstudios.com"
        assert "model_catalog_json" in examples.codex_profile()
        codex = examples.codex_profile()
        assert "model_auto_compact_token_limit" in codex
        assert "max_concurrent_threads_per_session = 1" in codex
        vscode_codex = examples.vscode_codex_config(goc)
        assert "model_catalog_json" in vscode_codex
        assert "model_auto_compact_token_limit" in vscode_codex
        assert "request_max_retries = 1" in vscode_codex
        assert "stream_max_retries = 0" in vscode_codex
        assert "max_concurrent_threads_per_session = 1" in vscode_codex
        for lam in (examples.claude_code_env, examples.claude_code_settings,
                    examples.vscode_claude_settings):
            van = lam(goc)
            assert "CLAUDE_CODE_MAX_CONTEXT_TOKENS" in van, lam.__name__
            assert "CLAUDE_CODE_AUTO_COMPACT_WINDOW" in van, lam.__name__
            assert "MAX_MCP_OUTPUT_TOKENS" in van, lam.__name__
            assert "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS" in van, lam.__name__
            assert "CLAUDE_CODE_MAX_RETRIES" in van, lam.__name__
            assert "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK" in van, lam.__name__
            assert "ENABLE_TOOL_SEARCH" in van, lam.__name__
            assert str(ngan_sach.CONG_BO_CHO_CLIENT) in van, lam.__name__

    def test_mo_ta_model_cong_khai_KHONG_hua_qua_thuc_te(self):
        """Mô tả trong manifest đi thẳng vào `DEVELOPER_GUIDE.md` ta xuất bản.

        🔴 SIẾT 01/09 (P08 F-02): trước đây phép kiểm này chỉ đòi **một** con số
           xuất hiện đâu đó trong mô tả **gộp** của mọi alias. Nên khi vision
           quảng cáo *"same 89K"* — con số của model **bên cạnh** — nó vẫn xanh.

        ⭐ Bài học chung hơn cả khuyết tật: nối mô tả của nhiều model lại rồi
           kiểm trên chuỗi gộp là **tự bịt mắt mình**, vì mọi câu hỏi "model nào
           nói con số này" đều biến mất trong lúc nối. Nay kiểm **từng alias**.
        """
        from apps.ltt_llm import manifest

        tool = next(t for t in manifest.MANIFEST.tools if t.name == "text.chat")
        for alias, spec in tool.api_contract["models"].items():
            mo_ta = spec["description"]
            if spec["constraints"].get("reads_images"):
                assert "images" in mo_ta, f"{alias}: metadata says vision but docs do not"
            assert "131K" not in mo_ta and "64K" not in mo_ta, (
                f"{alias}: van hua cua so cua ENGINE chu khong phai cua so "
                f"khach dung duoc")
            cua_minh = manifest._cua_so_noi_voi_khach(spec["id"])
            assert cua_minh in mo_ta, (
                f"{alias} (id {spec['id']}) phai noi con so cua CHINH NO "
                f"({cua_minh}), khong phai cua model khac")
            # ⛔ Và không được nói con số của model kia — đó chính là F-02.
            for id_khac in ngan_sach.CUA_SO_THEO_MODEL:
                if id_khac == spec["id"]:
                    continue
                khac = manifest._cua_so_noi_voi_khach(id_khac)
                if khac != cua_minh:
                    assert khac not in mo_ta, (
                        f"{alias} dang quang cao {khac} — do la con so cua "
                        f"{id_khac}, khong phai cua no")

    def test_canh_bao_provider_KHONG_go_so_cua_so(self):
        """🔴 O-13 (phương án C, 17/09): `providers.py` từng mang cảnh báo hiển
        thị *"engine có cửa sổ 131K; API public giới hạn input 96.256"* — gõ
        01/09, sai từ 03/09, không phép kiểm nào đọc. Cửa sổ/trần vào công bố
        THEO MODEL qua `/api/v1/models`; chuỗi hiển thị không được gõ lại số.
        """
        import re

        from platform_core import providers

        prov = providers.get("ltt_llm")
        so = re.compile(r"\d{2,3}[.,]\d{3}|\d+\s*K\b")
        for m in prov.models:
            for cau in (m.capabilities or {}).get("canh_bao", []) or []:
                assert not so.search(str(cau)), (
                    f"{m.id}: canh bao go so cua so/tran tay: {cau!r}")


class TestTaiLieuKhopMayChuThat:
    """Tài liệu công khai phải khớp thứ máy chủ **thật sự làm**.

    🔴 MỘT MỤC TRONG `CHAT_DIFFERENCES` GHI "No streaming yet" TỪ 24/08 TỚI
       30/08 — trong khi streaming đã sống trên hai cửa suốt thời gian đó, và
       chính máy chủ trả về câu chỉ sang hai cửa ấy khi khách gửi
       `stream: true` vào cửa đồng bộ.

       Tức tài liệu **mâu thuẫn với thông điệp lỗi của chính hệ thống**. Khách
       đọc "chưa có streaming" thì không thử, và không bao giờ tìm ra hai cửa
       họ cần để cắm Codex hay Claude Code — đúng thứ ta đang bán.
    """

    def test_KHONG_con_cau_noi_chua_co_streaming(self):
        from platform_core.public_api import examples

        van = " ".join(f"{a} {b}" for a, b in examples.CHAT_DIFFERENCES).lower()
        assert "no streaming yet" not in van
        for cua in ("/api/v1/messages", "/api/v1/responses"):
            assert cua in van or cua.replace("/api", "") in van, cua

    def test_ba_cua_deu_duoc_ke_ten(self):
        from platform_core.public_api import examples

        van = " ".join(f"{a} {b}" for a, b in examples.CHAT_DIFFERENCES)
        for cua in ("/api/v1/jobs", "/api/v1/chat/completions",
                    "/api/v1/messages", "/api/v1/responses"):
            assert cua in van, f"tai lieu khong nhac cua {cua}"

    def test_thong_diep_400_cua_may_chu_chi_dung_hai_cua_kia(self):
        """Nguồn của câu chỉ đường phải là **một**, và nó ở máy chủ.

        Nếu ai đó đổi thông điệp 400 mà quên tài liệu, phép kiểm này đỏ.
        """
        import inspect

        from server.api import chat as api_chat

        ma = inspect.getsource(api_chat)
        assert "/api/v1/messages" in ma and "/api/v1/responses" in ma, (
            "cua dong bo khong con chi sang hai cua stream — tai lieu va may "
            "chu se lech nhau nhu da lech tu 24/08 toi 30/08")


class TestNamSoNguCanhPhaiCONG_KHAI:
    """🔴 SINH RA TỪ SỰ CỐ 03/09, không phải từ mong muốn tài liệu đầy đủ.

    Một lượt `POST /api/v1/responses` ăn `413` ở 101.938 token vào trên trần
    96.256 — và trang công khai duy nhất nói về tích hợp (`/huong-dan`) **không
    có một con số nào** về ngữ cảnh. Khách không có gì để đối chiếu, nên họ
    đoán; và cái đoán sai luôn là cùng một cái: tưởng `context_window` là thứ
    mình được phép gửi.

    ⛔ Phép kiểm này chốt **cả năm** con số phải đứng riêng. Gộp hai cái bất kỳ
       là dựng lại đúng lớp lỗi đã mắc bốn lần ở dự án này.
    """

    def test_ba_con_so_may_doc_duoc_khop_nguon_chan_ly(self):
        from platform_core.public_api import examples

        theo_ten = {ten: gt for ten, gt, _ in examples.NGU_CANH_NAM_SO}
        assert theo_ten["Engine context"].replace(",", "") == str(
            ngan_sach.CUA_SO_MODEL)
        assert theo_ten["Hard input limit"].replace(",", "") == str(
            ngan_sach.TOKEN_VAO_TRAN)
        assert theo_ten["Advertised context"].replace(",", "") == str(
            ngan_sach.CONG_BO_CHO_CLIENT)
        assert theo_ten["Auto-compact at"].replace(",", "") == str(
            ngan_sach.NEN_CHO_CLIENT)
        assert theo_ten["Max output"].replace(",", "") == str(
            ngan_sach.TOKEN_RA_TRAN)

    def test_nam_so_KHAC_NHAU_va_dung_thu_tu(self):
        """Bất biến của cả chương trình, viết ra thành một dòng đọc được."""
        assert (ngan_sach.NEN_CHO_CLIENT
                < ngan_sach.CONG_BO_CHO_CLIENT
                < ngan_sach.TOKEN_VAO_TRAN
                < ngan_sach.CUA_SO_MODEL)
        from platform_core.public_api import examples

        gia_tri = [gt for _, gt, _ in examples.NGU_CANH_NAM_SO]
        assert len(set(gia_tri)) == len(gia_tri), (
            "hai trong nam con so dang bang nhau — mot trong hai la ban sao "
            "cua cai kia, va do dung la cach bon lan truoc da hong")

    def test_trang_CONG_KHAI_render_nam_so_va_muc_413(self):
        """Bánh cóc: khai biến mà quên đưa vào ngữ cảnh là bảng rỗng, im lặng."""
        from server.routes import tai_lieu_api

        ma = (pathlib.Path(tai_lieu_api.__file__)).read_text(encoding="utf-8")
        assert '"ngu_canh_nam_so": examples.NGU_CANH_NAM_SO' in ma
        assert '"loi_413": examples.LOI_413' in ma
        mau = pathlib.Path("server/templates/huong_dan.html").read_text(
            encoding="utf-8")
        assert "ngu_canh_nam_so" in mau and "loi_413" in mau, (
            "trang cong khai khong render muc ngu canh / 413")

    def test_413_KHONG_khuyen_xoa_phien(self):
        """⛔ "Xoá phiên rồi làm lại" mất việc đang làm mà **không** sửa gì.

        Nó là lời khuyên dễ viết nhất và sai nhất: nguyên nhân nằm ở cấu hình
        client, nên lần sau nó lặp lại y hệt.
        """
        from platform_core.public_api import examples

        van = " ".join(t + " " + c for t, c in examples.LOI_413).lower()
        for cam in ("start over", "clear the session", "delete the session",
                    "start a fresh conversation"):
            assert cam not in van, f"tai lieu 413 dang khuyen {cam!r}"
        assert "model_catalog_json" in van
        assert "claude_code_max_context_tokens" in van


class TestBaCuaPhaiCONG_KHAI:
    """Thứ quyết định người ta có mua hay không thì không được nằm sau đăng nhập.

    🔴 Tới 30/08, "có ba cửa, hai trong đó stream" chỉ hiện ở
       `/developers/quickstart` — **303 về `/login`** với khách ẩn danh. Tức câu
       trả lời cho *"tôi cắm được Codex/Claude Code vào đây không?"* nằm sau
       cổng đăng ký. Đúng thứ `server/routes/tai_lieu_api.py` sinh ra để sửa,
       chỉ là lần đó chưa áp cho mục này.
    """

    def test_ba_cua_co_du_bon_duong_va_danh_dau_cua_nao_stream(self):
        from platform_core.public_api import examples

        duong = {d for d, _, _ in examples.BA_CUA}
        assert duong == {"POST /api/v1/jobs", "POST /api/v1/chat/completions",
                         "POST /api/v1/messages", "POST /api/v1/responses"}
        stream = {d for d, kieu, _ in examples.BA_CUA if kieu == "streaming"}
        assert stream == {"POST /api/v1/messages", "POST /api/v1/responses"}

    def test_trang_CONG_KHAI_render_duoc_ba_cua(self):
        """Bánh cóc: khai biến mà quên đưa vào ngữ cảnh là bảng rỗng, im lặng."""
        from server.routes import tai_lieu_api

        ma = (pathlib.Path(tai_lieu_api.__file__)).read_text(encoding="utf-8")
        assert '"ba_cua": examples.BA_CUA' in ma
        mau = pathlib.Path("server/templates/huong_dan.html").read_text(
            encoding="utf-8")
        assert "ba_cua" in mau, "trang cong khai khong render ba cua"

    def test_BA_CUA_khop_CHAT_DIFFERENCES(self):
        """Hai chỗ nói cùng một sự thật thì phải khớp, nếu không lại lệch."""
        from platform_core.public_api import examples

        van = " ".join(f"{a} {b}" for a, b in examples.CHAT_DIFFERENCES)
        for d, _, _ in examples.BA_CUA:
            assert d.removeprefix("POST ") in van, d
