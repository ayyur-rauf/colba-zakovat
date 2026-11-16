"use client";

// Zakovat — mavsum reytingi: ball → J yig'indisi → qo'shimcha o'yin.

import { useApi } from "@/lib/hooks";
import type { SeasonStandings } from "@/lib/types";
import { Card, Empty, Notice, PageTitle } from "../ui";
import { PlaceCell, TeamStatusBadge } from "./common";

export default function ZakovatStandings() {
  const st = useApi<SeasonStandings>("zakovat/standings");
  const rows = st.data?.rows ?? [];
  const ties = rows.some((r) => r.tie_group);
  const max = Math.max(1, ...rows.map((r) => r.points));

  return (
    <>
      <PageTitle
        title="Mavsum reytingi"
        subtitle={`${st.data?.season.name ?? ""} · ball teng bo'lsa J yig'indisi, u ham teng bo'lsa — qo'shimcha o'yin`}
      />
      <Notice error={st.error} onClose={() => st.setError(null)} />
      {ties && (
        <div className="rounded-xl border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
          &quot;=&quot; belgili jamoalarning bali ham, J si ham teng — ular o&apos;rtasida qo&apos;shimcha o&apos;yin o&apos;tkazilishi kerak.
        </div>
      )}
      <Card>
        <table className="table">
          <thead>
            <tr>
              <th className="w-16">O&apos;rin</th>
              <th>Jamoa</th>
              <th className="hidden w-1/3 md:table-cell" />
              <th className="text-right">Ball</th>
              <th className="text-right">J</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.team.id} className={r.place === null ? "opacity-50" : ""}>
                <td className="text-lg">
                  <PlaceCell place={r.place} tie={r.tie_group} />
                </td>
                <td className="font-medium">
                  {r.team.name} {r.place === null && <TeamStatusBadge status={r.team.status} />}
                </td>
                <td className="hidden md:table-cell">
                  <div className="h-2 rounded-full bg-surface-2">
                    <div className="h-2 rounded-full bg-gradient-to-r from-accent-strong to-accent" style={{ width: `${(r.points / max) * 100}%` }} />
                  </div>
                </td>
                <td className="text-right text-lg font-semibold">{r.points}</td>
                <td className="text-right text-muted">{r.rating_j}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {st.data && rows.length === 0 && <Empty>Hali yakunlangan o&apos;yin yo&apos;q</Empty>}
      </Card>
    </>
  );
}
