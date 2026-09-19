# 02 — Journey & Control Registry

| Node/control | Action/contract | State/recovery | Verdict |
|---|---|---|---|
| Text manual input | nên là literal source 0 credit | Canvas hiện có thể gọi `text.generate` | **MISLEADING ở integration** |
| Text Generate | `prompt` → Gemini → text | quote/job/progress/error | LIVE |
| Text after image(s) | owned image → multimodal prompt | size/existence check | LIVE |
| Text after video | owned video → Gemini upload → delete | poll/timeout/delete | LIVE |
| format | plain/markdown/json instruction | không schema-validate JSON | PARTIAL |
| model | model_ref Gemini chat | provider fallback không có | PARTIAL |
| standalone run | qua Agent selected node | duplicate-run bug thuộc Agent audit | PARTIAL |
| `/kichban` legacy | redirect Agent | không lộ retired form | LIVE |
| history/project | Job/Agent run; legacy revision còn code | không có migration UX rõ | PARTIAL |

Các control node/composer nằm trong hồ sơ Agent; ở đây chỉ chấm handler/tool
contract, tránh tính trùng.

