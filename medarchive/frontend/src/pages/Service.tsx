import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, kzt, type PartnerPrice, type Service } from "../lib/api";
import { Card, Badge, Spinner, Empty, Icon } from "../components/ui";
import PriceHistoryChart from "../components/PriceHistoryChart";

export default function ServicePage() {
  const { id = "" } = useParams();
  const [svc, setSvc] = useState<Service | null>(null);
  const [rows, setRows] = useState<PartnerPrice[] | null>(null);
  const [sort, setSort] = useState<"price" | "date">("price");

  useEffect(() => {
    api.services().then((l) => setSvc(l.items.find((s) => s.service_id === id) ?? null));
  }, [id]);
  useEffect(() => {
    setRows(null);
    api.servicePartners(id, sort).then(setRows).catch(() => setRows([]));
  }, [id, sort]);

  const best = rows && rows.length ? rows.find((r) => r.price_resident_kzt != null) : null;

  return (
    <div className="max-w-4xl mx-auto">
      <Link to="/" className="text-sm text-primary hover:underline">← Назад к поиску</Link>

      <Card className="p-5 mt-3">
        <h1 className="text-2xl font-bold text-slate-900">{svc?.service_name ?? "Услуга"}</h1>
        <div className="mt-1 flex items-center gap-2 flex-wrap">
          {svc && <Badge tone="primary">{svc.category}</Badge>}
          {best?.price_resident_kzt != null && (
            <Badge tone="success">от {kzt(best.price_resident_kzt)}</Badge>
          )}
        </div>
      </Card>

      <div className="flex items-center justify-between mt-6 mb-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-fg">
          Партнёры {rows ? `(${rows.length})` : ""}
        </h2>
        <div className="flex gap-1 text-sm">
          {(["price", "date"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSort(s)}
              className={`px-2.5 py-1 rounded-md ${sort === s ? "bg-primary text-white" : "text-slate-600 hover:bg-slate-100"}`}
            >
              {s === "price" ? "по цене" : "по дате"}
            </button>
          ))}
        </div>
      </div>

      {!rows && <Spinner label="Загрузка цен…" />}
      {rows && rows.length === 0 && <Empty>Пока нет партнёров с этой услугой.</Empty>}

      <div className="space-y-2">
        {rows?.map((r) => (
          <Link key={r.partner_id} to={`/partner/${r.partner_id}`}>
            <Card className="p-4 hover:border-primary transition-colors cursor-pointer">
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="font-medium text-slate-900 truncate">{r.partner_name}</div>
                  <div className="text-sm text-muted-fg flex items-center gap-1">
                    {Icon.pin()} {r.city ?? "—"}
                    {r.effective_date && <span className="ml-2">· на {r.effective_date}</span>}
                    {r.is_verified && <span className="ml-2 text-success">✓ проверено</span>}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-lg font-bold text-slate-900 tnum">{kzt(r.price_resident_kzt)}</div>
                  <div className="text-xs text-muted-fg tnum">
                    нерезидент: {kzt(r.price_nonresident_kzt)}
                  </div>
                  {r.currency_original !== "KZT" && (
                    <div className="text-xs text-accent">ориг.: {r.price_original} {r.currency_original}</div>
                  )}
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      <PriceHistoryChart serviceId={id} />
    </div>
  );
}
