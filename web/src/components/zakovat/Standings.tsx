"use client";

// Zakovat — mavsum reytingi: shohsupa, turlar bo'yicha ballar, o'rin o'zgarishi,
// har jamoa tafsiloti va ballar qanday hisoblanishi haqida izoh.

import Link from "next/link";
import { Fragment, useState } from "react";
import { useApi } from "@/lib/hooks";
import type { SeasonStandings, StandingRow } from "@/lib/types";
import { Badge, Card, CardHeader, Empty, formatDate, Notice, PageTitle, Stat } from "../ui";
import { PlaceCell, TeamStatusBadge } from "./common";

export default function ZakovatStandings() {
  const st = useApi<SeasonStandings>("zakovat/standings");
  const [open, setOpen] = useState<number | null>(null);
  const [help, setHelp] = useState(false);

  const games = st.data?.games ?? [];
  const rows = st.data?.rows ?? [];
  const ranked = rows.filter((r) => r.place !== null);
  const ties = ranked.some((r) => r.tie_group);
  const max = Math.max(1, ...rows.map((r) => r.points));
  const bestGame = rows.reduce<{ team: string; pts: number } | null>(
    (acc, r) => (r.best > (acc?.pts ?? -1) ? { team: r.team.name, pts: r.best } : acc),
    null,
  );

  return (
    <>
      <PageTitle
        title="Mavsum reytingi"
        subtitle={st.data?.season.name}
        actions={
          <button onClick={() => setHelp(!help)} className="text-sm text-accent hover:underline">
            {help ? "Yopish" : "Ballar qanday hisoblanadi?"}
          </button>
        }
      />
      <Notice error={st.error} onClose={() => st.setError(null)} />

      {help && <HowItWorks />}

      {/* Qisqa ko'rsatkichlar */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="O'tkazilgan turlar" value={games.length} />
        <Stat label="Yetakchi" value={ranked[0]?.team.name ?? "—"} hint={ranked[0] ? `${ranked[0].points} ball` : undefined} />
        <Stat label="Bir turdagi eng yuqori" value={bestGame?.pts ?? "—"} hint={bestGame?.team} />
        <Stat label="Reytingdagi jamoalar" value={ranked.length} />
      </div>

      {/* Shohsupa */}
      {ranked.length >= 3 && (
        <div className="grid items-end gap-4 md:grid-cols-3">
          {[1, 0, 2].map((i) => {
            const r = ranked[i];
            const h = ["md:pb-10", "md:pb-4", "md:pb-0"][i];
            return (
              <Card key={r.team.id} className={`p-5 text-center ${i === 0 ? "border-gold/60 shadow-[0_10px_50px_-20px_var(--gold)]" : ""}`}>
                <div className={h}>
                  <div className="text-3xl">{["🥇", "🥈", "🥉"][i]}</div>
                  <div className="mt-2 text-xl font-semibold">{r.team.name}</div>
                  <div className="mt-1 text-3xl font-bold text-accent">{r.points}</div>
                  <div className="text-xs text-muted">
                    ball · J {r.rating_j} · {r.wins} ta g&apos;alaba
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {ties && (
        <div className="rounded-xl border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
          &quot;=&quot; belgili jamoalarning bali ham, J si ham teng — ular o&apos;rtasida qo&apos;shimcha o&apos;yin o&apos;tkaziladi.
        </div>
      )}

      {/* Asosiy jadval */}
      <Card className="overflow-x-auto">
        <table className="table min-w-[720px]">
          <thead>
            <tr>
              <th className="w-20">O&apos;rin</th>
              <th>Jamoa</th>
              {games.map((g) => (
                <th key={g.id} className="w-16 text-center" title={formatDate(g.starts_at).slice(0, 10)}>
                  {g.title.replace("-tur", "")}
                  <span className="block text-[10px] font-normal">tur</span>
                </th>
              ))}
              <th className="w-24 text-right">Ball</th>
              <th className="w-16 text-right">J</th>
              <th className="w-8" />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <Fragment key={r.team.id}>
                <tr
                  onClick={() => setOpen(open === r.team.id ? null : r.team.id)}
                  className={`cursor-pointer transition hover:bg-surface-2/60 ${r.place === null ? "opacity-50" : ""}`}
                >
                  <td>
                    <div className="flex items-center gap-2 text-lg">
                      <PlaceCell place={r.place} tie={r.tie_group} />
                      <Move now={r.place} prev={r.prev_place} />
                    </div>
                  </td>
                  <td>
                    <div className="font-medium">{r.team.name}</div>
                    <div className="mt-1.5 h-1.5 max-w-56 rounded-full bg-surface-2">
                      <div className="h-1.5 rounded-full bg-gradient-to-r from-accent-strong to-accent" style={{ width: `${(r.points / max) * 100}%` }} />
                    </div>
                  </td>
                  {games.map((g) => (
                    <td key={g.id} className="text-center">
                      <GameCellView cell={r.by_game[String(g.id)]} />
                    </td>
                  ))}
                  <td className="text-right text-xl font-bold">
                    {r.points}
                    {r.place === null && (
                      <div className="mt-1">
                        <TeamStatusBadge status={r.team.status} />
                      </div>
                    )}
                  </td>
                  <td className="text-right text-muted">{r.rating_j}</td>
                  <td className="text-muted">{open === r.team.id ? "▴" : "▾"}</td>
                </tr>
                {open === r.team.id && (
                  <tr>
                    <td colSpan={games.length + 5} className="bg-bg-elev/60">
                      <TeamDetail row={r} games={games} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
        {st.data && rows.length === 0 && <Empty>Hali yakunlangan o&apos;yin yo&apos;q</Empty>}
      </Card>
      <p className="text-xs text-muted">
        Turdagi katak: yuqorida — ball, pastda — o&apos;sha turdagi o&apos;rin. Qatorni bosing — jamoa tafsiloti ochiladi.
      </p>
    </>
  );
}

function Move({ now, prev }: { now: number | null; prev: number | null }) {
  if (now === null || prev === null || now === prev) return null;
  const up = now < prev;
  return (
    <span className={`text-xs font-medium ${up ? "text-success" : "text-danger"}`} title={`Oldingi turdan keyin: ${prev}-o'rin`}>
      {up ? "▲" : "▼"}
      {Math.abs(prev - now)}
    </span>
  );
}

function GameCellView({ cell }: { cell?: { points: number; place: number | null; eligible: boolean } }) {
  if (!cell) return <span className="text-muted/50">—</span>;
  if (!cell.eligible)
    return (
      <span className="text-xs text-muted" title="3 o'yinchidan kam — hisobga olinmagan (Nizom 4.3)">
        h/o
      </span>
    );
  return (
    <span className="leading-tight">
      <span className="block font-semibold">{cell.points}</span>
      <span className={`block text-[11px] ${cell.place === 1 ? "text-gold" : "text-muted"}`}>{cell.place}-o&apos;rin</span>
    </span>
  );
}

function TeamDetail({ row, games }: { row: StandingRow; games: SeasonStandings["games"] }) {
  const gameSum = Object.values(row.by_game).reduce((s, c) => s + c.points, 0);
  return (
    <div className="grid gap-5 p-4 md:grid-cols-3">
      <div className="space-y-2 text-sm">
        <div className="text-xs uppercase tracking-wider text-muted">Ko&apos;rsatkichlar</div>
        <div className="flex justify-between">
          <span className="text-muted">Qatnashgan turlar</span>
          <span>
            {row.played} / {games.length}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted">Tur g&apos;alabalari</span>
          <span>{row.wins}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted">Bir turda eng ko&apos;p</span>
          <span>{row.best}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted">O&apos;rtacha ball</span>
          <span>{row.played ? (gameSum / row.played).toFixed(1) : "—"}</span>
        </div>
      </div>

      <div className="text-sm md:col-span-2">
        <div className="mb-2 text-xs uppercase tracking-wider text-muted">Ball qanday yig&apos;ilgan</div>
        <table className="w-full">
          <tbody>
            {games.map((g) => {
              const c = row.by_game[String(g.id)];
              return (
                <tr key={g.id} className="border-b border-line/50">
                  <td className="py-1.5">
                    <Link href={`/zakovat/${g.id}/sheet`} className="hover:text-accent" onClick={(e) => e.stopPropagation()}>
                      {g.title}
                    </Link>
                  </td>
                  <td className="py-1.5 text-muted">{formatDate(g.starts_at).slice(0, 10)}</td>
                  <td className="py-1.5 text-muted">
                    {!c ? "qatnashmagan" : !c.eligible ? "hisobga olinmagan" : `${c.place}-o'rin · J ${c.rating_j}`}
                  </td>
                  <td className="py-1.5 text-right font-medium">{c?.eligible ? `+${c.points}` : "0"}</td>
                </tr>
              );
            })}
            {row.other_points !== 0 && (
              <tr className="border-b border-line/50">
                <td className="py-1.5" colSpan={3}>
                  Tuzatish <Badge tone="red">chiqib ketish / chetlatish</Badge>
                </td>
                <td className="py-1.5 text-right font-medium text-danger">{row.other_points}</td>
              </tr>
            )}
            <tr>
              <td className="pt-2 font-semibold" colSpan={3}>
                Jami
              </td>
              <td className="pt-2 text-right text-lg font-bold">{row.points}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HowItWorks() {
  const items = [
    ["To'g'ri javob", "Har bir to'g'ri javob — 1 ball. Noto'g'ri javobga ball berilmaydi (Nizom 6.1)."],
    ["3 o'yinchi qoidasi", "Savol jamoa uchun hisobga olinadi, agar o'sha paytda kamida 3 o'yinchi qatnashgan bo'lsa (Nizom 3.6, 4.3)."],
    ["Savol reytingi R", "R = N + 1, N — savolga javob topa olmagan jamoalar soni. Qiyin savol ko'proq qadrlanadi (Nizom 8.2)."],
    ["J", "Jamoa to'g'ri javob bergan savollar R lari yig'indisi (Nizom 8.3). Ball teng bo'lsa — J kattasi yuqorida."],
    ["Mavsum", "Turlardagi ballar qo'shiladi. Teng bo'lsa — J yig'indisi, u ham teng bo'lsa — qo'shimcha o'yin."],
    ["Chiqish", "Jamoa chiqib ketsa yoki chetlatilsa, mavsumdagi ballari nolga tushadi, boshqalarniki o'zgarmaydi (Nizom 3.9)."],
  ];
  return (
    <Card>
      <CardHeader title="Ballar qanday hisoblanadi" subtitle="Colba ligasi Nizomi asosida" />
      <div className="grid gap-4 p-5 md:grid-cols-2 lg:grid-cols-3">
        {items.map(([t, d]) => (
          <div key={t} className="rounded-xl border border-line bg-bg-elev/60 p-4">
            <div className="font-medium text-accent">{t}</div>
            <p className="mt-1 text-sm text-muted">{d}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}
