import { useCallback, useEffect, useState } from "react";
import { api, kzt, type ReviewItem } from "../../lib/api";
import { Card, Badge, Button, Spinner, Empty, Icon } from "../../components/ui";

export default function Queue() {
  const [items, setItems] = useState<ReviewItem[] | null>(null);
  const [idx, setIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(() => {
    api.unmatched("open").then((q) => { setItems(q); setIdx(0); }).catch(() => setItems([]));
  }, []);
  useEffect(load, [load]);

  const current = items?.[idx];

  const advance = useCallback(() => {
    setItems((prev) => {
      if (!prev) return prev;
      const next = prev.filter((_, i) => i !== idx);
      setIdx((i) => Math.min(i, Math.max(0, next.length - 1)));
      return next;
    });
  }, [idx]);

  const flash = (msg: string) => { setToast(msg); window.setTimeout(() => setToast(null), 2500); };

  const confirm = useCallback(async (serviceId: string) => {
    if (!current || busy) return;
    setBusy(true);
    try {
      const r = await api.match({ item_id: current.item_id, service_id: serviceId });
      flash(r.learned_synonym ? `✓ сохранено · выучен синоним «${r.learned_synonym}»` : "✓ сопоставлено");
      advance();
    } catch { flash("Ошибка сохранения"); } finally { setBusy(false); }
  }, [current, busy, advance]);

  const reject = useCallback(async () => {
    if (!current || busy) return;
    setBusy(true);
    try { await api.match({ item_id: current.item_id, reject: true }); flash("Отклонено"); advance(); }
    catch { flash("Ошибка"); } finally { setBusy(false); }
  }, [current, busy, advance]);

  // Keyboard-first: C/Enter confirm top, R reject, J/K navigate, 1–5 pick candidate.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!current) return;
      if (e.key === "c" || e.key === "Enter") { if (current.candidates[0]) confirm(current.candidates[0].service_id); }
      else if (e.key === "r") reject();
      else if (e.key === "j") setIdx((i) => Math.min((items?.length ?? 1) - 1, i + 1));
      else if (e.key === "k") setIdx((i) => Math.max(0, i - 1));
      else if (/^[1-5]$/.test(e.key)) { const c = current.candidates[+e.key - 1]; if (c) confirm(c.service_id); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [current, items, confirm, reject]);

  if (!items) return <div className="py-10"><Spinner label="Загрузка очереди…" /></div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-foreground">Очередь проверки</h1>
        <div className="flex items-center gap-2">
          <Badge tone={items.length ? "primary" : "success"}>{items.length} в очереди</Badge>
          <Button variant="outline" onClick={load}>обновить</Button>
        </div>
      </div>

      {items.length === 0 ? (
        <Card className="p-10"><Empty>Очередь пуста — все позиции проверены. 🎯</Empty></Card>
      ) : (
        <div className="grid lg:grid-cols-[280px_1fr] gap-4">
          {/* list */}
          <Card className="p-2 max-h-[70vh] overflow-auto">
            {items.map((it, i) => (
              <button
                key={it.review_id}
                onClick={() => setIdx(i)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 ${
                  i === idx ? "bg-primary text-white" : "hover:bg-slate-100 text-slate-700"
                }`}
              >
                <div className="truncate font-medium">{it.service_name_raw}</div>
                <div className={`truncate text-xs ${i === idx ? "text-blue-100" : "text-muted-fg"}`}>
                  {it.partner_name}
                </div>
              </button>
            ))}
          </Card>

          {/* detail */}
          {current && (
            <Card className="p-5">
              <div className="grid sm:grid-cols-2 gap-4 pb-4 border-b border-slate-100">
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted-fg mb-1">Исходный фрагмент</div>
                  <div className="font-mono text-sm bg-slate-50 border border-slate-200 rounded-lg p-3 text-slate-800">
                    {current.source_fragment ?? current.service_name_raw}
                  </div>
                  <div className="mt-2 text-sm text-slate-600">
                    Партнёр: <span className="font-medium">{current.partner_name}</span>
                    {current.specialty_hint && <> · {current.specialty_hint}</>}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted-fg mb-1">Извлечённые данные</div>
                  <div className="text-2xl font-bold text-slate-900">{current.service_name_raw}</div>
                  <div className="mt-1 text-sm text-slate-600 tnum">
                    резидент: {kzt(current.price_resident_kzt)} · нерезидент: {kzt(current.price_nonresident_kzt)}
                  </div>
                </div>
              </div>

              <div className="mt-4">
                <div className="text-xs uppercase tracking-wide text-muted-fg mb-2">
                  Предлагаемые соответствия (нажмите 1–5)
                </div>
                {current.candidates.length === 0 && (
                  <div className="text-sm text-muted-fg mb-3">Кандидатов нет — отклоните или сопоставьте вручную.</div>
                )}
                <div className="space-y-2">
                  {current.candidates.slice(0, 5).map((c, i) => (
                    <div key={c.service_id}
                      className="flex items-center justify-between gap-3 border border-slate-200 rounded-lg p-3 hover:border-primary transition-colors">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <kbd className="text-xs bg-slate-100 border border-slate-300 rounded px-1.5 py-0.5 text-slate-500">{i + 1}</kbd>
                          <span className="font-medium text-slate-900 truncate">{c.service_name}</span>
                        </div>
                        <div className="text-xs text-muted-fg mt-0.5">
                          {c.category} · лекс {(c.lexical * 100).toFixed(0)}% · сем {(c.semantic * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge tone={c.score >= 0.85 ? "success" : "warning"}>{(c.score * 100).toFixed(0)}%</Badge>
                        <Button variant="success" onClick={() => confirm(c.service_id)} disabled={busy}>
                          {Icon.check()} принять
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-5 flex items-center gap-2">
                <Button variant="danger" onClick={reject} disabled={busy}>{Icon.x()} отклонить (R)</Button>
                <div className="ml-auto text-xs text-muted-fg">
                  C/Enter — принять лучший · R — отклонить · J/K — навигация
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {toast && (
        <div role="status" aria-live="polite"
          className="fixed bottom-5 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-sm px-4 py-2 rounded-lg shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
