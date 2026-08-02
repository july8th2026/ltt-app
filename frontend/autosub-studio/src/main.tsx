import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { StudioShell } from './StudioShell'

const root = document.getElementById('autosub-studio-root')
if (!root) throw new Error('Missing #autosub-studio-root')
const csrfToken = root.dataset.csrfToken ?? ''
createRoot(root).render(<StrictMode><StudioShell csrfToken={csrfToken}/></StrictMode>)
root.setAttribute('aria-busy', 'false')
