"""Dịch **công cụ (tool)** giữa hợp đồng Anthropic và giao thức OpenAI.

🔴 VÌ SAO MODULE NÀY TỒN TẠI — ĐO 25/08.

   `/api/v1/messages` nhận request hình dạng **Anthropic**, còn máy B nói giao
   thức **OpenAI**. Hai bên gọi cùng một khái niệm bằng ba cái tên khác nhau, ở
   ba chỗ khác nhau:

   | | Anthropic | OpenAI |
   |---|---|---|
   | khai báo | `tools[].input_schema` | `tools[].function.parameters` |
   | model gọi | khối `tool_use` trong `content` | `message.tool_calls` |
   | ta trả kết quả | khối `tool_result` trong tin `user` | một tin `role="tool"` |

⛔ TRƯỚC MODULE NÀY, `_mot_cuc` **không truyền `tools` đi đâu cả** — nó dựng
   `{"model", "messages", "max_tokens"}` rồi thôi. Nghĩa là tác tử của khách khai
   đủ công cụ, gửi lên, và model **không bao giờ nhìn thấy chúng**. Không lỗi,
   không cảnh báo: model chỉ trả lời bằng chữ như thể khách chưa từng có tool.

   Đó là kiểu hỏng tệ nhất trong tuần này lặp lại lần nữa — **im lặng, và triệu
   chứng không chỉ về phía nguyên nhân**: khách sẽ nghĩ model kém, không nghĩ
   rằng cổng đã đánh rơi phần khai báo.

⚠️ `arguments` của OpenAI là một **chuỗi JSON**, còn `input` của Anthropic là một
   **đối tượng**. Quên bước `json.loads`/`json.dumps` ở giữa thì client nhận một
   chuỗi ở chỗ nó chờ một object — và nó hỏng ở tận trong mã của khách.
"""
from __future__ import annotations

import json
from typing import Any

#: `tool_choice` của Anthropic → của OpenAI. Ba giá trị, và chúng **không** trùng
#: tên: `any` của Anthropic là `required` của OpenAI.
CHON_TOOL = {"auto": "auto", "any": "required", "none": "none"}


def vi_sao_khong_dung_duoc(tools: Any) -> str | None:
    """Vì sao KHÔNG dùng được `tools` này — hoặc `None` nếu dùng được.

    🔴 VÌ SAO CẦN HÀM NÀY. `sang_openai_tools` **bỏ qua im lặng** mọi mục nó
       không hiểu, và trả `None` khi không còn mục nào. Hệ quả đo được 01/09:
       gửi `tools` khuôn **OpenAI** vào cửa Anthropic `/api/v1/messages` cho ra
       `200`, và model trả lời **"Xin lỗi, hiện tại tôi không có tool nào"**.

       Khách gõ sai hình dạng nhận một câu trả lời **hợp lý mà sai**, không phải
       một lỗi. Và đó là nhầm lẫn dễ mắc nhất ở cửa này: hai giao thức, hai
       khuôn tool, cùng một tên trường `tools`.

    ⛔ Nó cũng **lệch chuẩn với chính khu API này**, nơi lỗi gọi đúng tên scope
       thiếu (`missing_scope: usage:read`), nói *"A quote token is required"*, và
       đính `retry: never`. Anthropic thật trả `400` cho tool schema sai; ta khai
       tương thích giao thức đó thì phải trả lời như nó.

    ⭐ CHỈ báo lỗi khi khách khai tool mà **không mục nào** dùng được. Hỗn hợp
       hợp lệ + rác vẫn đi tiếp như cũ — đổi hành vi đó là một hồi quy cho
       client đang chạy, và cái giá lớn hơn cái lợi.
    """
    if not isinstance(tools, list) or not tools:
        return None                      # không khai gì: bình thường
    if sang_openai_tools(tools):
        return None                      # còn ít nhất một mục dùng được
    kieu_openai = any(
        isinstance(t, dict) and t.get("type") == "function"
        and isinstance(t.get("function"), dict) for t in tools)
    if kieu_openai:
        return ("`tools` dang o khuon OpenAI "
                '(`{"type":"function","function":{...}}`). Cua nay dung khuon '
                'Anthropic: `{"name":..., "description":..., "input_schema":{...}}`. '
                "Khuon OpenAI dung duoc o `/api/v1/chat/completions`.")
    return ("khong muc nao trong `tools` dung duoc: moi muc phai co `name` va "
            "`input_schema`.")


def sang_openai_tools(tools: Any) -> list | None:
    """`tools` Anthropic → `tools` OpenAI. `None` khi khách không khai gì."""
    if not isinstance(tools, list) or not tools:
        return None
    ra = []
    for t in tools:
        if not isinstance(t, dict) or not t.get("name"):
            continue
        # ⚠️ Tool phía máy chủ của Anthropic (`type: web_search_…`) khai bằng
        #    `type` chứ không có `input_schema`. Ta không chạy được chúng, nên bỏ
        #    qua thay vì gửi lên một thứ máy B chắc chắn không hiểu.
        if t.get("type") and "input_schema" not in t:
            continue
        ra.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description") or "",
                # OpenAI gọi nó là `parameters`. Thiếu thì khai một object rỗng —
                # bỏ trắng làm một số bộ giải mã từ chối cả lượt.
                "parameters": t.get("input_schema") or {"type": "object",
                                                        "properties": {}},
            },
        })
    return ra or None


