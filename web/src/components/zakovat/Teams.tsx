"use client";

// Zakovat — jamoalar: ro'yxat, tarkib, Tashkiliy guruh tasdig'i.

import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi, usePerms } from "@/lib/hooks";
import type { TeamDetail, TeamListItem } from "@/lib/types";
import { Badge, Button, Card, Empty, Notice, PageTitle } from "../ui";
import { TeamStatusBadge } from "./common";

export default function ZakovatTeams() {
  const { zakovatTg } = usePerms();
  const teams = useApi<TeamListItem[]>("zakovat/teams");
  const act = useAction();
  const [open, setOpen] = useState<number | null>(null);
  const [filter, setFilter] = useState<"all" | "pending">("all");

  const list = (teams.data ?? []).filter((t) => filter === "all" || t.status === "pending");
  const pendingCount = (teams.data ?? []).filter((t) => t.status === "pending").length;

  return (
    <>
      <PageTitle
        title="Jamoalar"
        subtitle="Jamoada 4–8 o'yinchi, bir o'yinchi — bitta jamoa (Nizom 3.2)"
        actions={
          <div className="flex rounded-lg border border-line p-0.5 text-sm">
            {(["all", "pending"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded-md px-3 py-1.5 ${filter === f ? "bg-surface-2 text-fg" : "text-muted"}`}
              >
                {f === "all" ? "Barchasi" : `Tasdiq kutmoqda (${pendingCount})`}
              </button>
            ))}
          </div>
        }
      />
      <Notice error={act.error ?? teams.error} notice={act.notice} onClose={act.clear} />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {list.map((t) => (
          <Card key={t.id} className="p-5">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="text-lg font-semibold">{t.name}</h3>
                <p className="text-sm text-muted">{t.members} o&apos;yinchi</p>
              </div>
              <TeamStatusBadge status={t.status} />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="ghost" onClick={() => setOpen(open === t.id ? null : t.id)}>
                Tarkib {open === t.id ? "▴" : "▾"}
              </Button>
              {zakovatTg && t.status === "pending" && (
                <Button
                  variant="success"
                  disabled={act.busy}
                  onClick={() => act.run(() => api(`zakovat/teams/${t.id}/approve`, { method: "POST" }), `${t.name} tasdiqlandi`).then(teams.reload)}
                >
                  Tasdiqlash
                </Button>
              )}
            </div>
            {open === t.id && <Members teamId={t.id} />}
          </Card>
        ))}
      </div>
      {teams.data && list.length === 0 && (
        <Card>
          <Empty>{filter === "pending" ? "Tasdiq kutayotgan jamoa yo'q" : "Jamoalar yo'q"}</Empty>
        </Card>
      )}
    </>
  );
}

function Members({ teamId }: { teamId: number }) {
  const team = useApi<TeamDetail>(`zakovat/teams/${teamId}`);
  if (!team.data) return <p className="mt-3 text-sm text-muted">Yuklanmoqda…</p>;
  return (
    <ul className="mt-4 space-y-1.5 border-t border-line pt-3 text-sm">
      {team.data.members.map((m) => (
        <li key={m.id} className="flex items-center justify-between gap-2">
          <span>
            {m.user.name}
            {m.user.id === team.data!.captain.id && <span className="ml-1.5 text-gold">★ sardor</span>}
          </span>
          <span className="flex items-center gap-2 text-xs text-muted">
            {m.user.branch}
            {m.status === "invited" && <Badge tone="amber">taklif</Badge>}
          </span>
        </li>
      ))}
    </ul>
  );
}
