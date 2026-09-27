import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { editorReducer, emptyDocument } from '../../../editorState'
import { slugCongCu } from '../../../nodeDefinition'
import type { LuatNoiDay, NhomPalette } from '../../../nodeDefinition'
import { taiPalette } from '../../../paletteApi'
import { loadOrCreateWorkflowV3, loadPreferences, loadWorkflowV3, savePreferences,
  saveWorkflowV3, WorkflowConflictError, type Workflow } from '../../../workflowApi'
import type { BangDinhNghia } from '../graph'
import { PHIEN_BAN_TRINH_BAY, type GiaoDien, type PhaLuu } from '../kieu'

/** Nạp · tự lưu · xung đột · bảng node · sở thích — mọi thứ trình soạn cần
 *  để MỞ ĐƯỢC, và vòng lưu giữ nó đồng bộ về sau.
 *
 *  ⭐ VÌ SAO MỘT HOOK, KHÔNG PHẢI BA
 *
 *     Ba cửa (`/palette`, workflow, `/preferences`) đi trong MỘT `Promise.all`
 *     và `phase` chỉ sang `'ready'` khi **cả ba** về. Tách thành ba effect độc
 *     lập là đổi hành vi, không phải dọn dẹp: canvas sẽ vẽ trước khi bảng node
 *     về, và mọi node hiện ra dưới dạng `nutThieu()` trong một nhịp — đúng cái
 *     màn hình "node biến mất rồi hiện lại" mà người dùng đọc là lỗi.
 */
/** Workflow mà TRANG yêu cầu mở, hoặc `''` nếu trang không nói.
 *
 *  🔴 VÌ SAO CÁI NÀY TỒN TẠI: `loadOrCreateWorkflowV3` mở `items[0]` của một
 *     danh sách sắp theo `updated_at DESC`, và trình soạn **tự lưu** — nên
 *     workflow mở ra luôn là workflow sửa gần nhất. Trên giao diện cũ không có
 *     đường nào tới workflow thứ hai (`01_CURRENT_UI_AUDIT.md` §1.1).
 *
 *  ⭐ Đọc từ DOM chứ không từ `location.pathname`: máy chủ là nơi đã lọc theo
 *     chủ sở hữu và trả 404 cho id của người khác (`trang.py::trang_mot_workflow`).
 *     Tự bóc id từ URL trong trình duyệt là đoán lại một việc đã có câu trả lời
 *     đúng, và nó sẽ lệch ngay khi đường dẫn đổi hình.
 */
function idTrangYeuCau(): string {
  const goc = document.querySelector<HTMLElement>('#agent-canvas-root')
  return (goc?.dataset.workflowId ?? '').trim()
}

export function useWorkflowDocument(csrf: string, offline: boolean) {
  const [state, dispatch] = useReducer(editorReducer,
    { document: emptyDocument(), past: [], future: [] })
  const [workflow, setWorkflow] = useState<Workflow>()
  const [nhomPalette, setNhomPalette] = useState<NhomPalette[]>([])
  const [luatNoiDay, setLuatNoiDay] = useState<LuatNoiDay | null>(null)
  const [phase, setPhase] = useState<PhaLuu>('loading')
  const [theme, setTheme] = useState<GiaoDien>('dark')
  //: Giu nguyen de gui tra `/preferences` — palette v3 khong con khai niem
  //  "cong cu chinh" nen khong co cong tac nao doi no nua.
  const [catalogMode, setCatalogMode] = useState<'simple' | 'advanced'>('advanced')
  const [retryNonce, setRetryNonce] = useState(0)
  const autosaveTimer = useRef<number | undefined>(undefined)

  useEffect(() => {
    let active = true
    const id = idTrangYeuCau()
    Promise.all([taiPalette(),
      id ? loadWorkflowV3(id) : loadOrCreateWorkflowV3(csrf),
      loadPreferences()])
      .then(([p, loaded, preferences]) => {
        if (!active) return
        setNhomPalette(p.nhom); setLuatNoiDay(p.luat_noi_day)
        setTheme(preferences.theme); setCatalogMode(preferences.catalog_mode)
        setWorkflow(loaded); dispatch({ type: 'replace', document: loaded.canvas }); setPhase('ready')
      }).catch(() => active && setPhase('error'))
    return () => { active = false }
  }, [csrf])

  // ⏱️ Debounce 800 ms. Đặc tả ở `tests/CanvasShellDacTa.test.tsx` — ba lần gõ
  //    liên tiếp phải gộp thành MỘT lần PUT, mang giá trị CUỐI.
  // ⛔ `workflow` CỐ Ý không nằm trong deps: một lần lưu xong trả về `revision`
  //    mới, mà đổi revision KHÔNG phải một lần sửa của người dùng — để nó vào
  //    deps là một vòng tự lưu vô hạn.
  useEffect(() => {
    if (!workflow || phase === 'loading' || offline) return
    if (JSON.stringify(workflow.canvas) === JSON.stringify(state.document)) return
    autosaveTimer.current = window.setTimeout(async () => {
      setPhase('saving')
      try {
        const saved = await saveWorkflowV3({ ...workflow, canvas: state.document }, csrf)
        setWorkflow(saved); setPhase('saved')
      } catch (error) { setPhase(error instanceof WorkflowConflictError ? 'conflict' : 'error') }
    }, 800)
    return () => { if (autosaveTimer.current) window.clearTimeout(autosaveTimer.current) }
  }, [state.document, csrf, offline, retryNonce]) // eslint-disable-line react-hooks/exhaustive-deps

  // ⭐ Khoa la SLUG cong cu (`image.generate`) vi do la thu `data.tool` giu va
  //    `bien_dich._node` doc. `NodeDefinition.type` mang tien to `app.`.
  const dinhNghia = useMemo(() => {
    const m: BangDinhNghia = new Map()
    for (const n of nhomPalette) for (const x of n.nut) m.set(slugCongCu(x), x)
    return m
  }, [nhomPalette])

  const doiGiaoDien = useCallback((nextTheme: GiaoDien) => {
    setTheme(nextTheme)
    void savePreferences({ theme: nextTheme, catalog_mode: catalogMode,
      presentation_version: PHIEN_BAN_TRINH_BAY }, csrf).catch(() => setPhase('error'))
  }, [catalogMode, csrf])

  const luuTen = useCallback(() => {
    if (!workflow) return
    void saveWorkflowV3({ ...workflow, canvas: state.document }, csrf)
      .then(setWorkflow).catch(() => setPhase('error'))
  }, [workflow, state.document, csrf])

  return { state, dispatch, workflow, setWorkflow, nhomPalette, luatNoiDay,
    phase, setPhase, theme, doiGiaoDien, dinhNghia, autosaveTimer, luuTen,
    thuLuuLai: () => setRetryNonce(value => value + 1) }
}
