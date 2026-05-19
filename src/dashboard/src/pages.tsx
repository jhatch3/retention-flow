// Per-section pages — each composes the relevant cards behind a PageHeader.
import { ExternalLink } from "lucide-react";
import type {
  FeatureImportance,
  ModelRegistry,
  PipelineStatus,
  Predictions,
  RunRecord,
  ShapData,
  WarehouseData,
} from "./api";
import { PageHeader } from "./shell";
import { Button, Card } from "./ui";
import { openExternal } from "./lib";
import {
  ChurnHero,
  FeatureImportanceCard,
  KpiRow,
  ModelRegistryCard,
  PipelineCard,
  ShapCard,
  WarehouseCard,
} from "./cards";
import { AtRiskTable, RecentRunsCard } from "./tables";
import { ScoringPanel } from "./ScoringPanel";
import { PipelineDag } from "./PipelineDag";
import { WarehouseTables } from "./WarehouseTables";

export function OverviewPage(p: {
  data?: WarehouseData;
  models?: ModelRegistry;
  pipeline?: PipelineStatus;
  fi?: FeatureImportance;
  predictions?: Predictions;
  runs?: RunRecord[];
  shap?: ShapData;
  threshold: number;
  modelVersion: string;
  running: boolean;
  onScored: (p: Predictions) => void;
}) {
  return (
    <>
      <PageHeader
        eyebrow="Production"
        title="Customer retention overview"
        description="Churn predictions, model health, and pipeline status. Rebuilt on demand and nightly by the Dagster schedule."
        meta={
          <span className="font-mono text-[11px] text-[var(--muted)]">
            snapshot · 2017-08-01
          </span>
        }
        actions={
          <Button
            variant="outline"
            rightIcon={<ExternalLink size={13} />}
            onClick={() => openExternal("http://localhost:5000")}
          >
            Open in MLflow
          </Button>
        }
      />
      <div className="space-y-6">
        <KpiRow data={p.data} models={p.models} pipeline={p.pipeline} />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <ChurnHero data={p.data} models={p.models} predictions={p.predictions} />
          </div>
          <PipelineCard pipeline={p.pipeline} />
        </div>

        <ModelRegistryCard models={p.models} />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <WarehouseCard data={p.data} />
          <FeatureImportanceCard
            fi={p.fi}
            championVersion={p.models?.champion_version}
          />
        </div>

        <ScoringPanel
          predictions={p.predictions}
          threshold={p.threshold}
          modelVersion={p.modelVersion}
          onScored={p.onScored}
        />
        <AtRiskTable
          predictions={p.predictions}
          threshold={p.threshold}
          shap={p.shap?.customers}
        />
        <RecentRunsCard runs={p.runs} />
      </div>

      <footer className="mt-10 flex items-center justify-between border-t border-[var(--line)] pt-4 font-mono text-[11px] text-[var(--muted)]">
        <span>RetentionFlow · dbt · Postgres 16 · MLflow · Dagster</span>
        <span>Pipeline {p.running ? "running…" : "idle"} · API :8000</span>
      </footer>
    </>
  );
}

export function PipelinePage({
  pipeline,
  data,
  championVersion,
  running,
  liveState,
  onRun,
}: {
  pipeline?: PipelineStatus;
  data?: WarehouseData;
  championVersion?: string | null;
  running: boolean;
  liveState: Record<string, string>;
  onRun: () => void;
}) {
  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Pipeline"
        description="dbt medallion build — staging views and the gold customer-features table. The asset graph lights up live as a rebuild runs."
      />
      <div className="space-y-6">
        <PipelineDag
          pipeline={pipeline}
          data={data}
          championVersion={championVersion}
          running={running}
          liveState={liveState}
          onRun={onRun}
        />
        <PipelineCard pipeline={pipeline} />
      </div>
    </>
  );
}

export function ModelsPage({
  models,
  fi,
  shap,
}: {
  models?: ModelRegistry;
  fi?: FeatureImportance;
  shap?: ShapData;
}) {
  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Models"
        description="MLflow registry — champion metrics, version history, feature importance, and SHAP attribution for the churn classifier."
      />
      <div className="space-y-6">
        <ModelRegistryCard models={models} />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <FeatureImportanceCard fi={fi} championVersion={models?.champion_version} />
          <ShapCard shap={shap} />
        </div>
      </div>
    </>
  );
}

export function WarehousePage({ data }: { data?: WarehouseData }) {
  return (
    <>
      <PageHeader
        eyebrow="Data"
        title="Warehouse"
        description="Postgres medallion schemas — raw Olist tables, the synthetic augmentation, and the analytics gold table."
      />
      <div className="space-y-6">
        <WarehouseCard data={data} />
        <WarehouseTables />
      </div>
    </>
  );
}

export function RunsPage({ runs }: { runs?: RunRecord[] }) {
  return (
    <>
      <PageHeader
        eyebrow="Data"
        title="Runs"
        description="History of pipeline rebuilds and batch-scoring runs triggered from the dashboard."
      />
      <RecentRunsCard runs={runs} />
    </>
  );
}

export function ScoringPage({
  predictions,
  shap,
  threshold,
  modelVersion,
  onScored,
}: {
  predictions?: Predictions;
  shap?: ShapData;
  threshold: number;
  modelVersion: string;
  onScored: (p: Predictions) => void;
}) {
  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Batch scoring"
        description="Score every customer in the gold table with the champion model. Predictions and SHAP land in the serving schema."
      />
      <div className="space-y-6">
        <ScoringPanel
          predictions={predictions}
          threshold={threshold}
          modelVersion={modelVersion}
          onScored={onScored}
        />
        <AtRiskTable
          predictions={predictions}
          threshold={threshold}
          shap={shap?.customers}
        />
      </div>
    </>
  );
}

export function ComingSoonPage({ title }: { title: string }) {
  return (
    <>
      <PageHeader
        eyebrow="Account"
        title={title}
        description="This section isn't built yet."
      />
      <Card title={title}>
        <div className="py-12 text-center text-[13px] text-[var(--muted)]">
          Coming soon
        </div>
      </Card>
    </>
  );
}
