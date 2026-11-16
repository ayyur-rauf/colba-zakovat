"use client";

// Boshlovchi pulti: joriy savol matni va javobi, taymer, savollar bo'ylab yurish.
// Klaviatura: ← → — oldingi/keyingi savol, Probel — taymer start/pauza, R — taymerni qaytarish.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { errText, useApi } from "@/lib/hooks";
import type { GameQuestionSlot, Live } from "@/lib/types";
import { fmtSeconds, useCountdown } from "@/lib/useCountdown";
import { usePolling } from "@/lib/usePolling";
import { Button, Card, LinkButton, Notice } from "../ui";
import { GameStatusBadge } from "./common";

export default function HostConsole() {
  const { id } = useParams<{ id: string }>();
  const [live, setLive] = useState<Live | null>(null);
  const [receivedAt, setReceivedAt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [showAnswer, setShowAnswer] = useState(true);
  const busy = useRef(false);
  const slots = useApi<GameQuestionSlot[]>(`zakovat/games/${id}/questions`);

  const load = useCallback(async () => {
    if (busy.current) return;
    try {
      const l = await api<Live>(`zakovat/games/${id}/live`);
      setLive(l);
      setReceivedAt(Date.now());
    } catch (e) {
      setError(errText(e));
    }
  }, [id]);
  usePolling(load, 2000);

  const run = useCallback(
    async (fn: () => Promise<unknown>) => {
      busy.current = true;
      try {
        await fn();
      } catch (e) {
        setError(errText(e));
      } finally {
        busy.current = false;
        await load();
      }
    },
    [load],
  );

  const g = live?.game;
  const total = g ? g.rounds * g.questions_per_round : 0;
  const cur = live?.current_question ?? 0;
  const timer = useCountdown(live?.timer, receivedAt);
  const inProgress = g?.status === "in_progress";

  const go = useCallback(
    (n: number) => run(() => api(`zakovat/games/${id}/current`, { method: "POST", body: { number: n } })),
    [id, run],
  );
  const timerAction = useCallback(
    (action: "start" | "pause" | "reset", seconds?: number) =>
      run(() => api(`zakovat/games/${id}/timer`, { method: "POST", body: { action, ...(seconds ? { seconds } : {}) } })),
    [id, run],
  );

  // Klaviatura
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!inProgress || (e.target instanceof HTMLElement && e.target.closest("input, textarea, select"))) return;
      if (e.key === "ArrowRight" && cur < total) go(cur + 1);
      else if (e.key === "ArrowLeft" && cur > 1) go(cur - 1);
      else if (e.key === " ") {
        e.preventDefault();
        timerAction(timer.running ? "pause" : "start");
      } else if (e.key.toLowerCase() === "r") timerAction("reset");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [inProgress, cur, total, go, timerAction, timer.running]);

  if (!live || !g) return <div className="p-10 text-center text-muted">{error ?? "Yuklanmoqda…"}</div>;

  const slot = slots.data?.find((s) => s.number === cur);
  const q = slot?.question;
  const pct = timer.total ? (timer.left / timer.total) * 100 : 0;
  const urgent = timer.left <= 10 && timer.left > 0;

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link href="/zakovat/games" className="text-sm text-muted hover:text-fg">
            ← O&apos;yinlar
          </Link>
          <h1 className="mt-1 flex items-center gap-3 text-2xl font-semibold">
            {g.title} — boshlovchi pulti <GameStatusBadge status={g.status} />
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <LinkButton href={`/zakovat/${id}/questions`}>Savollar</LinkButton>
          <LinkButton href={`/zakovat/${id}/sheet`}>Javoblar jadvali</LinkButton>
          <LinkButton href={`/ekran/${id}`} target="_blank">
            Katta ekran ↗
          </LinkButton>
        </div>
      </div>
      <Notice error={error} onClose={() => setError(null)} />
      {!inProgress && (
        <div className="rounded-xl border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
          O&apos;yin hozir ketmayapti. Savol va taymerni boshqarish o&apos;yin boshlangach ishlaydi (Javoblar jadvalida «O&apos;yinni boshlash»).
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Savol */}
        <Card className="p-6 lg:col-span-2">
          <div className="flex items-center justify-between">
            <div className="text-sm uppercase tracking-widest text-muted">
              {live.current_round}-raund · savol
            </div>
            <div className="text-sm text-muted">{cur} / {total}</div>
          </div>
          <div className="glow-text mt-1 text-6xl font-bold">{cur || "—"}</div>
          <div className="mt-5 min-h-28 whitespace-pre-line text-xl leading-relaxed">
            {q ? q.text : <span className="text-muted">Bu raqamga savol biriktirilmagan.</span>}
          </div>
          {q && (
            <div className="mt-5 rounded-xl border border-success/30 bg-success/10 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase tracking-wider text-success">Javob</span>
                <button className="text-xs text-muted hover:text-fg" onClick={() => setShowAnswer(!showAnswer)}>
                  {showAnswer ? "yashirish" : "ko'rsatish"}
                </button>
              </div>
              {showAnswer && (
                <>
                  <div className="mt-1 text-2xl font-semibold text-success">{q.answer}</div>
                  {q.accepted_answers && <div className="mt-1 text-sm text-muted">Qabul qilinadi: {q.accepted_answers.replace(/\n/g, ", ")}</div>}
                  {q.comment && <div className="mt-2 text-sm">{q.comment}</div>}
                  {q.source && <div className="mt-1 text-xs text-muted">Manba: {q.source}</div>}
                </>
              )}
            </div>
          )}
          <div className="mt-6 flex items-center justify-between gap-3">
            <Button variant="ghost" disabled={!inProgress || cur <= 1} onClick={() => go(cur - 1)}>
              ← Oldingi
            </Button>
            <div className="flex flex-wrap justify-center gap-1">
              {Array.from({ length: total }, (_, i) => i + 1).map((n) => {
                const has = slots.data?.find((s) => s.number === n)?.question;
                return (
                  <button
                    key={n}
                    disabled={!inProgress}
                    onClick={() => go(n)}
                    title={has ? "" : "Savol biriktirilmagan"}
                    className={`h-6 w-6 rounded text-[10px] ${
                      n === cur ? "bg-accent text-white" : n < cur ? "bg-surface-2 text-muted" : has ? "border border-line" : "border border-dashed border-warning/50 text-warning"
                    }`}
                  >
                    {n}
                  </button>
                );
              })}
            </div>
            <Button disabled={!inProgress || cur >= total} onClick={() => go(cur + 1)}>
              Keyingi →
            </Button>
          </div>
        </Card>

        {/* Taymer */}
        <Card className="flex flex-col items-center p-6">
          <div className="text-sm uppercase tracking-widest text-muted">Taymer</div>
          <div className="relative mt-4 grid h-48 w-48 place-items-center">
            <svg viewBox="0 0 100 100" className="absolute inset-0 -rotate-90">
              <circle cx="50" cy="50" r="45" fill="none" stroke="var(--surface-2)" strokeWidth="6" />
              <circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke={urgent ? "var(--danger)" : "var(--accent)"}
                strokeWidth="6"
                strokeLinecap="round"
                strokeDasharray={`${(pct / 100) * 282.7} 282.7`}
              />
            </svg>
            <span className={`text-5xl font-bold tabular-nums ${urgent ? "animate-pulse text-danger" : ""}`}>{fmtSeconds(timer.left)}</span>
          </div>
          <div className="mt-5 flex gap-2">
            <Button disabled={!inProgress} onClick={() => timerAction(timer.running ? "pause" : "start")} className="min-w-28">
              {timer.running ? "⏸ Pauza" : "▶ Start"}
            </Button>
            <Button variant="ghost" disabled={!inProgress} onClick={() => timerAction("reset")}>
              ↺
            </Button>
          </div>
          <div className="mt-4 flex gap-1.5">
            {[30, 45, 60, 90].map((s) => (
              <button
                key={s}
                disabled={!inProgress}
                onClick={() => timerAction("reset", s)}
                className={`rounded-lg px-2.5 py-1 text-xs ${timer.total === s ? "bg-accent-soft text-accent" : "text-muted hover:text-fg"}`}
              >
                {s}s
              </button>
            ))}
          </div>
          <div className="mt-auto pt-6 text-center text-xs text-muted">
            Klaviatura: ← → savol · Probel — start/pauza · R — qaytarish
          </div>
        </Card>
      </div>
    </>
  );
}
