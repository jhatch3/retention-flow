import { Suspense, lazy, useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type {
  EvalModel,
  FeatureImportance,
  ModelRegistry,
  PipelineReport,
  PipelineStatus,
  Predictions,
  Runs,
  ShapData,
  WarehouseData,
} from "./api";
import { RunReport } from "./RunReport";
import { Sidebar, TopBar } from "./shell";
import type { NavId } from "./shell";
import {
  ComingSoonPage,
  EvalPage,
  ModelsPage,
  OverviewPage,
  PipelinePage,
  RunsPage,
  ScoringPage,
  WarehousePage,
} from "./pages";
import { cx } from "./lib";

const InboxPage = lazy(() => import("./inbox/InboxPage"));

const BREADCRUMBS: Record<NavId, string[]> = {
  inbox: ["Workspace", "Inbox"],
  overview: ["Workspace", "Overview"],
  pipeline: ["Workspace", "Pipeline"],
  models: ["Workspace", "Models"],
  scoring: ["Workspace", "Scoring"],
  eval: ["Workspace", "Eval"],
  warehouse: ["Data", "Warehouse"],
  runs: ["Data", "Runs"],
  settings: ["Account", "Settings"],
};

export default function App() {
  const [active, setActive] = useState<NavId>("overview");
  const [collapsed, setCollapsed] = useState(false);
  const [running, setRunning] = useState(false);
  const [dagLive, setDagLive] = useState<Record<string, string>>({});
  const [report, setReport] = useState<PipelineReport>();

  const [pipeline, setPipeline] = useState<PipelineStatus>();
  const [data, setData] = useState<WarehouseData>();
  const [models, setModels] = useState<ModelRegistry>();
  const [fi, setFi] = useState<FeatureImportance>();
  const [predictions, setPredictions] = useState<Predictions>();
  const [shap, setShap] = useState<ShapData>();
  const [runs, setRuns] = useState<Runs>();
  const [evalModel, setEvalModel] = useState<EvalModel>();
  const [inboxCount, setInboxCount] = useState<number>();
  const [error, setError] = useState<string>();

  const loadAll = useCallback(() => {
    setError(undefined);
    api.pipeline().then(setPipeline).catch((e) => setError(String(e)));
    api.data().then(setData).catch((e) => setError(String(e)));
    api.models().then(setModels).catch((e) => setError(String(e)));
    api.featureImportance().then(setFi).catch((e) => setError(String(e)));
    api.predictions().then(setPredictions).catch((e) => setError(String(e)));
    api.shap().then(setShap).catch((e) => setError(String(e)));
    api.runs().then(setRuns).catch((e) => setError(String(e)));
    api.evalModel().then(setEvalModel).catch((e) => setError(String(e)));
    api.inbox
      .customers()
      .then((d) => setInboxCount(d.totals.all))
      .catch(() => undefined);
  }, []);

  useEffect(loadAll, [loadAll]);

  // "Run pipeline" — the full pipeline (dbt rebuild → train → score) over SSE.
  // dbt-node completions and the train/score phases feed the live DAG; the
  // final report opens the run-report modal.
  function runPipeline() {
    setRunning(true);
    setDagLive({});
    setReport(undefined);
    const es = new EventSource("/api/pipeline/run/stream");
    es.onmessage = (e) => {
      const evt = JSON.parse(e.data) as {
        message?: string;
        phase?: string;
        done?: boolean;
        report?: PipelineReport;
      };
      const match = /analytics\.(\w+)/.exec(evt.message ?? "");
      if (match) setDagLive((s) => ({ ...s, [match[1]]: "done" }));
      if (evt.phase === "train") setDagLive((s) => ({ ...s, churn_model: "running" }));
      if (evt.phase === "score") setDagLive((s) => ({ ...s, churn_model: "done" }));
      if (evt.done) {
        es.close();
        setRunning(false);
        if (evt.report) setReport(evt.report);
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
    api.shap().then(setShap).catch(() => undefined);
    api.runs().then(setRuns).catch(() => undefined);
  }, []);

  const champion = models?.versions.find((v) => v.is_champion);
  const threshold = Number(champion?.decision_threshold ?? 0.5);
  const modelVersion = models
    ? `churn-xgboost v${models.champion_version}`
    : "churn-xgboost";

  function page() {
    switch (active) {
      case "inbox":
        return (
          <Suspense
            fallback={
              <div className="grid h-full place-items-center text-[13px] text-[var(--muted)]">
                Loading…
              </div>
            }
          >
            <InboxPage />
          </Suspense>
        );
      case "overview":
        return (
          <OverviewPage
            data={data}
            models={models}
            pipeline={pipeline}
            fi={fi}
            predictions={predictions}
            runs={runs?.runs}
            shap={shap}
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
        return <ModelsPage models={models} fi={fi} shap={shap} />;
      case "warehouse":
        return <WarehousePage data={data} />;
      case "runs":
        return <RunsPage runs={runs?.runs} />;
      case "scoring":
        return (
          <ScoringPage
            predictions={predictions}
            shap={shap}
            threshold={threshold}
            modelVersion={modelVersion}
            onScored={handleScored}
          />
        );
      case "eval":
        return <EvalPage model={evalModel} />;
      case "settings":
        return <ComingSoonPage title="Settings" />;
      default:
        return null;
    }
  }

  const isInbox = active === "inbox";

  return (
    <div
      className={cx(
        "flex bg-[var(--bg)] text-[var(--fg)]",
        isInbox ? "h-screen" : "min-h-screen",
      )}
    >
      <Sidebar
        active={active}
        onChange={setActive}
        collapsed={collapsed}
        badges={{ inbox: inboxCount }}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          breadcrumb={BREADCRUMBS[active]}
          running={running}
          onRunPipeline={runPipeline}
          onSync={loadAll}
          onToggleSidebar={() => setCollapsed((c) => !c)}
        />

        <main
          data-theme={isInbox ? "light" : undefined}
          className={cx(
            "min-h-0 flex-1",
            isInbox ? "overflow-hidden" : "px-6 py-6 lg:px-8 lg:py-8",
          )}
        >
          {error && !isInbox && (
            <div className="mb-6 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-[12.5px] text-rose-200">
              {error} — is the API running on :8000?
            </div>
          )}
          {page()}
        </main>
      </div>
      {report && (
        <RunReport report={report} onClose={() => setReport(undefined)} />
      )}
    </div>
  );
}
