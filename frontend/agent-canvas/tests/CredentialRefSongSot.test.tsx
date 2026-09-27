// `credential_ref` phai SONG SOT qua vong tron doi tai lieu, va phai o MUC TREN
// CUNG cua mot buoc.
//
// ## Vi sao co tep nay
//
// Lan UI-5 dung `credential_ref` de mo khoa 33 node (27 -> 60 node publish
// duoc), nhung ho ⛔ khong duoc sua `workflowApi.ts` (so dung chung S4) nen ho
// khai mot kieu CUC BO:
//
//     export type BuocCoKetNoi = CanvasNode & { credential_ref?: string }
//
// ⇒ `CanvasNode` — kieu ma CA trinh soan dung — ⛔ khong he biet truong nay ton
//   tai. Mot kieu khong biet ve mot truong thi ⛔ khong ai duoc canh bao khi mot
//   phep bien doi danh roi no.
//
// ## 🔴 Va cho de roi la mot cho NOI HAI MODULE
//
// `platform_core/workflow/bien_dich.py` doc `n.get("credential_ref")` o **MUC
// TREN CUNG** cua node (ba cho: dong 560, 569, 648) — ⛔ KHONG duoi `data`.
// Neu trinh soan ghi no vao `data.credential_ref`, bien dich doc ra rong, node
// bi tu choi `credential_thieu`, va ⛔ khong mot loi bien dich TypeScript nao
// xuat hien: `data` la `Record<string, unknown>`, nhan moi khoa.
//
// ⇒ Do la cung mot hinh dang voi ba lan `canvas_to_plan()` vut cong di trong im
//   lang. Bat bien phai nam o BIEN, ⛔ khong nam trong y dinh cua nguoi viet.
import { describe, expect, it } from 'vitest'
import { fromV3, normalizeCanvas, toV3 } from '../src/workflowApi'
import type { CanvasDocument, CanvasDocumentV3, CanvasNode } from '../src/workflowApi'

const REF = 'cred_abc123'

// ── Phep do o TANG KIEU ──────────────────────────────────────────────────────
//
// 🔴 VI SAO MOT DONG NHU THE NAY, thay vi tin vao `credential_ref: REF` trong
//    `buoc()` ben duoi.
//
// Ban dau toi khang dinh *"neu `CanvasNode` chua khai truong nay thi `tsc` do o
// `buoc()`"*. **Sai.** `buoc()` tra ve mot object literal co `...ghiDe` o CUOI,
// va mot spread o cuoi lam TypeScript **tat kiem tra thuoc tinh du** — nen dong
// `credential_ref: REF` di qua ma ⛔ khong mot canh bao nao. Do luc ay:
// `CanvasNode` ⛔ KHONG co truong, tep NAY co trong pham vi tsc (11 tham chieu),
// va `tsc --noEmit` van **XANH**.
//
// ⇒ Va `vitest` thi cang khong the do: no ⛔ khong bao gio kiem kieu. Bay bai o
//   tep nay **deu xanh** trong khi kieu con thieu — mot phep do chay dung, ket
//   qua dung, tra loi mot cau KHAC.
//
// Dong duoi day thi do duoc: truy cap thuoc tinh tren mot gia tri DA CO KIEU
// `CanvasNode` ⇒ thieu truong la loi bien dich `TS2339`, ⛔ khong co duong lach.
// ⚠️ PHAI la mot khang dinh o TANG KIEU THUAN (`type ...`), ⛔ khong phai mot
//    bieu thuc. Ban dau toi viet:
//        const _x: string|undefined = (undefined as unknown as CanvasNode).credential_ref
//    No kiem kieu dung — nhung no CHAY, va luc chay no la `undefined.credential_ref`
//    ⇒ `TypeError` lam ca TEP test khong nap duoc. `vitest` bao *"1 failed"* o
//    muc TEP trong khi so bai van `238 passed`: mot tep chet lang le trong y het
//    mot tep khong ton tai.
// ⇒ Truy cap chi muc o tang kieu thi thieu truong la loi `TS2339`/`TS2339`-ho,
//   va no phat sinh **0 dong JavaScript**.
type _KIEU_PHAI_KHAI_CREDENTIAL_REF = CanvasNode['credential_ref']

