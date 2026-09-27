import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { OmmiShell } from './OmmiShell'

const root = document.getElementById('prompt-ai-ommi-root')
if (!root) throw new Error('Missing #prompt-ai-ommi-root')
const csrfToken = root.dataset.csrfToken ?? ''
// Tran so canh do BACKEND khai (`project_schema.MAX_SCENES`). So duoi chi la
// luoi cuoi cho ca `data-` vang; khong phai mot ban khai thu hai.
const maxScenes = Number(root.dataset.maxScenes) || 20
createRoot(root).render(
  <StrictMode>
    <OmmiShell csrfToken={csrfToken} maxScenes={maxScenes} />
  </StrictMode>,
)
root.setAttribute('aria-busy', 'false')
