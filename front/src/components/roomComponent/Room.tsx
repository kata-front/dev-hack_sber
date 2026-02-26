import { useParams } from 'react-router-dom'
import './Room.scss'
import { useInitCreatingRoomQuery } from './socketApi'
import { socketService } from '../../shared/socketServise'

function Room() {
  const { roomId } = useParams()
  const { data, isLoading, isError } = useInitCreatingRoomQuery(Number(roomId))

  return (
    <div className="room-page">
      <section className="room-section">
        {isLoading && <p>Loading...</p>}
        <p>Room ID: {data?.roomId}</p>
        <p>Room Name: {data?.roomName}</p>
        <p>Quiz Theme: {data?.quizTheme}</p>
        <p>Max Participants: {data?.maxParticipants}</p>
        <p>Chat: </p>
        {data?.messages?.map((message, index) => (
          <p key={index}>{message.text}</p>
        ))}
      </section>
    </div>
  )
}

export default Room
