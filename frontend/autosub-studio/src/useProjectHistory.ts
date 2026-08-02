import { useCallback, useEffect, useRef, useState } from 'react'
import type { StudioProject } from './studioApi'

const LIMIT = 80

export function useProjectHistory(initial: StudioProject | null,
                                  apply: (value: StudioProject) => void) {
  const past = useRef<StudioProject[]>([])
  const future = useRef<StudioProject[]>([])
  const [version, setVersion] = useState(0)
  const initialId = useRef('')

  useEffect(() => {
    if (initial && initial.id !== initialId.current) {
      initialId.current = initial.id; past.current = []; future.current = []
      setVersion(value => value + 1)
    }
  }, [initial])

  const record = useCallback((before: StudioProject) => {
    past.current.push(structuredClone(before))
    if (past.current.length > LIMIT) past.current.shift()
    future.current = []; setVersion(value => value + 1)
  }, [])

  const undo = useCallback((current: StudioProject | null) => {
    const previous = past.current.pop(); if (!previous || !current) return
    future.current.push(structuredClone(current)); apply(previous)
    setVersion(value => value + 1)
  }, [apply])

  const redo = useCallback((current: StudioProject | null) => {
    const next = future.current.pop(); if (!next || !current) return
    past.current.push(structuredClone(current)); apply(next)
    setVersion(value => value + 1)
  }, [apply])

  return { record, undo, redo, canUndo: version >= 0 && past.current.length > 0,
    canRedo: version >= 0 && future.current.length > 0 }
}
