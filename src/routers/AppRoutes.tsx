import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom";

import Dashboard from "../pages/dashbord/Dashboard";
import Chat from "../pages/chat/chat";
import Explorer from "../pages/explorer/Explorer";
import Models from "../pages/models/Models";
import Settings from "../pages/settings/Settings";

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Chat />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/explorer" element={<Explorer />} />
        <Route path="/models" element={<Models />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
