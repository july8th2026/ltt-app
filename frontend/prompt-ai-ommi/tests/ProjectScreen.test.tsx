import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ProjectScreen } from '../src/ProjectScreen'
import { promptApiBase, setCsrfToken } from '../src/ommiApi'

function reply(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status < 400,
    status,
    json: () => Promise.resolve(body),
  } as Response)
}

const catalog = {
  style: { id: 'style-1', kind: 'style', name: 'Style chọn', body: 'STYLE BODY' },
  meta: { id: 'meta-1', kind: 'meta', name: 'Meta chọn', body: 'META BODY' },
  snippet: { id: 'snippet-1', kind: 'snippet', name: 'Khóa nhân vật', body: 'SNIPPET BODY' },
}

describe('Brief & Director', () => {
  it('gọi API trực tiếp trong locale hiện tại, không qua redirect 302', () => {
    expect(promptApiBase('/en/prompt-ai-ommi')).toBe('/en/prompt-ai-ommi/api')
    expect(promptApiBase('/vi/prompt-ai-ommi')).toBe('/vi/prompt-ai-ommi/api')
    expect(promptApiBase('/prompt-ai-ommi')).toBe('/prompt-ai-ommi/api')
  })

  let revision: number
  let payload: Record<string, unknown>
  let saveBodies: Array<Record<string, unknown>>
  let applyBody: Record<string, unknown> | null

  beforeEach(() => {
    setCsrfToken('csrf')
    revision = 2
    payload = {
      kind: 'production', version: 1,
      brief: {
        title: 'Campaign', story: '', goal: '', audience: '', duration_seconds: 30,
        scene_count: 6, aspect_ratio: '16:9', language: 'vi', style_id: 'cinematic',
        style_custom: '', meta_prompt_id: '', snippet_ids: [],
      },
      resources: [], scenes: [], storyboard: {}, job_refs: [], ui: {},
    }
    saveBodies = []
    applyBody = null
    vi.stubGlobal('fetch', vi.fn((rawUrl: string, init?: RequestInit) => {
      const url = String(rawUrl)
      const method = (init?.method ?? 'GET').toUpperCase()
      if (url.endsWith('/projects') && method === 'GET') {
        return reply({ items: [{ id: 'p1', name: 'Campaign', revision }] })
      }
      if (/\/library\/(style|meta|snippet)\?/.test(url) && method === 'GET') {
        const kind = url.match(/\/library\/(style|meta|snippet)\?/)?.[1] as keyof typeof catalog
        const items = url.includes('catalog=true') ? [{
          ...catalog[kind], is_catalog: true, cloned_from_id: '', archived: false,
          updated_at: '2026-08-11T00:00:00Z',
        }] : []
        return reply({ items, total: items.length, catalog: url.includes('catalog=true'), counts: {} })
      }
      if (url.endsWith('/projects/p1') && method === 'GET') {
        return reply({ id: 'p1', name: 'Campaign', revision, status: 'active', payload,
          updated_at: '2026-08-11T00:00:00Z' })
      }
      if (url.endsWith('/projects/p1') && method === 'PUT') {
        const body = JSON.parse(String(init?.body)) as Record<string, unknown>
        saveBodies.push(body)
        payload = body.payload as Record<string, unknown>
        revision += 1
        return reply({ id: 'p1', name: 'Campaign', revision, status: 'active', payload,
          updated_at: '2026-08-11T00:00:00Z' })
      }
      if (url.endsWith('/projects/p1/preview') && method === 'POST') {
        return reply({ valid: true, checklist: [{ id: 'story', label: 'Nội dung', passed: true }],
          master_prompt: 'MASTER PROMPT WITH SELECTED CATALOG', resource_count: 0,
          scene_count: 6, selections: { style: 'Style chọn', meta: 'Meta chọn',
            snippets: ['Khóa nhân vật'] } })
      }
      if (url.endsWith('/projects/p1/quote') && method === 'POST') {
        return reply({ operation: 'director', credit: 12, scene_count: 6, model: 'gemini-test' })
      }
      if (url.endsWith('/projects/p1/generate') && method === 'POST') {
        return reply({ id: 'job-1', status: 'queued' }, 201)
      }
      if (url.endsWith('/jobs/job-1') && method === 'GET') {
        return reply({ id: 'job-1', status: 'done', progress: 100, progress_msg: '', error: '', result: {} })
      }
      if (url.endsWith('/projects/p1/apply/job-1') && method === 'POST') {
        applyBody = JSON.parse(String(init?.body)) as Record<string, unknown>
        return reply({ id: 'p1', name: 'Campaign', revision: revision + 1,
          status: 'active', payload, updated_at: '2026-08-11T00:00:00Z' })
      }
      return reply({ detail: `Không có route test ${method} ${url}` }, 404)
    }))
  })

  afterEach(() => vi.unstubAllGlobals())

  it('lưu draft hiện tại, dựng preview bằng lựa chọn catalog và áp dụng đúng revision', async () => {
    render(<ProjectScreen mode="brief" />)
    fireEvent.click(await screen.findByRole('button', { name: /Campaign/ }))

    const story = await screen.findByLabelText('Nội dung / câu chuyện')
    fireEvent.change(story, { target: { value: 'Một câu chuyện đủ dài để dựng thành sáu cảnh nhất quán.' } })
    fireEvent.change(screen.getByLabelText('Phong cách'), { target: { value: 'style-1' } })
    fireEvent.change(screen.getByLabelText('Meta Director'), { target: { value: 'meta-1' } })
    fireEvent.click(screen.getByRole('checkbox', { name: /Khóa nhân vật/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Xem trước prompt' }))

    await screen.findByText('MASTER PROMPT WITH SELECTED CATALOG')
    const firstBrief = (saveBodies[0].payload as { brief: Record<string, unknown> }).brief
    expect(firstBrief.story).toContain('đủ dài')
    expect(firstBrief.style_id).toBe('style-1')
    expect(firstBrief.meta_prompt_id).toBe('meta-1')
    expect(firstBrief.snippet_ids).toEqual(['snippet-1'])

    fireEvent.click(screen.getByRole('button', { name: 'Báo giá AI Director' }))
    await screen.findByText('12 credit')
    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận và chạy' }))
    await waitFor(() => expect(applyBody).toEqual({ revision: 4 }))
  })
})
