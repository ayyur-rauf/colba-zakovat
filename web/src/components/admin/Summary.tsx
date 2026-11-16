"use client";

// Boshqaruv — "Yil sarhisobi": mukofotlash uchun mavsum natijalari, filiallar kesimi, Excel.

import { downloadFile } from "@/lib/download";
import { useApi } from "@/lib/hooks";
import { Button, Card, CardHeader, Empty, Notice, PageTitle, Stat } from "../ui";

type Summary = {
  season: { id: number; name: string; start: string; end: string };
  zakovat: {
    games_played: number;
    teams: number;
    players: number;
    top: { place: number; team: string; points: number; rating_j: number; members: string[] }[];
  };
  kitobxonlik: {
    rounds_done: number;
    reviews: number;
    readers: number;
    top: { place: number; user: { id: number; name: string; branch: string | null }; points: number }[];
  };
  branches: {
    branch: string;
    employees: number;
    zakovat_players: number;
    readers: number;
    participants: number;
    participation: number;
    kitob_points: number;
  }[];
};

const MEDAL = ["🥇", "🥈", "🥉"];

export default function AdminSummary() {
  const s = useApi<Summary>("manage/summary");
  const d = s.data;

  return (
    <>
      <PageTitle
        title="Yil sarhisobi"
        subtitle={d ? `${d.season.name} · "Yil sarhisobi" dasturida taqdirlash uchun (Nizom 10.1)` : undefined}
        actions={
          <Button onClick={() => downloadFile("manage/summary/export").catch((e) => s.setError(e.message))}>⬇ Excel hisobot</Button>
        }
      />
      <Notice error={s.error} onClose={() => s.setError(null)} />
      {d && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Zakovat turlari" value={d.zakovat.games_played} hint={`${d.zakovat.teams} jamoa · ${d.zakovat.players} o'yinchi`} />
            <Stat label="Kitobxonlik turlari" value={d.kitobxonlik.rounds_done} hint={`${d.kitobxonlik.reviews} ta izoh`} />
            <Stat label="Kitobxonlar" value={d.kitobxonlik.readers} />
            <Stat
              label="Umumiy ishtirok"
              value={`${Math.round(
                (100 * d.branches.reduce((a, b) => a + b.participants, 0)) / Math.max(1, d.branches.reduce((a, b) => a + b.employees, 0)),
              )}%`}
              hint="kamida bitta tadbirda qatnashgan xodimlar"
            />
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader title="🧠 Zakovat — g'olib jamoalar" />
              <div className="space-y-3 p-5">
                {d.zakovat.top.map((t, i) => (
                  <div key={t.team} className={`rounded-xl border p-4 ${i === 0 ? "border-gold/60 bg-gold/5" : "border-line bg-bg-elev/60"}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-semibold">
                        {MEDAL[i]} {t.team}
                      </span>
                      <span className="text-xl font-bold text-accent">{t.points}</span>
                    </div>
                    <div className="mt-1 text-xs text-muted">{t.members.join(", ")}</div>
                  </div>
                ))}
                {d.zakovat.top.length === 0 && <Empty>Hali natija yo&apos;q</Empty>}
              </div>
            </Card>
            <Card>
              <CardHeader title="📚 Kitobxonlik — eng faol kitobxonlar" />
              <table className="table">
                <tbody>
                  {d.kitobxonlik.top.map((r) => (
                    <tr key={r.user.id}>
                      <td className="w-10 font-semibold">{r.place <= 3 ? MEDAL[r.place - 1] : r.place}</td>
                      <td>{r.user.name}</td>
                      <td className="text-muted">{r.user.branch}</td>
                      <td className="text-right font-semibold">{r.points}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {d.kitobxonlik.top.length === 0 && <Empty>Hali natija yo&apos;q</Empty>}
            </Card>
          </div>

          <Card className="overflow-x-auto">
            <CardHeader title="Filiallar kesimi" subtitle="Ishtirok — Zakovat jamoasida yoki kitobxonlikda qatnashgan xodimlar ulushi" />
            <table className="table min-w-[700px]">
              <thead>
                <tr>
                  <th>Filial</th>
                  <th className="text-right">Xodimlar</th>
                  <th className="text-right">Zakovat</th>
                  <th className="text-right">Kitobxonlar</th>
                  <th className="w-1/4">Ishtirok</th>
                  <th className="text-right">Kitobxonlik ballari</th>
                </tr>
              </thead>
              <tbody>
                {d.branches.map((b) => (
                  <tr key={b.branch}>
                    <td className="font-medium">{b.branch}</td>
                    <td className="text-right">{b.employees}</td>
                    <td className="text-right">{b.zakovat_players}</td>
                    <td className="text-right">{b.readers}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="h-2 flex-1 rounded-full bg-surface-2">
                          <div className="h-2 rounded-full bg-gradient-to-r from-accent-strong to-accent" style={{ width: `${b.participation}%` }} />
                        </div>
                        <span className="w-10 text-right text-sm">{b.participation}%</span>
                      </div>
                    </td>
                    <td className="text-right">{b.kitob_points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </>
  );
}
