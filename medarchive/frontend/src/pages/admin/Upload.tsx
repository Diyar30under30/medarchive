import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Job } from "../../lib/api";
import { Card, Badge, Button, Spinner, Icon } from "../../components/ui";

const STATUS_TONE: Record<string, "muted" | "primary" | "success" | "danger"> = {
  pending: "muted", processing: "primary", done: "success", error: "danger",
};

export default function Upload() {
  const [job, setJob] = useState<Job | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const poll = useRef<number>();
  const fileRef = useRef<HTMLInputElement>(null);

  const refreshJobs = () => api.jobs().then(setJobs).catch(() => {});
  useEffect(() => { refreshJobs(); }, []);

  const upload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".zip")) { setErr("Нужен ZIP-архив"); return; }
    setErr(null); setBusy(true);
    try {
      const j = await api.ingest(file);
      setJob(j);
      window.clearInterval(poll.current);
      poll.current = window.setInterval(async () => {
        const updated = await api.job(j.job_id);
        setJob(updated);
        if (updated.status === "done" || updated.status === "error") {
          window.clearInterval(poll.current);
          refreshJobs();
        }
      }, 1500);
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };

  useEffect(() => () => window.clearInterval(poll.current), []);

  const progress = job && job.total_files ? (job.processed_files / job.total_files) * 100 : 0;

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-xl font-bold text-foreground mb-4">Загрузка архива</h1>

      <Card
        className={`p-10 border-2 border-dashed text-center transition-colors ${
          drag ? "border-primary bg-blue-50/50" : "border-slate-300"
        }`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f) upload(f); }}
      >
        <div className="flex justify-center text-primary mb-2">{Icon.upload("w-8 h-8")}</div>
        <div className="font-medium text-slate-800">Перетащите ZIP-архив прайс-листов сюда</div>
        <div className="text-sm text-muted-fg mt-1">или</div>
        <div className="mt-3">
          <Button onClick={() => fileRef.current?.click()} disabled={busy}>
            {busy ? "Загрузка…" : "Выбрать файл"}
          </Button>
          <input ref={fileRef} type="file" accept=".zip" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); }} />
        </div>
        {err && <div className="mt-3 text-sm text-destructive">{err}</div>}
      </Card>

      {job && (
        <Card className="p-5 mt-4">
          <div className="flex items-center justify-between mb-2">
            <div className="font-medium text-slate-800">{job.archive_name}</div>
            <Badge tone={STATUS_TONE[job.status]}>{job.status}</Badge>
          </div>
          <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full bg-primary rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
          <div className="mt-2 flex items-center justify-between text-sm text-muted-fg tnum">
            <span>{job.processed_files} / {job.total_files} файлов</span>
            <span>{job.error_count > 0 && <span className="text-destructive">{job.error_count} ошибок</span>}</span>
          </div>
          {(job.status === "processing" || job.status === "pending") && (
            <div className="mt-2"><Spinner label="Обработка…" /></div>
          )}
          {job.status === "done" && (
            <div className="mt-3 flex gap-2">
              <Link to="/admin"><Button variant="outline">смотреть метрики →</Button></Link>
              <Link to="/admin/queue"><Button>открыть очередь проверки →</Button></Link>
            </div>
          )}
        </Card>
      )}

      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-fg mt-6 mb-2">Недавние задачи</h2>
      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted text-muted-fg text-xs uppercase">
            <tr>
              <th className="text-left font-medium px-4 py-2">Архив</th>
              <th className="text-center font-medium px-4 py-2">Статус</th>
              <th className="text-right font-medium px-4 py-2">Файлов</th>
              <th className="text-right font-medium px-4 py-2">Ошибок</th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-muted-fg">Пока нет задач.</td></tr>
            )}
            {jobs.map((j) => (
              <tr key={j.job_id} className="border-t border-slate-100">
                <td className="px-4 py-2 text-slate-800">{j.archive_name}</td>
                <td className="px-4 py-2 text-center"><Badge tone={STATUS_TONE[j.status]}>{j.status}</Badge></td>
                <td className="px-4 py-2 text-right tnum">{j.processed_files}/{j.total_files}</td>
                <td className="px-4 py-2 text-right tnum">{j.error_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
