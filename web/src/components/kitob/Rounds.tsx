"use client";

// Kitobxonlik — turlar: yangi tur, ovoz berish, o'qish, baholash bosqichlarini boshqarish.

import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi, usePerms } from "@/lib/hooks";
import type { Book, ReadingRound } from "@/lib/types";
import { Button, Card, CardHeader, Empty, Field, formatDate, Notice, PageTitle } from "../ui";
import { openProtectedFile, RoundStatusBadge } from "./common";

const STEPS = ["draft", "voting", "reading", "grading", "done"] as const;
const STEP_TITLE = ["Qoralama", "Ovoz", "O'qish", "Baholash", "Yakun"];

export default function KitobRounds() {
  const { kitobOrganizer: org } = usePerms();
  const rounds = useApi<ReadingRound[]>("kitob/rounds");
  const act = useAction();
  const [creating, setCreating] = useState(false);

  return (
    <>
      <PageTitle
        title="Kitobxonlik turlari"
        subtitle="Ovoz → eng ko'p ovoz olgan kitob → hammaga bir xil o'qish muddati → izoh → baholash"
        actions={org && <Button onClick={() => setCreating(!creating)}>+ Yangi tur</Button>}
      />
      <Notice error={act.error ?? rounds.error} notice={act.notice} onClose={act.clear} />
      {creating && (
        <NewRound
          act={act}
          onDone={() => {
            setCreating(false);
            rounds.reload();
          }}
        />
      )}
      <div className="space-y-4">
        {(rounds.data ?? []).map((r) => (
          <RoundCard key={r.id} r={r} org={org} act={act} reload={rounds.reload} />
        ))}
      </div>
      {rounds.data?.length === 0 && (
        <Card>
          <Empty>Hali tur yo&apos;q{org ? " — «Yangi tur» tugmasini bosing" : ""}</Empty>
        </Card>
      )}
    </>
  );
}

type Act = ReturnType<typeof useAction>;

