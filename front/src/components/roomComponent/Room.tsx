import { useParams } from 'react-router-dom'
import BlueRoom from './team/BlueRoom'
import RedRoom from './team/RedRoom'
import { useRoomController } from './model/useRoomController'

function Room() {
  const { roomId } = useParams()
  const controller = useRoomController({ roomId })
  const RoomVariant = controller.team === 'blue' ? BlueRoom : RedRoom

  if (!controller.data && !controller.isLoading) {
    return <p className="room-text room-text--error">Некорректная ссылка на комнату.</p>
  }

  return (
    <RoomVariant
      roomId={controller.roomId}
      data={controller.data}
      isLoading={controller.isLoading}
      isError={controller.isError}
      canInitRoom={controller.canInitRoom}
      messages={controller.messages}
      participantsCount={controller.participantsCount}
      draft={controller.draft}
      onDraftChange={controller.onDraftChange}
      onSend={controller.onSend}
      messageEndRef={controller.messageEndRef}
      gameView={controller.gameView}
      onStartGame={controller.onStartGame}
      onNextQuestion={controller.onNextQuestion}
      onAnswer={controller.onAnswer}
      isStartingGame={controller.isStartingGame}
      isAdvancingQuestion={controller.isAdvancingQuestion}
      canRequestNextQuestion={controller.canRequestNextQuestion}
      isHost={controller.isHost}
      isStartDisabled={controller.isStartDisabled}
      adminState={controller.adminState}
      adminActions={controller.adminActions}
    />
  )
}

export default Room
