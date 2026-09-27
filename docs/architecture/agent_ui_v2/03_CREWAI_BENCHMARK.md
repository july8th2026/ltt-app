# CrewAI — UI/UX benchmark (2026-09-27)

Phạm vi: CHỈ UI/UX (thông tin kiến trúc điều hướng, form, trực quan hoá, quan sát vận hành,
human-in-the-loop, sinh bằng AI, giấy phép). KHÔNG bàn ngữ nghĩa runtime/engine (đã có audit khác).

Sources: `docs.crewai.com/en/concepts/flows` (mục Plot Flows), `docs.crewai.com/en/observability/tracing`,
`docs.crewai.com/v1.15.21/en/guides/frontend/human-in-the-loop`, `docs.crewai.com/en/learn/human-input-on-execution`,
`docs-platform.crewai.com/platform/en/features/crew-studio`, GitHub `crewAIInc/crewAI` (repo API + `search_code`
qua `gh search code`, path `lib/crewai/src/crewai/flow/visualization/**`, `docs/edge/en/**`), GitHub
`strnad/CrewAI-Studio` (toàn bộ `app/*.py` đọc qua `gh api repos/.../contents/...`, issue #75), license API
của cả hai repo. Không truy cập được: bên trong CrewAI AMP thật (SaaS đóng, không có tài khoản) — chỉ đọc
trang tiếp thị/docs công khai của AMP.

---

## 1. Kiến trúc thông tin (Agents vs Tasks vs Crews vs Flows)

**CrewAI-Studio (`strnad/CrewAI-Studio`, MIT, cộng đồng)** — app Streamlit thuần, KHÔNG có canvas.
`app/app.py` định nghĩa điều hướng bằng một `st.radio` trong sidebar với đúng 8 mục cấp cao nhất
(nguyên văn từ code, `pages()` dict):

```
Crews · Tools · Agents · Tasks · Knowledge · Kickoff! · Results · Import/export
```

Mỗi mục là một trang riêng render bởi lớp `Page*` tương ứng (`pg_crews.py`, `pg_tools.py`,
`pg_agents.py`, `pg_tasks.py`, `pg_knowledge.py`, `pg_crew_run.py`, `pg_results.py`,
`pg_export_crew.py`). Agents/Tasks không thuộc về một Crew "sở hữu" chúng — chúng là danh sách
phẳng toàn cục, gán n-n vào Crew qua tab: mỗi trang Agents/Tasks có tab "All", "Unassigned", rồi
một tab cho từng Crew hiện có (`pg_agents.py`, `pg_tasks.py`: `tabs = [all, unassigned] + [crew.name
for crew in ss.crews]`). Không có khái niệm "Flow" trong Studio — Flow (decorator `@start`/`@listen`)
là tính năng chỉ có ở code framework (`crewai flow plot`, mục 4), Studio chỉ biết `Crew` (danh sách
Agent + Task tuần tự/song song).

**Crew Studio trong CrewAI AMP (SaaS đóng)** — khác hẳn: theo `docs-platform.crewai.com/platform/en/
features/crew-studio`, đây là bố cục 3 cột — panel trái "AI Thoughts" (luồng suy luận streaming),
canvas giữa vẽ Agent/Task như node nối nhau, panel phải "Resources" kéo-thả. Có CANVAS thật (khác
Studio cộng đồng), gọi là "vibe coding AI Agents" — người dùng vừa kéo-thả node vừa mô tả bằng chat,
hai cách chia sẻ chung state.

**Bài học cho LTT:** (1) Điều hướng phẳng theo *loại đối tượng* (Agents/Tasks/Tools là danh sách toàn
cục, gán n-n vào Crew qua tab) đơn giản hơn cây phân cấp cứng — đáng cân nhắc cho các đối tượng dùng
lại nhiều (tool, agent template). (2) Hai sản phẩm CrewAI cho thấy rõ ràng: form+list (OSS, rẻ, đủ dùng
cho automation cá nhân) và canvas+chat (AMP, trả phí, cho việc trình bày/khám phá) là hai tầng SẢN PHẨM
khác nhau, không phải hai giai đoạn của cùng một UI — LTT nên quyết định sớm sẽ nhắm tầng nào trước khi
thiết kế, thay vì cố làm một UI phục vụ cả hai.

## 2. Form tạo Agent

Nguồn: `strnad/CrewAI-Studio` `app/my_agent.py`, method `MyAgent.draw()`. Không progressive
disclosure — TẤT CẢ field nằm phẳng trong một `st.form` duy nhất, theo đúng thứ tự khai báo:

1. `role` — `st.text_input`
2. `backstory` — `st.text_area`
3. `goal` — `st.text_area`
4. `allow_delegation` — `st.checkbox`
5. `verbose` — `st.checkbox`
6. `cache` — `st.checkbox`
7. `llm_provider_model` — `st.selectbox` (danh sách "provider:model" ghép sẵn)
8. `temperature` — `st.slider` (0.0–1.0)
9. `max_iter` — `st.number_input` (1–100, mặc định 25)
10. `tools` — `st.multiselect` (tên tool + tham số đầu tiên làm nhãn phân biệt, vd `"Search (google.com)"`)
11. `knowledge_source_ids` — `st.multiselect` (chỉ hiện nếu đã có knowledge source nào trong hệ thống)

Không có field `llm` tách biệt kiểu cấu hình nâng cao — chọn model gộp luôn provider (`llm_provider_
model`) và tự suy sang `create_llm()`. Khi xem (không edit), toàn bộ form sập thành một `st.expander`
đóng, tiêu đề = `role` (cắt 60 ký tự) + tên model, có dấu `❗` tiền tố nếu agent invalid (thiếu tool hợp
lệ). Không có wizard nhiều bước, không có tab con trong form — "form" ở đây đúng nghĩa 1 khối, submit
một lần bằng nút Save; Edit/Delete là hai nút ở chế độ xem.

**Bài học cho LTT:** (1) Một danh sách field phẳng, không phân nhóm, là ĐỦ khi số field nhỏ (~11) và
đối tượng "Agent" của CrewAI khá mỏng — LTT không cần build accordion nhiều tầng cho form tương tự
nếu domain object cũng mỏng như vậy; đầu tư progressive disclosure chỉ đáng khi field > ~15-20.
(2) Gộp provider+model thành một lựa chọn duy nhất (thay vì 2 dropdown phụ thuộc) giảm 1 bước quyết
định — đáng học cho form cấu hình LLM nội bộ của LTT (`apps/ltt_llm`). (3) Nhãn tool tự sinh từ tham
số đầu tiên (`"{display_name} ({first_param_value})"`) giải quyết vấn đề "nhiều instance cùng loại tool
trông giống hệt nhau trong multiselect" — pattern nhỏ nhưng cụ thể, đáng chép khi LTT cho phép nhiều
cấu hình cùng loại công cụ.

## 3. Soạn Task

Nguồn: `strnad/CrewAI-Studio` `app/my_task.py`, method `MyTask.draw()`. Cũng một `st.form` phẳng:

1. `description` — `st.text_area`
2. `expected_output` — `st.text_area`
3. `agent` — `st.selectbox` (đúng MỘT agent phụ trách; không hỗ trợ multi-agent per task)
4. `async_execution` — `st.checkbox`
5. `context_from_async_tasks_ids` — `st.multiselect`, options lọc = các task khác có `async_execution=True`
6. `context_from_sync_tasks_ids` — `st.multiselect`, options lọc = các task khác có `async_execution=False`

**Không có canvas/mũi tên nối task→task nào cả.** Phụ thuộc "task→task" (tương đương `context=[...]`
của `crewai.Task`) được biểu diễn thuần bằng HAI Ô MULTISELECT DẠNG DANH SÁCH, tách theo async/sync
(vì API `Task(context=...)` của core framework chấp nhận cả list task đồng bộ lẫn coroutine chưa
resolve, và Studio tách UI theo đó thay vì gộp một danh sách). Nhãn mỗi lựa chọn = 120 ký tự đầu của
`description` task đó — không có ID ngắn gọn, không có xem trước graph phụ thuộc, không cảnh báo vòng
lặp (cycle) ở UI, không kiểm tra tại chỗ khi submit (chỉ `is_valid()` kiểm tra "có agent chưa", không
kiểm tra context có tạo vòng lặp). Task không tồn tại độc lập ngoài Crew về mặt thực thi (crew quyết
định `Process.sequential`/`Process.hierarchical`), nhưng về mặt UI Task vẫn là danh sách phẳng y hệt
Agent (tab All/Unassigned/theo-Crew).

**Bài học cho LTT:** (1) Biểu diễn phụ thuộc bằng multiselect id→text-snippet là giải pháp RẺ, không
cần renderer đồ hoạ, nhưng KHÔNG bắt được lỗi vòng lặp hay hiển thị "chuỗi phụ thuộc dài bao nhiêu" —
nếu LTT copy pattern này, nên thêm validate cycle phía server ngay từ đầu (rẻ hơn nhiều so với vá sau).
(2) Việc tách context theo async/sync ngay ở UI (thay vì một multiset chung) lộ rõ một chi tiết RUNTIME
(coroutine chưa resolve) ra tới tận form — đây là bài học NGƯỢC: đừng để implementation detail của
engine rò vào UI như CrewAI đã làm, LTT nên gộp lại một control "phụ thuộc vào task nào" và xử lý
sync/async ở tầng dưới. (3) Task không có trường "tools" riêng trong Studio (tools đến từ Agent được
gán) — nếu LTT muốn override tool theo từng task, đây là chỗ CrewAI-Studio cố tình đơn giản hoá, không
đáng bắt chước nếu LTT cần override per-task.

## 4. Trực quan hoá Flow (`crewai flow plot`)

Nguồn: `crewAIInc/crewAI` path `lib/crewai/src/crewai/flow/visualization/` (`builder.py`,
`renderers/interactive.py`, `assets/interactive.js`, `assets/interactive_flow.html.j2`) + docs
`docs/edge/en/concepts/flows.mdx` mục "Plot Flows".

- **Cách gọi**: `flow.plot("ten_file")` (Python) hoặc `crewai flow plot` (CLI, trong project đã
  `crewai create flow`) → sinh MỘT file HTML tĩnh, đứng một mình, mở bằng trình duyệt bất kỳ.
- **Thư viện**: KHÔNG dùng pyvis (dù `pyvis` từng xuất hiện trong một cassette test không liên quan
  trực tiếp đến flow-plot). Renderer hiện tại tự build: `builder.py` tính cấu trúc DAG
  (`FlowStructure`, node/edge từ decorator `@start`/`@listen`/`@router`) → `renderers/interactive.py`
  tính toạ độ node theo tầng (`calculate_node_positions`, phân theo `level` = khoảng cách BFS từ node
  `@start`) → render bằng template Jinja2 (`interactive_flow.html.j2`) nhúng JS thuần
  (`interactive.js`) gọi hàm `loadVisCDN()` — tức là vẫn dựa trên thư viện đồ hoạ mạng **vis.js /
  vis-network** tải từ CDN, cộng thêm `lucide` (icon) và `prism.js` (tô màu cú pháp Python) để hiện mã
  nguồn method khi click node (constant `DRAWER.WIDTH = 400` → có drawer/side-panel).
- **Cách vẽ `@start`/`@listen`/`@router`**: mỗi loại node có màu riêng qua biến CSS
  (`--node-bg-start`, `--node-bg-router`, `--node-bg-listen` — mặc định), viền đậm hơn
  (`border_width = 3`) cho `start` và `router`; `router` còn viền màu cam thương hiệu
  (`CREWAI_ORANGE = "#FF5A50"`). Cạnh nối (`edges`) tô theo điều kiện AND/OR trong
  `_definition_condition_parts` (constant `AND_CONDITION`/`OR_CONDITION`), và có phần riêng cho
  `human_feedback.emit` (nếu method Flow có bước human-feedback thì router event xuất phát từ đó thay
  vì `@router` trả về thường).
- **Đọc hay sửa được?** CHỈ ĐỌC. Đây là ảnh chụp cấu trúc tại thời điểm plot (định nghĩa method +
  decorator), không đồng bộ ngược lại code, không cho kéo-thả để sửa flow — khác hẳn canvas
  kéo-thả-sửa-được của Crew Studio (mục 1, 8). Phần "interactive" chỉ là zoom/pan/hover/click-để-xem-
  code-nguồn, không phải edit.

**Bài học cho LTT:** (1) Một file HTML tĩnh tự chứa (Jinja2 template + JS/CSS nhúng, CDN cho lib đồ
hoạ) là cách RẺ để cho người dùng "xem" workflow mà không cần một server riêng — đáng cân nhắc cho một
chế độ export/debug ("xuất sơ đồ") độc lập với canvas chỉnh sửa chính của LTT. (2) Phân biệt rõ bằng
màu + viền cho 3 loại node (`start`/`router`/`listen`) và tô cạnh khác nhau cho AND/OR giúp người đọc
suy luận logic rẽ nhánh mà không cần đọc code — LTT nên áp dụng quy ước màu tương tự nếu có nút rẽ
nhánh (router/condition) trong Agent/Workflow UI riêng. (3) Việc gắn drawer xem mã nguồn khi click node
(dùng `prism.js`) là điểm cộng nhỏ cho debug nhưng KHÔNG đáng chép nguyên xi nếu LTT hướng tới "sửa
trực tiếp trên canvas" — CrewAI cố tình để plot chỉ đọc, LTT có canvas sửa được nên cần một mô hình
đồng bộ hai chiều mà CrewAI OSS không giải quyết.

## 5. Trải nghiệm chạy/test

**CrewAI-Studio (OSS)** — nguồn `app/pg_crew_run.py`, trang "Kickoff!":
- Chọn Crew từ `st.selectbox`, các placeholder `{bien}` tự trích từ description/expected_output/
  role/backstory/goal (regex `\{(.*?)\}`) hiện thành ô nhập text riêng.
- Chạy trong MỘT thread nền (`threading.Thread` chạy `crewai_crew.kickoff()`), giao tiếp qua
  `queue.Queue`; UI chính poll bằng vòng lặp `st.rerun()` + `time.sleep(1)` mỗi giây (không phải
  streaming thật, không WebSocket) — đây là "step callback" giả lập bằng polling stdout.
- **Console output**: một class `ConsoleCapture` chặn stdout của tiến trình, gom vào
  `st.expander("Console output")` hiện bằng `st.code()` — chính là log verbose thô của crewAI, không
  parse thành sự kiện có cấu trúc, có nút "Clear console".
- Không có timeline UI thật (không có danh sách bước theo thời gian, không progress bar theo %) —
  chỉ có spinner (`st.spinner("Running...")`) trong lúc chờ, và console text cuộn.
- Kết thúc: 3 khối kết quả riêng — "Final output" (expanded), "Full output" (raw object), "Tasks
  results" (list từng `TaskOutput.raw` theo task) — cộng nút "Open printable view" render HTML riêng
  qua `window.open()` để in.
- Nút "Stop" gọi `PyThreadState_SetAsyncExc` để bắn `SystemExit` vào thread đang chạy — dừng cứng,
  không phải cancel mềm qua API crewAI.

**CrewAI AMP (Crew Studio, SaaS)** — theo `docs-platform.crewai.com`: có "Execution view" với "event
timeline" và "detailed logs (Details, Messages, Raw Data)" — tức có một khái niệm timeline THẬT (khác
Studio OSS), nhưng tài liệu công khai không mô tả chi tiết bố cục từng dòng sự kiện.

