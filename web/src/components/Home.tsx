"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { RequireAuth, useAuth } from "@/lib/auth";
import { GAME_STATUS, type Game } from "@/lib/types";
import { Badge, ErrorBar, formatDate, Header } from "./ui";

const STATUS_TONE = {
  planned: "gray",
  registration: "blue",
  in_progress: "amber",
  preliminary: "amber",
  final: "green",
  cancelled: "red",
} as const;

function Dashboard() {
  const { me, zakovat } = useAuth();
  const [games, setGames] = useState<Game[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Game[]>("zakovat/games").then(setGames).catch((e) => setError(e.message));
  }, []);

  const staff = zakovat?.is_scorer || zakovat?.is_tg;

  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-7xl flex-1 space-y-6 px-4 py-6">
        <div>
          <h1 className="text-2xl font-semibold">Assalomu alaykum, {me?.employee?.full_name ?? me?.name}!</h1>
          <p className="text-gray-500">
            {zakovat?.season.name}
            {zakovat?.team && (
              <>
                {" "}
                · Jamoangiz: <b className="text-gray-700">{zakovat.team.name}</b>
                {zakovat.is_captain && " (sardor)"}
              </>
            )}
            {staff && <> · {zakovat?.is_tg ? "Tashkiliy guruh" : "Hisob hay'ati"}</>}
          </p>
        </div>

        <ErrorBar message={error} onClose={() => setError(null)} />

        <section className="rounded-2xl border border-gray-200 bg-white">
          <div className="border-b border-gray-100 px-5 py-4">
            <h2 className="font-semibold">Zakovat — Colba ligasi o&apos;yinlari</h2>
          </div>
          <ul className="divide-y divide-gray-100">
            {games.map((g) => (
              <li key={g.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
                <div>
                  <div className="font-medium">
                    {g.title}{" "}
                    {g.kind !== "league" && <Badge>{g.kind === "practice" ? "Mashq" : "Qo'shimcha"}</Badge>}
                  </div>
                  <div className="text-sm text-gray-500">
                    {formatDate(g.starts_at)} {g.venue && `· ${g.venue}`} · {g.approved_teams} jamoa
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={STATUS_TONE[g.status]}>{GAME_STATUS[g.status]}</Badge>
                  {staff && g.approved_teams > 0 && g.status !== "cancelled" && (
                    <Link
                      href={`/zakovat/${g.id}/sheet`}
                      className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
                    >
                      Javoblar jadvali
                    </Link>
                  )}
                  {g.approved_teams > 0 && (
                    <Link
                      href={`/zakovat/${g.id}/screen`}
                      target="_blank"
                      className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
                    >
                      Katta ekran ↗
                    </Link>
                  )}
                </div>
              </li>
            ))}
            {games.length === 0 && !error && <li className="px-5 py-6 text-center text-gray-400">O&apos;yinlar yo&apos;q</li>}
          </ul>
        </section>
      </main>
    </>
  );
}

export default function Home() {
  return (
    <RequireAuth>
      <Dashboard />
    </RequireAuth>
  );
}
