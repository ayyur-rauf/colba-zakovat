"use client";

import { tokens } from "@/lib/api";
import { ROUND_STATUS, type RoundStatus } from "@/lib/types";
import { Badge } from "../ui";

const TONE = { draft: "gray", voting: "accent", reading: "amber", grading: "amber", done: "green" } as const;

export function RoundStatusBadge({ status }: { status: RoundStatus }) {
  return <Badge tone={TONE[status]}>{ROUND_STATUS[status]}</Badge>;
}

/** Himoyalangan faylni (PDF, izoh fayli) token bilan yuklab, yangi oynada ochadi. */
export async function openProtectedFile(path: string) {
  const res = await fetch(`/api/${path}`, { headers: { Authorization: `Bearer ${tokens.access ?? ""}` } });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail ?? "Faylni ochib bo'lmadi");
  }
  const url = URL.createObjectURL(await res.blob());
  window.open(url, "_blank");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
