import RoomView, { type RoomViewProps } from './RoomView'

type BlueRoomProps = Omit<RoomViewProps, 'team'>

function BlueRoom(props: BlueRoomProps) {
  return <RoomView {...props} team="blue" />
}

export default BlueRoom
