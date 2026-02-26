export type startAction = 'join' | 'create' | null

export type LoginResponse = {
    ok: boolean;
    roomId?: number;
}

export type DataFormCreateRoom = {
    roomId: number
    roomName: string
    quizTheme: string
    maxParticipants: number
}

export type InfoRoom = {
  roomId: string,
  roomName: string,
  quizTheme: string,
  maxParticipants: number,
  messages?: Array<{
    command: 'red' | 'blue'
    createdAt: string
    text: string
  }>
  participants?: Array<any>
}