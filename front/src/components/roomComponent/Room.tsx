import { type FormEvent, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useInitCreatingRoomQuery } from './socketApi'
import { socketService } from '../../shared/socketServise'
import type { TeamCommand } from '../../shared/types'
import BlueRoom from './team/BlueRoom'
import RedRoom from './team/RedRoom'

const SOCKET_EVENTS = {
  message: 'message',
}

function Room() {
  const { roomId } = useParams()
  const roomIdNumber = Number(roomId)
  const canInitRoom = Number.isFinite(roomIdNumber)

  const { data, isLoading, isError } = useInitCreatingRoomQuery(roomIdNumber, {
    skip: !canInitRoom,
  })

  const [draft, setDraft] = useState('')
  const messageEndRef = useRef<HTMLLIElement | null>(null)

  const messages = data?.messages ?? []
  const participantsCount =
    typeof data?.participants?.length === 'number' ? data?.participants?.length : null

  const team: TeamCommand = data?.team === 'blue' ? 'blue' : 'red'
  const RoomVariant = team === 'blue' ? BlueRoom : RedRoom

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length])

  const handleSend = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = draft.trim()
    if (!trimmed || !canInitRoom) return

    const socket = socketService.getSocket() ?? socketService.connect()
    socket.emit(SOCKET_EVENTS.message, {
      roomId: roomIdNumber,
      text: trimmed,
      command: team,
      createdAt: new Date().toISOString(),
    })

    setDraft('')
  }

  if (!data && !isLoading) return <p className="room-text room-text--error"> URL.</p>

  return (
    <RoomVariant
      roomId={roomId}
      data={data}
      isLoading={isLoading}
      isError={isError}
      canInitRoom={canInitRoom}
      messages={messages}
      participantsCount={participantsCount}
      draft={draft}
      onDraftChange={setDraft}
      onSend={handleSend}
      messageEndRef={messageEndRef}
    />
  )
}

export default Room