**Bài học cho LTT:** (1) Bắt stdout/console verbose thô và hiện trong một expander cuộn là giải pháp
"đủ dùng" cực rẻ để có run-feedback mà không cần thiết kế event schema — chấp nhận được cho một MVP,
nhưng LTT (đã có job_runner/leases thật) nên làm tốt hơn ngay vì đã có hạ tầng job/step; đừng lùi về
mức "console log thô" khi đã có state máy thật. (2) Polling 1 lần/giây bằng `st.rerun()` là một
anti-pattern UX rõ ràng (giật, tốn CPU, trễ tối đa 1s) — bài học NGƯỢC, LTT nên dùng WebSocket/SSE thật
cho step-by-step nếu muốn "trải nghiệm chạy" mượt hơn CrewAI-Studio. (3) Tách 3 khối kết quả (final /
full / theo-từng-task) là một cấu trúc hiển thị kết quả hợp lý, đáng giữ nguyên ý tưởng: luôn cho xem
"câu trả lời cuối" tách biệt khỏi "log/kết quả từng bước".

## 6. Observability (AMP traces/dashboard)

Nguồn: `docs.crewai.com/en/observability/tracing` (đọc qua WebFetch, không có tài khoản AMP thật nên
không chụp được UI sống — xem mục Giới hạn). Theo tài liệu, dashboard Traces của AMP hiển thị:

