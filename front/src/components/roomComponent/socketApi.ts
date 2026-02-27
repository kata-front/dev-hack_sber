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
                let selfParticipantId: number | null = null;

                const resolveSelfParticipantId = (data: InfoRoom & { role?: string }) => {
                    const rawId =
                        (data as { participantId?: number }).participantId ??
                        (data as { selfParticipantId?: number }).selfParticipantId ??
                        (data as { playerId?: number }).playerId;
                    if (typeof rawId === 'number') return rawId;
                    if (socket.id && data.participants) {
                        const match = data.participants.find(
                            (participant) => String(participant.id) === socket.id
                        );
                        if (match) return match.id;
                    }
                    const last = data.participants?.[data.participants.length - 1];
                    return typeof last?.id === 'number' ? last.id : null;
                };

                socket.emit("create_room", roomId);

                socket.on("room_created", (data) => {
                    selfParticipantId = resolveSelfParticipantId(data);
                    updateCachedData(() => data);
                });

                socket.on("player_joined", (parsicipant: Parsicipant) => {
                    updateCachedData((draft) => {
                        const participants = draft.participants || [];
                        if (participants.some((participant) => participant.id === parsicipant.id)) return;
                        draft.participants = [...participants, parsicipant];
                    });
                });

                socket.on('message', (message) => {
                    updateCachedData((draft) => {
                        draft.messages = [...(draft.messages || []), message];
                    });
                });

                socket.on('user_left', (parsicipant: Parsicipant) => {
                    updateCachedData((draft) => {
                        const participants =
                            draft.participants?.filter((participant) => participant.id !== parsicipant.id) || [];
                        draft.participants = participants;
                        if (parsicipant.role === 'host' && participants.length > 0) {
                            participants[0].role = 'host';
                            if (selfParticipantId !== null && participants[0].id === selfParticipantId) {
                                draft.role = 'host';
                            }
                        }
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
                let selfParticipantId: number | null = null;

                const resolveSelfParticipantId = (data: InfoRoom & { role?: string }) => {
                    const rawId =
                        (data as { participantId?: number }).participantId ??
                        (data as { selfParticipantId?: number }).selfParticipantId ??
                        (data as { playerId?: number }).playerId;
                    if (typeof rawId === 'number') return rawId;
                    if (socket.id && data.participants) {
                        const match = data.participants.find(
                            (participant) => String(participant.id) === socket.id
                        );
                        if (match) return match.id;
                    }
                    const last = data.participants?.[data.participants.length - 1];
                    return typeof last?.id === 'number' ? last.id : null;
                };

                socket.emit("join_room", roomId);

                socket.on("room_joined", (data) => {
                    console.log(data)
                    selfParticipantId = resolveSelfParticipantId(data);
                    updateCachedData(() => data);
                });

                socket.on("player_joined", (parsicipant: Parsicipant) => {
                    updateCachedData((draft) => {
                        const participants = draft.participants || [];
                        if (participants.some((participant) => participant.id === parsicipant.id)) return;
                        draft.participants = [...participants, parsicipant];
                    });
                });

                socket.on('message', (message) => {
                    updateCachedData((draft) => {
                        draft.messages = [...(draft.messages || []), message];
                    });
                });

                socket.on('user_left', (parsicipant: Parsicipant) => {
                    updateCachedData((draft) => {
                        const participants =
                            draft.participants?.filter((participant) => participant.id !== parsicipant.id) || [];
                        draft.participants = participants;
                        if (parsicipant.role === 'host' && participants.length > 0) {
                            participants[0].role = 'host';
                            if (selfParticipantId !== null && participants[0].id === selfParticipantId) {
                                draft.role = 'host';
                            }
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
