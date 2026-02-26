import { baseApi } from "../../shared/baseApi";
import type { InfoRoom } from "../../shared/types";
import { socketService } from "../../shared/socketServise";

export const socketApi = baseApi.injectEndpoints({
    endpoints: (build) => ({
        initCreatingRoom: build.query<InfoRoom, number>({
            query: (roomId) => `/init_room/${roomId}`,

            async onCacheEntryAdded(
                payload,
                { cacheDataLoaded, cacheEntryRemoved, updateCachedData }
            ) {
                await cacheDataLoaded;

                const socket = socketService.connect();

                socket.emit("create_room", payload);

                socket.on("room_created", (data) => {
                    updateCachedData(() => data);
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
    })
});

export const { useInitCreatingRoomQuery } = socketApi;