- **Agent decisions** — cách agent suy luận/quyết định qua từng bước.
- **Task execution timeline** — biểu diễn trực quan thứ tự + phụ thuộc giữa các task đã chạy.
- **Tool usage** — tool nào được gọi và kết quả trả về.
- **LLM calls** — từng lời gọi model, gồm cả prompt lẫn response.
- **Performance metrics** — thời gian thực thi, số token, chi phí ước tính (token/cost lấy từ
  trường kiểu `gen_ai.usage.*` theo chuẩn OpenTelemetry GenAI semantic conventions mà bài viết
  openobserve.ai mô tả — CrewAI dùng OpenTelemetry cho tracing nền, AMP là nơi hiển thị).
- **Error tracking** — lỗi + stack trace chi tiết theo từng span.
- Trace chỉ lên AMP sau khi người dùng đồng ý upload ("explicit user consent to upload") — có nghĩa
  tracing mặc định không tự động gửi dữ liệu ra ngoài môi trường chạy.

Tài liệu công khai KHÔNG cho thấy ảnh chụp màn hình cụ thể hay tên cột chính xác của bảng — chỉ mô tả
bằng văn bản các nhóm dữ liệu trên. Không xác minh được bố cục panel thật (số lượng, vị trí, có filter
theo agent/task không).

