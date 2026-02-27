export type startAction = 'join' | 'create' | null

export type LoginResponse = {
  ok: true;
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

export type Parsicipant = {
  id: number // id socket
  command?: TeamCommand,
  role: 'host' | 'participant'
}

export type StatusGame = 'waiting' | 'active' | 'finished'
export type AnswerStatus = 'correct' | 'incorrect'
export type Question = {
  question: string,
  team: TeamCommand,
  answers: Array<string>
  statusAnswer: AnswerStatus
}

export type GameInfo = {
  status: StatusGame
  activeTeam: TeamCommand
  questions: Array<Question>
  activeQuestionIndex: number
  counter: number
}

export type InfoRoom = {
  roomId: number
  roomName: string
  quizTheme: string
  maxParticipants: number
  messages?: RoomMessage[]
  participants?: Array<Parsicipant>
  gameInfo?: GameInfo
}
