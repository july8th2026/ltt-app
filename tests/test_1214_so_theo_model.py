"""Số theo model trong `apps/ltt_llm/ngan_sach.py` (dual-model 2.6).

🔴 VÌ SAO BỘ NÀY TỒN TẠI, VÀ VÌ SAO NÓ KHÔNG PHẢI `test_334` MỞ RỘNG

`test_334` hỏi *"các con số có còn đồng ý với nhau không"*. Nó đọc hằng và đối
chiếu hằng. Ở 2.6 xuất hiện một câu hỏi **khác hình dạng**: *"những con số ấy có
thật sự được DẪN XUẤT theo từng model, hay chỉ tình cờ bằng nhau?"* — và một
phép kiểm đọc hằng **không phân biệt được hai điều đó**.

⭐ Cách duy nhất phân biệt là **làm nó động**: đổi cửa sổ của MỘT model rồi đòi
   con số dẫn xuất của **đúng model đó** dịch theo, còn của model kia thì
   không. Một hằng số dùng chung sẽ làm cả hai cùng dịch (hoặc cùng đứng yên),
   và đó là lúc phép kiểm đỏ. Ngày 11/09 → 12/09 hai model **thật sự** có cùng
   cửa sổ, nên không đối chứng này thì không có bằng chứng nào.

📏 Nguồn của mọi con số dưới đây — **đo**, không đoán:
   `docs/ltt_llm_dual/10_BENCHMARK_P3.md` §G1b (3090), §G3/§G3b (5060 Ti), §G4
   (prefill, token/ảnh, nạp kho ấm); `docs/ltt_llm_dual/DECISION_LOG.md` L-14
   (ngữ cảnh + 3 slot), L-16 (bộ cờ mà các phép đo G4 chạy dưới).
"""
from __future__ import annotations

import pytest

from apps.ltt_llm import ngan_sach

#: Đo §G1b (3090, `-np 3` + mmproj trên GPU, `-ub` mặc định: VRAM 24.131 MiB,
#: `Shared` 568 trong dải sàn ⇒ không tràn, biên 445 MiB) và §G3 (5060 Ti,
#: `-c 262144 -kvu` KV q8_0 + mmproj: VRAM 13.423 MiB, biên 2.888 MiB).
CUA_SO_DO_DUOC = {"qwen38-api": 221_184, "qwen35-api": 262_144}


class TestCuaSoLaSoDO:
    """Cửa sổ engine phải đúng bằng số đo, và đúng **hai** model."""

    def test_cua_so_tung_model_dung_bang_so_do(self):
        assert ngan_sach.CUA_SO_THEO_MODEL == CUA_SO_DO_DUOC

    def test_hai_cua_so_KHAC_NHAU(self):
        """⛔ Không phải trang trí: nếu chúng bằng nhau thì mọi phép kiểm dẫn
        xuất dưới đây trở thành tautology — một hằng số dùng chung sẽ vượt qua
        tất cả. Đây là điều kiện để phần còn lại của tệp có nghĩa.

        Và chúng khác nhau vì **phần cứng**, không vì sở thích: 3090 + 27B không
        đủ VRAM cho 262.144 cùng mmproj ở 3 slot (đo ~25,2 GB — L-14), còn 5060
        Ti + 9B chỉ tốn ~7,3 GiB trọng số nên dù card nhỏ hơn 8 GB, phần còn lại
        cho KV vẫn rộng hơn.
        """
        assert (ngan_sach.CUA_SO_THEO_MODEL["qwen38-api"]
                != ngan_sach.CUA_SO_THEO_MODEL["qwen35-api"])

    def test_model_mac_dinh_la_mot_khoa_that(self):
        assert ngan_sach.MODEL_MAC_DINH in ngan_sach.CUA_SO_THEO_MODEL
        assert ngan_sach.CUA_SO_MODEL == (
            ngan_sach.CUA_SO_THEO_MODEL[ngan_sach.MODEL_MAC_DINH])

    def test_hep_nhat_la_HEP_NHAT(self):
        assert ngan_sach.CUA_SO_HEP_NHAT == min(
            ngan_sach.CUA_SO_THEO_MODEL.values())

    def test_khong_con_hang_cua_so_vision(self):
        assert not hasattr(ngan_sach, "CUA_SO_MODEL_VISION")


