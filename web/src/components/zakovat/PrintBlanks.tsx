"use client";

// Qog'oz blankalar (TZ 4.4): har jamoa uchun har savolga bitta blanka, A4 varaqda 8 tadan.
// Brauzerning "Chop etish" oynasidan to'g'ridan-to'g'ri printerga yoki PDF ga saqlash mumkin.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { RequireAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import type { Sheet } from "@/lib/types";
import { Button } from "../ui";

const PER_PAGE = 8;

function Blanks() {
  const { id } = useParams<{ id: string }>();
  const sheet = useApi<Sheet>(`zakovat/games/${id}/sheet`);
  const [round, setRound] = useState<number | "all">("all");
  const [onlyTeam, setOnlyTeam] = useState<number | "all">("all");

  if (sheet.error) return <div className="p-10 text-center text-danger">{sheet.error}</div>;
  if (!sheet.data) return <div className="p-10 text-center text-muted">Yuklanmoqda…</div>;

  const g = sheet.data.game;
  const qpr = g.questions_per_round;
  const numbers = Array.from({ length: g.rounds * qpr }, (_, i) => i + 1).filter(
    (n) => round === "all" || Math.ceil(n / qpr) === round,
  );
  const teams = sheet.data.teams.filter((t) => onlyTeam === "all" || t.team.id === onlyTeam);

  // har jamoa yangi varaqdan boshlanadi
  const pages: { team: (typeof teams)[number]; nums: number[] }[] = [];
  for (const t of teams) for (let i = 0; i < numbers.length; i += PER_PAGE) pages.push({ team: t, nums: numbers.slice(i, i + PER_PAGE) });

  return (
    <div className="blanks">
      <style>{`
        @page { size: A4; margin: 8mm; }
        @media print {
          body { background: #fff !important; color: #000 !important; }
          .blanks .page { break-after: page; box-shadow: none !important; margin: 0 !important; }
        }
      `}</style>

      <div className="mx-auto flex max-w-[210mm] flex-wrap items-center gap-3 px-4 py-5 print:hidden">
        <Link href={`/zakovat/${id}/sheet`} className="text-sm text-muted hover:text-fg">
          ← Jadval
        </Link>
        <h1 className="flex-1 text-xl font-semibold">
          {g.title} — blankalar <span className="text-sm font-normal text-muted">({pages.length} varaq)</span>
        </h1>
        <select className="field w-auto" value={round} onChange={(e) => setRound(e.target.value === "all" ? "all" : Number(e.target.value))}>
          <option value="all">Barcha raundlar</option>
          {Array.from({ length: g.rounds }, (_, i) => i + 1).map((r) => (
            <option key={r} value={r}>
              {r}-raund
            </option>
          ))}
        </select>
        <select className="field w-auto" value={onlyTeam} onChange={(e) => setOnlyTeam(e.target.value === "all" ? "all" : Number(e.target.value))}>
          <option value="all">Barcha jamoalar</option>
          {sheet.data.teams.map((t) => (
            <option key={t.team.id} value={t.team.id}>
              {t.table_number}. {t.team.name}
            </option>
          ))}
        </select>
        <Button onClick={() => window.print()}>🖨 Chop etish</Button>
      </div>

      {pages.map((p, i) => (
        <div
          key={i}
          className="page mx-auto mb-6 grid h-[281mm] w-[194mm] grid-cols-2 grid-rows-4 bg-white text-black shadow-2xl print:mb-0"
        >
          {p.nums.map((n) => (
            <div key={n} className="flex flex-col border border-dashed border-gray-400 p-[5mm]">
              <div className="flex items-start justify-between text-[9pt] text-gray-600">
                <span>Colba ligasi · {g.title}</span>
                <span>{Math.ceil(n / qpr)}-raund</span>
              </div>
              <div className="mt-[2mm] flex items-end justify-between">
                <div>
                  <div className="text-[8pt] uppercase text-gray-500">Stol / Jamoa</div>
                  <div className="text-[13pt] font-bold leading-tight">
                    {p.team.table_number ?? "—"}. {p.team.team.name}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[8pt] uppercase text-gray-500">Savol</div>
                  <div className="text-[28pt] font-black leading-none">{n}</div>
                </div>
              </div>
              <div className="mt-[3mm] text-[8pt] uppercase text-gray-500">Javob</div>
              <div className="mt-[1mm] flex flex-1 flex-col justify-evenly">
                {[0, 1, 2].map((l) => (
                  <div key={l} className="border-b border-gray-400" />
                ))}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export default function PrintBlanks() {
  return (
    <RequireAuth>
      <Blanks />
    </RequireAuth>
  );
}
