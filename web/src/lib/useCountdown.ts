"use client";

import { useEffect, useState } from "react";
import type { TimerState } from "./types";

/** Serverdan kelgan taymer holatidan sekundomer hisoblaydi (har 200 ms yangilanadi). */
export function useCountdown(timer: TimerState | undefined, receivedAt: number) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!timer?.running) return;
    const t = setInterval(() => setNow(Date.now()), 200);
    return () => clearInterval(t);
  }, [timer?.running]);
  if (!timer) return { left: 0, running: false, total: 0 };
  const left = timer.running ? Math.max(0, timer.remaining - (now - receivedAt) / 1000) : timer.remaining;
  return { left, running: timer.running && left > 0, total: timer.seconds };
}

export function fmtSeconds(s: number) {
  const v = Math.ceil(s);
  return `${Math.floor(v / 60)}:${String(v % 60).padStart(2, "0")}`;
}