function Stepper({ status }: { status: ReadingRound["status"] }) {
  const idx = STEPS.indexOf(status);
  return (
    <div className="flex items-center gap-1">
      {STEP_TITLE.map((t, i) => (
        <div key={t} className="flex items-center gap-1">
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs ${
              i < idx ? "bg-success/15 text-success" : i === idx ? "bg-accent text-white" : "bg-surface-2 text-muted"
            }`}
          >
            {t}
          </span>
          {i < STEP_TITLE.length - 1 && <span className="h-px w-3 bg-line" />}
        </div>
      ))}
    </div>
  );
}

function RoundCard({ r, org, act, reload }: { r: ReadingRound; org: boolean; act: Act; reload: () => void }) {
  const [voteEnds, setVoteEnds] = useState("");
  const [pick, setPick] = useState("");
  const total = Object.values(r.votes ?? {}).reduce((a, b) => a + b, 0);
  const post = (path: string, body?: unknown, ok?: string) =>
    act.run(() => api(`kitob/rounds/${r.id}/${path}`, { method: "POST", body }), ok).then(reload);

  return (
    <Card>
      <CardHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            {r.title} <RoundStatusBadge status={r.status} />
          </span>
        }
        subtitle={<Stepper status={r.status} />}
      />
      <div className="grid gap-6 p-5 lg:grid-cols-2">
        {/* Kitoblar va ovozlar */}
        <div>
          <h3 className="mb-3 text-sm font-medium text-muted">{r.selected_book ? "Tanlangan kitob" : "Nomzod kitoblar"}</h3>
          <ul className="space-y-2.5">
            {(r.selected_book ? [r.selected_book] : r.candidates).map((b) => {
              const n = r.votes?.[String(b.id)] ?? 0;
              return (
                <li key={b.id} className="rounded-lg border border-line bg-bg-elev/60 px-3 py-2.5">
                  <div className="flex items-center justify-between gap-2 text-sm">
                    <span>
                      <span className="font-medium">{b.title}</span> <span className="text-muted">— {b.author}</span>
                    </span>
                    {r.votes && !r.selected_book && <span className="text-muted">{n} ovoz</span>}
                  </div>
                  {r.votes && !r.selected_book && (
                    <div className="mt-2 h-1.5 rounded-full bg-surface-2">
                      <div className="h-1.5 rounded-full bg-accent" style={{ width: total ? `${(n / total) * 100}%` : 0 }} />
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
          {r.can_read && (
            <Button
              variant="soft"
              className="mt-3"
              onClick={() => openProtectedFile(`kitob/rounds/${r.id}/book`).catch((e) => act.setError(e.message))}
            >
              📖 Kitobni ochish (PDF)
            </Button>
          )}
        </div>

        {/* Muddatlar va amallar */}
        <div className="space-y-3 text-sm">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
            <dt className="text-muted">Ovoz berish tugashi</dt>
            <dd>{formatDate(r.vote_ends)}</dd>
            <dt className="text-muted">O&apos;qish boshlandi</dt>
            <dd>{formatDate(r.reading_starts)}</dd>
            <dt className="text-muted">Izoh muddati</dt>
            <dd>{formatDate(r.my_deadline)}</dd>
            <dt className="text-muted">O&apos;qish muddati</dt>
            <dd>{r.reading_days} kun</dd>
            <dt className="text-muted">Mezonlar</dt>
            <dd>{r.criteria.map((c) => `${c.name} (${c.max_points})`).join(", ")}</dd>
          </dl>

          {org && (
            <div className="rounded-xl border border-line bg-bg-elev/60 p-4">
              <div className="mb-2 text-xs uppercase tracking-wider text-muted">Keyingi qadam</div>
              {r.status === "draft" && (
                <div className="flex flex-wrap items-end gap-2">
                  <Field label="Ovoz berish tugash vaqti">
                    <input className="field" type="datetime-local" value={voteEnds} onChange={(e) => setVoteEnds(e.target.value)} />
                  </Field>
                  <Button
                    disabled={!voteEnds || act.busy}
                    onClick={() => post("start-voting", { vote_ends: new Date(voteEnds).toISOString() }, "Ovoz berish boshlandi")}
                  >
                    Ovoz berishni boshlash
                  </Button>
                </div>
              )}
              {r.status === "voting" && (
                <div className="flex flex-wrap items-end gap-2">
                  <Field label="Ovozlar teng bo'lsa — kitobni tanlang" hint="Odatda bo'sh qoldiring: eng ko'p ovoz olgani tanlanadi">
                    <select className="field" value={pick} onChange={(e) => setPick(e.target.value)}>
                      <option value="">Avtomatik</option>
                      {r.candidates.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.title}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Button
                    disabled={act.busy}
                    onClick={() => post("close-voting", pick ? { book_id: Number(pick) } : {}, "Kitob tanlandi, o'qish boshlandi")}
                  >
                    Ovozni yakunlash
                  </Button>
                </div>
              )}
              {r.status === "reading" && (
                <Button disabled={act.busy} onClick={() => post("start-grading", undefined, "Baholash boshlandi")}>
                  Baholashni boshlash
                </Button>
              )}
              {r.status === "grading" && (
                <div className="flex flex-wrap gap-2">
                  <Link href={`/kitobxonlik/grading?round=${r.id}`} className="rounded-[10px] bg-accent-soft px-3.5 py-2 text-accent">
                    Izohlarni baholash →
                  </Link>
                  <Button
                    variant="success"
                    disabled={act.busy}
                    onClick={() =>
                      window.confirm("Natijalarni tasdiqlaysizmi? Ballar xodimlar hisobiga yoziladi, baholar qulflanadi.") &&
                      post("approve", undefined, "Natijalar tasdiqlandi")
                    }
                  >
                    Natijalarni tasdiqlash
                  </Button>
                </div>
              )}
              {r.status === "done" && <span className="text-success">Tur yakunlangan, ballar yozilgan ✓</span>}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

function NewRound({ act, onDone }: { act: Act; onDone: () => void }) {
  const books = useApi<Book[]>("kitob/books");
  const [title, setTitle] = useState("");
  const [picked, setPicked] = useState<number[]>([]);
  const [days, setDays] = useState("10");
  const [minLen, setMinLen] = useState("500");
  const [reviewers, setReviewers] = useState("1");
  const [criteria, setCriteria] = useState([
    { name: "Mazmunni tushunish", max_points: 10 },
    { name: "Shaxsiy fikr va tahlil", max_points: 10 },
    { name: "Savodxonlik va uslub", max_points: 5 },
  ]);

  return (
    <Card>
      <CardHeader title="Yangi tur" subtitle="Kamida 2 ta kitobni ovozga qo'ying" />
      <form
        className="space-y-5 p-5"
        onSubmit={async (e) => {
          e.preventDefault();
          const ok = await act.run(
            () =>
              api("kitob/rounds", {
                method: "POST",
                body: {
                  title,
                  book_ids: picked,
                  criteria,
                  reading_days: Number(days),
                  min_review_length: Number(minLen),
                  reviewers_per_review: Number(reviewers),
                },
              }),
            "Tur yaratildi",
          );
          if (ok) onDone();
        }}
      >
        <div className="grid gap-4 md:grid-cols-4">
          <Field label="Nomi">
            <input className="field" required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Dekabr kitobi" />
          </Field>
          <Field label="O'qish muddati (kun)">
            <input className="field" type="number" min={1} max={60} value={days} onChange={(e) => setDays(e.target.value)} />
          </Field>
          <Field label="Izoh minimal uzunligi">
            <input className="field" type="number" min={0} value={minLen} onChange={(e) => setMinLen(e.target.value)} />
          </Field>
          <Field label="Bir izohga tekshiruvchilar">
            <input className="field" type="number" min={1} max={5} value={reviewers} onChange={(e) => setReviewers(e.target.value)} />
          </Field>
        </div>

        <div>
          <div className="mb-2 text-sm font-medium">Ovozga qo&apos;yiladigan kitoblar</div>
          <div className="grid gap-2 md:grid-cols-2">
            {(books.data ?? []).map((b) => {
              const on = picked.includes(b.id);
              return (
                <button
                  type="button"
                  key={b.id}
                  onClick={() => setPicked(on ? picked.filter((x) => x !== b.id) : [...picked, b.id])}
                  className={`rounded-lg border px-3 py-2 text-left text-sm transition ${
                    on ? "border-accent bg-accent-soft" : "border-line hover:bg-surface-2"
                  }`}
                >
                  {on ? "☑" : "☐"} <span className="font-medium">{b.title}</span> <span className="text-muted">— {b.author}</span>
                </button>
              );
            })}
          </div>
          {books.data?.length === 0 && (
            <p className="text-sm text-muted">
              Kitob yo&apos;q. Avval{" "}
              <Link className="text-accent" href="/kitobxonlik/books">
                Kitoblar
              </Link>{" "}
              bo&apos;limida qo&apos;shing.
            </p>
          )}
        </div>

        <div>
          <div className="mb-2 text-sm font-medium">Baholash mezonlari</div>
          <div className="space-y-2">
            {criteria.map((c, i) => (
              <div key={i} className="flex gap-2">
                <input
                  className="field"
                  value={c.name}
                  onChange={(e) => setCriteria(criteria.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))}
                />
                <input
                  className="field w-28"
                  type="number"
                  min={1}
                  value={c.max_points}
                  onChange={(e) => setCriteria(criteria.map((x, j) => (j === i ? { ...x, max_points: Number(e.target.value) } : x)))}
                />
                <Button type="button" variant="ghost" onClick={() => setCriteria(criteria.filter((_, j) => j !== i))}>
                  ✕
                </Button>
              </div>
            ))}
            <Button type="button" variant="ghost" onClick={() => setCriteria([...criteria, { name: "", max_points: 5 }])}>
              + Mezon
            </Button>
          </div>
        </div>

        <Button type="submit" disabled={act.busy || picked.length < 2 || criteria.length === 0}>
          Turni yaratish
        </Button>
      </form>
    </Card>
  );
}
