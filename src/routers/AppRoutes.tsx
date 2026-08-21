import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom";

import Dashboard from "../pages/dashbord/Dashboard";
import Chat from "../pages/chat/chat";
import Explorer from "../pages/explorer/Explorer";
import Models from "../pages/models/Models";
import Settings from "../pages/settings/Settings";
import Auth from "../pages/auth/Auth";
import { AuthProvider, useAuth } from "../auth/AuthContext";
import type { ReactNode } from "react";

function ProtectedRoute({ children }: { children: ReactNode }) {
  return useAuth().session ? children : <Navigate to="/login" replace />;
}

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <AuthProvider><Routes>
        <Route path="/login" element={<Auth />} />
        <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
        <Route path="/explorer" element={<ProtectedRoute><Explorer /></ProtectedRoute>} />
        <Route path="/models" element={<ProtectedRoute><Models /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes></AuthProvider>
    </BrowserRouter>
  );
}
