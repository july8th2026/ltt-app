# A4 — Competitor Benchmark

| Capability/JTBD | LTT | ChatGPT | Claude | Gemini | Perplexity | LTT verdict |
|---|---:|---:|---:|---:|---:|---|
| Durable contextual chat | 1 | 3 | 3 | 3 | 3 | REPAIR thread recovery/branch |
| Markdown/code/table/copy | 1 | 3 | 3 | 3 | 3 | BUILD table stake |
| Files + persistent knowledge | 1 | 3 | 3 | 3 | 3 | FIX attachment truth; DEFER vector store per Q56 |
| Web research/citations | 0 | 3 | 2 | 3 | 3 | DEFER until provider/cost contract |
| Image generation/edit | 1 | 3 | 1 | 3 | 2 | FIX cost/control first |
| Regenerate/edit/branch response | 1 | 3 | 3 | 3 | 2 | BUILD message controls |
| Search/export/history management | 1 | 3 | 2 | 3 | 3 | EXTEND without new runtime |
| Privacy/retention/delete control | 0 | 3 | 3 | 3 | 3 | REPAIR blocker |
| Commercial provider contract | 0 | 3 | 3 | 3 | 3 | REPAIR/migrate |
| LTT credit receipt | 2 | N/A | N/A | N/A | N/A | KEEP, make all paths honest |

**TABLE_STAKES:** context đúng, formatted output, retry/copy/edit, attachment truth, timeout/recovery, delete/retention, commercial auth. **DIFFERENTIATOR:** Vietnamese creative presets, transparent per-turn LTT receipt, handoff to LTT image/video/apps. **ANTI-FEATURE:** thêm memory/vector/web tool trước khi thread/credit/privacy đúng. Q56 vẫn hiệu lực: conversation là đơn vị project, không tạo runtime project thứ hai.

## Official snapshot sources

- [ChatGPT Projects](https://help.openai.com/en/articles/10169521-projects-in-chatgpt)
- [OpenAI account sharing policy](https://help.openai.com/en/articles/10471989-openai-account-sharing-policy)
- [ChatGPT vs API billing](https://help.openai.com/en/articles/9039756-billing-settings-in-chatgpt-vs-platform)
- [OpenAI Services Agreement](https://openai.com/policies/services-agreement/)
- [Claude projects](https://support.anthropic.com/en/articles/9519177-how-can-i-create-and-manage-projects)
- [Gemini Apps Help](https://support.google.com/gemini?hl=en)
- [Perplexity Spaces](https://www.perplexity.ai/help-center/en/articles/10352961-what-are-spaces)

OpenAI docs xác nhận Codex có ChatGPT-managed và API-key auth cho local clients, nhưng không chứng minh một subscription cá nhân được phép làm backend dùng chung cho khách trả credit. Vì vậy compliance là blocker cần API/business authorization hoặc xác nhận bằng văn bản, không phải kết luận pháp lý suy đoán.