def sang_openai_tool_choice(chon: Any) -> Any:
    """`tool_choice` Anthropic → OpenAI. `None` khi không khai (để mặc định)."""
    if isinstance(chon, str):
        return CHON_TOOL.get(chon)
    if not isinstance(chon, dict):
        return None
    loai = chon.get("type")
    if loai == "tool" and chon.get("name"):
        return {"type": "function", "function": {"name": chon["name"]}}
    return CHON_TOOL.get(loai or "")


def _chu(khoi: Any) -> str:
    """Gom phần văn bản của một `content` — chuỗi hoặc danh sách khối."""
    if isinstance(khoi, str):
        return khoi
    if isinstance(khoi, list):
        return "\n".join(str((m or {}).get("text", "")) for m in khoi
                         if isinstance(m, dict) and m.get("type") == "text")
    return ""


def sang_openai_messages(messages: Any) -> list:
    """`messages` Anthropic → `messages` OpenAI, **giữ nguyên vòng gọi tool**.

    🔴 CHỖ KHÓ NHẤT: một tin `user` của Anthropic có thể chứa **nhiều** khối
       `tool_result`, và OpenAI đòi **mỗi kết quả là một tin riêng** với
       `role="tool"` + `tool_call_id`. Gộp chúng thành một tin `user` là làm mất
       liên kết với lượt gọi, và model sẽ không biết kết quả nào của tool nào.

    ⚠️ Thứ tự phải giữ: `tool` phải đứng **ngay sau** tin assistant đã gọi nó.
    """
    ra: list = []
    for tin in messages or []:
        if not isinstance(tin, dict):
            continue
        vai = tin.get("role")
        noi = tin.get("content")

        if vai == "assistant":
            goi = [k for k in (noi if isinstance(noi, list) else [])
                   if isinstance(k, dict) and k.get("type") == "tool_use"]
            m: dict = {"role": "assistant", "content": _chu(noi)}
            if goi:
                m["tool_calls"] = [{
                    "id": k.get("id") or "",
                    "type": "function",
                    "function": {
                        "name": k.get("name") or "",
                        # OpenAI doi CHUOI JSON, Anthropic dua OBJECT.
                        "arguments": json.dumps(k.get("input") or {},
                                                ensure_ascii=False),
                    },
                } for k in goi]
            ra.append(m)
            continue

        if vai == "user" and isinstance(noi, list):
            ket_qua = [k for k in noi if isinstance(k, dict)
                       and k.get("type") == "tool_result"]
            if ket_qua:
                for k in ket_qua:
                    ra.append({"role": "tool",
                               "tool_call_id": k.get("tool_use_id") or "",
                               "content": _chu(k.get("content"))})
                # Phan chu con lai trong cung tin user (neu co) van la mot luot noi.
                con = _chu([k for k in noi if isinstance(k, dict)
                            and k.get("type") == "text"])
                if con.strip():
                    ra.append({"role": "user", "content": con})
                continue

        ra.append({"role": vai or "user", "content": _chu(noi)})
    return ra


def sang_anthropic_content(noi_dung: str, tool_calls: Any) -> list:
    """Kết quả OpenAI → `content` của Anthropic (khối `text` + khối `tool_use`).

    ⛔ `stop_reason: "tool_use"` là một **lời hứa** rằng danh sách này có ít nhất
       một khối `tool_use`. Client đọc `stop_reason` rồi đi tìm khối đó để chạy
       tool; không thấy thì nó **treo**, chứ không báo lỗi.
    """
    ra: list = []
    if (noi_dung or "").strip():
        ra.append({"type": "text", "text": noi_dung})
    for g in tool_calls or ():
        if not isinstance(g, dict):
            continue
        ham = g.get("function") or {}
        tham_so = ham.get("arguments")
        if isinstance(tham_so, str):
            try:
                tham_so = json.loads(tham_so or "{}")
            except ValueError:
                # ⚠️ Model sinh JSON hỏng là chuyện có thật. Đưa nguyên chuỗi vào
                #    một khoá để client còn thấy, thay vì bỏ cả khối tool_use —
                #    bỏ khối là quay về đúng ca "hứa mà không có" ở trên.
                tham_so = {"_raw": ham.get("arguments")}
        if not isinstance(tham_so, dict):
            tham_so = {"_raw": tham_so}
        ra.append({"type": "tool_use", "id": g.get("id") or "",
                   "name": ham.get("name") or "", "input": tham_so})
    # Một phản hồi KHÔNG BAO GIỜ được có `content` rỗng: hợp đồng đòi một mảng có
    # nghĩa, và một số client coi mảng rỗng là lỗi giải mã.
    return ra or [{"type": "text", "text": noi_dung or ""}]
