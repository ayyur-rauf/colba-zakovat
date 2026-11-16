"use client";

// Kitobxonlik — baholash: tekshiruvchi izohlarni mezonlar bo'yicha baholaydi.

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi, usePerms } from "@/lib/hooks";
import type { ReadingRound, ReviewForGrading } from "@/lib/types";
import { Badge, Button, Card, Empty, Field, formatDate, Notice, PageTitle } from "../ui";
import { openProtectedFile, RoundStatusBadge } from "./common";

export default function KitobGrading() {
  const { kitobReviewer } = usePerms();
  const params = useSearchParams();
  const router = useRouter();
  const rounds = useApi<ReadingRound[]>("kitob/rounds");
  const candidates = (rounds.data ?? []).filter((r) => r.status === "grading" || r.status === "done");
  const selectedId = Number(params.get("round")) || candidates.find((r) => r.status === "grading")?.id || candidates[0]?.id;
  const round = candidates.find((r) => r.id === selectedId) ?? null;

  if (!kitobReviewer) {
    return (
      <Card>
        <Empty>Bu bo&apos;lim faqat tekshiruvchi va tashkilotchilar uchun.</Empty>
      </Card>
    );
  }

  return (
    <>
      <PageTitle
        title="Izohlarni baholash"
        subtitle="O'z izohingiz ro'yxatda ko'rinmaydi. Natija tasdiqlangach baho o'zgartirilmaydi."
        actions={
          candidates.length > 0 && (
            <select className="field w-auto" value={selectedId ?? ""} onChange={(e) => router.replace(`/kitobxonlik/grading?round=${e.target.value}`)}>
              {candidates.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.title}
                </option>
              ))}
            </select>
          )
        }
      />
      <Notice error={rounds.error} onClose={() => rounds.setError(null)} />
      {round ? (
        <ReviewList round={round} />
      ) : (
        rounds.data && (
          <Card>
            <Empty>Baholash bosqichidagi tur yo&apos;q</Empty>
          </Card>
        )
      )}
    </>
  );
}

function ReviewList({ round }: { round: ReadingRound }) {
  const reviews = useApi<ReviewForGrading[]>(`kitob/rounds/${round.id}/reviews`);
  const list = reviews.data ?? [];
  const graded = list.filter((r) => r.my_grade).length;
  return (
    <>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <RoundStatusBadge status={round.status} />
        <span className="text-muted">Kitob: {round.selected_book?.title}</span>
        <Badge tone={graded === list.length && list.length ? "green" : "amber"}>
          Siz baholadingiz: {graded} / {list.length}
        </Badge>
      </div>
      <Notice error={reviews.error} onClose={() => reviews.setError(null)} />
      <div className="space-y-4">
        {list.map((r) => (
          <ReviewCard key={r.id} review={r} round={round} onSaved={reviews.reload} />
        ))}
      </div>
      {reviews.data && list.length === 0 && (
        <Card>
          <Empty>Izoh yo&apos;q</Empty>
        </Card>
      )}
    </>
  );
}

function ReviewCard({ review, round, onSaved }: { review: ReviewForGrading; round: ReadingRound; onSaved: () => void }) {
  const act = useAction();
  const [open, setOpen] = useState(!review.my_grade && round.status === "grading");
  const [scores, setScores] = useState<Record<number, string>>(() =>
    Object.fromEntries(round.criteria.map((c) => [c.id, String(review.my_grade?.scores[c.id] ?? "")])),
  );
  const [comment, setComment] = useState(review.my_grade?.comment ?? "");
  const locked = review.status === "approved" || round.status !== "grading";
  const total = round.criteria.reduce((s, c) => s + (Number(scores[c.id]) || 0), 0);
  const max = round.criteria.reduce((s, c) => s + c.max_points, 0);

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3.5">
        <div>
          <div className="font-medium">{review.author.name}</div>
          <div className="text-xs text-muted">Yuborilgan: {formatDate(review.submitted_at)}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {review.my_grade ? <Badge tone="green">Sizning bahoyingiz: {review.my_grade.total}</Badge> : <Badge tone="amber">Baholanmagan</Badge>}
          {review.average && <Badge tone="gold">O&apos;rtacha: {review.average}</Badge>}
          <Badge>{review.grades_count} ta baho</Badge>
          <Button variant="ghost" onClick={() => setOpen(!open)}>
            {open ? "Yopish" : "Ochish"}
          </Button>
        </div>
      </div>
      {open && (
        <div className="grid gap-5 p-5 lg:grid-cols-5">
          <div className="lg:col-span-3">
            {review.text ? (
              <p className="whitespace-pre-line text-sm leading-relaxed text-fg/90">{review.text}</p>
            ) : (
              <p className="text-sm text-muted">Matn yo&apos;q — faylga qarang.</p>
            )}
            {review.has_file && (
              <Button
                variant="soft"
                className="mt-3"
                onClick={() => openProtectedFile(`kitob/reviews/${review.id}/file`).catch((e) => act.setError(e.message))}
              >
                📎 Izoh faylini ochish
              </Button>
            )}
          </div>
          <form
            className="space-y-3 lg:col-span-2"
            onSubmit={async (e) => {
              e.preventDefault();
              const ok = await act.run(
                () =>
                  api(`kitob/reviews/${review.id}/grade`, {
                    method: "POST",
                    body: { scores: round.criteria.map((c) => ({ criterion_id: c.id, points: Number(scores[c.id]) })), comment },
                  }),
                "Baho saqlandi",
              );
              if (ok) onSaved();
            }}
          >
            <Notice error={act.error} notice={act.notice} onClose={act.clear} />
            {round.criteria.map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-3">
                <span className="text-sm">{c.name}</span>
                <span className="flex items-center gap-1.5">
                  <input
                    className="field w-20 text-center"
                    type="number"
                    min={0}
                    max={c.max_points}
                    required
                    disabled={locked}
                    value={scores[c.id]}
                    onChange={(e) => setScores({ ...scores, [c.id]: e.target.value })}
                  />
                  <span className="w-8 text-xs text-muted">/ {c.max_points}</span>
                </span>
              </div>
            ))}
            <div className="flex justify-between border-t border-line pt-2 text-sm">
              <span className="text-muted">Jami</span>
              <span className="font-semibold">
                {total} / {max}
              </span>
            </div>
            <Field label="Xodimga izoh">
              <textarea className="field min-h-20" disabled={locked} value={comment} onChange={(e) => setComment(e.target.value)} />
            </Field>
            {!locked && (
              <Button type="submit" disabled={act.busy} className="w-full">
                {review.my_grade ? "Bahoni yangilash" : "Bahoni saqlash"}
              </Button>
            )}
          </form>
        </div>
      )}
    </Card>
  );
}