function buoc(ghiDe: Partial<CanvasNode> = {}): CanvasNode {
  return {
    id: 'n1', type: 'tool', position: { x: 0, y: 0 },
    data: { tool: 'app.youtube.upload', params: {} },
    credential_ref: REF,
    ...ghiDe,
  }
}

function taiLieuV2(nodes: CanvasNode[]): CanvasDocument {
  return {
    version: 2, goal: '', budget_max_credit: 0, active_page_id: 'p1',
    pages: [{
      id: 'p1', name: '', nodes, edges: [],
      viewport: { x: 0, y: 0, zoom: 1 },
      frames: [], notes: [], comments: [],
      view: { grid: true, connections: true, minimap: true },
    }],
  } as unknown as CanvasDocument
}

describe('credential_ref song sot qua vong doi tai lieu', () => {
  it('KIEU `CanvasNode` khai `credential_ref` — khong can kieu cuc bo', () => {
    // ⚠️ Bai NAY chi do hanh vi luc chay. Menh de ve KIEU duoc do bang
    //    `_KIEU_PHAI_KHAI_CREDENTIAL_REF` o dau tep + `npx tsc --noEmit` —
    //    `vitest` ⛔ khong bao gio kiem kieu, nen no ⛔ khong the la nhan chung
    //    cho mot loi hua ve kieu.
    const n = buoc()
    expect(n.credential_ref).toBe(REF)
  })

  it('o MUC TREN CUNG, ⛔ KHONG duoi `data`', () => {
    const n = buoc()
    expect(n.credential_ref).toBe(REF)
    // 🔴 Ve doi chung. `bien_dich` doc muc tren cung; mot ban va ghi vao `data`
    //    se lam bai tren xanh ma node van bi tu choi `credential_thieu`.
    expect((n.data as Record<string, unknown>).credential_ref).toBeUndefined()
  })

  it('song sot qua `toV3`', () => {
    const v3 = toV3(taiLieuV2([buoc()]))
    expect(v3.pages[0].nodes[0].credential_ref).toBe(REF)
  })

  it('song sot qua `fromV3`', () => {
    const v3 = toV3(taiLieuV2([buoc()])) as CanvasDocumentV3
    expect(fromV3(v3).pages[0].nodes[0].credential_ref).toBe(REF)
  })

  it('song sot qua `normalizeCanvas` (duong tai lieu v1 cu)', () => {
    // ⚠️ Duong nay de roi truong nhat: `normalizeCanvas` DUNG lai mot tai lieu
    //    v2 tu mot tai lieu v1 phang. Neu no liet ke tung truong cua node thay
    //    vi truyen ca mang, `credential_ref` se bien mat im lang.
    const v1 = { version: 1, goal: '', budget_max_credit: 0,
                 nodes: [buoc()], edges: [],
                 viewport: { x: 0, y: 0, zoom: 1 } }
    const v2 = normalizeCanvas(v1 as unknown as CanvasDocument)
    expect(v2.pages[0].nodes[0].credential_ref).toBe(REF)
  })

  it('vong TRON (v2 -> v3 -> v2) giu nguyen ref', () => {
    const goc = taiLieuV2([buoc({ id: 'a' }), buoc({ id: 'b', credential_ref: undefined })])
    const ve = fromV3(toV3(goc) as CanvasDocumentV3)
    expect(ve.pages[0].nodes.map(n => n.credential_ref)).toEqual([REF, undefined])
  })

  it('buoc KHONG co ket noi thi truong VANG, ⛔ khong phai chuoi rong', () => {
    // ⭐ `undefined` va `''` la HAI trang thai khac nhau o bien nay:
    //    `bien_dich` doi `str(n.get("credential_ref") or "")`, nen ca hai deu
    //    thanh `''` o may chu — nhung o trinh soan, `''` nghia la *nguoi dung da
    //    xoa ket noi*, con vang nghia la *buoc nay chua bao gio can ket noi*.
    //    Gop hai thu do vao mot gia tri lam mat kha nang phan biet.
    const n = buoc({ credential_ref: undefined })
    expect('credential_ref' in n).toBe(true)   // khai tuong minh la `undefined`
    expect(n.credential_ref).toBeUndefined()
  })
})
