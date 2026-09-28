"""
Bản khai của `ltt_llm` — model ngôn ngữ chạy trên máy nhà, bán ra ngoài. (H38)

⭐ MỘT KHAI BÁO, HAI CÁNH CỬA.

   Public API của nền tảng (H35/Q92) xây quanh **tool**: `/api/v1/tools` và
   `/api/v1/models` đều **suy ra từ manifest**, không có danh sách trung tâm nào.
   `catalog.build_models` nói rõ vì sao: *"a central list is a second place to
   update, and the day it disagrees with the tools it is the catalog that is
   wrong"*.

   Nên chat **phải** khai như một tool. Đổi lại ta được miễn phí:

     GET  /api/v1/tools              liệt kê `text.chat`
     GET  /api/v1/models             liệt kê `ltt-3.8`, `ltt-3.5`
     POST /api/v1/jobs               ĐƯỜNG BẤT ĐỒNG BỘ, chạy ngay, không viết gì thêm
     principal.may_use_tool(...)     phân quyền theo khoá khách

   Và cánh cửa thứ hai — `POST /api/v1/chat/completions`, đồng bộ, tương thích
   OpenAI — dùng **chính khai báo này**, không dựng sổ model thứ hai.

⭐ VÌ SAO CẦN CẢ HAI CỬA, KHÔNG PHẢI MỘT:

     đồng bộ (OpenAI)   khách trỏ SDK vào là chạy; nhưng **Cloudflare mặc định
                        cắt ở 125 giây**, nên chỉ hợp prompt vừa phải
     bất đồng bộ (job)  né được trần 125 giây; nhưng khách phải học hình dạng
                        job của ta

   🔴 ĐOẠN NÀY ĐÃ TRÔI **HAI LẦN**, VÀ LẦN THỨ HAI LÀ BÀI HỌC THẬT.

   Lần một (01/09, P08 F-02/F-03): bản cũ viết *"public API giữ trần input 65K
   theo Q116"* trong khi trần thật đã là số dẫn xuất từ lâu.

   Lần hai (09/09): **bản vá của lần một cũng trôi.** Nó thay 65K bằng một bảng
   số cụ thể — `-c 131072`, trần vào 96.256, công bố 89K — và đợt nâng ngữ cảnh
   03/09 làm **cả bảng** hết đúng.

   Lần ba (12/09, dual-model 2.6): **lại một bảng số nữa được chèn vào đây**, lần
   này cho hai model. Nó đúng lúc viết và sẽ sai đúng như hai lần trước — đây là
   ghi chép của lần gỡ nó ra.

   ⭐ VÌ SAO ĐÁNG GHI BA LẦN: bản vá lần một **chính nó là một thông báo đính
      chính về số trôi**, và nó trôi y hệt cái nó đi sửa. Nó sửa **giá trị**;
      khuyết tật là **hình dạng** — một tài liệu chép lại con số của nơi khác sẽ
      trôi mỗi lần nơi kia đổi, và không ai có nghĩa vụ nhớ tới nó.

      Chính tệp này đã đặt tên cho việc ấy ở `_cua_so_noi_voi_khach` bên dưới:
      *"Sửa giá trị không phải sửa hình dạng."* Lần một đọc câu đó và vẫn làm
      đúng điều nó cảnh báo. Lần ba cũng thế.

   ⛔ NÊN Ở ĐÂY KHÔNG CÓ BẢNG SỐ NÀO. Muốn biết số hôm nay:

        apps/ltt_llm/ngan_sach.py   — CUA_SO_THEO_MODEL · TOKEN_VAO_TRAN
                                      CONG_BO_CHO_CLIENT (dẫn xuất theo model)
        GET /api/v1/tools           — thứ khách thật sự đọc
        GET /health cua cong may B  — tran.input_tokens

      Ràng buộc duy nhất đáng phát biểu ở đây là **hình dạng**, và nó bất biến
      với mọi lần đổi `-c`:

        cửa sổ engine  >  trần vào  >  công bố cho client

   ⛔ MỘT CÂU Ở ĐÂY ĐÃ HẾT ĐÚNG, và nó đáng ghi vì cùng một loại lỗi:
      *"Vision luôn có cửa sổ hẹp hơn text, vì hồ sơ của nó phải nạp thêm
      mmproj."* Câu ấy đúng khi vision là **hồ sơ thứ hai của cùng một model**
      (`qwen38-vision`, đã gỡ ở D02/2.3). Từ dual-model, đọc ảnh là việc của
      một **model khác trên một card khác**, và model ấy có cửa sổ **rộng hơn**.
      Một bất biến giữa hai con số của hai máy khác nhau không phải bất biến —
      nó là một sự trùng hợp đang chờ lật.

   ⚠️ Máy B **chưa** chạy hai hồ sơ dual-model: `llama-swap.yaml` còn hồ sơ cũ
      cho tới Task 3.3, nên `/health` của nó hôm nay vẫn trả số cũ. Hai phép
      kiểm đối chiếu yaml trong `test_334`/`test_1201` mang `xfail(strict=True,
      reason="cho Task 3.3")` đúng vì cửa sổ thời gian này — `strict` để chúng
      **đỏ trở lại** ngay khi yaml lên, thay vì lặng lẽ xanh mãi.

   ⛔ Bài học còn nguyên giá trị: cửa sổ *engine* KHÔNG phải thứ khách nhét vào
      được — phải chừa chỗ cho câu trả lời. Nói con số engine với khách là đúng
      lỗi đã bị bắt ngày 01/09, và khoảng cách giữa hai số không phải số lẻ làm
      tròn được.

   Cửa job vẫn là đường lui cho tác vụ dài.

⛔ GIÁ: `credit_cost` ở đây là **TRẦN ƯỚC CAO**, không phải giá cuối. Với LLM,
   số token RA chỉ biết được sau khi sinh xong. Nền tảng giữ chỗ theo trần này rồi
   **quyết toán theo số thật** (`credit.quyet_toan` không bao giờ thu quá phần đã
   giữ). Công thức nằm ở `platform_core/llm/gia_token.py` — **một chỗ duy nhất**,
   dùng chung cho cả hai cửa.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AdmissionModel, AppManifest, ToolSpec

from apps.ltt_llm import features as _features

#: ⛔ CÁC HẰNG DƯỚI ĐÂY LÀ **BÍ DANH**, KHÔNG PHẢI ĐỊNH NGHĨA.
#:
#:    Nguồn chân lý là `apps/ltt_llm/ngan_sach.py`. Giữ tên cũ ở đây để mã đang
#:    gọi không phải sửa, nhưng **đừng gán số vào chúng nữa** — gán ở đây là
#:    dựng lại đúng cái chồng chéo mà `ngan_sach.py` sinh ra để dẹp.
from apps.ltt_llm.ngan_sach import (CONG_BO_CHO_CLIENT,
                                    CUA_SO_MODEL as CUA_SO_NGU_CANH,
                                    HO_SO,
                                    NHOM_CU_TRU_38,
                                    TAI_NGUYEN_35, TAI_NGUYEN_38,
                                    TOKEN_RA_TRAN as MAX_TOKENS_TRAN,
                                    ANH_BYTE_TOI_DA, SO_ANH_TOI_DA,
                                    cong_bo_cua, mac_dinh_cho,
                                    tran_theo_ngu_canh)

def _khai_admission(model_id: str, tai_nguyen: str, nhom_cu_tru: str = "",
                    vai_tro: str = "") -> AdmissionModel:
    """Bản khai admission của MỘT model — chép NGUYÊN hồ sơ `ngan_sach.HO_SO`.

    ⭐ Một hàm, không phải hai lời gọi `AdmissionModel(...)` tự điền: mỗi trường
       của hồ sơ (slot, pool, ngưỡng whale, đệm ước, token mỗi ảnh) đi qua đúng
       một chỗ, nên thêm trường vào hồ sơ mà quên một model là không thể.
    """
    h = HO_SO[model_id]
    return AdmissionModel(tai_nguyen, h.seq_cap, h.token_budget, nhom_cu_tru,
                          vai_tro, nguong_whale=h.nguong_whale,
                          dem_uoc=h.dem_uoc,
                          token_giu_moi_anh=h.token_giu_moi_anh,
                          mot_prefill_dai=h.mot_prefill_dai,
                          toc_prefill_tok_s=h.toc_prefill_uoc_tok_s)


#: Token ra mặc định của **cửa job** (manifest phục vụ đường job).
MAX_TOKENS_MAC_DINH = mac_dinh_cho("job")


def _cua_so_noi_voi_khach(model_id: str) -> str:
    """Con số ngữ cảnh **đúng với thứ khách thật sự nhét vào được**, theo model.

    🔴 THAM SỐ `model_id` LÀ BẢN VÁ CHO MỘT LỜI HỨA SAI THỨ HAI (01/09, P08 F-02).

       Bản đầu của hàm này **không có tham số** — nó trả một con số cho **mọi**
       alias. Nên alias đọc ảnh được quảng cáo *"same 89K usable input
       context"* trong khi máy B chặn nó ở 65.536, và đo thật cho `413`.

       ⭐ Điều đáng học: bản vá 30/08 dưới đây sửa **con số** (131K → 89K) và
          coi như xong. Khuyết tật thật là **một con số cho hai model**, và nó
          sống thêm một ngày sau khi "đã sửa". Sửa giá trị không phải sửa hình
          dạng.

    🔴 TRƯỚC 30/08 CHỖ NÀY GÕ TAY "131K", VÀ ĐÓ LÀ MỘT LỜI HỨA SAI.

       "131K" là cửa sổ của **engine**. Trần đầu vào của Public API là
       `TOKEN_VAO_TRAN` (chừa chỗ cho câu trả lời dài nhất và cho sai số của
       phép ước, tính theo token ƯỚC), còn con số ta **công bố** cho client là
       `CONG_BO_CHO_CLIENT` (quy đổi sang token THẬT, chia `HE_SO_UOC_TREN_THAT`).

       ⛔ Ba con số ấy **cố ý không gõ ra ở đây** — xem đầu tệp: đúng chỗ này
          từng chép chúng ra và cả ba đã trôi hai lần. Đọc `ngan_sach.py`.

       Khách đọc "131K", nhét 120K token vào, và ăn **413**. Không có gì trên
       trang nói cho họ biết vì sao — đúng lớp lỗi "hai nơi nói hai con số" mà
       `ngan_sach.py` sinh ra để dẹp, chỉ là lần này nó rò ra tới **khách hàng**.

    ⛔ Đừng gõ lại số ở đây. `DEVELOPER_GUIDE.md` **sinh ra** từ manifest này
       (`tools/build_public_api_docs.py`), nên một con số gõ tay ở đây sẽ tự
       nhân bản sang tài liệu ta xuất bản.
    """
    return f"{round(cong_bo_cua(model_id) / 1000)}K"




def _cost(params: dict) -> int:
    """Trần credit của một lượt gọi. **Ước CAO có chủ ý.**

    Giữ thiếu thì khách tiêu quá số dư; giữ dư thì hoàn lại. Chiều sai thứ nhất
    đắt hơn nhiều.

    ⛔ Không tự nghĩ ra công thức ở đây. Gọi `gia_token` — nó là chỗ duy nhất được
       phép đại diện cho giá, và cả cửa đồng bộ lẫn cửa job đều đọc nó.

    🔴 GIÁ THEO MODEL KHÁCH XIN (D07, dual-model 2.5). Trần của cửa job phải
       dùng **cùng** bảng giá mà quyết toán sẽ dùng; lấy giá 3.8 cho một job 3.5
       là báo giá gấp 20 lần ở token ra và chặn khách ở cửa số dư.

    ⚠️ `params["model"]` vắng ⇒ `MODEL_MAC_DINH` — **cùng** mặc định mà
       `features.kiem_tham_so` áp cho chính yêu cầu này, đọc từ `canonical` chứ
       không gõ lại tên. Tên lạ thì `kiem_tham_so`/`kiem_ten_model` đã chặn từ
       trước; tới được đây mà vẫn lạ thì `gia_token` ném, không đoán.
    """
    from platform_core.llm import canonical, gia_token

    from apps.ltt_llm.features import uoc_token_vao

    token_vao_uoc = uoc_token_vao(params.get("messages"), params.get("tools"))

    xin_ra = params.get("max_tokens")
    xin_ra = int(xin_ra) if isinstance(xin_ra, (int, float)) else MAX_TOKENS_MAC_DINH
    xin_ra = max(1, min(xin_ra, MAX_TOKENS_TRAN))

    model = str(params.get("model") or canonical.MODEL_MAC_DINH)
    tran = gia_token.uoc_tran(token_vao_uoc=token_vao_uoc, max_tokens=xin_ra,
                              model=model)
    return max(1, tran.tong_credit_lam_tron_len)


MANIFEST = AppManifest(
    slug="ltt_llm",
    display_name=N_('LTT LLM — model ngôn ngữ của nhà'),
    route_prefix="/ltt-llm",
    summary=N_('Model ngôn ngữ chạy trên máy nhà: coding, chat, agent, '
               'tóm tắt, đọc ảnh. Bán qua API cho khách lập trình.'),
    icon="🧠",
    accent="#3F51B5",

    nav=(),                     # chưa có giao diện web — API trước, UI sau

    # ⛔ SỬA 2026-08-26 — TRƯỚC ĐÓ ĐÂY LÀ MỘT LINK 404 TRONG HEADER CỦA **MỌI**
    #    KHÁCH ĐÃ ĐĂNG NHẬP. Đo được: `GET /ltt-llm` → **404**, mà
    #    `visible_on_surface(authenticated=True)` vẫn trả `True`.
    #
    #    Vì sao: `nav=()` **không** có nghĩa là "không có nav" — `nav_entries()`
    #    tự sinh lại một dòng trỏ vào `route_prefix` khi app không khai gì. Và
    #    app này không có `routes.py`, nên đích của dòng đó không tồn tại.
    #
    # ⭐ `catalog_parent` là cơ chế hợp đồng đã có sẵn cho đúng việc này, và
    #    `anhnoibo` đã dùng nó để tránh **đúng cái bẫy này** — chú thích ở
    #    `apps/anhnoibo/manifest.py` mô tả chính xác kịch bản trên. App này thì
    #    không, nên nó rơi vào.
    #
    #    Chọn `chatltt` làm cha: đó là sản phẩm văn bản/hội thoại mà khách
    #    thấy được. Model nhà là **một executor nữa** dưới sản phẩm đó — đúng
    #    nghĩa mà hợp đồng đặt ra cho `catalog_parent`.
    #
    # 🔴 Cha CŨ là `chataistudio`, đã **gỡ hẳn** ở pha 07 (AI CLEAN REBUILD V2)
    #    vì nó là bản sao thứ hai của `chatltt` sau khi mất Codex. Một
    #    `catalog_parent` trỏ tới app không tồn tại làm mục này **rơi khỏi**
    #    catalog — mất chứ không báo lỗi.
    #
    # ⛔ KHÔNG đổi `surface` để chữa: Public API chỉ nhận `"customer"`
    #    (`PUBLIC_SURFACES`), nên đổi surface là đóng luôn đường bán API.
    catalog_parent="chatltt",
    job_types=("ltt_llm.chat",),
    requires=("api",),          # KHÔNG cần GPU của máy A: việc nặng ở máy B
    credit_cost=_cost,
    # Sức khoẻ cho catalog của sản phẩm khác (H43 Phase 06): `GET /live` của
    # cổng máy B, không cần khoá, timeout ngắn. Xem `features.suc_khoe`.
    suc_khoe=_features.suc_khoe,

    enabled=True,
    group="AI",
    # ⛔ HAI CỜ KHÁC NHAU, ĐỪNG TRỘN:
    #    `public`  — catalog WEB (H6/Q30). False vì chưa có trang giới thiệu.
    #    `surface` — Public API chỉ nhận `"customer"` (`PUBLIC_SURFACES`), và
    #                đó đúng bản chất: đây là năng lực BÁN CHO KHÁCH.
    #    Cộng thêm cổng thứ ba: `LTT_PUBLIC_API_TOOLS` phải liệt kê `text.chat`.
    #    Ba cổng độc lập — quên một cái thì thiếu tính năng, không phải lộ hàng.
    public=False,
    surface="customer",
    lifecycle="development",
    # ⛔ BẮT BUỘC với mọi app `surface="customer"` không có `catalog_parent`:
    #    `test_60::test_portfolio_surface_and_lifecycle_match_locked_decisions`
    #    đòi mọi thẻ hiện ở catalog phải nói được **nó làm gì** — thẻ trống là
    #    một ô trong cửa hàng không ghi bán gì.
    capabilities=("AI Text",),
    notes=("Model chạy ở máy B qua `llm_gateway` (:8299). Máy B KHÔNG giữ bí mật "
           "nào của nền tảng (Q102). Gọi qua `platform_core/llm/dieu_phoi.py` — "
           "đừng tự dựng HTTP, đó đúng là lỗi mà `dieu_phoi` sinh ra để sửa."),

    tools=(ToolSpec(
        name="text.chat", job_type="ltt_llm.chat",
        description=N_('Sinh văn bản từ hội thoại: coding, chat, agent, tóm tắt.'),
        ten_ngan=N_('Sinh văn bản từ hội thoại'),
        # ── Sức chứa admission THEO MODEL (dual-model 2.3) ───────────────────
        #
        # 🔴 BỘ BA TĨNH (`admission_resource`/`admission_slots`/
        #    `admission_token_pool`) ĐÃ GỠ, KHÔNG PHẢI QUÊN. Tới 2.3 tool này
        #    phục vụ **hai model trên hai card**, nên một tên tài nguyên duy
        #    nhất (`llm_remote`) tả sai sức chứa: mọi lượt 3.5 sẽ xếp cùng hàng
        #    với 3.8 và một suất giành được ở card này không bảo vệ card kia.
        #
        # ⛔ Hệ quả phải biết khi đọc mã khác: từ đây `tool.admission_resource`
        #    là **rỗng**. Mọi chỗ hỏi "tool này giành tài nguyên nào" phải hỏi
        #    `admission_cho(model)` — kể cả HAI CHỖ NỘP JOB
        #    (`runtime_noi_bo/job.py`, `public_api/invocation.py`) ghi hai cột
        #    `Job.admission_resource/slots`, vì `jobs.claim` và `job_scheduler`
        #    gác hàng đợi bằng đúng hai cột đó (R20).
        #
        # Số lấy từ `ngan_sach.HO_SO` — đừng gõ số ở đây (test_1201, test_1229).
        admission_theo_model={
            "ltt-3.8": _khai_admission("qwen38-api", TAI_NGUYEN_38,
                                       NHOM_CU_TRU_38, "mac_dinh"),
            "ltt-3.5": _khai_admission("qwen35-api", TAI_NGUYEN_35),
        },
        sync_executor="apps.ltt_llm.executor:EXECUTOR",
        params_schema={
            "messages": {"type": "json[]", "required": True},
            "model": {"type": "enum",
                      "values": ["ltt-3.8", "ltt-3.5"],
                      "default": "ltt-3.8"},
            "max_tokens": {"type": "int", "min": 1, "max": MAX_TOKENS_TRAN,
                           "default": MAX_TOKENS_MAC_DINH},
            "temperature": {"type": "number", "min": 0.0, "max": 2.0},
            # `json[]`, khong phai `json`: OpenAI khai `tools` la mot MANG.
            "tools": {"type": "json[]"},
            # `none` = TAT suy nghi (L-02, 13/09/2026). Xem `features.kiem_tham_so`.
            # 🔴 `none` DA BO 14/09/2026 — xem `features.kiem_tham_so`.
            #    Do duoc: `none` cho **2 token** thay vi ~1.180 tren cung prompt.
            #    Ba nguon doc lap (do 14/09, bang 12/09 trong llama-swap.yaml,
            #    model card Qwen ve tham so lay mau) noi cung mot dieu.
            # Q131: khong khai mot default CHUNG trong schema. Qwen3.8 chinh
            # thuc co low|medium|xhigh; nen tang mac dinh medium (L-33, 19/09 -
            # may chu chen khi bo trong); Qwen3.5 chinh
            # thuc chi co thinking on/off, server giu on va template v22.5 dung
            # medium khi client khong gui effort. `ngan_sach.nghi_mac_dinh()`
            # so huu default theo model de admission khop hanh vi may B.
            "reasoning_effort": {"type": "enum",
                                 "values": ["low", "medium", "xhigh"]},
            # ── Mo 14/09/2026: engine DA lam duoc, cua cua ta dang vut di ────
            #
            # ⛔ Sau khoa duoi day khong phai nang luc MOI. Do 14/09 tren
            #    production: cung mot `response_format: json_schema`, may B tra
            #    dung khuon con qua may A thi khuon bi bo qua va JSON bi boc
            #    trong ```json — vi `features.kiem_tham_so` la danh sach trang
            #    va nem chung di, roi van tra **200**.
            #
            # 🔑 Khai o day KHONG chi de sinh tai lieu: `tests/test_1255` chot
            #    CO HOC rang moi khoa trong bang nay phai SONG SOT qua
            #    `kiem_tham_so`. Do la thu ngan lop loi nay quay lai, chu khong
            #    phai loi van nay.
            "response_format": {"type": "json"},
            # 🔴 CHUOI, KHONG phai doi tuong — va day la mot GIOI HAN CUA NEN
            #    TANG duoc ghi ra chu khong phai mot lua chon san pham.
            #
            #    Hop dong that cua `tool_choice` la mot HOP: chuoi
            #    (`none|auto|required`) HOAC doi tuong chi dich danh mot ham.
            #    `platform_core/public_api/invocation._validate_value` chi co
            #    sau kieu (integer/number/boolean/array/object/string) va
            #    KHONG co kieu hop. Khai `json` thi `"auto"` bi tu choi
            #    ("must be an object"); khai chuoi thi dang doi tuong khong
            #    cong bo duoc.
            #
            # ⇒ Chon dang CHUOI (truong hop pho bien), va `kiem_tham_so` cung
            #   chi nhan chuoi — hop dong va hanh vi khop nhau tuyet doi. Ep
            #   MOT ham cu the la nang luc that con thieu; no doi nen tang co
            #   kieu hop truoc, va do la viec cua tang nen tang chu khong phai
            #   cua app nay. KHONG nhan am tham dang doi tuong roi khong khai:
            #   mot nang luc khong ai cong bo la mot nang luc khong ai di tren.
            "tool_choice": {"type": "enum",
                            "values": ["none", "auto", "required"]},
            "parallel_tool_calls": {"type": "bool"},
            "top_p": {"type": "number", "min": 0.0, "max": 1.0},
            "seed": {"type": "int"},
            # `json[]` chu khong `json`: day la mot MANG chuoi. Cung ly do
            # `tools` o tren khai `json[]`.
            "stop": {"type": "json[]"},
        },
        returns={"content": "text", "tool_calls": "json[]", "usage": "json"},

        # Hợp đồng node V2 (spec §4.5).
        #
        # `class="api"`: engine chạy ở máy B — máy A không giữ VRAM nào.
        # ⛔ `slots` CỐ TÌNH KHÔNG KHAI, không phải quên. Suất của tool này
        #    KHÔNG phải hằng số: nó là `HO_SO[model].seq_cap`
        #    (`ngan_sach.py:334` qwen38-api = 3, `:340` qwen35-api = 4), đi vào
        #    `admission_theo_model` ở trên qua `_khai_admission` (dòng 112-126).
        #    `resource` chỉ tả được MỘT con số tĩnh cho cả tool, nên mọi giá trị
        #    viết ở đây đều sai cho ít nhất một model — kể cả 0, thứ khai thành
        #    "không tốn suất nào" đúng vào tool đã làm sập pool 19/09. Chỗ hỏi
        #    đúng vẫn là `registry.admission_luc_nop()` / `admission_cho(model)`
        #    (xem khối 🔴 ngay trên `admission_theo_model`).
        side_effect="external",
        resource={"class": "api"},
        idempotency={"key_fields": ("messages", "model", "max_tokens",
                                    "temperature", "top_p", "seed",
                                    "reasoning_effort", "response_format",
                                    "tools", "tool_choice",
                                    "parallel_tool_calls", "stop")},

        # ── Public API (Q92) ─────────────────────────────────────────────────
        api_exposed=True,
        api_contract={
            "scopes": ("jobs:create",),
            "description": ("Generate text from a conversation. Handles coding, "
                            "chat, agentic tool use, summarisation and image "
                            "reading. OpenAI-compatible message format."),
            # ⭐ ALIAS ≠ ID NỘI BỘ, và khoảng cách đó chính là giá trị của alias:
            #    "Aliases exist so a vendor change is not a breaking change."
            #    Khách ghim vào `ltt-3.8`; ngày ta đổi GGUF bên dưới thì mã của họ
            #    không phải sửa một dòng nào.
            #    ⚠️ Bản đầu tôi đặt alias trùng hệt id — `test_212` bắt được.
            #    🔴 VÀ BẢN THỨ HAI ĐẶT ALIAS TRÙNG HỆT **SLUG APP** (`ltt_llm`),
            #       thứ cũng xoá lớp đệm, chỉ theo chiều khác: khách ghim vào
            #       `ltt_llm` thì ngày ta tách app hay đổi chủ tool, tên họ ghim
            #       không còn nghĩa gì. Cắt 11/09/2026 (D02): đúng HAI tên,
            #       `ltt-3.8` và `ltt-3.5`, không tên nào trùng slug hay id.
            # ⛔ `constraints.context_window` KHÔNG PHẢI TRANG TRÍ. Thiếu nó thì
            #    `server/api/tools.py:_dang_codex` rơi về hằng số lùi
            #    `CUA_SO_CONG_BO_MAC_DINH` (60.000) — và khách nhận **hai con số
            #    khác nhau trong CÙNG một phản hồi**: phần chữ nói 89K, trường
            #    `context_window` nói 60000 (P08 F-03).
            #
            #    `test_334::TestBanSaoConLai` nay buộc **mọi** alias ở đây phải
            #    tự khai, nên đường lùi không bao giờ áp cho model nhà nữa.
            "models": {
                # ⭐ `reads_images` Ở CẢ HAI — sửa 2026-09-13 (L-03).
                #
                #    Chú thích cũ ở đây viết *"hồ sơ `qwen38-api` trên máy B chưa
                #    nạp `mmproj`... Task 3.3 nạp rồi mới bật cờ này"*. Task 3.3
                #    **đã xong**, và chú thích thì không tự biết điều đó.
                #
                # 📏 Đo 13/09 trên máy B thật (`llama-swap /running`), không suy:
                #
                #      qwen38-api  --mmproj H:/LTT_LLM/models/mmproj-F16.gguf
                #      qwen35-api  --mmproj H:/LTT_LLM/models/mmproj-9B-F16-unsloth.gguf
                #
                #    và chính llama-swap khai cả hai hồ sơ là *"doc anh"*. Đối
                #    chứng hành vi: gửi ảnh cho `ltt-3.8` thì nó **đọc và trả
                #    lời về ảnh**; không gửi thì nó nói *"I don't see any image
                #    attached"* — tức nó phân biệt được có ảnh hay không.
                #
                # 🔴 VÀ ĐÂY LÀ CHIỀU NGUY HIỂM CỦA LỚP LỖI F-02, không phải chiều
                #    chú thích cũ lo. Chú thích cũ lo *hứa thừa* (khai đọc ảnh mà
                #    engine không đọc được). Thứ đã thực sự xảy ra là *hứa
                #    thiếu*: engine đọc được suốt, còn bản khai bảo khách rằng
                #    không — nên `server/api/tools.py:52` tắt nút đính ảnh, và
                #    một năng lực đã trả tiền để dựng thì **không ai dùng được**.
                "ltt-3.8": {
                    "id": "qwen38-api",
                    "description": (f"{_cua_so_noi_voi_khach('qwen38-api')} usable "
                                    f"input context. Deepest model: coding, chat, "
                                    f"agentic tool use, summarisation. It reads "
                                    f"images too — send them as OpenAI image_url "
                                    f"parts."),
                    "stability": "stable",
                    "constraints": {
                        "context_window": cong_bo_cua("qwen38-api"),
                        "max_output_tokens": MAX_TOKENS_TRAN,
                        "reads_images": True,
                        # 🔴 Cong bo 14/09/2026. Truoc do tran nay CO THAT va
                        #    dang cuong che (do: 4 anh -> 200, 5 anh -> 400)
                        #    nhung khong cho nao noi cho khach biet.
                        "max_images": SO_ANH_TOI_DA,
                        "max_image_bytes": ANH_BYTE_TOI_DA,
                    },
                },
                "ltt-3.5": {
                    "id": "qwen35-api",
                    "description": (f"Faster and much cheaper, "
                                    f"{_cua_so_noi_voi_khach('qwen35-api')} usable "
                                    f"input context. Same message format, and it "
                                    f"reads images — send them as OpenAI "
                                    f"image_url parts."),
                    "stability": "stable",
                    "constraints": {
                        "context_window": cong_bo_cua("qwen35-api"),
                        "max_output_tokens": MAX_TOKENS_TRAN,
                        "reads_images": True,
                        # 🔴 Cong bo 14/09/2026. Truoc do tran nay CO THAT va
                        #    dang cuong che (do: 4 anh -> 200, 5 anh -> 400)
                        #    nhung khong cho nao noi cho khach biet.
                        "max_images": SO_ANH_TOI_DA,
                        "max_image_bytes": ANH_BYTE_TOI_DA,
                    },
                },
            },
            "enums": {
                "model": ["ltt-3.8", "ltt-3.5"],
                "reasoning_effort": ["low", "medium", "xhigh"],
            },
            "params": {
                "messages": {
                    "description": ("Conversation so far, OpenAI format: a list "
                                    "of {role, content}. `content` may be a "
                                    "string, or a list of parts for images."),
                    "example": [{"role": "user", "content": "Explain HTTP 429."}],
                },
                "model": {
                    "description": (f"`ltt-3.8` is the deepest model and reads "
                                    f"images "
                                    f"({_cua_so_noi_voi_khach('qwen38-api')} usable "
                                    f"input context). `ltt-3.5` answers faster, "
                                    f"costs much less and reads images, with "
                                    f"{_cua_so_noi_voi_khach('qwen35-api')} "
                                    f"usable input context."),
                    "example": "ltt-3.8",
                },
                "max_tokens": {
                    "description": ("Ceiling on generated tokens. Credit is held "
                                    "against this and refunded down to what was "
                                    "actually generated."),
                    "example": 1024,
                },
                "temperature": {"description": "Sampling temperature.", "example": 0.7},
                "tools": {
                    "description": ("Function definitions, OpenAI format. The "
                                    "model may answer with `tool_calls`."),
                    "example": [],
                },
                "reasoning_effort": {
                    "description": (
                        "How much the model thinks before answering. LTT 3.8 "
                        "offers `low`, `medium` and `xhigh`. When omitted, "
                        "LTT 3.8 uses `medium` (`high`/`max` are read as `xhigh`, "
                        "`minimal` as `low`). LTT 3.5 has a single mode with "
                        "thinking always on: a value is accepted and ignored "
                        "(response header `X-LTT-Effort-Bo-Qua: 1`). Turning "
                        "thinking off is rejected on both. "
                        "The thinking budget is set by the server; budget "
                        "fields sent by a client are dropped. GET "
                        "/api/v1/models lists each model's levels. Use `low` on "
                        "LTT 3.8 when you want the shortest answers - do NOT "
                        "reach for a small "
                        "`max_tokens` instead: thinking spends that same "
                        "budget, so the model can reason until it is cut off "
                        "and return empty content with finish_reason=length."),
                    "example": "medium",
                },
                "response_format": {
                    "description": (
                        "Constrain the answer's shape. `{\"type\":\"json_object\"}` "
                        "returns bare JSON; `{\"type\":\"json_schema\","
                        "\"json_schema\":{\"name\":...,\"schema\":{...}}} ` forces "
                        "the answer to match that schema. The constraint is "
                        "enforced by the decoder, not by prompting, so the "
                        "output cannot drift out of shape."),
                    "example": {"type": "json_object"},
                },
                "tool_choice": {
                    "description": (
                        "Whether the model may, must, or must not call a tool: "
                        "`none`, `auto` or `required`. Without it `tools` is "
                        "only ever a suggestion."),
                    "example": "auto",
                },
                "parallel_tool_calls": {
                    "description": ("Allow several tool calls in one turn. "
                                    "Support depends on the model's own "
                                    "template."),
                    "example": True,
                },
                "top_p": {
                    "description": ("Nucleus sampling cutoff, in (0..1]. Lower "
                                    "keeps only the likeliest tokens."),
                    "example": 0.9,
                },
                "seed": {
                    "description": ("Same seed plus same input gives the same "
                                    "answer back, which is what makes a test "
                                    "over this API repeatable."),
                    "example": 42,
                },
                "stop": {
                    "description": ("Up to four strings; generation ends as soon "
                                    "as one appears. Four is the ceiling the "
                                    "wire format itself sets, not one we "
                                    "invented."),
                    "example": ["\n\n"],
                },
            },
        },
    ),),
)
