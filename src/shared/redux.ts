import { configureStore } from "@reduxjs/toolkit";
import { pinApi } from "../components/startWindow/pinApi";
import { useDispatch, useSelector } from "react-redux";

export const store = configureStore({
    reducer: {
        [pinApi.reducerPath]: pinApi.reducer,
    },
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware().concat(pinApi.middleware),
}); 

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const useAppSelector = useSelector.withTypes<RootState>()
export const useAppDispatch = useDispatch.withTypes<AppDispatch>()
