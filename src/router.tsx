import { createBrowserRouter, Outlet, redirect } from "react-router-dom";
import ActionButtons from "./components/startWindow/ActionButtons";
import Room from "./components/roomComponent/Room";

export const router = createBrowserRouter([
    {
        path: "/",
        element: (
            <div>
                <div>Home</div>
                <Outlet />
            </div>
        ),
        children: [
            {
                index: true,
                loader: () => redirect("/login") 
            },
            {
                path: "/login",
                element: <ActionButtons />
            },
            {
                path: "/room",
                element: <Room />
            }
        ]
    }
])
