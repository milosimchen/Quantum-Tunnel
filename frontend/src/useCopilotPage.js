import { useEffect } from 'react'
import { useCopilot } from './CopilotContext'

// Tell the copilot what's on this page. Pass a value that changes when the
// page's relevant state changes (it's compared by JSON, so plain data only).
export function useCopilotPage(page) {
  const { setPageContext } = useCopilot()
  const key = JSON.stringify(page)
  useEffect(() => {
    setPageContext(JSON.parse(key))
  }, [key, setPageContext])
}
