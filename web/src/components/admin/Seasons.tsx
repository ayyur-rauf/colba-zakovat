"use client";

// Boshqaruv — mavsumlar (o'quv yillari): yaratish va joriysini tanlash.

import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import { Badge, Button, Card, CardHeader, Field, Notice, PageTitle } from "../ui";

type Season = { id: number; name: string; start_date: string; end_date: string; is_active: boolean };

export default function AdminSeasons() {
  const seasons = useApi<Season[]>("manage/seasons");
  const act = useAction();
  const year = new Date().getFullYear();
  const [v, setV] = useState({ name: `${year}–${year + 1}`, start_date: `${year}-09-01`, end_date: `${year + 1}-08-31` });

  return (
    <>
      <PageTitle title="Mavsumlar" subtitle="Mavsum = o'quv yili. Ballar va reytinglar joriy mavsum bo'yicha yig'iladi" />
      <Notice error={act.error ?? seasons.error} notice={act.notice} onClose={act.clear} />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(seasons.data ?? []).map((s) => (
          <Card key={s.id} className={`p-5 ${s.is_active ? "border-accent/60" : ""}`}>
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">{s.name}</h3>
              {s.is_active ? <Badge tone="accent">Joriy</Badge> : <Badge>Arxiv / kelgusi</Badge>}
            </div>
            <p className="mt-1 text-sm text-muted">
              {s.start_date.split("-").reverse().join(".")} — {s.end_date.split("-").reverse().join(".")}
            </p>
            {!s.is_active && (
              <Button
                variant="soft"
                className="mt-4"
                disabled={act.busy}
                onClick={() =>
                  window.confirm(`"${s.name}" joriy mavsum qilinsinmi? Reytinglar va yangi o'yinlar shu mavsumga o'tadi.`) &&
                  act.run(() => api(`manage/seasons/${s.id}/activate`, { method: "POST" }), "Joriy mavsum o'zgardi").then(seasons.reload)
                }
              >
                Joriy qilish
              </Button>
            )}
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader title="Yangi mavsum" subtitle="Mavsumlar ustma-ust tushmasligi kerak" />
        <form
          className="grid gap-4 p-5 md:grid-cols-4"
          onSubmit={async (e) => {
            e.preventDefault();
            const ok = await act.run(() => api("manage/seasons", { method: "POST", body: v }), "Mavsum yaratildi");
            if (ok) seasons.reload();
          }}
        >
          <Field label="Nomi">
            <input className="field" required value={v.name} onChange={(e) => setV({ ...v, name: e.target.value })} />
          </Field>
          <Field label="Boshlanishi">
            <input className="field" type="date" required value={v.start_date} onChange={(e) => setV({ ...v, start_date: e.target.value })} />
          </Field>
          <Field label="Tugashi">
            <input className="field" type="date" required value={v.end_date} onChange={(e) => setV({ ...v, end_date: e.target.value })} />
          </Field>
          <div className="flex items-end">
            <Button type="submit" disabled={act.busy}>
              Yaratish
            </Button>
          </div>
        </form>
      </Card>
    </>
  );
}
