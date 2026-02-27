import { createSlice } from "@reduxjs/toolkit";

export const roleSlice = createSlice({
    name: "role",
    initialState: {
        role: "",
    },
    selectors: {
        selectRole: (state) => state.role
    },
    reducers: {
        setRole: (state, action) => {
            state.role = action.payload;
        },
    },
})