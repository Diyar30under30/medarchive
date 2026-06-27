import { useCallback, useEffect, useRef, useState } from "react";
import { api, kzt, type ReviewItem, type Service } from "../../lib/api";
import { Card, Badge, Button, Spinner, Empty, Icon } from "../../components/ui";

export default function Queue() {
  const [items, setItems] = useState<ReviewItem[] | null>(null);
  const [idx, setIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  // "Correct": search the whole directory or create a new service (ТЗ §4.3).
  const [correcting, setCorrecting] = useState(false);
  const [dirQ, setDirQ] = useState("");
  const [dirResults, setDirResults] = useState<Service[]>([]);
  const [newName, setNewName] = useState("");
  const [newCat, setNewCat] = useState("");
  const dirTimer = useRef<number>();

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

  const createNew = useCallback(async () => {
    if (!current || busy || !newName.trim()) return;
    setBusy(true);
    try {
      const r = await api.match({
        item_id: current.item_id,
        new_service_name: newName.trim(),
        new_service_category: newCat.trim() || undefined,
      });
      flash(`✓ создана услуга «${newName.trim()}»` + (r.learned_synonym ? ` · синоним «${r.learned_synonym}»` : ""));
      advance();
    } catch { flash("Ошибка создания"); } finally { setBusy(false); }
  }, [current, busy, newName, newCat, advance]);

  // Reset the correct panel whenever the focused item changes.
  useEffect(() => {
    setCorrecting(false); setDirQ(""); setDirResults([]); setNewName(""); setNewCat("");
  }, [current?.item_id]);

  // Debounced directory search for the "Correct" flow.
  useEffect(() => {
    if (!dirQ.trim()) { setDirResults([]); return; }
    window.clearTimeout(dirTimer.current);
    dirTimer.current = window.setTimeout(() => {
      api.services(dirQ, undefined, 8).then((l) => setDirResults(l.items)).catch(() => setDirResults([]));
    }, 200);
    return () => window.clearTimeout(dirTimer.current);
  }, [dirQ]);

  // Keyboard-first: C/Enter confirm top, R reject, J/K navigate, 1–5 pick candidate.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!current) return;
      // Don't hijack keys while typing in the correct/search fields.
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
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
          <Button
            variant="success"
            disabled={busy || items.length === 0}
            title="Принять все позиции с уверенностью ≥ 85%"
            onClick={async () => {
              setBusy(true);
              try {
                const r = await api.batchConfirm(0.85);
                flash(`✓ принято ${r.confirmed}` + (r.synonyms_learned ? ` · выучено ${r.synonyms_learned} синонимов` : ""));
                load();
              } catch { flash("Ошибка"); } finally { setBusy(false); }
            }}
          >
            принять все ≥85%
          </Button>
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

              {/* Correct: pick any service from the directory or create a new one (ТЗ §4.3). */}
              <div className="mt-4 pt-4 border-t border-slate-100">
                {!correcting ? (
                  <Button variant="outline" onClick={() => setCorrecting(true)} disabled={busy}>
                    исправить — выбрать из справочника / создать новую
                  </Button>
                ) : (
                  <div className="space-y-3">
                    <div>
                      <div className="text-xs uppercase tracking-wide text-muted-fg mb-1">Поиск по справочнику</div>
                      <input
                        autoFocus value={dirQ} onChange={(e) => setDirQ(e.target.value)}
                        placeholder="название услуги…"
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-ring/40"
                      />
                      {dirResults.length > 0 && (
                        <div className="mt-2 space-y-1 max-h-48 overflow-auto">
                          {dirResults.map((s) => (
                            <div key={s.service_id}
                              className="flex items-center justify-between gap-2 border border-slate-200 rounded-lg px-3 py-2">
                              <div className="min-w-0">
                                <div className="text-sm font-medium text-slate-900 truncate">{s.service_name}</div>
                                <div className="text-xs text-muted-fg">{s.category}</div>
                              </div>
                              <Button variant="success" onClick={() => confirm(s.service_id)} disabled={busy}>выбрать</Button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="border-t border-slate-100 pt-3">
                      <div className="text-xs uppercase tracking-wide text-muted-fg mb-1">Создать новую услугу</div>
                      <div className="flex flex-col sm:flex-row gap-2">
                        <input value={newName} onChange={(e) => setNewName(e.target.value)}
                          placeholder="название" className="flex-1 px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-ring/40" />
                        <input value={newCat} onChange={(e) => setNewCat(e.target.value)}
                          placeholder="категория" className="sm:w-48 px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-ring/40" />
                        <Button onClick={createNew} disabled={busy || !newName.trim()}>создать и сопоставить</Button>
                      </div>
                    </div>
                    <button onClick={() => setCorrecting(false)} className="text-xs text-muted-fg hover:text-slate-700">отмена</button>
                  </div>
                )}
              </div>

              <div className="mt-5 flex items-center gap-2">
                <Button variant="danger" onClick={reject} disabled={busy}>{Icon.x()} отклонить (R)</Button>
                <div className="ml-auto text-xs text-muted-fg">
                  C/Enter — принять · R — отклонить · J/K — навигация
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
