import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import App from "./App";
import "./styles/globals.css";
import { Dashboard } from "./pages/Dashboard";
import { BackendsPage } from "./pages/BackendsPage";
import { TasksPage } from "./pages/TasksPage";
import { ArchivePage } from "./pages/ArchivePage";
import { LocalDemo } from "./pages/LocalDemo";

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "demo", element: <LocalDemo /> },
      { path: "backends", element: <BackendsPage /> },
      { path: "tasks", element: <TasksPage /> },
      { path: "archive", element: <ArchivePage /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