class TestTranCongBoLaDANXUAT:
    """Trần vào/công bố/nén phải là **dẫn xuất theo model**, không phải số chọn tay."""

    def test_cung_MOT_cong_thuc_cho_moi_model(self):
        """Hai model phải mang **cùng một lời hứa**, chỉ khác cửa sổ.

        ⛔ Một model được công thức "nới tay" riêng thì con số công bố của chúng
           không còn so sánh được, và khách không có cách nào biết lời hứa nào
           áp cho model nào (khuyết tật F-02).
        """
        for model, cua_so in ngan_sach.CUA_SO_THEO_MODEL.items():
            vao = ngan_sach.tran_vao_cua(model)
            assert vao == cua_so - ngan_sach.TOKEN_RA_TRAN - ngan_sach.DEM_UOC, model
            assert ngan_sach.cong_bo_cua(model) == int(vao * 0.92), model
            nen = ngan_sach.nen_cua(model)
            assert nen == max(
                0, ngan_sach.cong_bo_cua(model) - ngan_sach.TOKEN_RA_TRAN), model

    def test_khong_con_so_nao_go_tay_o_muc_cong_bo(self):
        """Số công bố của **model mặc định** chỉ là ô tương ứng của bảng trên."""
        md = ngan_sach.MODEL_MAC_DINH
        assert ngan_sach.TOKEN_VAO_TRAN == ngan_sach.tran_vao_cua(md)
        assert ngan_sach.CONG_BO_CHO_CLIENT == ngan_sach.cong_bo_cua(md)
        assert ngan_sach.NEN_CHO_CLIENT == ngan_sach.nen_cua(md)

    def test_moi_model_deu_chua_tron_mot_luot_sinh_dai_nhat(self):
        for model in ngan_sach.CUA_SO_THEO_MODEL:
            assert (ngan_sach.cong_bo_cua(model) - ngan_sach.nen_cua(model)
                    >= ngan_sach.TOKEN_RA_TRAN), model

    def test_tran_body_du_cho_model_RONG_NHAT(self):
        """🔴 Trần body là MỘT con số của cả cửa `/api/v1`, nên nó phải chừa đủ
        cho model **rộng nhất** — không phải cho model mặc định.

        ⛔ Lấy theo model mặc định (hẹp hơn) là dựng lại đúng lỗi 30/08 "hai
           trần không biết nhau mà cái nhỏ hơn thắng", chỉ đổi model.
        """
        rong_nhat = max(ngan_sach.CUA_SO_THEO_MODEL,
                        key=ngan_sach.CUA_SO_THEO_MODEL.get)
        assert ngan_sach.BODY_BYTES_TOI_THIEU >= int(
            ngan_sach.tran_vao_cua(rong_nhat) * ngan_sach.BYTE_MOI_TOKEN_JSON)

    # ── ĐỐI CHỨNG: dịch cửa sổ MỘT model, đòi ĐÚNG model đó dịch theo ────────
    #
    # 🔑 Đây là phép kiểm **duy nhất** trong tệp phân biệt được "dẫn xuất theo
    #    model" với "một hằng số dùng chung". Mọi phép kiểm đọc hằng ở trên đều
    #    xanh với cả hai thiết kế.

    @pytest.mark.parametrize("bi_doi,giu_nguyen",
                             [("qwen38-api", "qwen35-api"),
                              ("qwen35-api", "qwen38-api")])
    def test_doi_cua_so_MOT_model_thi_CHI_model_do_dich(
            self, monkeypatch, bi_doi, giu_nguyen):
        truoc = {m: (ngan_sach.tran_vao_cua(m), ngan_sach.cong_bo_cua(m),
                     ngan_sach.nen_cua(m))
                 for m in ngan_sach.CUA_SO_THEO_MODEL}

        from dataclasses import replace

        # Phương án C bước 2: `-c` gõ ở `HO_SO`, `CUA_SO_THEO_MODEL` dẫn xuất từ nó.
        ho_so_moi = dict(ngan_sach.HO_SO)
        ho_so_moi[bi_doi] = replace(ho_so_moi[bi_doi],        # một bước `-c` thật
                                    engine_ctx=ho_so_moi[bi_doi].engine_ctx + 8_192)
        bang_moi = {m: h.engine_ctx for m, h in ho_so_moi.items()}
        monkeypatch.setattr(ngan_sach, "HO_SO", ho_so_moi)
        monkeypatch.setattr(ngan_sach, "CUA_SO_THEO_MODEL", bang_moi)

        sau = {m: (ngan_sach.tran_vao_cua(m), ngan_sach.cong_bo_cua(m),
                   ngan_sach.nen_cua(m))
               for m in bang_moi}

        assert sau[bi_doi] != truoc[bi_doi], (
            f"doi cua so cua {bi_doi} ma tran/cong bo/nen cua no KHONG dich — "
            f"nghia la chung khong duoc dan xuat tu cua so do")
        assert sau[bi_doi][0] == truoc[bi_doi][0] + 8_192
        assert sau[giu_nguyen] == truoc[giu_nguyen], (
            f"doi cua so cua {bi_doi} lam dich luon so cua {giu_nguyen} — "
            f"hai model dang dung chung MOT con so")


