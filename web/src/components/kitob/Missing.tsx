"use client";

// Izoh yubormagan xodimlar va ularga muddatni uzaytirish (tashkilotchi).

import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import { Badge, Button, formatDate, Notice } from "../ui";

type Missing = { submitted: number; items: { id: number; name: string; branch: string; extended_until: string | null }[] };

/** Yangi muddat: umumiy muddat (yoki hozir, qaysi biri kech bo'lsa) + kunlar. */
function extendedUntil(deadline: string | null, days: number) {
  const now = Date.now();
  const base = deadline ? Math.max(new Date(deadline).getTime(), now) : now;
  return new Date(base + days * 86400_000);
}

export default function MissingPanel({ roundId, deadline }: { roundId: number; deadline: string | null }) {
  const [open, setOpen] = useState(false);
  const data = useApi<Missing>(open ? `kitob/rounds/${roundId}/missing` : null);
  const act = useAction();
  const [q, setQ] = useState("");
  const items = (data.data?.items ?? []).filter((i) => !q || i.name.toLowerCase().includes(q.toLowerCase()));

  const extend = async (userId: number, name: string) => {
    const days = window.prompt(`${name} — muddat necha kunga uzaytirilsin?`, "3");
    if (!days || !Number(days)) return;
    const reason = window.prompt("Sabab:");
    if (!reason?.trim()) return;
    const until = extendedUntil(deadline, Number(days));
    await act.run(
      () => api(`kitob/rounds/${roundId}/extensions`, { method: "POST", body: { user_id: userId, until: until.toISOString(), reason } }),
      `${name}: muddat ${formatDate(until.toISOString())} gacha uzaytirildi`,
    );
    data.reload();
  };

  return (
    <div className="rounded-xl border border-line bg-bg-elev/60 p-4">
      <button className="flex w-full items-center justify-between text-sm" onClick={() => setOpen(!open)}>
        <span className="font-medium">Izoh yubormaganlar</span>
        <span className="text-muted">
          {data.data ? `${data.data.items.length} kishi · yuborgan: ${data.data.submitted}` : "ko'rish"} {open ? "▴" : "▾"}
        </span>
      </button>
      {open && (
        <div className="mt-3 space-y-2">
          <Notice error={act.error ?? data.error} notice={act.notice} onClose={act.clear} />
          <input className="field" placeholder="Ism bo'yicha" value={q} onChange={(e) => setQ(e.target.value)} />
          <ul className="max-h-72 divide-y divide-line overflow-y-auto">
            {items.map((i) => (
              <li key={i.id} className="flex items-center justify-between gap-2 py-2 text-sm">
                <span>
                  {i.name} <span className="text-muted">· {i.branch}</span>
                  {i.extended_until && (
                    <span className="ml-2">
                      <Badge tone="amber">{formatDate(i.extended_until)} gacha</Badge>
                    </span>
                  )}
                </span>
                <Button variant="ghost" className="py-1 text-xs" disabled={act.busy} onClick={() => extend(i.id, i.name)}>
                  Muddat uzaytirish
                </Button>
              </li>
            ))}
          </ul>
          {data.data && items.length === 0 && <p className="text-sm text-muted">Hamma izoh yuborgan 🎉</p>}
        </div>
      )}
    </div>
  );
}
