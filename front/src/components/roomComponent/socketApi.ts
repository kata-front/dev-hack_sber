import { baseApi } from "../../shared/baseApi";
import type { InfoRoom, Parsicipant, TeamCommand } from "../../shared/types";
import { socketService } from "../../shared/socketServise";

export const socketApi = baseApi.injectEndpoints({
    endpoints: (build) => ({
        initCreatingRoom: build.query<InfoRoom & { role: 'host' | 'participant' }, number>({
            query: (roomId) => `/create_room/${roomId}`,

            async onCacheEntryAdded(
                roomId,
                { cacheDataLoaded, cacheEntryRemoved, updateCachedData }
            ) {
                await cacheDataLoaded;

                const socket = socketService.connect();


                console.log('socket')

                socket.emit("create_room", roomId);

                socket.on("room_created", (data) => {
                    updateCachedData(() => data);
                });

                socket.on("player_joined", (parsicipant: Parsicipant) => {
                    updateCachedData((draft) => {
                        draft.participants = [...(draft.participants || []), parsicipant];
                    });
                });

                socket.on('message', (message) => {
                    updateCachedData((draft) => {
                        draft.messages = [...(draft.messages || []), message];
                    });
                });

                await cacheEntryRemoved;

                socket.disconnect();
            }
        }),
        initJoiningRoom: build.query<InfoRoom & { role: 'host' | 'participant', team: TeamCommand }, number>({
            query: (roomId) => `/join_room/${roomId}`,

            async onCacheEntryAdded(
                roomId,
                { cacheDataLoaded, cacheEntryRemoved, updateCachedData }
            ) {
                await cacheDataLoaded;

                const socket = socketService.connect();

                socket.emit("join_room", roomId);

                socket.on("room_joined", (data) => {
                    console.log(data)
                    updateCachedData(() => data);
                });

                socket.on("player_joined", (parsicipant: Parsicipant) => {
                    updateCachedData((draft) => {
                        draft.participants = [...(draft.participants || []), parsicipant];
                    });
                });

                socket.on('message', (message) => {
                    updateCachedData((draft) => {
                        draft.messages = [...(draft.messages || []), message];
                    });
                });

                socket.on('user_left', (parsicipant: Parsicipant) => {
                    updateCachedData((draft) => {
                        draft.participants = draft.participants?.filter(p => p.id !== parsicipant.id);
                        if (parsicipant.role === 'host' && draft.participants && draft.participants.length > 0) {
                            draft.participants[0].role = 'host'
                        }
                    });
                });

                await cacheEntryRemoved;

                socket.disconnect();
            }
        }),
    })
});

export const { useInitCreatingRoomQuery, useInitJoiningRoomQuery } = socketApi;