class TestSoSlot:
    """`-np 3` (L-14) mỗi hồ sơ, và pool KV là **của từng model** (`HO_SO`)."""

    def test_ba_slot(self):
        for model, h in ngan_sach.HO_SO.items():
            assert (h.np, h.seq_cap) == (3, 3), model

    def test_pool_kv_theo_model(self):
        assert ngan_sach.POOL_38 == ngan_sach.HO_SO["qwen38-api"].token_budget
        assert ngan_sach.POOL_35 == ngan_sach.HO_SO["qwen35-api"].token_budget
        assert ngan_sach.POOL_38 != ngan_sach.POOL_35
        # Pool A = `-c` − biên token (phương án C; biên đề xuất 8.192 theo
        # `KET_QUA_DO_17_09.md`, chờ chốt ở bước 4). Đọc hằng, không gõ số.
        for model, h in ngan_sach.HO_SO.items():
            assert h.token_budget == (ngan_sach.CUA_SO_THEO_MODEL[model]
                                      - h.bien_pool_token), model
            assert h.bien_pool_token == ngan_sach.BIEN_POOL_TOKEN, model

    def test_ho_so_tu_mau_thuan_thi_NEM_luc_nap(self):
        """Một hồ sơ sai phải đỏ lúc NẠP, không thành một lượt tràn KV lúc chạy."""
        from dataclasses import replace

        h = ngan_sach.HO_SO["qwen38-api"]
        with pytest.raises(ValueError):
            replace(h, seq_cap=h.np + 1)
        with pytest.raises(ValueError):
            replace(h, bien_pool_token=ngan_sach.TOKEN_RA_TRAN)
        with pytest.raises(ValueError):
            replace(h, dem_uoc=0)


