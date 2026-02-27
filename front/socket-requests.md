# Socket Requests (Frontend Contract)

Server URL: `http://82.24.174.86:8888`

## Client -> Server

1. `create_room`
Payload:
```json
12345
```

2. `join_room`
Payload:
```json
12345
```

3. `message`
Payload:
```json
{
  "roomId": 12345,
  "text": "hello",
  "command": "red",
  "createdAt": "2026-02-27T12:00:00.000Z"
}
```

4. `start_game`
Payload:
```json
{
  "roomId": 12345
}
```

5. `next_question`
Payload:
```json
{
  "roomId": 12345
}
```

6. `answer`
Payload:
```json
{
  "roomId": 12345,
  "questionIndex": 2,
  "answer": "200",
  "team": "blue"
}
```

## Server -> Client

1. `room_created` -> room snapshot for host
2. `room_joined` -> room snapshot for participant
3. `player_joined` -> new participant
4. `user_left` -> participant who left
5. `message` -> chat message
6. `game_started` -> full `GameInfo`
7. `new_question` -> current `Question`
8. `next_question` -> alias with same `Question` payload
9. `check_answer` -> `correct | incorrect`
10. `timer_tick` -> `{ counter: number }`
11. `timer_end` -> `{ counter: number }`
12. `game_finished` -> `waiting | active | finished`