**Bài học cho LTT:** (1) Việc AMP dựa trên chuẩn OpenTelemetry GenAI semantic conventions (thay vì tự
định nghĩa schema riêng) là điều đáng học nhất ở mục này: nếu LTT muốn observability cho lớp Agent/
Workflow mới, nên map field theo chuẩn `gen_ai.*` ngay từ đầu để có thể cắm vào backend tracing có sẵn
(Jaeger, Tempo, Datadog...) thay vì tự chế. (2) Yêu cầu "đồng ý rõ ràng trước khi upload trace" là một
mẫu hình về quyền riêng tư đáng copy cho một nền tảng đa người dùng như LTT — trace có thể chứa dữ liệu
khách hàng nhạy cảm (prompt/response thật). (3) Vì không xác minh được bố cục panel thật, LTT không nên
copy nguyên UI dashboard của AMP mà chỉ nên copy MÔ HÌNH DỮ LIỆU (agent/task/tool/llm-call/error như
5 loại span trên).

## 7. Human-in-the-loop UX

- **CrewAI OSS, cấp Task (`human_input=True`)** — `docs.crewai.com/en/learn/human-input-on-execution`:
  "the agent prompts the user for input before delivering its final answer" — tài liệu KHÔNG nói rõ
  cơ chế UI cụ thể (CLI input() thô hay modal); dựa trên bản chất CLI-first của crewAI OSS, đây gần
  chắc là một `input()` chặn ở terminal, không phải widget đồ hoạ.
