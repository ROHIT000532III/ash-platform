import { NavLink } from "react-router-dom";

export default function Sidebar() {
  return (
    <div className="sidebar">
      <h2>ASH</h2>

      <NavLink to="/">🏠 Dashboard</NavLink>

      <NavLink to="/chat">💬 Chat</NavLink>

      <NavLink to="/explorer">📁 Explorer</NavLink>

      <NavLink to="/models">🤖 Models</NavLink>

      <NavLink to="/settings">⚙ Settings</NavLink>
    </div>
  );
}