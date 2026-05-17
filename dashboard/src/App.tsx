import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type {
  FeatureImportance,
  ModelRegistry,
  PipelineStatus,
  Predictions,
  Runs,
  WarehouseData,
} from "./api";
import { Sidebar, TopBar } from "./shell";
import type { NavId } from "./shell";
import {
  ComingSoonPage,
  ModelsPage,
  OverviewPage,
  PipelinePage,
  RunsPage,
  ScoringPage,
  WarehousePage,
} from "./pages";

const BREADCRUMBS: Record<NavId, string[]> = {
  overview: ["Workspace", "Overview"],
  pipeline: ["Workspace", "Pipeline"],
  models: ["Workspace", "Models"],
  scoring: ["Workspace", "Scoring"],
  warehouse: ["Data", "Warehouse"],
  runs: ["Data", "Runs"],
  settings: ["Account", "Settings"],
};

export default function App() {
  const [active, setActive] = useState<NavId>("overview");
  const [collapsed, setCollapsed] = useState(false);
  const [running, setRunning] = useState(false);
  const [dagLive, setDagLive] = useState<Record<string, string>>({});

  const [pipeline, setPipeline] = useState<PipelineStatus>();
  const [data, setData] = useState<WarehouseData>();
  const [models, setModels] = useState<ModelRegistry>();
  const [fi, setFi] = useState<FeatureImportance>();
  const [predictions, setPredictions] = useState<Predictions>();
  const [runs, setRuns] = useState<Runs>();
  const [error, setError] = useState<string>();

  const loadAll = useCallback(() => {
    setError(undefined);
    api.pipeline().then(setPipeline).catch((e) => setError(String(e)));
    api.data().then(setData).catch((e) => setError(String(e)));
    api.models().then(setModels).catch((e) => setError(String(e)));
    api.featureImportance().then(setFi).catch((e) => setError(String(e)));
    api.predictions().then(setPredictions).catch((e) => setError(String(e)));
    api.runs().then(setRuns).catch((e) => setError(String(e)));
  }, []);

  useEffect(loadAll, [loadAll]);

  // "Run pipeline" — drop analytics + rebuild via the SSE rebuild stream.
  // Per-dbt-node completions feed the live pipeline DAG.
  function runPipeline() {
    setRunning(true);
    setDagLive({});
    const es = new EventSource("/api/pipeline/rebuild/stream");
    es.onmessage = (e) => {
      const evt = JSON.parse(e.data) as {
        message?: string;
        stage?: string;
        done?: boolean;
      };
      const match = /analytics\.(\w+)/.exec(evt.message ?? "");
      if (match) {
        const node = match[1];
        setDagLive((s) => ({
          ...s,
          [node]: evt.stage === "error" ? "error" : "done",
        }));
      }
      if (evt.done) {
        es.close();
        setRunning(false);
        loadAll();
      }
    };
    es.onerror = () => {
      es.close();
      setRunning(false);
    };
  }

  const handleScored = useCallback((p: Predictions) => {
    setPredictions(p);
    api.runs().then(setRuns).catch(() => undefined);
  }, []);

  const champion = models?.versions.find((v) => v.is_champion);
  const threshold = Number(champion?.decision_threshold ?? 0.5);
  const modelVersion = models
    ? `churn-xgboost v${models.champion_version}`
    : "churn-xgboost";

  function page() {
    switch (active) {
      case "overview":
        return (
          <OverviewPage
            data={data}
            models={models}
            pipeline={pipeline}
            fi={fi}
            predictions={predictions}
            runs={runs?.runs}
            threshold={threshold}
            modelVersion={modelVersion}
            running={running}
            onScored={handleScored}
          />
        );
      case "pipeline":
        return (
          <PipelinePage
            pipeline={pipeline}
            data={data}
            championVersion={models?.champion_version}
            running={running}
            liveState={dagLive}
            onRun={runPipeline}
          />
        );
      case "models":
        return <ModelsPage models={models} fi={fi} />;
      case "warehouse":
        return <WarehousePage data={data} />;
      case "runs":
        return <RunsPage runs={runs?.runs} />;
      case "scoring":
        return (
          <ScoringPage
            predictions={predictions}
            threshold={threshold}
            modelVersion={modelVersion}
            onScored={handleScored}
          />
        );
      case "settings":
        return <ComingSoonPage title="Settings" />;
      default:
        return null;
    }
  }

  return (
    <div className="flex min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <Sidebar active={active} onChange={setActive} collapsed={collapsed} />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          breadcrumb={BREADCRUMBS[active]}
          running={running}
          onRunPipeline={runPipeline}
          onSync={loadAll}
          onToggleSidebar={() => setCollapsed((c) => !c)}
        />

        <main className="flex-1 px-6 py-6 lg:px-8 lg:py-8">
          {error && (
            <div className="mb-6 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-[12.5px] text-rose-200">
              {error} — is the API running on :8000?
            </div>
          )}
          {page()}
        </main>
      </div>
    </div>
  );
}
