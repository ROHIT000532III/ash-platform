import { Outlet } from "react-router-dom";

import Sidebar from "../components/Sidebar/sidebar";

export default function AppRoutes() {
  return (
    <div className="layout">
      <Sidebar />
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