- **CrewAI-Studio (cộng đồng, Streamlit)** — tìm `human_input` trong toàn bộ repo qua
  `gh search code "human_input" repo:strnad/CrewAI-Studio`: KHÔNG có kết quả nào. Studio không surface
  `human_input=True` bằng bất kỳ widget nào — issue mở **#75 "Human as a tool"** (từ 2025-04-02, vẫn
  OPEN tại thời điểm khảo sát 2026-09-27) xác nhận đây là tính năng còn thiếu, người dùng cộng đồng
  đang xin bổ sung.
- **CrewAI AMP, cấp Flow** — `docs.crewai.com/v1.15.21/en/guides/frontend/human-in-the-loop`: đây MỚI
  là cơ chế human-in-the-loop có tài liệu rõ nhất, nhưng nó là một **SDK/hook cho frontend riêng của
  khách hàng**, không phải một widget dựng sẵn trong AMP:
  - Agent gọi một tool do frontend đăng ký (`frontend-registered action`) → runtime FLOW PAUSE tại
    lời gọi tool đó.
  - Hook `useHumanInTheLoop` trả về `args` (tham số model đã sinh ra, vd danh sách `steps` đề xuất),
    `status` (bằng `"executing"` nghĩa là đang chờ), và hàm `respond(value)` để resume.
  - Nguyên văn tài liệu: *"When the agent calls the tool, your component appears; when the user acts,
    you call `respond()` to resume the agent."*
  - **Không có widget dựng sẵn** — ví dụ minh hoạ (`StepReview`) chỉ là template, đội frontend phải tự
    xây UI approve/modify/reject.

