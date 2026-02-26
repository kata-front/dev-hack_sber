import RoomView, { type RoomViewProps } from './RoomView'

type RedRoomProps = Omit<RoomViewProps, 'team'>

function RedRoom(props: RedRoomProps) {
  return <RoomView {...props} team="red" />
}

export default RedRoom
