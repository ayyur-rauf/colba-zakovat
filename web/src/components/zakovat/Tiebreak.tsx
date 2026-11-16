"use client";

// Teng jamoalar uchun qo'shimcha o'yin yaratish (o'yin ichida yoki mavsum reytingida).

import { useState } from "react";
import { api } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { Badge, Button, Card, CardHeader, Field, Notice } from "../ui";

export type TieGroup = { group: number; place: number | null; teams: { id: number; name: string }[] };

export function groupTies(rows: { place: number | null; tie_group: number | null; team: { id: number; name: string } }[]): TieGroup[] {
  const map = new Map<number, TieGroup>();
  for (const r of rows) {
    if (!r.tie_group) continue;
    const g = map.get(r.tie_group) ?? { group: r.tie_group, place: r.place, teams: [] };
    g.teams.push(r.team);
    map.set(r.tie_group, g);
  }
  return [...map.values()];
}

export default function TiebreakPanel({ ties, endpoint, onCreated }: { ties: TieGroup[]; endpoint: string; onCreated: () => void }) {
  const act = useAction();
  const [open, setOpen] = useState<number | null>(null);
  const [when, setWhen] = useState("");
  const [questions, setQuestions] = useState("6");
  if (ties.length === 0) return null;

  return (
    <Card className="border-warning/40">
      <CardHeader
        title="⚖ Teng jamoalar — qo'shimcha o'yin"
        subtitle="Ball ham, J ham teng. Qo'shimcha o'yin faqat o'rinni aniqlaydi, ball bermaydi."
      />
      <div className="space-y-3 p-5">
        <Notice error={act.error} notice={act.notice} onClose={act.clear} />
        {ties.map((t) => (
          <div key={t.group} className="rounded-xl border border-line bg-bg-elev/60 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="amber">{t.place}-o&apos;rin uchun</Badge>
                {t.teams.map((x) => (
                  <span key={x.id} className="font-medium">
                    {x.name}
                  </span>
                ))}
              </div>
              <Button variant="soft" onClick={() => setOpen(open === t.group ? null : t.group)}>
                Qo&apos;shimcha o&apos;yin yaratish
              </Button>
            </div>
            {open === t.group && (
              <form
                className="mt-3 flex flex-wrap items-end gap-3"
                onSubmit={async (e) => {
                  e.preventDefault();
                  const ok = await act.run(
                    () =>
                      api(endpoint, {
                        method: "POST",
                        body: { team_ids: t.teams.map((x) => x.id), starts_at: new Date(when).toISOString(), questions: Number(questions) },
                      }),
                    "Qo'shimcha o'yin yaratildi — O'yinlar ro'yxatida",
                  );
                  if (ok) {
                    setOpen(null);
                    onCreated();
                  }
                }}
              >
                <Field label="Vaqti">
                  <input className="field w-auto" type="datetime-local" required value={when} onChange={(e) => setWhen(e.target.value)} />
                </Field>
                <Field label="Savollar soni">
                  <input className="field w-24" type="number" min={1} max={36} value={questions} onChange={(e) => setQuestions(e.target.value)} />
                </Field>
                <Button type="submit" disabled={act.busy}>
                  Yaratish
                </Button>
              </form>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