**Bài học cho LTT:** (1) Cả ba tầng của CrewAI đều KHÔNG có một widget human-in-the-loop dựng sẵn,
tổng quát — kể cả ở AMP trả phí, đây vẫn là "hook + tự xây UI". Đây là khoảng trống rõ ràng nhất trong
toàn bộ hệ sinh thái CrewAI: nếu LTT xây được MỘT component chuẩn (approve/reject/modify) dùng lại
được cho mọi loại action nhạy cảm, đó là lợi thế cạnh tranh thật, không phải việc "đuổi kịp" CrewAI.
(2) Mẫu `args/status/respond()` — pause tại đúng lời gọi tool, expose y nguyên tham số đề xuất, resume
bằng một hàm gọi lại — là một hợp đồng API sạch, đáng chép cho core (không phải UI): LTT nên định nghĩa
một "pause point" tương tự trong `job_runner.py`/`leases.py` thay vì để mỗi tool tự chế cách dừng riêng.
(3) Việc Studio cộng đồng bỏ qua hẳn `human_input` (issue #75 mở >1 năm không ai làm) cho thấy tính
năng này tốn công làm UI đúng cách — LTT nên coi human-in-the-loop UI là hạng mục ưu tiên thiết kế sớm,
không phải thứ "thêm sau" như cộng đồng CrewAI đã để trôi.

## 8. Sinh bằng AI (AI-assisted authoring)

- **CrewAI-Studio (cộng đồng)**: KHÔNG có tính năng sinh crew/agent từ prompt tự nhiên. Toàn bộ tạo
  mới đi qua nút "Create agent"/"Create task" rồi điền form thủ công (mục 2, 3) — xác nhận qua đọc
  trực tiếp `pg_agents.py`/`pg_tasks.py`/`my_agent.py`/`my_task.py`: không có import nào tới một LLM
  để sinh cấu hình, chỉ có `create_llm()` dùng để CHẠY agent, không dùng để soạn agent.
- **Crew Studio trong CrewAI AMP (SaaS)**: CÓ, đây chính là tính năng cốt lõi của Crew Studio —
  `docs-platform.crewai.com/platform/en/features/crew-studio`: "Describe the automation you want; the
  AI generates agents, tasks, and tools" — người dùng gõ mô tả bằng chat, AI sinh trực tiếp node lên
  canvas (Agent/Task/Tool), trợ lý còn "hỏi lại để làm rõ role và định nghĩa task"
  ("clarifies requirements by asking follow-up questions to refine agent roles and task definitions").
  Có hỗ trợ nhập bằng giọng nói (icon micro).
- **Preview/diff hay áp dụng thẳng?** Theo tài liệu công khai đọc được: **KHÔNG có bước preview/diff
  tường minh trước khi áp dụng** — AI sinh thẳng node lên canvas đang mở (canvas ↔ chat "chia sẻ
  chung state", nghĩa là một bên sửa thì bên kia thấy ngay). Không có mô tả nút "Apply changes" hay
  "review before commit" nào trong tài liệu đã fetch. Vì canvas vẫn ở dạng node có thể xoá/sửa tay sau
  đó, cơ chế "preview" trên thực tế CHÍNH LÀ canvas — nhưng đây là suy luận từ mô tả tài liệu, không
  phải xác nhận trực tiếp có step "duyệt trước khi ghi".

**Bài học cho LTT:** (1) CrewAI AMP áp dụng thay đổi do AI sinh ra TRỰC TIẾP lên canvas sống, dựa vào
việc canvas vốn đã cho sửa/xoá tay ngay sau đó để "tự sửa sai" — đây là một lựa chọn UX chấp nhận được
CHỈ KHI người dùng luôn thấy toàn bộ canvas sau mỗi lượt sinh (không có phần nào ẩn/gộp). Nếu LTT làm
tính năng tương tự cho Agent/Workflow, nên cân nhắc một bước diff rõ ràng hơn AMP — nhất là vì LTT có
`credit.py`/`jobs.py` thật, một lần AI-generate sai có thể tạo ra workflow tốn credit thật khi chạy thử.
(2) "Hỏi lại để làm rõ" trước khi sinh (thay vì đoán và sinh luôn) là mẫu hình đáng học độc lập với
canvas — áp dụng được cả cho một form-based flow (chatbot hỏi thêm trước khi điền form hộ người dùng).
(3) Vì đây là tính năng trả phí, đóng, LTT không thể sao chép chi tiết triển khai — chỉ nên học Ý TƯỞNG
"chat và canvas chia sẻ trạng thái" như một yêu cầu kiến trúc (state đơn, hai view), không phải chép
UI cụ thể.

## 9. Giấy phép

Cả hai repo xác minh qua GitHub REST API (`gh api repos/<owner>/<repo>`, field `license`) VÀ đọc trực
tiếp nội dung file license:

- **`crewAIInc/crewAI`** — SPDX `MIT`. File `LICENSE` ở gốc repo, nguyên văn phần đầu:
  > "Copyright (c) 2025 crewAI, Inc.
  > Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
  > associated documentation files (the "Software"), to deal in the Software without restriction,
  > including without limitation the rights to use, copy, modify, merge, publish, distribute,
  > sublicense, and/or sell copies of the Software..."
- **`strnad/CrewAI-Studio`** — SPDX `MIT` (API báo `license.key: "mit"`; file thực tế tên là
  **`LICENCE`** — chính tả Anh, không phải `LICENSE`, dễ bỏ sót khi grep). Nguyên văn phần đầu:
  > "MIT License
  > Copyright (c) 2024 Jakub Strnad
  > Permission is hereby granted, free of charge, to any person obtaining a copy of this software..."

**Kết luận pháp lý cho LTT**: MIT ở cả hai cho phép **PORT trực tiếp mã nguồn** (copy, sửa, đóng gói
lại, kể cả trong sản phẩm thương mại đóng nguồn), miễn giữ lại thông báo bản quyền + giấy phép gốc
trong bản phân phối có chứa mã đó (điều kiện MIT duy nhất). Không có nghĩa vụ copyleft, không cần
open-source lại phần LTT tự viết thêm. Vẫn cần: (a) nếu port nguyên khối file/hàm, giữ header bản
quyền gốc hoặc dẫn nguồn trong NOTICE nội bộ; (b) không dùng tên/logo "CrewAI" cho sản phẩm LTT (MIT
không cấp quyền thương hiệu — đây là giới hạn thông thường, không đọc thấy điều khoản trademark riêng
trong hai file LICENSE/LICENCE này).

Lưu ý: **CrewAI AMP** (SaaS đóng, `crewai.com/amp`) không có mã nguồn công khai để xét giấy phép — chỉ
crewAI framework (thư viện Python) và CrewAI-Studio (giao diện cộng đồng) là mã mở, MIT.

**Bài học cho LTT:** (1) LTT có quyền port thẳng các đoạn UI Streamlit của CrewAI-Studio (form Agent/
Task, cơ chế console-capture, generate printable view...) làm điểm khởi đầu nếu muốn một bản MVP nhanh,
miễn giữ chú thích bản quyền — rẻ hơn nhiều so với tự viết lại từ đầu các phần cơ học (form, luồng
thread/queue chạy nền). (2) Vì AMP đóng nguồn, MỌI thứ học được ở mục 1/6/8 về AMP chỉ là PATTERN
(ý tưởng kiến trúc), không có dòng code nào để port — khác hẳn với CrewAI-Studio nơi có thể port thật.
(3) Luôn kiểm tên file license thực tế (ở đây là `LICENCE` không phải `LICENSE`) trước khi kết luận
"không có license" — một lần dò `contents/LICENSE` trả 404 gần như khiến kết luận sai.

## Bảng chấm 0-5

Thang chấm áp cho HỆ SINH THÁI CrewAI nói chung (ghi rõ Studio OSS hay AMP quyết định điểm khi khác biệt).

| Tiêu chí | Điểm | Lý do (một mệnh đề) |
|---|---|---|
| Agent authoring UX | 3/5 | Form phẳng đủ trường (role/goal/backstory/tools/llm/max_iter/delegation) nhưng không progressive disclosure và validate tối thiểu (chỉ kiểm tool hợp lệ, không kiểm role/goal trống có ý nghĩa) |
| Task/flow visualization | 2/5 | Task→Task chỉ là 2 multiselect theo id (không đồ hoạ, không phát hiện vòng lặp); Flow có đồ thị vis.js đẹp nhưng chỉ-đọc và tách rời hẳn khỏi UI soạn Task/Crew |
| Run/test UX | 2/5 | Studio OSS chỉ có console log thô + poll 1 giây (không streaming thật); AMP có "event timeline" nhưng không xác minh được chi tiết |
| Observability | 3/5 | AMP map theo chuẩn OpenTelemetry GenAI (điểm cộng kiến trúc) nhưng UI dashboard thật không xác minh được (đóng SaaS) |
| Human-in-loop UX | 1/5 | Không tầng nào (OSS Task-level, Studio cộng đồng, hay AMP Flow-level) có widget dựng sẵn; AMP chỉ cấp hook, cộng đồng thậm chí chưa làm (issue #75 mở >1 năm) |
| AI-assisted authoring | 3/5 | Có thật ở AMP (chat sinh node lên canvas, hỏi lại làm rõ) nhưng không thấy bước preview/diff tường minh trước khi ghi; OSS/Studio cộng đồng không có gì |
| Information architecture | 3/5 | Điều hướng phẳng theo loại đối tượng (Agents/Tasks/Tools) rõ ràng, dễ theo ở quy mô nhỏ, nhưng không biểu diễn được quan hệ Crew↔Agent↔Task khi số lượng crew lớn (chỉ có tab, không có tìm kiếm/lọc) |

## Giới hạn của khảo sát này

- **CrewAI AMP là SaaS đóng, không có tài khoản để đăng nhập thật** — mọi mô tả về AMP (Crew Studio
  canvas, Traces dashboard, Execution view) đến từ trang tiếp thị/docs công khai
  (`docs-platform.crewai.com`, `docs.crewai.com/en/observability/tracing`,
  `docs.crewai.com/v1.15.21/en/guides/frontend/human-in-the-loop`), KHÔNG phải quan sát trực tiếp giao
  diện đang chạy. Không có ảnh chụp màn hình thật nào được xem — chỉ có mô tả bằng văn bản của chính
  CrewAI, có thể phóng đại hoặc lược bớt nhược điểm.
- Không dùng Playwright/trình duyệt thật để thao tác CrewAI-Studio cộng đồng (dù có thể tự triển khai
  local) — do đây là audit UI/UX của SẢN PHẨM BÊN THỨ BA cho một tài liệu quy hoạch (planning doc),
  không phải kiểm tra GUI của chính LTTSTUDIOSAPP, nên đọc mã nguồn Streamlit trực tiếp (chính xác
  100% về field/logic, vì đó chính là mã sinh UI) được coi là đủ và tiết kiệm hơn dựng môi trường chạy
  Streamlit + Playwright chỉ để xác nhận lại đúng những gì mã nguồn đã nói.
- **Không xác minh được** cơ chế UI cụ thể của `human_input=True` ở crewAI OSS thuần (CLI `input()` hay
  khác) — tài liệu không nói rõ, và không có môi trường CLI crewAI thật để tái hiện.
- **Không xác minh được** bố cục chính xác (số cột, tên field) của bảng Traces trong AMP dashboard —
  tài liệu công khai mô tả bằng gạch đầu dòng văn bản, không có ảnh chụp màn hình được trích trong nội
  dung fetch được.
- **Không xác minh được** liệu Crew Studio (AMP) có bước "preview/diff trước khi áp dụng" thay đổi do
  AI sinh ra hay không — suy luận "áp dụng thẳng lên canvas sống" dựa trên việc tài liệu không nhắc gì
  đến bước duyệt, không phải một phủ định tường minh đã đọc thấy.
- Không tìm/không có UI repo chính thức nào khác của CrewAI ngoài `strnad/CrewAI-Studio` (một dự án
  CỘNG ĐỒNG, không phải do crewAI Inc. duy trì) — không loại trừ khả năng có UI mã nguồn mở khác chưa
  được tìm thấy qua `gh search code`/`WebSearch` trong phạm vi thời gian khảo sát.
- Không đọc lại toàn bộ lịch sử phiên bản `crewai flow plot` (đổi từ pyvis/networkx sang vis.js tự
  build ở phiên bản nào, khi nào) — chỉ xác nhận trạng thái HIỆN TẠI của code trên nhánh mặc định.
