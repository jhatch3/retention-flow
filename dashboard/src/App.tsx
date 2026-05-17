import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  BarChart3,
  Boxes,
  CircleCheck,
  Database,
  GitBranch,
  TrendingDown,
  Users,
} from "lucide-react";
import { api } from "./api";
import type {
  FeatureImportance,
  ModelRegistry,
  PipelineStatus,
  Predictions,
  WarehouseData,
} from "./api";
import { Card, Kpi, Skeleton, Stat, chartTooltip } from "./ui";
import { ScoringPanel } from "./ScoringPanel";

export default function App() {
  const [pipeline, setPipeline] = useState<PipelineStatus>();
  const [data, setData] = useState<WarehouseData>();
  const [models, setModels] = useState<ModelRegistry>();
  const [fi, setFi] = useState<FeatureImportance>();
  const [preds, setPreds] = useState<Predictions>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    api.pipeline().then(setPipeline).catch((e) => setError(String(e)));
    api.data().then(setData).catch((e) => setError(String(e)));
    api.models().then(setModels).catch((e) => setError(String(e)));
    api.featureImportance().then(setFi).catch((e) => setError(String(e)));
    api.predictions().then(setPreds).catch((e) => setError(String(e)));
  }, []);

  const champion = models?.versions.find((v) => v.is_champion);
  const cm = models?.champion_metrics ?? {};
  const splitData = data
    ? Object.entries(data.splits).map(([name, rows]) => ({ name, rows }))
    : [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/50 px-8 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <h1 className="text-lg font-bold tracking-tight">RetentionFlow</h1>
            <p className="text-xs text-slate-500">
              churn pipeline — dbt · Postgres · MLflow
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span
              className={`h-2 w-2 rounded-full ${error ? "bg-red-500" : "bg-emerald-500"}`}
            />
            {error ? "API unreachable" : "Connected"}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-8">
        {error && (
          <div className="rounded-lg border border-red-800 bg-red-950 p-3 text-sm text-red-300">
            {error} — is the API running on :8000?
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Kpi
            icon={<Users size={20} />}
            label="customers (gold)"
            value={data ? data.gold_rows.toLocaleString() : "—"}
          />
          <Kpi
            icon={<TrendingDown size={20} />}
            label="churn rate"
            accent="text-amber-400"
            value={data ? `${(data.gold_churn_rate * 100).toFixed(1)}%` : "—"}
          />
          <Kpi
            icon={<Activity size={20} />}
            label="champion ROC-AUC"
            accent="text-sky-400"
            value={champion?.roc_auc != null ? champion.roc_auc.toFixed(3) : "—"}
          />
          <Kpi
            icon={<CircleCheck size={20} />}
            label="dbt tests passed"
            accent="text-emerald-400"
            value={
              pipeline?.available
                ? `${pipeline.tests?.pass ?? 0}/${pipeline.tests_total}`
                : "—"
            }
          />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card
            title="Pipeline — dbt"
            icon={<GitBranch size={15} />}
            right={pipeline?.generated_at?.slice(0, 16).replace("T", " ")}
          >
            {!pipeline ? (
              <Skeleton className="h-44 w-full" />
            ) : pipeline.available ? (
              <>
                <div className="mb-4 flex gap-8">
                  <Stat
                    label="models built"
                    value={`${pipeline.models_ok}/${pipeline.model_count}`}
                    accent="text-emerald-400"
                  />
                  <Stat
                    label="tests"
                    value={`${pipeline.tests?.pass ?? 0} pass`}
                    accent={
                      (pipeline.tests?.fail ?? 0) > 0
                        ? "text-red-400"
                        : "text-emerald-400"
                    }
                  />
                </div>
                <div className="max-h-44 overflow-auto rounded-lg border border-slate-800">
                  {pipeline.models?.map((m) => (
                    <div
                      key={m.name}
                      className="flex items-center justify-between border-b border-slate-800/60 px-3 py-1.5 text-xs last:border-0"
                    >
                      <span className="flex items-center gap-2">
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            m.status === "success" ? "bg-emerald-500" : "bg-red-500"
                          }`}
                        />
                        <span className="font-mono text-slate-300">{m.name}</span>
                      </span>
                      <span className="tabular-nums text-slate-600">
                        {m.execution_time}s
                      </span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-500">
                No dbt run found — run <code>dbt build</code>.
              </p>
            )}
          </Card>

          <Card title="Warehouse — Postgres" icon={<Database size={15} />}>
            {data ? (
              <>
                <div className="mb-4 flex flex-wrap gap-6">
                  <Stat label="gold rows" value={data.gold_rows.toLocaleString()} />
                  <Stat label="raw orders" value={data.raw_orders.toLocaleString()} />
                  <Stat
                    label="synthetic orders"
                    value={data.synthetic_orders.toLocaleString()}
                  />
                </div>
                <ResponsiveContainer width="100%" height={110}>
                  <BarChart data={splitData}>
                    <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                    <YAxis stroke="#64748b" fontSize={11} />
                    <Tooltip contentStyle={chartTooltip} cursor={{ fill: "#1e293b" }} />
                    <Bar dataKey="rows" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <div className="mt-3 space-y-1">
                  {data.segments.map((s) => (
                    <div key={s.segment} className="flex justify-between text-xs">
                      <span className="text-slate-400">
                        {s.segment} customers ({s.rows.toLocaleString()})
                      </span>
                      <span className="font-semibold tabular-nums text-amber-400">
                        {(s.churn_rate * 100).toFixed(1)}% churn
                      </span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <Skeleton className="h-56 w-full" />
            )}
          </Card>

          <Card
            title="Model registry — MLflow"
            icon={<Boxes size={15} />}
            right={champion ? `champion v${champion.version}` : undefined}
          >
            {models ? (
              <>
                <div className="mb-4 flex flex-wrap gap-6">
                  <Stat
                    label="ROC-AUC"
                    value={cm.roc_auc?.toFixed(3) ?? "—"}
                    accent="text-sky-400"
                  />
                  <Stat label="PR-AUC" value={cm.pr_auc?.toFixed(3) ?? "—"} />
                  <Stat label="precision" value={cm.precision?.toFixed(3) ?? "—"} />
                  <Stat
                    label="recall"
                    value={cm.recall?.toFixed(3) ?? "—"}
                    accent="text-emerald-400"
                  />
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs uppercase text-slate-500">
                      <th className="pb-2 text-left">version</th>
                      <th className="pb-2 text-right">ROC-AUC</th>
                      <th className="pb-2 text-right">threshold</th>
                    </tr>
                  </thead>
                  <tbody>
                    {models.versions.map((v) => (
                      <tr key={v.version} className="border-t border-slate-800">
                        <td className="py-1.5">
                          v{v.version}
                          {v.is_champion && (
                            <span className="ml-2 rounded bg-emerald-900 px-1.5 py-0.5 text-xs text-emerald-300">
                              champion
                            </span>
                          )}
                        </td>
                        <td className="text-right tabular-nums">{v.roc_auc ?? "—"}</td>
                        <td className="text-right tabular-nums">
                          {v.decision_threshold ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : (
              <Skeleton className="h-56 w-full" />
            )}
          </Card>

          <Card
            title="Feature importance — champion model"
            icon={<BarChart3 size={15} />}
          >
            {fi ? (
              <ResponsiveContainer width="100%" height={420}>
                <BarChart data={fi.features} layout="vertical" margin={{ left: 30 }}>
                  <XAxis type="number" stroke="#64748b" fontSize={10} />
                  <YAxis
                    type="category"
                    dataKey="feature"
                    stroke="#64748b"
                    fontSize={10}
                    width={140}
                  />
                  <Tooltip contentStyle={chartTooltip} cursor={{ fill: "#1e293b" }} />
                  <Bar dataKey="importance" fill="#38bdf8" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Skeleton className="h-96 w-full" />
            )}
          </Card>

          <div className="lg:col-span-2">
            <ScoringPanel preds={preds} onScored={setPreds} />
          </div>
        </div>
      </main>
    </div>
  );
}
