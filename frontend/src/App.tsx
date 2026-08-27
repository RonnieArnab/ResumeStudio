import { useEffect, useState } from "react";
import { apiClient } from "./api/client";
import AppLayout from "./components/layout/AppLayout";
import JobsPage from "./components/jobs/JobsPage";
import ResumeWorkspace from "./components/resume/ResumeWorkspace";
import { useStore } from "./state/store";

interface HealthResponse {
  status: string;
  environment: string;
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const session = useStore((state) => state.session);
  const view = useStore((state) => state.view);

  useEffect(() => {
    apiClient
      .get<HealthResponse>("/health")
      .then(setHealth)
      .catch((err: Error) => setHealthError(err.message));
  }, []);

  const meta = session
    ? `session ${session.session_id.slice(0, 8)}`
    : healthError
      ? "backend unreachable"
      : health
        ? `backend ${health.status}`
        : "connecting…";

  return <AppLayout meta={meta}>{view === "jobs" ? <JobsPage /> : <ResumeWorkspace />}</AppLayout>;
}
