export function createWebSocket(taskId, onMessage, onClose) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const url = `${protocol}//${host}/ws/progress/${taskId}`

  let ws = null
  let retryCount = 0
  const maxRetries = 5
  let closed = false

  function connect() {
    ws = new WebSocket(url)

    ws.onopen = () => {
      retryCount = 0
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (e) {
        console.error('WebSocket message parse error:', e)
      }
    }

    ws.onclose = (event) => {
      if (closed) return
      if (retryCount < maxRetries) {
        retryCount++
        setTimeout(() => connect(), 1000 * retryCount)
      } else {
        onClose && onClose(event)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  connect()

  return {
    close() {
      closed = true
      if (ws) ws.close()
    }
  }
}