class TestNguongWhale:
    """🔑 `NGUONG_WHALE` phải **dẫn xuất từ đường cong prefill ĐO ĐƯỢC**."""

    def test_hai_nguong_KHAC_NHAU(self):
        """⛔ Phép đo §G4 nói thế: một lượt 163K token chặn prefill **257 s trên
        3.8** nhưng **125 s trên 3.5**. Chép một con số từ model này sang model
        kia là tuyên bố hai card có cùng đường cong.
        """
        assert (ngan_sach.NGUONG_WHALE["qwen38-api"]
                != ngan_sach.NGUONG_WHALE["qwen35-api"])
        assert (ngan_sach.NGUONG_WHALE["qwen35-api"]
                > ngan_sach.NGUONG_WHALE["qwen38-api"]), (
            "3.5 prefill nhanh gap ~2 lan o MOI do dai, nen no phai chiu duoc "
            "prompt DAI HON truoc khi thanh ca voi")

    def test_khoang_cach_163K_dung_nhu_G4_ghi(self):
        """Đối chiếu chính đường cong với con số văn xuôi của §G4 (±5 %)."""
        t38 = ngan_sach.thoi_gian_prefill_s("qwen38-api", 163_000)
        t35 = ngan_sach.thoi_gian_prefill_s("qwen35-api", 163_000)
        assert 245 <= t38 <= 270, t38          # §G4 ghi 257 s
        assert 118 <= t35 <= 132, t35          # §G4 ghi 125 s

    def test_nguong_la_MOC_CAO_NHAT_con_trong_ngan_sach_cho(self):
        """Định nghĩa của ngưỡng, đo thẳng: ở ngưỡng thì còn kịp, bước tiếp thì
        không. ⛔ Không kiểm "bằng 33.792" — kiểm **tính chất**, để đổi phép đo
        là ngưỡng tự đi theo mà phép kiểm vẫn đúng."""
        for model, nguong in ngan_sach.NGUONG_WHALE.items():
            tai_nguong = ngan_sach.thoi_gian_prefill_s(model, nguong)
            buoc_tiep = ngan_sach.thoi_gian_prefill_s(model, nguong + 512)
            assert tai_nguong <= ngan_sach.WHALE_CHAN_TOI_DA_S, (
                f"{model}: {nguong} token prefill {tai_nguong:.1f}s, qua "
                f"nguong chan {ngan_sach.WHALE_CHAN_TOI_DA_S}s")
            assert buoc_tiep > ngan_sach.WHALE_CHAN_TOI_DA_S, (
                f"{model}: con cho them duoc ma da goi la ca voi")
            assert nguong % 512 == 0, "buoc phai la boi cua `-ub` mac dinh"

    def test_so_trong_PLAN_khong_theo_duoc_duong_cong(self):
        """🔴 GHI LẠI MỘT SỰ LỆCH CÓ CHỦ Ý, để nó không bị đọc là lỗi đánh máy.

        Plan ghi tạm `16_384 / 32_768`. Đường cong đo cho hai con số ấy **13,7 s**
        và **15,9 s** — chưa tới một nửa ngưỡng chặn ta tuyên bố (30 s). Chúng
        không sai về hướng (3.5 phải cao hơn 3.8) nhưng chúng **không dẫn xuất
        từ** cái gì: tỉ lệ theo đo là ~1,68× chứ không phải 2×.

        ⇒ 2.6 dùng số dẫn xuất. Phép kiểm này chốt rằng số của plan **không**
          thoả định nghĩa, để không ai "sửa lại cho khớp plan".

        ⚠️ Phương án C (17/09): mục tiêu chặn có thể đổi (đề xuất 9 s,
           `KET_QUA_DO_17_09.md`), nên phép kiểm so với MỤC TIÊU đang khai
           (`WHALE_CHAN_TOI_DA_S`), không với 30 s gõ tay.
        """
        chan = ngan_sach.WHALE_CHAN_TOI_DA_S
        for model, so_plan in (("qwen38-api", 16_384), ("qwen35-api", 32_768)):
            if ngan_sach.thoi_gian_prefill_s(model, so_plan) <= chan:
                assert ngan_sach.NGUONG_WHALE[model] > so_plan, model
            else:
                assert ngan_sach.NGUONG_WHALE[model] < so_plan, model

    def test_nguong_chan_la_MOT_tuyen_bo_mot_cho(self):
        """Mục tiêu chặn là một **tuyên bố**, khai ĐÚNG MỘT chỗ và hồ sơ đọc nó.

        🔴 Phương án C bước 2 (17/09): bản trước chốt nó BẰNG `cho_whale_toi_da_s`
           (30 s, whale nhường lượt tương tác bao lâu). Hai đại lượng khác nghĩa —
           một là "prefill được làm nghèo người khác bao lâu", một là "whale đứng
           chờ nhường bao lâu" — nên buộc chúng bằng nhau là chặn đúng lần đổi mà
           số đo 17/09 đề xuất (mục tiêu 9 s). Đổi mục tiêu = đổi một dòng
           `WHALE_CHAN_TOI_DA_S`; phép kiểm này đi theo.
        """
        for model, h in ngan_sach.HO_SO.items():
            assert h.nguong_whale == ngan_sach.nguong_whale_theo_chan(
                model, ngan_sach.WHALE_CHAN_TOI_DA_S), model

    @pytest.mark.parametrize("chan_s", [9.0, 30.0])
    def test_doi_muc_tieu_chan_thi_nguong_dich_dung_chieu(self, chan_s):
        """Mục tiêu chặn thấp hơn ⇒ ngưỡng thấp hơn, ở MỌI model (9 s và 30 s)."""
        for model in ngan_sach.DUONG_PREFILL_TOK_S:
            n = ngan_sach.nguong_whale_theo_chan(model, chan_s)
            assert ngan_sach.thoi_gian_prefill_s(model, n) <= chan_s, model
            assert ngan_sach.thoi_gian_prefill_s(model, n + 512) > chan_s, model
        assert (ngan_sach.nguong_whale_theo_chan("qwen38-api", 9.0)
                < ngan_sach.nguong_whale_theo_chan("qwen38-api", 30.0))

    def test_duong_that_doc_nguong_THEO_MODEL(self):
        """🔴 Cầu nối được hứa ở đây từ 12/09 — nay đã làm (phương án C, O-06).

        Trước 17/09 nền tảng giữ **một** ngưỡng chung 16.384 (env
        `LTT_LLM_NGUONG_WHALE`) và bảng `NGUONG_WHALE` không ai dùng. Nay ngưỡng đi
        `HO_SO` → `AdmissionModel.nguong_whale` → `luat_cho`, và env đã gỡ.
        Phép kiểm hành vi qua đường thật: `tests/test_1229_phuong_an_c_hop_dong.py`.
        """
        from apps.ltt_llm.manifest import MANIFEST
        from platform_core.llm import tham_so_da_luot
        from platform_core.llm.canonical import ALIAS_SANG_ID

        assert not hasattr(tham_so_da_luot.doc(), "nguong_whale")
        tool = MANIFEST.tools[0]
        for alias, model_id in ALIAS_SANG_ID.items():
            assert (tool.admission_cho(alias).nguong_whale
                    == ngan_sach.NGUONG_WHALE[model_id]), alias

    # ── ĐỐI CHỨNG: dịch ĐƯỜNG CONG của một model ────────────────────────────

    @pytest.mark.parametrize("bi_doi,giu_nguyen",
                             [("qwen38-api", "qwen35-api"),
                              ("qwen35-api", "qwen38-api")])
    def test_doi_duong_cong_MOT_model_thi_CHI_nguong_do_dich(
            self, monkeypatch, bi_doi, giu_nguyen):
        """Ngưỡng phải đi ra **từ đường cong**, không phải nằm cạnh nó."""
        # ⛔ Điều kiện để phần dưới có nghĩa: bảng công bố PHẢI là kết quả của
        #    hàm dẫn xuất. Một `NGUONG_WHALE` gõ tay vượt qua mọi phép kiểm
        #    monkeypatch bên dưới, vì chúng gọi hàm chứ không đọc bảng.
        chan = ngan_sach.WHALE_CHAN_TOI_DA_S
        assert ngan_sach.NGUONG_WHALE == {
            m: ngan_sach.nguong_whale_theo_chan(m, chan)
            for m in ngan_sach.DUONG_PREFILL_TOK_S}
        assert {m: h.nguong_whale for m, h in ngan_sach.HO_SO.items()} == \
            ngan_sach.NGUONG_WHALE, "HO_SO phai mang dung nguong dan xuat"

        truoc = {m: ngan_sach.nguong_whale_theo_chan(m, chan)
                 for m in ngan_sach.NGUONG_WHALE}

        cong_moi = dict(ngan_sach.DUONG_PREFILL_TOK_S)
        cong_moi[bi_doi] = tuple((n, toc * 2.0)
                                 for n, toc in cong_moi[bi_doi])
        monkeypatch.setattr(ngan_sach, "DUONG_PREFILL_TOK_S", cong_moi)

        sau = {m: ngan_sach.nguong_whale_theo_chan(m, chan) for m in cong_moi}
        assert sau[bi_doi] > truoc[bi_doi], (
            f"{bi_doi} prefill nhanh gap doi ma nguong ca voi khong nhuc nhich "
            f"— nghia la no khong duoc dan xuat tu duong cong")
        assert sau[giu_nguyen] == truoc[giu_nguyen], (
            f"doi duong cong cua {bi_doi} lam dich luon nguong cua "
            f"{giu_nguyen} — hai model dang dung chung MOT duong cong")


