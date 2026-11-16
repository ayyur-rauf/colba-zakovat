"use client";

// Hisob hay'ati: javoblar jadvali (jamoalar × savollar), raund tarkibi, joriy savol,
// Tashkiliy guruh uchun o'yin holatini boshqarish va apellyatsiyalar.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { RequireAuth, useAuth } from "@/lib/auth";
import { GAME_STATUS, type Appeal, type Sheet, type SheetTeam } from "@/lib/types";
import { Badge, Button, ErrorBar, Header } from "../ui";

const POLL_MS = 4000;
const MAX_ON_STAGE = 6;
const MIN_PLAYERS = 3;

function Inner() {
  const { id } = useParams<{ id: string }>();
  const { zakovat } = useAuth();
  const isTg = !!zakovat?.is_tg;
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [round, setRound] = useState<number | null>(null);
  const [appeals, setAppeals] = useState<Appeal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const pending = useRef(0);
  // Belgilar ketma-ket yuboriladi: tez ikki marta bosilganda server oxirgi bosishni oladi.
  const markQueue = useRef<Promise<unknown>>(Promise.resolve());

  const load = useCallback(async () => {
    if (pending.current > 0) return; // foydalanuvchi o'zgarishi yuborilayotganda ustidan yozmaymiz
    try {
      const s = await api<Sheet>(`zakovat/games/${id}/sheet`);
      if (pending.current === 0) setSheet(s);
      setRound((r) => r ?? Math.max(1, s.current_round || 1));
      if (s.game.status === "preliminary" || s.game.status === "final") {
        setAppeals(await api<Appeal[]>(`zakovat/games/${id}/appeals`));
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Server bilan aloqa yo'q.");
    }
  }, [id]);

  usePolling(load, POLL_MS);

  async function run(fn: () => Promise<unknown>) {
    pending.current += 1;
    try {
      await fn();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Server bilan aloqa yo'q.");
    } finally {
      pending.current -= 1;
      await load();
    }
  }

  if (!sheet || round === null) {
    return <div className="p-10 text-center text-gray-500">{error ?? "Yuklanmoqda…"}</div>;
  }

  const g = sheet.game;
  const qpr = g.questions_per_round;
  const first = (round - 1) * qpr + 1;
  const questions = Array.from({ length: qpr }, (_, i) => first + i);
  const editable = g.status === "in_progress";
  const lineupEditable = g.status === "in_progress" || g.status === "registration" || g.status === "planned";

  function toggle(team: SheetTeam, q: number) {
    if (!editable) return;
    const cur = team.answers[q - 1];
    const next = cur !== true;
    // darhol ko'rsatamiz, keyin serverga yuboramiz
    setSheet((s) =>
      s && {
        ...s,
        teams: s.teams.map((t) =>
          t.team.id === team.team.id ? { ...t, answers: t.answers.map((a, i) => (i === q - 1 ? next : a)) } : t,
        ),
      },
    );
    const send = () =>
      api(`zakovat/games/${id}/marks`, { method: "POST", body: { team_id: team.team.id, number: q, correct: next } });
    const job = markQueue.current.catch(() => undefined).then(send);
    markQueue.current = job;
    run(() => job);
  }

  const setCurrent = (n: number) =>
    run(() => api(`zakovat/games/${id}/current`, { method: "POST", body: { number: n } }));

  function gameAction(action: "start" | "publish" | "finalize", confirmText: string) {
    if (!window.confirm(confirmText)) return;
    run(() => api(`zakovat/games/${id}/${action}`, { method: "POST" }));
  }

  const pendingAppeals = appeals.filter((a) => a.status === "pending");

  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-[1400px] flex-1 space-y-4 px-4 py-5">
        {/* Sarlavha */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Link href="/" className="text-sm text-gray-500 hover:text-gray-700">
              ← O&apos;yinlar
            </Link>
            <h1 className="text-2xl font-semibold">
              {g.title} <Badge tone={editable ? "amber" : g.status === "final" ? "green" : "blue"}>{GAME_STATUS[g.status]}</Badge>
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href={`/zakovat/${id}/screen`}
              target="_blank"
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm hover:bg-gray-50"
            >
              Katta ekran ↗
            </Link>
            {isTg && (
              <Button
                variant="ghost"
                onClick={() => run(() => api(`zakovat/games/${id}`, { method: "PATCH", body: { hide_standings: !g.hide_standings } }))}
              >
                {g.hide_standings ? "🙈 Reyting yashirin" : "👁 Reyting ochiq"}
              </Button>
            )}
            {isTg && (g.status === "planned" || g.status === "registration") && (
              <Button onClick={() => gameAction("start", "O'yinni boshlaysizmi? Ro'yxatdan o'tish yopiladi.")}>
                O&apos;yinni boshlash
              </Button>
            )}
            {isTg && g.status === "in_progress" && (
              <Button
                variant="success"
                onClick={() =>
                  gameAction("publish", "Dastlabki natijani e'lon qilasizmi? Shundan keyin belgilar faqat apellyatsiya orqali o'zgaradi.")
                }
              >
                Dastlabki natijani e&apos;lon qilish
              </Button>
            )}
            {isTg && g.status === "preliminary" && (
              <Button
                variant="success"
                disabled={pendingAppeals.length > 0}
                title={pendingAppeals.length ? "Avval apellyatsiyalarni ko'rib chiqing" : ""}
                onClick={() => gameAction("finalize", "Yakuniy natijani tasdiqlaysizmi? Ballar mavsum reytingiga yoziladi.")}
              >
                Yakuniy natijani tasdiqlash
              </Button>
            )}
          </div>
        </div>

        <ErrorBar message={error} onClose={() => setError(null)} />

        {/* Joriy savol va raundlar */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3">
          <div className="flex items-center gap-2">
            {Array.from({ length: g.rounds }, (_, i) => i + 1).map((r) => (
              <button
                key={r}
                onClick={() => setRound(r)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                  r === round ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {r}-raund {r === sheet.current_round && editable && "•"}
              </button>
            ))}
          </div>
          {editable && (
            <div className="flex items-center gap-2">
              <Button variant="ghost" disabled={sheet.current_question <= 1} onClick={() => setCurrent(sheet.current_question - 1)}>
                ◀
              </Button>
              <span className="min-w-36 text-center font-medium">
                Joriy savol: <span className="text-brand-600">{sheet.current_question}</span> / {g.rounds * qpr}
              </span>
              <Button
                variant="ghost"
                disabled={sheet.current_question >= g.rounds * qpr}
                onClick={() => setCurrent(sheet.current_question + 1)}
              >
                ▶
              </Button>
            </div>
          )}
        </div>

        {/* Javoblar jadvali */}
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50 text-gray-600">
                <th className="sticky left-0 z-10 bg-gray-50 px-3 py-2 text-left font-medium">Stol / Jamoa</th>
                {questions.map((q) => (
                  <th key={q} className="px-1 py-2 font-medium">
                    <button
                      disabled={!editable}
                      onClick={() => setCurrent(q)}
                      title={editable ? "Joriy savol qilish" : ""}
                      className={`h-8 w-9 rounded-md ${
                        q === sheet.current_question && editable ? "bg-brand-600 text-white" : "hover:bg-gray-200"
                      }`}
                    >
                      {q}
                    </button>
                  </th>
                ))}
                <th className="px-3 py-2 font-medium">Ball</th>
                <th className="px-3 py-2 font-medium">J</th>
                <th className="px-3 py-2 font-medium">O&apos;rin</th>
              </tr>
            </thead>
            <tbody>
              {sheet.teams.map((t) => {
                const counted = new Set(t.counted);
                const onStage = t.lineup.filter((l) => l.round_no === round).length;
                return (
                  <tr key={t.team.id} className="border-t border-gray-100">
                    <td className="sticky left-0 z-10 bg-white px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="grid h-7 w-7 place-items-center rounded-md bg-gray-100 text-xs font-semibold">
                          {t.table_number ?? "–"}
                        </span>
                        <div>
                          <div className="font-medium">{t.team.name}</div>
                          <div className={`text-xs ${onStage < MIN_PLAYERS ? "text-red-600" : "text-gray-400"}`}>
                            Tarkib: {onStage}/{MAX_ON_STAGE}
                            {onStage < MIN_PLAYERS && " — hisobga olinmaydi"}
                          </div>
                        </div>
                      </div>
                    </td>
                    {questions.map((q) => {
                      const v = t.answers[q - 1];
                      const isCounted = counted.has(q);
                      return (
                        <td key={q} className="px-1 py-1 text-center">
                          <button
                            onClick={() => toggle(t, q)}
                            disabled={!editable}
                            title={isCounted ? "" : "Bu savolda 3 o'yinchidan kam — hisobga olinmaydi"}
                            className={`h-9 w-9 rounded-md border text-base font-semibold transition ${
                              v === true
                                ? "border-emerald-300 bg-emerald-100 text-emerald-700"
                                : v === false
                                  ? "border-red-200 bg-red-50 text-red-500"
                                  : "border-gray-200 bg-white text-gray-300"
                            } ${isCounted ? "" : "cell-uncounted opacity-60"} ${
                              q === sheet.current_question && editable ? "ring-2 ring-brand-500" : ""
                            } ${editable ? "hover:scale-105" : "cursor-default"}`}
                          >
                            {v === true ? "✓" : v === false ? "✗" : "·"}
                          </button>
                        </td>
                      );
                    })}
                    <td className="px-3 py-2 text-center text-base font-semibold">{t.points}</td>
                    <td className="px-3 py-2 text-center text-gray-500">{t.rating_j}</td>
                    <td className="px-3 py-2 text-center font-medium">{t.place ?? "–"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-gray-400">
          Katakni bosing: ✓ to&apos;g&apos;ri ↔ ✗ noto&apos;g&apos;ri. Chiziqli katak — o&apos;sha savolda jamoada 3 o&apos;yinchidan kam
          bo&apos;lgan, ball hisobga olinmaydi (Nizom 3.6, 4.3). Jadval har {POLL_MS / 1000} soniyada yangilanadi.
        </p>

        {/* Tarkib */}
        <section className="rounded-xl border border-gray-200 bg-white">
          <div className="border-b border-gray-100 px-4 py-3">
            <h2 className="font-semibold">{round}-raund tarkibi</h2>
            <p className="text-xs text-gray-500">
              Bir vaqtda ko&apos;pi bilan {MAX_ON_STAGE} o&apos;yinchi. Raund boshlangach almashtirib bo&apos;lmaydi, kech kelgan o&apos;yinchi
              joriy savoldan qo&apos;shiladi (Nizom 5.2, 4.3).
            </p>
          </div>
          <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">
            {sheet.teams.map((t) => (
              <LineupCard
                key={t.team.id}
                team={t}
                round={round}
                roundFirst={first}
                editable={lineupEditable}
                canRemove={lineupEditable && !(editable && sheet.current_question >= first)}
                onAdd={(userId) =>
                  run(() =>
                    api(`zakovat/games/${id}/lineup`, {
                      method: "POST",
                      body: { team_id: t.team.id, round_no: round, user_id: userId },
                    }),
                  )
                }
                onRemove={(entryId) => run(() => api(`zakovat/games/${id}/lineup/${entryId}/remove`, { method: "POST" }))}
                onCopy={() =>
                  run(() =>
                    api(`zakovat/games/${id}/lineup/copy`, {
                      method: "POST",
                      body: { team_id: t.team.id, from_round: round - 1, to_round: round },
                    }),
                  )
                }
              />
            ))}
          </div>
        </section>

        {/* Apellyatsiyalar */}
        {(g.status === "preliminary" || g.status === "final") && (
          <section className="rounded-xl border border-gray-200 bg-white">
            <div className="border-b border-gray-100 px-4 py-3">
              <h2 className="font-semibold">
                Apellyatsiyalar {pendingAppeals.length > 0 && <Badge tone="amber">{pendingAppeals.length} ta kutmoqda</Badge>}
              </h2>
            </div>
            <ul className="divide-y divide-gray-100">
              {appeals.map((a) => (
                <li key={a.id} className="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
                  <div className="max-w-3xl text-sm">
                    <div className="font-medium">
                      {a.team.name} · {a.number}-savol{" "}
                      <Badge tone={a.status === "pending" ? "amber" : a.status === "accepted" ? "green" : "red"}>
                        {a.status === "pending" ? "Kutmoqda" : a.status === "accepted" ? "Qabul qilindi" : "Rad etildi"}
                      </Badge>
                    </div>
                    <p className="mt-1 text-gray-700">{a.content}</p>
                    <p className="text-gray-500">Dalil: {a.evidence}</p>
                    {a.decision_reason && <p className="text-gray-500">Qaror: {a.decision_reason}</p>}
                  </div>
                  {isTg && a.status === "pending" && g.status === "preliminary" && (
                    <div className="flex gap-2">
                      {[true, false].map((accept) => (
                        <Button
                          key={String(accept)}
                          variant={accept ? "success" : "danger"}
                          onClick={() => {
                            const reason = window.prompt(accept ? "Qabul qilish sababi:" : "Rad etish sababi:");
                            if (reason?.trim())
                              run(() => api(`zakovat/appeals/${a.id}/decide`, { method: "POST", body: { accept, reason } }));
                          }}
                        >
                          {accept ? "Qabul qilish" : "Rad etish"}
                        </Button>
                      ))}
                    </div>
                  )}
                </li>
              ))}
              {appeals.length === 0 && <li className="px-4 py-5 text-center text-sm text-gray-400">Apellyatsiya yo&apos;q</li>}
            </ul>
          </section>
        )}
      </main>
    </>
  );
}

function LineupCard({
  team,
  round,
  roundFirst,
  editable,
  canRemove,
  onAdd,
  onRemove,
  onCopy,
}: {
  team: SheetTeam;
  round: number;
  roundFirst: number;
  editable: boolean;
  canRemove: boolean;
  onAdd: (userId: number) => void;
  onRemove: (entryId: number) => void;
  onCopy: () => void;
}) {
  const entries = team.lineup.filter((l) => l.round_no === round);
  const inLineup = new Set(entries.map((e) => e.user.id));
  const available = team.players.filter((p) => !inLineup.has(p.id));
  const full = entries.length >= MAX_ON_STAGE;
  const prevCount = team.lineup.filter((l) => l.round_no === round - 1).length;

  return (
    <div className="rounded-lg border border-gray-200 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-medium">{team.team.name}</span>
        <Badge tone={entries.length < MIN_PLAYERS ? "red" : "green"}>
          {entries.length}/{MAX_ON_STAGE}
        </Badge>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {entries.map((e) => (
          <span key={e.id} className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-xs">
            {e.user.name}
            {e.from_question > roundFirst && <span className="text-amber-700">({e.from_question}-savoldan)</span>}
            {canRemove && (
              <button onClick={() => onRemove(e.id)} className="text-gray-400 hover:text-red-600" title="Olib tashlash">
                ✕
              </button>
            )}
          </span>
        ))}
        {entries.length === 0 && <span className="text-xs text-gray-400">Tarkib kiritilmagan</span>}
      </div>
      {editable && (
        <div className="mt-2 flex flex-wrap gap-2">
          <select
            disabled={full || available.length === 0}
            value=""
            onChange={(ev) => ev.target.value && onAdd(Number(ev.target.value))}
            className="rounded-md border border-gray-300 px-2 py-1 text-xs disabled:bg-gray-50"
          >
            <option value="">+ O&apos;yinchi qo&apos;shish</option>
            {available.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          {round > 1 && prevCount > 0 && entries.length === 0 && (
            <button onClick={onCopy} className="rounded-md border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50">
              {round - 1}-raund tarkibini ko&apos;chirish
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function ScoreSheet() {
  return (
    <RequireAuth>
      <Inner />
    </RequireAuth>
  );
}
