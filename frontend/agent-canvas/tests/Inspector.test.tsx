import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Inspector } from '../src/Inspector'
import type { PaletteTool } from '../src/editorState'
import type { CanvasNode } from '../src/workflowApi'

const tool: PaletteTool = { name: 'video.generate', description: 'Video', app_slug: 'video',
  app_name: 'Video', requires: ['api'], returns: { video_key: 'video' }, verifiable: [],
  params_schema: { model: { type: 'model_ref', values: ['mini', 'full'] },
    resolution: { type: 'enum', depends_on: 'model', values: [] } },
  schema_variants: { model: {
    mini: { model: { type: 'model_ref', values: ['mini', 'full'] },
      resolution: { type: 'enum', values: ['480p', '720p'] } },
    full: { model: { type: 'model_ref', values: ['mini', 'full'] },
      resolution: { type: 'enum', values: ['480p', '720p', '4k'] } },
  } } }

afterEach(cleanup)

function Harness({ connect = vi.fn() }: { connect?: (field: string, value: string) => void }) {
  const [node, setNode] = useState<CanvasNode>({ id: 'n1', type: 'tool', position: { x: 0, y: 0 },
    data: { tool: 'video.generate', params: { model: 'mini' }, fanout: 1 } })
  return <Inspector node={node} tool={tool} readOnly={false} csrfToken="test-csrf"
    connections={{ resolution: [{ value: 'n0|size', label: 'n0 · size' }] }} onConnect={connect}
    onChange={data => setNode(current => ({ ...current, data: { ...current.data, ...data } }))} />
}

describe('schema inspector', () => {
  it('switches depends_on enum variants when model changes', () => {
    render(<Harness />)
    expect(screen.queryByRole('option', { name: '4k' })).not.toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', { name: 'model' }), { target: { value: 'full' } })
    expect(screen.getByRole('option', { name: '4k' })).toBeInTheDocument()
  })

  it('offers a keyboard-compatible typed connection choice', () => {
    const connect = vi.fn(); render(<Harness connect={connect} />)
    fireEvent.change(screen.getByRole('combobox', { name: 'Nối dữ liệu từ' }),
      { target: { value: 'n0|size' } })
    expect(connect).toHaveBeenCalledWith('resolution', 'n0|size')
  })
})
