"use client";

// Zaldagi proyektor uchun katta ekran: joriy raund va savol, jonli reyting
// (Tashkiliy guruh "yashirish"ni yoqsa — reyting ko'rinmaydi).

import { useParams } from "next/navigation";
import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { fmtSeconds, useCountdown } from "@/lib/useCountdown";
import { RequireAuth } from "@/lib/auth";
import { Logo } from "../ui";
import type { Live } from "@/lib/types";

const POLL_MS = 1500;

function Inner() {
  const { id } = useParams<{ id: string }>();
  const [live, setLive] = useState<Live | null>(null);
  const [offline, setOffline] = useState(false);
  const [receivedAt, setReceivedAt] = useState(0);

  const load = useCallback(async () => {
    try {
      setLive(await api<Live>(`zakovat/games/${id}/live`));
      setReceivedAt(Date.now());
      setOffline(false);
    } catch {
      setOffline(true);
    }
  }, [id]);

  usePolling(load, POLL_MS);
  const timer = useCountdown(live?.timer, receivedAt);

  if (!live) return <div className="min-h-screen" />;

  const g = live.game;
  const total = g.rounds * g.questions_per_round;
  const ranked = live.standings.filter((s) => s.eligible);
  const finished = g.status === "preliminary" || g.status === "final";

  return (
    <div className="flex min-h-screen flex-col px-6 py-6 lg:px-10 lg:py-8">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Logo size={56} />
          <div>
            <div className="text-sm uppercase tracking-widest text-accent">Colba ligasi · Zakovat</div>
            <div className="glow-text text-3xl font-semibold">{g.title}</div>
          </div>
        </div>
        {offline && <span className="rounded-full bg-danger/20 px-3 py-1 text-sm text-danger">Aloqa uzildi…</span>}
      </header>

      {g.status === "in_progress" && (
        <section className="mt-10 grid grid-cols-3 gap-4 lg:gap-8">
          <div className="card p-6 lg:p-8">
            <div className="text-xl text-muted">Raund</div>
            <div className="text-7xl font-bold leading-none lg:text-[9rem]">{live.current_round}</div>
          </div>
          <div className="rounded-[var(--radius)] border border-accent/40 bg-accent-soft p-6 lg:p-8">
            <div className="text-xl text-muted">Savol</div>
            <div className="glow-text text-7xl font-bold leading-none whitespace-nowrap lg:text-[9rem]">
              {live.current_question}
              <span className="text-3xl text-muted lg:text-5xl"> / {total}</span>
            </div>
          </div>
          <div
            className={`card p-6 lg:p-8 ${timer.left <= 10 && timer.left > 0 ? "border-danger/60" : ""}`}
          >
            <div className="text-xl text-muted">Vaqt</div>
            <div
              className={`text-7xl font-bold tabular-nums leading-none lg:text-[9rem] ${
                timer.left <= 10 && timer.left > 0 ? "animate-pulse text-danger" : timer.left === 0 ? "text-muted" : ""
              }`}
            >
              {fmtSeconds(timer.left)}
            </div>
          </div>
        </section>
      )}

      {finished && (
        <div className="mt-8 text-center text-3xl font-semibold text-success">
          {g.status === "final" ? "Yakuniy natija" : "Dastlabki natija — apellyatsiyalar qabul qilinmoqda"}
        </div>
      )}

      <section className="mt-10 flex-1">
        {live.standings_hidden ? (
          <div className="card grid h-full min-h-60 place-items-center text-4xl text-muted">
            Reyting oxirida e&apos;lon qilinadi 🤫
          </div>
        ) : (
          <table className="w-full text-2xl lg:text-3xl">
            <thead>
              <tr className="text-left text-xl text-muted">
                <th className="w-24 py-3">O&apos;rin</th>
                <th className="py-3">Jamoa</th>
                <th className="w-40 py-3 text-right">Ball</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((s) => (
                <tr key={s.team.id} className="border-t border-line">
                  <td className={`py-4 font-bold ${s.place === 1 ? "text-gold" : "text-accent"}`}>{s.place}</td>
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
