import { baseApi } from '../../shared/baseApi'
import type { InfoRoom, Parsicipant, TeamCommand } from '../../shared/types'
import { socketService } from '../../shared/socketServise'

type RoomSnapshotBase = InfoRoom & { role: 'host' | 'participant' }
type HostSnapshot = RoomSnapshotBase
type ParticipantSnapshot = RoomSnapshotBase & { team: TeamCommand }
type SelfParticipantIdPayload = {
  participantId?: number | string
  selfParticipantId?: number | string
  playerId?: number | string
}

const toParticipantKey = (value: unknown) => {
  if (value === null || value === undefined) return null
  return String(value)
}

const isSameParticipant = (left: unknown, right: unknown) => {
  const leftKey = toParticipantKey(left)
  const rightKey = toParticipantKey(right)
  return leftKey !== null && rightKey !== null && leftKey === rightKey
}

const resolveSelfParticipantKey = (
  snapshot: RoomSnapshotBase,
  socketId?: string
) => {
  const payload = snapshot as SelfParticipantIdPayload
  const fromPayload =
    payload.participantId ?? payload.selfParticipantId ?? payload.playerId
  const payloadKey = toParticipantKey(fromPayload)
  if (payloadKey) return payloadKey

  if (socketId && snapshot.participants) {
    const socketMatch = snapshot.participants.find((participant) =>
      isSameParticipant(participant.id, socketId)
    )
    if (socketMatch) return toParticipantKey(socketMatch.id)
  }

  const last = snapshot.participants?.[snapshot.participants.length - 1]
  return toParticipantKey(last?.id)
}

const addParticipantIfMissing = (
  participants: Parsicipant[],
  incoming: Parsicipant
) => {
  const exists = participants.some((participant) =>
    isSameParticipant(participant.id, incoming.id)
  )
  if (exists) return participants
  return [...participants, incoming]
}

const handleRoomSocketFlow = <TSnapshot extends RoomSnapshotBase>(
  roomId: number,
  socketJoinEvent: 'create_room' | 'join_room',
  socketSnapshotEvent: 'room_created' | 'room_joined',
  updateCachedData: (recipe: (draft: TSnapshot) => void) => void
) => {
  const socket = socketService.connect()
  let selfParticipantKey: string | null = null

  const onSnapshot = (snapshot: TSnapshot) => {
    selfParticipantKey = resolveSelfParticipantKey(snapshot, socket.id)
    updateCachedData(() => snapshot)
  }

  const onPlayerJoined = (participant: Parsicipant) => {
    updateCachedData((draft) => {
      const participants = draft.participants ?? []
      draft.participants = addParticipantIfMissing(participants, participant)
    })

    if (!selfParticipantKey && socket.id && isSameParticipant(participant.id, socket.id)) {
      selfParticipantKey = toParticipantKey(participant.id)
    }
  }

  const onMessage = (message: NonNullable<InfoRoom['messages']>[number]) => {
    updateCachedData((draft) => {
      draft.messages = [...(draft.messages ?? []), message]
    })
  }

  const onUserLeft = (leftParticipant: Parsicipant) => {
    updateCachedData((draft) => {
      const remainingParticipants =
        draft.participants?.filter(
          (participant) => !isSameParticipant(participant.id, leftParticipant.id)
        ) ?? []

      draft.participants = remainingParticipants

      if (leftParticipant.role === 'host' && remainingParticipants.length > 0) {
        remainingParticipants[0].role = 'host'
        if (
          selfParticipantKey &&
          isSameParticipant(remainingParticipants[0].id, selfParticipantKey)
        ) {
          draft.role = 'host'
        }
      }
    })
  }

  socket.emit(socketJoinEvent, roomId)
  socket.on(socketSnapshotEvent, onSnapshot)
  socket.on('player_joined', onPlayerJoined)
  socket.on('message', onMessage)
  socket.on('user_left', onUserLeft)

  return () => {
    socket.off(socketSnapshotEvent, onSnapshot)
    socket.off('player_joined', onPlayerJoined)
    socket.off('message', onMessage)
    socket.off('user_left', onUserLeft)
    socket.disconnect()
  }
}

export const socketApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    initCreatingRoom: build.query<HostSnapshot, number>({
      query: (roomId) => `/create_room/${roomId}`,

      async onCacheEntryAdded(roomId, { cacheDataLoaded, cacheEntryRemoved, updateCachedData }) {
        await cacheDataLoaded

        const cleanup = handleRoomSocketFlow(
          roomId,
          'create_room',
          'room_created',
          updateCachedData
        )

        await cacheEntryRemoved
        cleanup()
      },
    }),
    initJoiningRoom: build.query<ParticipantSnapshot, number>({
      query: (roomId) => `/join_room/${roomId}`,

      async onCacheEntryAdded(roomId, { cacheDataLoaded, cacheEntryRemoved, updateCachedData }) {
        await cacheDataLoaded

        const cleanup = handleRoomSocketFlow(
          roomId,
          'join_room',
          'room_joined',
          updateCachedData
        )

        await cacheEntryRemoved
        cleanup()
      },
    }),
  }),
})

export const { useInitCreatingRoomQuery, useInitJoiningRoomQuery } = socketApi
