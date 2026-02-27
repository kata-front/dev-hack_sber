import type { TeamCommand } from '../../../shared/types'

export type AdminPanelState = {
  isLobbyLocked: boolean
  isChatMuted: boolean
  areHintsEnabled: boolean
  isPaused: boolean
}

export type AdminPanelActions = {
  toggleLobbyLock: () => void
  toggleChatMuted: () => void
  toggleHintsEnabled: () => void
  togglePause: () => void
  shuffleTeams: () => void
  resetTeams: () => void
}

export type TeamAssignments = Record<number, TeamCommand>
