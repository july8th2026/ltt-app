# 03 — Competitor Benchmark: Prompt AI OMMI

## Nguồn chính thức

1. LTX Studio: connected Gen Space, Storyboard, Retake và Elements/character
   consistency — https://ltx.io/blog/ltx-studio-tutorial và
   https://ltx.io/blog/top-ltx-studio-features
2. Google Flow: tạo/animate bằng text, ingredients, frames và reusable references
   — https://support.google.com/flow/answer/16353334?hl=en và
   https://support.google.com/flow/answer/16352836?hl=en
3. Runway: saved references, `@` mention và workspace assets —
   https://help.runwayml.com/hc/en-us/articles/52963720640275-Using-reference-media-to-guide-your-generations
4. Adobe Firefly Boards: style/reference source, consistent panels và animate panel
   — https://helpx.adobe.com/uk/firefly/how-to/create-commercial-storyboard-firefly-boards.html
5. FLORA: canvas/node building blocks và model catalog —
   https://docs.flora.ai/editor/canvas và https://docs.flora.ai/blocks/editor
6. Freepik Spaces: node/connectors, Run Node/Workflow/Downstream, autosave,
   history và result gắn node — https://ru.freepik.com/ai/docs/getting-started-with-spaces,
   https://ru.freepik.com/ai/docs/nodes-and-connectors và
   https://ru.freepik.com/ai/docs/introduction-to-spaces

## Feature parity

| Năng lực | Chuẩn thị trường | OMMI hiện tại | Khoảng cách |
|---|---|---|---|
| Brief → storyboard | guided, connected, editable | backend mạnh, UI rời rạc | Lớn |
| Reference consistency | reusable asset/tag/reference per shot | resource library không gắn được | Rất lớn |
| Per-shot generation | run/retry/result/version tại shot | một phần | Trung bình-lớn |
| Production handoff | panel/shot → image/video | API có, UI thiếu | Rất lớn |
| History/recovery | autosave, version, restore | API rải rác; UI thiếu | Lớn |
| Model choice | intent/model at run, cost visible | không có selector | Lớn |
| Visual orchestration | canvas/blocks/connectors | không có trong OMMI | Có thể hoãn |
| Collaboration/template | reuse/share/team | library cơ bản | Lớn nhưng không MVP blocker |
| Customer simplicity | progressive disclosure | 10 màn hình ngang, meta jargon | Lớn |

## Kết luận benchmark

Không nên sao chép toàn bộ canvas của FLORA/Spaces vào OMMI ngay. Khoảng cách
quan trọng nhất là **kết nối dữ liệu và hành trình**: reference → brief → scene →
generation → output/version/handoff. OMMI đã có nhiều primitive backend nên ưu
tiên nối một studio customer-facing duy nhất, rồi mới cân nhắc canvas nâng cao.