class TestSoDoKhacCuaG4:
    """Các số đo còn lại của §G4 phải sống ở nguồn chân lý, không ở chỗ dùng."""

    def test_token_moi_anh_la_so_DO(self):
        """Đo bằng **hiệu** `n_prompt_tokens` giữa cùng một câu hỏi có ảnh và
        không ảnh (17 → 787). Giống nhau ở cả hai model, và **đi thẳng vào hoá
        đơn** nên không được ước bằng công thức patch."""
        assert ngan_sach.TOKEN_MOI_ANH == 770

    def test_dat_cho_cua_nen_tang_KHONG_uoc_THIEU_cho_moi_anh(self):
        """⛔ Chiều của bất biến quan trọng: đặt chỗ **thừa** là an toàn (chỉ
        tốn suất), đặt chỗ **thiếu** là tràn pool KV — và một lần tràn pool giết
        MỌI slot khi `-kvu` (llama.cpp b10689). Nên hồ sơ được phép chừa cao
        hơn số đo, không được chừa thấp hơn.

        Phương án C (O-11): số đặt chỗ là `HO_SO[m].token_giu_moi_anh`, đi qua
        `AdmissionModel`; env `LTT_LLM_TOKEN_MOI_ANH` đã gỡ.
        """
        from apps.ltt_llm.manifest import MANIFEST
        from platform_core.llm import tham_so_da_luot
        from platform_core.llm.canonical import ALIAS_SANG_ID

        assert not hasattr(tham_so_da_luot.doc(), "token_moi_anh")
        tool = MANIFEST.tools[0]
        for alias, model_id in ALIAS_SANG_ID.items():
            giu = tool.admission_cho(alias).token_giu_moi_anh
            assert giu == ngan_sach.HO_SO[model_id].token_giu_moi_anh, alias
            assert giu >= ngan_sach.TOKEN_MOI_ANH, alias

    def test_nap_kho_am_theo_model(self):
        """§G4: 16,3 s (3.8) và 12,1 s (3.5) — **kho ấm**. Task 5.2 còn giả định
        45,0; nó phải đọc hằng này chứ không gõ lại một con số thứ hai."""
        assert ngan_sach.NAP_KHO_AM_S == {"qwen38-api": 16.3,
                                          "qwen35-api": 12.1}
        assert set(ngan_sach.NAP_KHO_AM_S) == set(ngan_sach.CUA_SO_THEO_MODEL)


