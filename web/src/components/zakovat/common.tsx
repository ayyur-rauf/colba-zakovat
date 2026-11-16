"use client";

import { GAME_STATUS, TEAM_STATUS, type GameStatus } from "@/lib/types";
import { Badge } from "../ui";

const GAME_TONE = {
  planned: "gray",
  registration: "accent",
  in_progress: "amber",
  preliminary: "amber",
  final: "green",
  cancelled: "gray",
} as const;

export function GameStatusBadge({ status }: { status: GameStatus }) {
  return (
    <Badge tone={GAME_TONE[status]}>
      {status === "in_progress" && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-warning" />}
      {GAME_STATUS[status]}
    </Badge>
  );
}

export function TeamStatusBadge({ status }: { status: string }) {
  const tone = status === "active" ? "green" : status === "pending" ? "amber" : status === "draft" ? "gray" : "red";
  return <Badge tone={tone}>{TEAM_STATUS[status] ?? status}</Badge>;
}

export function PlaceCell({ place, tie }: { place: number | null; tie?: number | null }) {
  if (place === null) return <span className="text-muted">—</span>;
  const medal = place === 1 ? "text-gold" : place <= 3 ? "text-fg" : "text-muted";
  return (
    <span className={`font-semibold ${medal}`}>
      {place}
      {tie ? <span className="ml-1 text-xs text-warning" title="Teng — qo'shimcha o'yin kerak">=</span> : null}
    </span>
  );
}
