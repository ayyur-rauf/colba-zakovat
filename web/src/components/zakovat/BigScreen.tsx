"use client";

// Zaldagi proyektor uchun katta ekran: joriy raund va savol, jonli reyting
// (Tashkiliy guruh "yashirish"ni yoqsa — reyting ko'rinmaydi).

import { useParams } from "next/navigation";
import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { RequireAuth } from "@/lib/auth";
import type { Live } from "@/lib/types";

const POLL_MS = 3000;

function Inner() {
  const { id } = useParams<{ id: string }>();
  const [live, setLive] = useState<Live | null>(null);
  const [offline, setOffline] = useState(false);

  const load = useCallback(async () => {
    try {
      setLive(await api<Live>(`zakovat/games/${id}/live`));
      setOffline(false);
    } catch {
      setOffline(true);
    }
  }, [id]);

  usePolling(load, POLL_MS);

  if (!live) return <div className="min-h-screen bg-slate-950" />;

  const g = live.game;
  const total = g.rounds * g.questions_per_round;
  const ranked = live.standings.filter((s) => s.eligible);
  const finished = g.status === "preliminary" || g.status === "final";

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 px-6 py-6 text-white lg:px-10 lg:py-8">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="grid h-14 w-14 place-items-center rounded-2xl bg-brand-500 text-3xl font-bold">C</span>
          <div>
            <div className="text-sm uppercase tracking-widest text-slate-400">Colba ligasi · Zakovat</div>
            <div className="text-3xl font-semibold">{g.title}</div>
          </div>
        </div>
        {offline && <span className="rounded-full bg-red-500/20 px-3 py-1 text-sm text-red-300">Aloqa uzildi…</span>}
      </header>

      {g.status === "in_progress" && (
        <section className="mt-10 grid grid-cols-2 gap-4 lg:gap-8">
          <div className="rounded-3xl bg-white/5 p-6 lg:p-8">
            <div className="text-xl text-slate-400">Raund</div>
            <div className="text-7xl font-bold leading-none lg:text-[9rem]">{live.current_round}</div>
          </div>
          <div className="rounded-3xl bg-brand-500/20 p-6 lg:p-8">
            <div className="text-xl text-slate-300">Savol</div>
            <div className="text-7xl font-bold leading-none whitespace-nowrap lg:text-[9rem]">
              {live.current_question}
              <span className="text-3xl text-slate-400 lg:text-5xl"> / {total}</span>
            </div>
          </div>
        </section>
      )}

      {finished && (
        <div className="mt-8 text-center text-3xl font-semibold text-emerald-300">
          {g.status === "final" ? "Yakuniy natija" : "Dastlabki natija — apellyatsiyalar qabul qilinmoqda"}
        </div>
      )}

      <section className="mt-10 flex-1">
        {live.standings_hidden ? (
          <div className="grid h-full place-items-center rounded-3xl border border-white/10 text-4xl text-slate-400">
            Reyting oxirida e&apos;lon qilinadi 🤫
          </div>
        ) : (
          <table className="w-full text-2xl lg:text-3xl">
            <thead>
              <tr className="text-left text-xl text-slate-400">
                <th className="w-24 py-3">O&apos;rin</th>
                <th className="py-3">Jamoa</th>
                <th className="w-40 py-3 text-right">Ball</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((s) => (
                <tr key={s.team.id} className="border-t border-white/10">
                  <td className="py-4 font-bold text-brand-100">{s.place}</td>
                  <td className="py-4">{s.team.name}</td>
                  <td className="py-4 text-right font-bold">{s.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default function BigScreen() {
  return (
    <RequireAuth>
      <Inner />
    </RequireAuth>
  );
}
