import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

const API_BASE_URL = "http://82.24.174.86:8888/api/v1/";

export const baseApi = createApi({
    baseQuery: fetchBaseQuery({ baseUrl: API_BASE_URL }),
    endpoints: () => ({})
})