class TestTranRaTheoNguCanh:
    """`tran_theo_ngu_canh` và `executor.context_output_cap` phải biết model."""

    def test_khong_neu_model_thi_dung_cua_so_HEP_NHAT(self):
        """⛔ Không rơi về model mặc định, và tuyệt đối không về model rộng
        nhất: bên gọi không nêu model là bên gọi không biết mình ở model nào.

        Phương án C bước 2: "cửa sổ" ở đây là NGÂN SÁCH ĐẶT CHỖ (`-c` − biên)."""
        hep = ngan_sach.NGAN_SACH_HEP_NHAT
        vao = hep - ngan_sach.DEM_UOC - 100
        assert ngan_sach.tran_theo_ngu_canh(vao) == 100

    def test_neu_model_thi_dung_cua_so_CUA_NO(self):
        for model, h in ngan_sach.HO_SO.items():
            vao = h.token_budget - h.dem_uoc - 100
            assert ngan_sach.tran_theo_ngu_canh(vao, model) == 100, model

    def test_luot_vao_dai_nhat_van_dat_cho_VUA_ngan_sach(self):
        """Bất biến 1 của phương án C: `vào ≤ tran_vao ⇒ đặt chỗ ≤ pool`.

        Kẹp `ra` theo `-c` thay vì theo ngân sách thì lượt vào dài nhất hợp lệ
        đặt chỗ VƯỢT pool và nhận 413 dù đã qua trần vào."""
        for model, h in ngan_sach.HO_SO.items():
            vao = ngan_sach.tran_vao_cua(model)
            ra = ngan_sach.tran_theo_ngu_canh(vao, model)
            assert ra >= 1, model
            assert vao + ra + h.dem_uoc <= h.token_budget, model

    def test_model_la_thi_NEM(self):
        with pytest.raises(KeyError):
            ngan_sach.tran_theo_ngu_canh(10, "qwen38-vision")

    def test_luon_it_nhat_1(self):
        for model in ngan_sach.CUA_SO_THEO_MODEL:
            assert ngan_sach.tran_theo_ngu_canh(10_000_000, model) >= 1

    def test_executor_nhan_BI_DANH_cong_khai(self):
        """⭐ Bí danh (`ltt-3.8`), không phải id nội bộ — id nội bộ không bao giờ
        được rời máy A (INV-015), nên bên gọi ở nền tảng chỉ cầm bí danh."""
        from apps.ltt_llm.executor import EXECUTOR
        from platform_core.llm.canonical import ALIAS_SANG_ID

        for alias, model_id in ALIAS_SANG_ID.items():
            ngan = ngan_sach.HO_SO[model_id].token_budget
            vao = ngan - ngan_sach.DEM_UOC - 100
            assert EXECUTOR.context_output_cap(vao, alias) == 100, alias

    def test_executor_KHONG_neu_alias_van_chay_va_bao_thu(self):
        """Bên gọi không biết model (không nêu bí danh) phải tiếp tục chạy, và
        phải nhận con số **hẹp nhất**. (Từ phương án C bước 2 — O-24 — bốn chỗ gọi
        ở nền tảng đều truyền bí danh; nhánh này là lưới cho bên gọi lạ.)"""
        from apps.ltt_llm.executor import EXECUTOR
        vao = ngan_sach.NGAN_SACH_HEP_NHAT - ngan_sach.DEM_UOC - 100
        assert EXECUTOR.context_output_cap(vao) == 100

    def test_bi_danh_la_thi_NEM(self):
        from apps.ltt_llm.executor import EXECUTOR
        with pytest.raises(KeyError):
            EXECUTOR.context_output_cap(10, "ltt_llm_vision")
