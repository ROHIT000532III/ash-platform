import WelcomeBanner from "../../components/Dashboard/WelcomeBanner";
import QuickActions from "../../components/Dashboard/QuickActions";
import SystemStatus from "../../components/Dashboard/SystemStatus";
import ModelStatus from "../../components/Dashboard/ModelStatus";
import RecentProjects from "../../components/Dashboard/RecentProjects";

export default function Dashboard() {
  return (
    <>
      <WelcomeBanner />

      <div className="dashboard">
        <QuickActions />
        <SystemStatus />
        <ModelStatus />
        <RecentProjects />
      </div>
    </>
  );
}