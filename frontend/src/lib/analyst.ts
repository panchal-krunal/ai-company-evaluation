import { useSyncExternalStore } from 'react'

/** The analyst's name, recorded on comments, overrides and approvals (until login is added). */
const KEY = 'analyst-name'
const listeners = new Set<() => void>()

function read(): string {
  try {
    return localStorage.getItem(KEY) ?? ''
  } catch {
    return ''
  }
}

export function setAnalystName(name: string) {
  try {
    localStorage.setItem(KEY, name)
  } catch {
    // storage unavailable: the name lasts for this page view only
  }
  listeners.forEach((l) => l())
}

export function useAnalystName(): string {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    read,
    () => '',
  )
}
