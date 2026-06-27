import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, kzt, type Anomaly } from "../../lib/api";
import { Card, Badge, Spinner, Empty } from "../../components/ui";

const KIND_LABEL: Record<string, { label: string; tone: "danger" | "warning" }> = {
  price_jump: { label: "скачок цены >50%", tone: "danger" },
  nonresident_lt_resident: { label: "нерезидент < резидент", tone: "warning" },
  future_date: { label: "дата в будущем", tone: "warning" },
  nonpositive_price: { label: "цена ≤ 0", tone: "danger" },
  other: { label: "прочее", tone: "warning" },
};

export default function Anomalies() {
  const [rows, setRows] = useState<Anomaly[] | null>(null);

  useEffect(() => { api.anomalies().then(setRows).catch(() => setRows([])); }, []);

  if (!rows) return <div className="py-10"><Spinner label="Загрузка аномалий…" /></div>;

  const byKind = rows.reduce<Record<string, number>>((a, r) => { a[r.kind] = (a[r.kind] ?? 0) + 1; return a; }, {});

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-foreground">Аномалии</h1>
        <Badge tone={rows.length ? "danger" : "success"}>{rows.length} выявлено</Badge>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {Object.entries(byKind).map(([k, n]) => (
          <Badge key={k} tone={KIND_LABEL[k]?.tone ?? "warning"}>
            {KIND_LABEL[k]?.label ?? k}: {n}
          </Badge>
        ))}
      </div>

      {rows.length === 0 ? (
        <Card className="p-10"><Empty>Аномалий не обнаружено.</Empty></Card>
      ) : (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted text-muted-fg text-xs uppercase">
              <tr>
                <th className="text-left font-medium px-4 py-2.5">Тип</th>
                <th className="text-left font-medium px-4 py-2.5">Услуга</th>
                <th className="text-left font-medium px-4 py-2.5">Партнёр</th>
                <th className="text-right font-medium px-4 py-2.5">Резидент</th>
                <th className="text-left font-medium px-4 py-2.5">Детали</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.item_id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-2.5">
                    <Badge tone={KIND_LABEL[r.kind]?.tone ?? "warning"}>{KIND_LABEL[r.kind]?.label ?? r.kind}</Badge>
                  </td>
                  <td className="px-4 py-2.5">
                    {r.service_id ? (
                      <Link to={`/service/${r.service_id}`} className="text-slate-900 hover:text-primary">
                        {r.service_name ?? r.service_name_raw}
                      </Link>
                    ) : (
                      <span className="text-slate-700">{r.service_name_raw}</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-slate-700">{r.partner_name}</td>
                  <td className="px-4 py-2.5 text-right tnum">{kzt(r.price_resident_kzt)}</td>
                  <td className="px-4 py-2.5 text-xs text-muted-fg font-mono max-w-xs truncate" title={r.note}>{r.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
