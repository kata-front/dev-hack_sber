export type TeamCommand = 'red' | 'blue'
export type ParticipantRole = 'host' | 'participant'
export type GameStatus = 'waiting' | 'active' | 'finished'
export type AnswerStatus = 'correct' | 'incorrect'
export type GameDifficulty = 'easy' | 'medium' | 'hard'

export interface Participant {
  id: string
  name: string
  role: ParticipantRole
  team: TeamCommand | null
  joinedAt: string
}

export interface RoomMessage {
  id: string
  text: string
  createdAt: string
  authorName: string
  command: TeamCommand | null
}

export interface Question {
  id: string
  text: string
  options: string[]
  team: TeamCommand
  selectedOption: number | null
  statusAnswer: AnswerStatus | null
}

export interface Score {
  red: number
  blue: number
}

export interface GameInfo {
  status: GameStatus
  activeTeam: TeamCommand
  activeQuestionIndex: number
  counter: number
  scores: Score
  questions: Question[]
}

export interface Room {
  pin: string
  topic: string
  difficulty: GameDifficulty
  questionsPerTeam: 5 | 6 | 7
  maxParticipants: number
  timerSeconds: number
  status: GameStatus
  createdAt: string
  participants: Participant[]
  messages: RoomMessage[]
  gameInfo: GameInfo | null
}

export interface SessionInfo {
  roomPin: string
  participantId: string
  name: string
  role: ParticipantRole
}

export interface AuthRoomResponse {
  session: SessionInfo
  participant: Participant
  room: Room
}

export interface SessionStateResponse {
  authenticated: boolean
  session?: SessionInfo
  participant?: Participant
  room?: Room
}

export interface CheckPinResponse {
  ok: boolean
  roomPin?: string
}

export interface StartGameResponse {
  room: Room
  generationSource?: 'ai' | 'fallback'
  generationMessage?: string | null
}

export interface KickParticipantResponse {
  room: Room
  kickedParticipant: Participant
}

export interface RestartGameResponse {
  room: Room
}

export interface ApiError {
  detail?: string
}
