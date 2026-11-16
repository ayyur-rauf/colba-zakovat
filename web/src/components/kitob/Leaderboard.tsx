"use client";

// Kitobxonlik — mavsum reytingi (shaxsiy ballar).

import { useApi } from "@/lib/hooks";
import type { LeaderRow } from "@/lib/types";
import { Card, Empty, PageTitle } from "../ui";

export default function KitobLeaderboard() {
  const lb = useApi<LeaderRow[]>("kitob/leaderboard");
  const rows = lb.data ?? [];
  const top = rows.slice(0, 3);

  return (
    <>
      <PageTitle title="Kitobxonlar reytingi" subtitle="Mavsum davomida tasdiqlangan izohlar uchun ballar" />
      {lb.error ? (
        <Card>
          <Empty>{lb.error}</Empty>
        </Card>
      ) : (
        <>
          {top.length > 0 && (
            <div className="grid gap-4 md:grid-cols-3">
              {top.map((r, i) => (
                <Card key={r.user.id} className={`p-5 text-center ${i === 0 ? "border-gold/50" : ""}`}>
                  <div className="text-3xl">{["🥇", "🥈", "🥉"][i]}</div>
                  <div className="mt-2 text-lg font-semibold">{r.user.name}</div>
                  <div className="text-sm text-muted">{r.user.branch}</div>
                  <div className="mt-2 text-2xl font-bold text-accent">{r.points}</div>
                </Card>
              ))}
            </div>
          )}
          <Card>
            <table className="table">
              <thead>
                <tr>
                  <th className="w-16">O&apos;rin</th>
                  <th>Xodim</th>
                  <th>Filial</th>
                  <th className="text-right">Ball</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.user.id}>
                    <td className={`font-semibold ${r.place === 1 ? "text-gold" : ""}`}>{r.place}</td>
                    <td>{r.user.name}</td>
                    <td className="text-muted">{r.user.branch}</td>
                    <td className="text-right font-semibold">{r.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {lb.data && rows.length === 0 && <Empty>Hali ball yo&apos;q</Empty>}
          </Card>
        </>
      )}
    </>
  );
}
