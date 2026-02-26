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

export type TeamCommand = 'red' | 'blue'

export type RoomMessage = {
  command: TeamCommand
  createdAt: string
  text: string
}

export type InfoRoom = {
  roomId: number
  roomName: string
  quizTheme: string
  maxParticipants: number
  team?: TeamCommand
  messages?: RoomMessage[]
  participants?: Array<{
    id: number // id socket
    command: TeamCommand,
    role: 'host' | 'participant'
  }>
}
