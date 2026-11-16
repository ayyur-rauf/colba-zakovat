"use client";

// O'yin savollari: 1..N raqamlarga bankdan savol biriktirish, avtomatik to'ldirish.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi, usePerms } from "@/lib/hooks";
import type { Game, GameQuestionSlot, QuestionBank } from "@/lib/types";
import { Badge, Button, Card, CardHeader, Empty, LinkButton, Notice, PageTitle } from "../ui";

export default function GameQuestions() {
  const { id } = useParams<{ id: string }>();
  const { zakovatTg } = usePerms();
  const game = useApi<Game>(`zakovat/games/${id}`);
  const slots = useApi<GameQuestionSlot[]>(`zakovat/games/${id}/questions`);
  const [search, setSearch] = useState("");
  const free = useApi<QuestionBank>(zakovatTg ? `zakovat/questions?free=1&status=approved${search ? `&q=${encodeURIComponent(search)}` : ""}` : null);
  const act = useAction();
  const [picking, setPicking] = useState<number | null>(null);

  const g = game.data;
  const list = slots.data ?? [];
  const filled = list.filter((s) => s.question).length;
  const locked = g?.status === "final" || g?.status === "cancelled";
  const rounds = g ? Array.from({ length: g.rounds }, (_, i) => i + 1) : [];

  const reloadAll = () => {
    slots.reload();
    free.reload();
  };
  const assign = (number: number, question_id: number | null) =>
    act.run(() => api(`zakovat/games/${id}/questions`, { method: "POST", body: { number, question_id } })).then(() => {
      setPicking(null);
      reloadAll();
    });

  return (
    <>
      <div>
        <Link href="/zakovat/games" className="text-sm text-muted hover:text-fg">
          ← O&apos;yinlar
        </Link>
      </div>
      <PageTitle
        title={`${g?.title ?? ""} — savollar`}
        subtitle={
          <span className="flex items-center gap-2">
            To&apos;ldirilgan: {filled} / {list.length}
            <Badge tone={filled === list.length && list.length ? "green" : "amber"}>{filled === list.length ? "tayyor" : "to'liq emas"}</Badge>
          </span>
        }
        actions={
          <>
            {zakovatTg && !locked && (
              <Button
                variant="soft"
                disabled={act.busy || !free.data?.items.length || filled === list.length}
                onClick={() =>
                  act
                    .run(
                      () =>
                        api(`zakovat/games/${id}/questions/autofill`, {
                          method: "POST",
                          body: { question_ids: (free.data?.items ?? []).map((q) => q.id) },
                        }),
                      "Bo'sh raqamlar tasdiqlangan savollar bilan to'ldirildi",
                    )
                    .then(reloadAll)
                }
              >
                ⚡ Avtomatik to&apos;ldirish
              </Button>
            )}
            <LinkButton href={`/zakovat/${id}/host`}>Boshlovchi pulti</LinkButton>
          </>
        }
      />
      <Notice error={act.error ?? slots.error} notice={act.notice} onClose={act.clear} />

      {rounds.map((r) => (
        <Card key={r}>
          <CardHeader title={`${r}-raund`} />
          <ul className="divide-y divide-line">
            {list
              .filter((s) => s.round === r)
              .map((s) => (
                <li key={s.number} className="px-5 py-3">
                  <div className="flex flex-wrap items-start gap-4">
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-surface-2 font-semibold">{s.number}</span>
                    <div className="min-w-0 flex-1 text-sm">
                      {s.question ? (
                        <>
                          <p className="line-clamp-2">{s.question.text}</p>
                          <p className="mt-1 text-muted">
                            Javob: <span className="text-success">{s.question.answer}</span>
                            {s.question.topic && ` · ${s.question.topic}`}
                          </p>
                        </>
                      ) : (
                        <p className="pt-2 text-muted">Bo&apos;sh</p>
                      )}
                    </div>
                    {zakovatTg && !locked && (
                      <div className="flex gap-2">
                        <Button variant="ghost" onClick={() => setPicking(picking === s.number ? null : s.number)}>
                          {s.question ? "Almashtirish" : "Tanlash"}
                        </Button>
                        {s.question && (
                          <Button variant="ghost" onClick={() => assign(s.number, null)} title="Bo'shatish">
                            ✕
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                  {picking === s.number && (
                    <div className="mt-3 rounded-xl border border-line bg-bg-elev/60 p-3">
                      <input
                        className="field mb-2"
                        autoFocus
                        placeholder="Tasdiqlangan, biriktirilmagan savollardan qidirish"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                      />
                      <ul className="max-h-72 space-y-1 overflow-y-auto">
                        {(free.data?.items ?? []).map((q) => (
                          <li key={q.id}>
                            <button
                              onClick={() => assign(s.number, q.id)}
                              className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-surface-2"
                            >
                              <span className="line-clamp-1">{q.text}</span>
                              <span className="text-xs text-muted">
                                {q.answer}
                                {q.topic && ` · ${q.topic}`}
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                      {free.data?.items.length === 0 && (
                        <Empty>
                          Bo&apos;sh savol yo&apos;q. <Link className="text-accent" href="/zakovat/questions">Savollar bankida</Link> yangisini qo&apos;shing va
                          &quot;Tasdiqlangan&quot; qiling.
                        </Empty>
                      )}
                    </div>
                  )}
                </li>
              ))}
          </ul>
        </Card>
      ))}
    </>
  );
}
