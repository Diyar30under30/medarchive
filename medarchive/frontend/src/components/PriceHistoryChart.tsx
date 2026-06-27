import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { api, kzt, type PriceHistory } from "../lib/api";
import { Card, Spinner } from "./ui";

const LINE_COLORS = ["#1e40af", "#d97706", "#059669", "#3b82f6", "#7c3aed", "#dc2626"];

export default function PriceHistoryChart({ serviceId }: { serviceId: string }) {
  const [hist, setHist] = useState<PriceHistory | null>(null);

  useEffect(() => { api.priceHistory(serviceId).then(setHist).catch(() => setHist(null)); }, [serviceId]);

  if (!hist) return <Spinner label="Загрузка истории…" />;
  if (hist.entries.length < 2) return null; // nothing to plot

  // Pivot entries → [{ date, [partner]: price }], one Line per partner.
  const partners = Array.from(new Set(hist.entries.map((e) => e.partner_name ?? "—")));
  const dates = Array.from(new Set(hist.entries.map((e) => e.effective_date ?? ""))).filter(Boolean).sort();
  const data = dates.map((date) => {
    const row: Record<string, number | string> = { date };
    for (const e of hist.entries) {
      if (e.effective_date === date && e.price_resident_kzt != null) {
        row[e.partner_name ?? "—"] = e.price_resident_kzt;
      }
    }
    return row;
  });

  return (
    <Card className="p-5 mt-6">
      <h2 className="text-sm font-semibold text-slate-700 mb-3">История цен (резидент)</h2>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ left: 4, right: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#64748b" }} />
          <YAxis tick={{ fontSize: 12, fill: "#64748b" }}
            tickFormatter={(v) => new Intl.NumberFormat("ru-RU").format(v as number)} width={64} />
          <Tooltip formatter={(v) => kzt(v as number)} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {partners.map((p, i) => (
            <Line key={p} type="monotone" dataKey={p} stroke={LINE_COLORS[i % LINE_COLORS.length]}
              strokeWidth={2} dot={{ r: 3 }} connectNulls />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
