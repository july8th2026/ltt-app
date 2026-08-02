import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { CanvasShell } from './CanvasShell'

const root = document.getElementById('agent-canvas-root')
if (!root) throw new Error('Missing #agent-canvas-root')

createRoot(root).render(<StrictMode><CanvasShell /></StrictMode>)
root.setAttribute('aria-busy', 'false')
