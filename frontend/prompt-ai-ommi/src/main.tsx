import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { OmmiShell } from './OmmiShell'

const root = document.getElementById('prompt-ai-ommi-root')
if (!root) throw new Error('Missing #prompt-ai-ommi-root')
const csrfToken = root.dataset.csrfToken ?? ''
createRoot(root).render(
  <StrictMode>
    <OmmiShell csrfToken={csrfToken} />
  </StrictMode>,
)
root.setAttribute('aria-busy', 'false')
