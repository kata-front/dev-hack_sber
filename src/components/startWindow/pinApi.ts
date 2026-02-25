import { baseApi } from "../../shared/baseApi";

export const pinApi = baseApi.injectEndpoints({
    endpoints: (build) => ({
        checkPin: build.mutation<boolean, number>({
            query: user_pin => ({
                url: "/check_pin",
                method: "POST",
                body: { pin: user_pin },
            }),
        }),
        createRoom: build.mutation<boolean, {
            roomName: string;
            quizTheme: string;
            maxParticipants: number;
        }>({
            query: roomInfo => ({
                url: "/create_room",
                method: "POST",
                body: roomInfo,
            }),
        }),
    }),
});

export const { useCheckPinMutation, useCreateRoomMutation } = pinApi;
