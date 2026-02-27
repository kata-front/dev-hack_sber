import { baseApi } from "../../shared/baseApi";
import type { DataFormCreateRoom, LoginResponse } from "../../shared/types";

export const pinApi = baseApi.injectEndpoints({
    endpoints: (build) => ({
        checkPin: build.mutation<LoginResponse, number>({
            query: user_pin => ({
                url: "/check_pin",
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pin: user_pin }),
            }),
        }),
        createRoom: build.mutation<LoginResponse, DataFormCreateRoom>({
            query: roomInfo => ({
                url: "/create_room",
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(roomInfo) || roomInfo,
            }),
        }),
    }),
});

export const { useCheckPinMutation, useCreateRoomMutation } = pinApi;
