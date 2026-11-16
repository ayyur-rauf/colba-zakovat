"use client";

// Zakovat — umumiy ko'rinish: keyingi/joriy o'yin, qisqa reyting, tashkilotchi uchun vazifalar.

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { useApi, usePerms } from "@/lib/hooks";
import type { Game, SeasonStandings, TeamListItem } from "@/lib/types";
import { Card, CardHeader, Empty, formatDate, LinkButton, Notice, Stat } from "../ui";
import { GameStatusBadge, PlaceCell } from "./common";

export default function ZakovatOverview() {
  const { zakovat } = useAuth();
  const perms = usePerms();
  const staff = perms.zakovatTg || perms.zakovatScorer;
  const games = useApi<Game[]>("zakovat/games");
  const standings = useApi<SeasonStandings>("zakovat/standings");
  const teams = useApi<TeamListItem[]>("zakovat/teams");

  const list = games.data ?? [];
  const live = list.find((g) => g.status === "in_progress" || g.status === "preliminary");
  const upcoming = list.find((g) => (g.status === "registration" || g.status === "planned") && new Date(g.starts_at) > new Date());
  const played = list.filter((g) => g.status === "final" && g.kind === "league").length;
  const leagueTotal = list.filter((g) => g.kind === "league").length;
  const pendingTeams = (teams.data ?? []).filter((t) => t.status === "pending").length;
  const activeTeams = (teams.data ?? []).filter((t) => t.status === "active").length;
  const focus = live ?? upcoming;

  return (
    <>
      <Notice error={games.error ?? standings.error} onClose={() => games.setError(null)} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="O'tkazilgan turlar" value={`${played} / ${leagueTotal}`} hint="liga o'yinlari" />
        <Stat label="Faol jamoalar" value={activeTeams} />
        <Stat label="Tasdiq kutayotgan" value={pendingTeams} hint={staff ? "Jamoalar bo'limida" : undefined} />
        <Stat label="Mening jamoam" value={zakovat?.team?.name ?? "—"} />
      </div>

      <div className="grid gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader title={live ? "Hozir" : "Keyingi o'yin"} />
          {focus ? (
            <div className="p-6">
              <div className="flex flex-wrap items-center gap-3">
                <h3 className="text-3xl font-bold">{focus.title}</h3>
                <GameStatusBadge status={focus.status} />
              </div>
              <div className="mt-3 grid gap-1 text-sm text-muted">
                <span>🗓 {formatDate(focus.starts_at)}</span>
                {focus.venue && <span>📍 {focus.venue}</span>}
                <span>
                  👥 {focus.approved_teams} jamoa tasdiqlangan{focus.max_teams ? ` (joy: ${focus.max_teams})` : ""}
                </span>
                <span>⏳ Ro&apos;yxat muddati: {formatDate(focus.registration_deadline)}</span>
              </div>
              <div className="mt-5 flex flex-wrap gap-2">
                {staff && focus.approved_teams > 0 && (
                  <LinkButton href={`/zakovat/${focus.id}/sheet`} variant="primary">
                    Javoblar jadvali
                  </LinkButton>
                )}
                {focus.approved_teams > 0 && (
                  <LinkButton href={`/ekran/${focus.id}`} target="_blank">
                    Katta ekran ↗
                  </LinkButton>
                )}
                <LinkButton href="/zakovat/games">Barcha o&apos;yinlar</LinkButton>
              </div>
            </div>
          ) : (
            <Empty>Rejalashtirilgan o&apos;yin yo&apos;q</Empty>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader
            title="Mavsum reytingi"
            actions={
              <Link href="/zakovat/standings" className="text-sm text-accent hover:underline">
                To&apos;liq →
              </Link>
            }
          />
          <table className="table">
            <tbody>
              {(standings.data?.rows ?? [])
                .filter((r) => r.place !== null)
                .slice(0, 6)
                .map((r) => (
                  <tr key={r.team.id}>
                    <td className="w-10">
                      <PlaceCell place={r.place} tie={r.tie_group} />
                    </td>
                    <td>{r.team.name}</td>
                    <td className="text-right font-semibold">{r.points}</td>
                  </tr>
                ))}
            </tbody>
          </table>
          {standings.data && standings.data.rows.length === 0 && <Empty>Hali natija yo&apos;q</Empty>}
        </Card>
      </div>
    </>
  );
}
