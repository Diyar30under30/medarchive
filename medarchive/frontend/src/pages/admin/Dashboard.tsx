import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid,
} from "recharts";
import { api, type Metrics } from "../../lib/api";
import { Card, StatCard, Spinner, Badge } from "../../components/ui";

const METHOD_COLORS: Record<string, string> = {
  exact: "#1e40af", synonym: "#2563eb", lexical: "#3b82f6", semantic: "#0ea5e9",
  manual: "#d97706", none: "#cbd5e1",
};

export default function Dashboard() {
  const [m, setM] = useState<Metrics | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    const load = () => api.metrics().then(setM).catch(() => setErr(true));
    load();
    const t = setInterval(load, 5000); // live refresh
    return () => clearInterval(t);
  }, []);

  if (err) return <Card className="p-6 text-destructive">API недоступен. Запустите бэкенд на :8000.</Card>;
  if (!m) return <div className="py-10"><Spinner label="Загрузка метрик…" /></div>;

  const pct = Math.round(m.auto_normalization_rate * 100);
  const methodData = Object.entries(m.matches_by_method)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-foreground">Панель оператора</h1>
        <Badge tone="muted">обновлено {new Date(m.generated_at).toLocaleTimeString("ru-RU")}</Badge>
      </div>

      {/* Headline metric */}
      <div className="grid lg:grid-cols-4 gap-3 mb-3">
        <Card className="p-6 lg:col-span-1 bg-primary text-white">
          <div className="text-xs font-medium uppercase tracking-wide text-blue-100">Авто-нормализация</div>
          <div className="mt-2 text-6xl font-bold tnum">{pct}<span className="text-3xl">%</span></div>
          <div className="mt-1 text-sm text-blue-100">
            {m.auto_matched} из {m.positions_total} позиций · цель ≥ 70%
          </div>
          <div className="mt-3 h-2 bg-blue-900/40 rounded-full overflow-hidden">
            <div className="h-full bg-accent rounded-full transition-all" style={{ width: `${pct}%` }} />
          </div>
        </Card>
        <StatCard label="Документов обработано" value={m.documents_total}
          sub={`${m.documents_errored} с ошибкой`} />
        <StatCard label="Очередь проверки" value={m.review_queue_open}
          tone={m.review_queue_open > 0 ? "primary" : "default"}
          sub={<Link to="/admin/queue" className="text-primary hover:underline">открыть очередь →</Link>} />
        <StatCard label="Аномалий выявлено" value={m.anomalies_flagged}
          tone={m.anomalies_flagged > 0 ? "danger" : "default"} sub="цены/даты/дубли" />
      </div>

      <div className="grid lg:grid-cols-3 gap-3">
        <StatCard label="Услуг в справочнике" value={m.services_in_directory} />
        <StatCard label="Позиций всего" value={m.positions_total}
          sub={`${m.unmatched} без сопоставления`} />
        <StatCard label="Сопоставлено" value={m.matched_any} tone="success" />
      </div>

      <div className="grid lg:grid-cols-2 gap-3 mt-3">
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Сопоставления по методу</h2>
          {methodData.length === 0 ? (
            <div className="text-sm text-muted-fg py-8 text-center">Нет данных</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={methodData} margin={{ left: -16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#64748b" }} />
                <YAxis tick={{ fontSize: 12, fill: "#64748b" }} allowDecimals={false} />
                <Tooltip cursor={{ fill: "#f1f5f9" }} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {methodData.map((d) => (
                    <Cell key={d.name} fill={METHOD_COLORS[d.name] ?? "#3b82f6"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card className="p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Качество по форматам</h2>
          <div className="space-y-2.5">
            {Object.entries(m.per_format_success).map(([fmt, d]) => (
              <div key={fmt}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium text-slate-700">{fmt}</span>
                  <span className="text-muted-fg tnum">{d.ok}/{d.total} · {Math.round(d.success_rate * 100)}%</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-secondary rounded-full" style={{ width: `${d.success_rate * 100}%` }} />
                </div>
              </div>
            ))}
            {Object.keys(m.per_format_success).length === 0 && (
              <div className="text-sm text-muted-fg">Загрузите архив, чтобы увидеть статистику.</div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
