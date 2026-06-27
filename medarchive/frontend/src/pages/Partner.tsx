import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, kzt, type Partner, type PriceItem } from "../lib/api";
import { Card, Badge, Spinner, Empty, Icon } from "../components/ui";

export default function PartnerPage() {
  const { id = "" } = useParams();
  const [partner, setPartner] = useState<Partner | null>(null);
  const [items, setItems] = useState<PriceItem[] | null>(null);

  useEffect(() => {
    api.partners().then((ps) => setPartner(ps.find((p) => p.partner_id === id) ?? null));
    api.partnerServices(id).then(setItems).catch(() => setItems([]));
  }, [id]);

  const freshness = items?.reduce<string | null>((a, it) => {
    if (!it.effective_date) return a;
    return !a || it.effective_date > a ? it.effective_date : a;
  }, null);

  return (
    <div className="max-w-4xl mx-auto">
      <Link to="/" className="text-sm text-primary hover:underline">← Назад к поиску</Link>

      <Card className="p-5 mt-3">
        <h1 className="text-2xl font-bold text-slate-900">{partner?.name ?? "Партнёр"}</h1>
        <div className="mt-2 grid sm:grid-cols-2 gap-x-6 gap-y-1 text-sm text-slate-600">
          {partner?.city && <div className="flex items-center gap-1">{Icon.pin()} {partner.city}</div>}
          {partner?.address && <div>{partner.address}</div>}
          {partner?.contact_phone && <div>тел.: {partner.contact_phone}</div>}
          {partner?.bin && <div>БИН: <span className="tnum">{partner.bin}</span></div>}
        </div>
        {freshness && (
          <div className="mt-3"><Badge tone="muted">прайс актуален на {freshness}</Badge></div>
        )}
      </Card>

      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-fg mt-6 mb-2">
        Прайс-лист {items ? `(${items.length})` : ""}
      </h2>

      {!items && <Spinner label="Загрузка прайс-листа…" />}
      {items && items.length === 0 && <Empty>Нет активных позиций.</Empty>}

      {items && items.length > 0 && (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted text-muted-fg text-xs uppercase">
              <tr>
                <th className="text-left font-medium px-4 py-2.5">Услуга</th>
                <th className="text-right font-medium px-4 py-2.5">Резидент</th>
                <th className="text-right font-medium px-4 py-2.5">Нерезидент</th>
                <th className="text-center font-medium px-4 py-2.5">Статус</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.item_id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-2.5">
                    {it.service_id ? (
                      <Link to={`/service/${it.service_id}`} className="text-slate-900 hover:text-primary">
                        {it.service_name ?? it.service_name_raw}
                      </Link>
                    ) : (
                      <span className="text-slate-500" title={`исходное: ${it.service_name_raw}`}>
                        {it.service_name_raw}
                      </span>
                    )}
                    {it.service_name && it.service_name_raw !== it.service_name && (
                      <span className="block text-xs text-muted-fg">исходно: {it.service_name_raw}</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right tnum">{kzt(it.price_resident_kzt)}</td>
                  <td className="px-4 py-2.5 text-right tnum text-muted-fg">{kzt(it.price_nonresident_kzt)}</td>
                  <td className="px-4 py-2.5 text-center">
                    {it.is_verified ? <Badge tone="success">✓</Badge> : <Badge tone="warning">на проверке</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
