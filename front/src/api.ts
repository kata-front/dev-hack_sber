import type {
  AuthRoomResponse,
  CheckPinResponse,
  Room,
  RoomMessage,
  SessionStateResponse,
  StartGameResponse,
} from './types'

const API_BASE = '/api/v1'

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
  })

  if (!response.ok) {
    let detail = 'Request failed'
    try {
      const data = (await response.json()) as { detail?: string | { msg?: string }[] }
      if (typeof data.detail === 'string') {
        detail = data.detail
      } else if (Array.isArray(data.detail) && data.detail[0]?.msg) {
        detail = data.detail[0].msg
      }
    } catch {
      // ignore parse errors and keep default message
    }
    throw new Error(detail)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export const api = {
  getSession(): Promise<SessionStateResponse> {
    return request<SessionStateResponse>('/session', { method: 'GET' })
  },

  logout(): Promise<{ ok: boolean }> {
    return request<{ ok: boolean }>('/session/logout', { method: 'POST' })
  },

  checkPin(pin: string): Promise<CheckPinResponse> {
    return request<CheckPinResponse>('/rooms/check-pin', {
      method: 'POST',
      body: JSON.stringify({ pin }),
    })
  },

  createRoom(payload: {
    hostName: string
    topic: string
    questionsPerTeam: 5 | 6 | 7
    maxParticipants: number
    timerSeconds: number
  }): Promise<AuthRoomResponse> {
    return request<AuthRoomResponse>('/rooms', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  joinRoom(pin: string, payload: { playerName: string }): Promise<AuthRoomResponse> {
    return request<AuthRoomResponse>(`/rooms/${pin}/join`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  getRoom(pin: string): Promise<Room> {
    return request<Room>(`/rooms/${pin}`, { method: 'GET' })
  },

  startGame(pin: string): Promise<StartGameResponse> {
    return request<StartGameResponse>(`/rooms/${pin}/start`, { method: 'POST' })
  },

  submitAnswer(pin: string, optionIndex: number): Promise<{ room: Room }> {
    return request<{ room: Room }>(`/rooms/${pin}/answer`, {
      method: 'POST',
      body: JSON.stringify({ optionIndex }),
    })
  },

  sendMessage(pin: string, text: string): Promise<RoomMessage> {
    return request<RoomMessage>(`/rooms/${pin}/messages`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    })
  },

  leaveRoom(pin: string): Promise<{ ok: boolean }> {
    return request<{ ok: boolean }>(`/rooms/${pin}/leave`, { method: 'POST' })
  },
}
