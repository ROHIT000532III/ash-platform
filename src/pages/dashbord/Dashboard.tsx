import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <div className="dashboard">
      <h1>ASH AI ENTERPRISE</h1>

      <h2>Dashboard</h2>
      <p>Your intelligent workspace is ready.</p>

      <div className="status">
        System Online
      </div>

      <div className="cards">
        <div className="card">
          <span>🤖</span>
          <h3>AI Models</h3>
          <strong>03</strong>
          <p>Available</p>
        </div>

        <div className="card">
          <span>💬</span>
          <h3>AI Sessions</h3>
          <strong>12</strong>
          <p>This week</p>
        </div>

        <div className="card">
          <span>📁</span>
          <h3>Projects</h3>
          <strong>08</strong>
          <p>Active projects</p>
        </div>

        <div className="card">
          <span>⚡</span>
          <h3>System</h3>
          <strong>98%</strong>
          <p>Healthy</p>
        </div>
      </div>

      <section className="workspace">
        <h2>AI WORKSPACE</h2>

        <h1>Build. Think. Automate.</h1>

        <p>
          ASH AI Enterprise gives you one intelligent workspace
          for AI, projects, models and automation.
        </p>

        <button onClick={() => navigate("/chat")}>
          💬 Start AI Chat →
        </button>
      </section>

      <section>
        <h2>Quick Actions</h2>

        <div className="actions">
          <button onClick={() => navigate("/chat")}>
            💬 New Chat
          </button>

          <button onClick={() => navigate("/explorer")}>
            📁 Open Explorer
          </button>

          <button onClick={() => navigate("/models")}>
            🤖 Model Manager
          </button>

          <button onClick={() => navigate("/settings")}>
            ⚙ Settings
          </button>
        </div>
      </section>
    </div>
  );
}