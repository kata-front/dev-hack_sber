import { useCallback, useEffect, useMemo, useRef } from 'react'
import type { Parsicipant, RoomMessage, TeamCommand } from '../../../shared/types'
import { socketService } from '../../../shared/socketServise'
import { useAppDispatch } from '../../../shared/redux'
import { socketApi } from '../socketApi'
import type {
  AdminPanelActions,
  AdminPanelState,
  TeamAssignments,
} from '../adminPanel/adminTypes'

const ADMIN_MESSAGE_PREFIX = '__admin__:'

type AdminCommand =
  | { type: 'lobby_lock'; value: boolean }
  | { type: 'chat_muted'; value: boolean }
  | { type: 'hints_enabled'; value: boolean }
  | { type: 'pause'; value: boolean }
  | { type: 'shuffle_teams'; assignments: TeamAssignments }
  | { type: 'reset_teams'; assignments: TeamAssignments }

const INITIAL_ADMIN_STATE: AdminPanelState = {
  isLobbyLocked: false,
  isChatMuted: false,
  areHintsEnabled: true,
  isPaused: false,
}

const parseAdminCommand = (text: string): AdminCommand | null => {
  if (!text.startsWith(ADMIN_MESSAGE_PREFIX)) return null
  try {
    return JSON.parse(text.slice(ADMIN_MESSAGE_PREFIX.length)) as AdminCommand
  } catch {
    return null
  }
}

const buildAdminMessage = (command: AdminCommand) =>
  `${ADMIN_MESSAGE_PREFIX}${JSON.stringify(command)}`

const buildAlternatingAssignments = (participants: Parsicipant[]): TeamAssignments => {
  const sorted = [...participants].sort((a, b) => a.id - b.id)
  const assignments: TeamAssignments = {}
  sorted.forEach((participant, index) => {
    assignments[participant.id] = index % 2 === 0 ? 'red' : 'blue'
  })
  return assignments
}

const buildShuffledAssignments = (participants: Parsicipant[]): TeamAssignments => {
  const shuffled = [...participants]
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1))
    const temp = shuffled[index]
    shuffled[index] = shuffled[swapIndex]
    shuffled[swapIndex] = temp
  }
  const assignments: TeamAssignments = {}
  shuffled.forEach((participant, index) => {
    assignments[participant.id] = index % 2 === 0 ? 'red' : 'blue'
  })
  return assignments
}

const deriveStateFromMessages = (messages: RoomMessage[]): AdminPanelState =>
  messages.reduce<AdminPanelState>((state, message) => {
    const command = parseAdminCommand(message.text)
    if (!command) return state

    switch (command.type) {
      case 'lobby_lock':
        return { ...state, isLobbyLocked: command.value }
      case 'chat_muted':
        return { ...state, isChatMuted: command.value }
      case 'hints_enabled':
        return { ...state, areHintsEnabled: command.value }
      case 'pause':
        return { ...state, isPaused: command.value }
      default:
        return state
    }
  }, INITIAL_ADMIN_STATE)

type UseAdminControlsParams = {
  roomId: number | null
  canInitRoom: boolean
  isHost: boolean
  team: TeamCommand
  messages: RoomMessage[]
  participants?: Parsicipant[]
  roomQueryEndpoint: 'initCreatingRoom' | 'initJoiningRoom'
  selfParticipantId: number | null
}

export const useAdminControls = ({
  roomId,
  canInitRoom,
  isHost,
  team,
  messages,
  participants,
  roomQueryEndpoint,
  selfParticipantId,
}: UseAdminControlsParams) => {
  const dispatch = useAppDispatch()
  const state = useMemo(() => deriveStateFromMessages(messages), [messages])
  const lastProcessedIndexRef = useRef(0)

  const applyAssignments = useCallback(
    (assignments: TeamAssignments) => {
      if (!roomId || !canInitRoom) return

      dispatch(
        socketApi.util.updateQueryData(roomQueryEndpoint, roomId, (draft) => {
          if (!draft?.participants) return
          draft.participants = draft.participants.map((participant) => ({
            ...participant,
            command: assignments[participant.id] ?? participant.command,
          }))

          if (selfParticipantId && assignments[selfParticipantId]) {
            ;(draft as { team?: TeamCommand }).team = assignments[selfParticipantId]
          }
        })
      )
    },
    [dispatch, roomId, canInitRoom, roomQueryEndpoint, selfParticipantId]
  )

  useEffect(() => {
    if (!messages?.length) {
      lastProcessedIndexRef.current = 0
      return
    }

    if (messages.length < lastProcessedIndexRef.current) {
      lastProcessedIndexRef.current = 0
    }

    for (let index = lastProcessedIndexRef.current; index < messages.length; index += 1) {
      const command = parseAdminCommand(messages[index].text)
      if (!command) continue

      if (command.type === 'shuffle_teams' || command.type === 'reset_teams') {
        applyAssignments(command.assignments)
      }
    }

    lastProcessedIndexRef.current = messages.length
  }, [messages, applyAssignments])

  const emitAdminCommand = useCallback(
    (command: AdminCommand) => {
      if (!roomId || !canInitRoom || !isHost) return

      const socket = socketService.getSocket() ?? socketService.connect()
      socket.emit('message', {
        roomId,
        text: buildAdminMessage(command),
        command: team,
        createdAt: new Date().toISOString(),
      })
    },
    [roomId, canInitRoom, isHost, team]
  )

  const actions: AdminPanelActions = {
    toggleLobbyLock: () => {
      if (!isHost) return
      emitAdminCommand({ type: 'lobby_lock', value: !state.isLobbyLocked })
    },
    toggleChatMuted: () => {
      if (!isHost) return
      emitAdminCommand({ type: 'chat_muted', value: !state.isChatMuted })
    },
    toggleHintsEnabled: () => {
      if (!isHost) return
      emitAdminCommand({ type: 'hints_enabled', value: !state.areHintsEnabled })
    },
    togglePause: () => {
      if (!isHost) return
      emitAdminCommand({ type: 'pause', value: !state.isPaused })
    },
    shuffleTeams: () => {
      if (!isHost || !participants?.length) return
      const assignments = buildShuffledAssignments(participants)
      applyAssignments(assignments)
      emitAdminCommand({ type: 'shuffle_teams', assignments })
    },
    resetTeams: () => {
      if (!isHost || !participants?.length) return
      const assignments = buildAlternatingAssignments(participants)
      applyAssignments(assignments)
      emitAdminCommand({ type: 'reset_teams', assignments })
    },
  }

  const visibleMessages = useMemo(
    () => messages.filter((message) => !parseAdminCommand(message.text)),
    [messages]
  )

  return {
    state,
    actions,
    visibleMessages,
  }
}
