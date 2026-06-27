import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, type SearchResult } from "../lib/api";
import { Card, Badge, Spinner, Empty, Icon } from "../components/ui";

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const timer = useRef<number>();

  useEffect(() => {
    if (!q.trim()) {
      setRes(null);
      return;
    }
    setLoading(true);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      api.search(q).then(setRes).catch(() => setRes(null)).finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timer.current);
  }, [q]);

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mt-6 mb-8">
        <h1 className="text-3xl font-bold text-foreground">Поиск медицинских услуг</h1>
        <p className="mt-2 text-muted-fg">
          Найдите услугу и сравните цены партнёров — для резидентов и нерезидентов.
        </p>
      </div>

      <div className="relative">
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-fg">{Icon.search()}</span>
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Например: ОАК, Глюкоза, УЗИ, Консультация…"
          aria-label="Поиск услуг и партнёров"
          className="w-full pl-11 pr-4 py-3.5 rounded-xl border border-slate-300 bg-surface text-base shadow-card focus:outline-none focus:ring-2 focus:ring-ring/40 focus:border-primary"
        />
      </div>

      <div className="mt-5 min-h-[200px]">
        {loading && <div className="py-6"><Spinner label="Поиск…" /></div>}
        {!loading && q && res && res.services.length === 0 && res.partners.length === 0 && (
          <Empty>Ничего не найдено по запросу «{q}».</Empty>
        )}

        {res && res.services.length > 0 && (
          <section className="mb-6">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-fg mb-2">
              Услуги ({res.services.length})
            </h2>
            <div className="space-y-2">
              {res.services.map((s) => (
                <Link key={s.service_id} to={`/service/${s.service_id}`}>
                  <Card className="p-3.5 hover:border-primary transition-colors flex items-center justify-between cursor-pointer">
                    <div>
                      <div className="font-medium text-slate-900">{s.service_name}</div>
                      <div className="text-sm text-muted-fg">{s.category}</div>
                    </div>
                    <Badge tone="primary">смотреть цены →</Badge>
                  </Card>
                </Link>
              ))}
            </div>
          </section>
        )}

        {res && res.partners.length > 0 && (
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-fg mb-2">
              Партнёры ({res.partners.length})
            </h2>
            <div className="grid sm:grid-cols-2 gap-2">
              {res.partners.map((p) => (
                <Link key={p.partner_id} to={`/partner/${p.partner_id}`}>
                  <Card className="p-3.5 hover:border-primary transition-colors cursor-pointer h-full">
                    <div className="font-medium text-slate-900">{p.name}</div>
                    <div className="text-sm text-muted-fg flex items-center gap-1 mt-0.5">
                      {Icon.pin()} {p.city ?? "—"}
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          </section>
        )}

        {!q && (
          <Card className="p-6 text-sm text-muted-fg">
            <div className="font-medium text-slate-700 mb-1">Подсказка</div>
            Поиск понимает аббревиатуры и варианты написания: «ОАК», «CBC», «б/х»,
            «УЗИ ОБП» — всё сопоставляется с эталонным справочником услуг.
          </Card>
        )}
      </div>
    </div>
  );
}
