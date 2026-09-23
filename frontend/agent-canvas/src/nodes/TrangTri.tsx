// Node TRANG TRI: frame, sticky note, comment.
//
// ⭐ Chung khong phai node cua do thi — `bien_dich.py` khong bao gio thay
//    chung, va chung khong co cong, khong co tham so, khong co gia. Chung o
//    day vi React Flow ve moi thu bang mot `nodeTypes`.
//
// ⛔ Khong mot ten app hay ten tool nao duoc phep xuat hien trong tep nay: no
//    ve `name`/`text` do nguoi dung go, khong tra mot bang nao.
import type { NodeProps } from '@xyflow/react'

export function FrameNode({ data }: NodeProps) {
  const typed = data as { name?: string; count?: number }
  return <section className="canvas-frame-node" aria-label={`Frame ${typed.name ?? ''}`}>
    <header><strong>{typed.name ?? 'Frame'}</strong><span>{typed.count ?? 0} node</span></header>
  </section>
}

export function AnnotationNode({ data }: NodeProps) {
  const typed = data as { kind?: 'note' | 'comment'; text?: string }
  return <article className={`canvas-annotation-node ${typed.kind ?? 'note'}`}
    aria-label={`${typed.kind === 'comment' ? 'Comment' : 'Sticky note'} ${typed.text ?? ''}`}>
    <small>{typed.kind === 'comment' ? 'COMMENT' : 'NOTE'}</small>
    <p>{typed.text}</p>
  </article>
}
