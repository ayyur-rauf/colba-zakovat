"use client";

// Hisob hay'ati: javoblar jadvali (jamoalar × savollar), raund tarkibi, joriy savol,
// Tashkiliy guruh uchun o'yin holatini boshqarish va apellyatsiyalar.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { downloadFile } from "@/lib/download";
import { errText, useApi, usePerms } from "@/lib/hooks";
import { usePolling } from "@/lib/usePolling";
import type { Appeal, Sheet, SheetTeam } from "@/lib/types";
import { Badge, Button, Card, CardHeader, Empty, LinkButton, Notice } from "../ui";
import { GameStatusBadge, PlaceCell } from "./common";
import TiebreakPanel, { groupTies } from "./Tiebreak";

const POLL_MS = 4000;
const MAX_ON_STAGE = 6;
const MIN_PLAYERS = 3;

export default function ScoreSheet() {
  const { id } = useParams<{ id: string }>();
  const { zakovatTg: isTg, admin } = usePerms();
  const results = useApi<{ rows: { place: number | null; tie_group: number | null; team: { id: number; name: string } }[] }>(
    `zakovat/games/${id}/results`,
  );
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [round, setRound] = useState<number | null>(null);
  const [appeals, setAppeals] = useState<Appeal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const pending = useRef(0);
  // Belgilar ketma-ket yuboriladi: tez ikki marta bosilganda server oxirgi bosishni oladi.
  const markQueue = useRef<Promise<unknown>>(Promise.resolve());
  // Klaviatura kursori: qaysi jamoa (indeks) va qaysi savol
  const [cursor, setCursor] = useState<{ t: number; q: number } | null>(null);

  const load = useCallback(async () => {
    if (pending.current > 0) return; // o'zgarish yuborilayotganda ustidan yozmaymiz
    try {
      const s = await api<Sheet>(`zakovat/games/${id}/sheet`);
      if (pending.current === 0) setSheet(s);
      setRound((r) => r ?? Math.max(1, s.current_round || 1));
      if (s.game.status === "preliminary" || s.game.status === "final") {
        setAppeals(await api<Appeal[]>(`zakovat/games/${id}/appeals`));
      }
    } catch (e) {
      setError(errText(e));
    }
  }, [id]);

  usePolling(load, POLL_MS);

  async function run(fn: () => Promise<unknown>) {
    pending.current += 1;
    try {
      await fn();
    } catch (e) {
      setError(errText(e));
    } finally {
      pending.current -= 1;
      await load();
    }
  }

  function setMark(team: SheetTeam, q: number, next: boolean) {
    if (sheet?.game.status !== "in_progress") return;
    if (team.answers[q - 1] === next) return;
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

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!sheet || round === null || sheet.game.status !== "in_progress") return;
      if ((e.target instanceof HTMLElement && e.target.closest("input, textarea, select"))) return;
      const teams = sheet.teams;
      const qpr = sheet.game.questions_per_round;
      const firstQ = (round - 1) * qpr + 1;
      const lastQ = firstQ + qpr - 1;
      const c = cursor ?? { t: 0, q: Math.min(Math.max(sheet.current_question, firstQ), lastQ) };
      const move = (t: number, q: number) => {
        e.preventDefault();
        setCursor({ t: (t + teams.length) % teams.length, q: Math.min(Math.max(q, firstQ), lastQ) });
      };
      if (e.key === "ArrowDown") move(c.t + 1, c.q);
      else if (e.key === "ArrowUp") move(c.t - 1, c.q);
      else if (e.key === "ArrowRight") move(c.t, c.q + 1);
      else if (e.key === "ArrowLeft") move(c.t, c.q - 1);
      else if (["1", "+", "Enter", "0", "-"].includes(e.key) && teams[c.t]) {
        e.preventDefault();
        setMark(teams[c.t], c.q, ["1", "+", "Enter"].includes(e.key));
        // keyingi jamoaga; oxirgisidan keyin — keyingi savolning birinchi jamoasi
        if (c.t + 1 < teams.length) setCursor({ t: c.t + 1, q: c.q });
        else setCursor({ t: 0, q: Math.min(c.q + 1, lastQ) });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (!sheet || round === null) {
    return <div className="p-10 text-center text-muted">{error ?? "Yuklanmoqda…"}</div>;
  }

  const g = sheet.game;
  const qpr = g.questions_per_round;
  const first = (round - 1) * qpr + 1;
  const questions = Array.from({ length: qpr }, (_, i) => first + i);
  const editable = g.status === "in_progress";
  const lineupEditable = editable || g.status === "registration" || g.status === "planned";

  function toggle(team: SheetTeam, q: number) {
    setMark(team, q, team.answers[q - 1] !== true);
  }

  const setCurrent = (n: number) => run(() => api(`zakovat/games/${id}/current`, { method: "POST", body: { number: n } }));

  function gameAction(action: "start" | "publish" | "finalize", confirmText: string) {
    if (!window.confirm(confirmText)) return;
    run(() => api(`zakovat/games/${id}/${action}`, { method: "POST" }));
  }

  const pendingAppeals = appeals.filter((a) => a.status === "pending");

  return (
    <>
      {/* Sarlavha va boshqaruv */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link href="/zakovat/games" className="text-sm text-muted hover:text-fg">
            ← O&apos;yinlar
          </Link>
          <h1 className="mt-1 flex items-center gap-3 text-2xl font-semibold">
            {g.title} <GameStatusBadge status={g.status} />
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <LinkButton href={`/zakovat/${id}/host`}>Boshlovchi pulti</LinkButton>
          <LinkButton href={`/chop/${id}`} target="_blank">
            Blankalar
          </LinkButton>
          <LinkButton href={`/ekran/${id}`} target="_blank">
            Katta ekran ↗
          </LinkButton>
          {isTg && (
            <Button
              variant="ghost"
              onClick={() => run(() => api(`zakovat/games/${id}`, { method: "PATCH", body: { hide_standings: !g.hide_standings } }))}
            >
              {g.hide_standings ? "🙈 Reyting yashirin" : "👁 Reyting ochiq"}
            </Button>
          )}
          {isTg && (g.status === "planned" || g.status === "registration") && (
            <Button onClick={() => gameAction("start", "O'yinni boshlaysizmi? Ro'yxatdan o'tish yopiladi.")}>▶ O&apos;yinni boshlash</Button>
          )}
          {isTg && g.status === "in_progress" && (
            <Button
              variant="success"
              onClick={() => gameAction("publish", "Dastlabki natijani e'lon qilasizmi? Shundan keyin belgilar faqat apellyatsiya orqali o'zgaradi.")}
            >
              Dastlabki natijani e&apos;lon qilish
            </Button>
          )}
          {(g.status === "final" || g.status === "preliminary") && (
            <Button variant="ghost" onClick={() => downloadFile(`zakovat/games/${id}/export`).catch((e) => setError(e.message))}>
              ⬇ Excel
            </Button>
          )}
          {admin && g.status === "final" && (
            <Button
              variant="ghost"
              onClick={() => {
                const reason = window.prompt("Yakuniy natijani qayta ochish sababi (faqat bosh admin). Ballar vaqtincha qaytariladi:");
                if (reason?.trim()) run(() => api(`zakovat/games/${id}/reopen`, { method: "POST", body: { reason } }));
              }}
            >
              ↺ Qayta ochish
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

      <Notice error={error} onClose={() => setError(null)} />

      {isTg && g.status === "final" && results.data && (
        <TiebreakPanel ties={groupTies(results.data.rows)} endpoint={`zakovat/games/${id}/tiebreak`} onCreated={results.reload} />
      )}

      {/* Raundlar va joriy savol */}
      <Card className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div className="flex items-center gap-1.5">
          {Array.from({ length: g.rounds }, (_, i) => i + 1).map((r) => (
            <button
              key={r}
              onClick={() => setRound(r)}
              className={`rounded-lg px-3.5 py-1.5 text-sm font-medium transition ${
                r === round ? "bg-accent text-white" : "bg-surface-2 text-muted hover:text-fg"
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
            <span className="min-w-40 text-center">
              Joriy savol: <span className="text-xl font-bold text-accent">{sheet.current_question}</span>
              <span className="text-muted"> / {g.rounds * qpr}</span>
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
      </Card>

      {/* Javoblar jadvali */}
      <Card className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-accent-soft text-xs font-semibold text-muted">
              <th className="sticky left-0 z-10 bg-accent-soft-solid px-4 py-3 text-left">Jamoa / Savol</th>
              {questions.map((q) => (
                <th key={q} className="px-1 py-2.5">
                  <button
                    disabled={!editable}
                    onClick={() => setCurrent(q)}
                    title={editable ? "Joriy savol qilish" : ""}
                    className={`h-8 w-9 rounded-md transition ${
                      q === sheet.current_question && editable ? "bg-accent text-white" : "hover:bg-surface-2"
                    }`}
                  >
                    S{q}
                  </button>
                </th>
              ))}
              <th className="px-3 py-3">Ball</th>
              <th className="px-3 py-3">SR</th>
              <th className="px-3 py-3">O&apos;rin</th>
            </tr>
          </thead>
          <tbody>
            {sheet.teams.map((t, ti) => {
              const counted = new Set(t.counted);
              const onStage = t.lineup.filter((l) => l.round_no === round).length;
              return (
                <tr key={t.team.id} className="border-t border-line">
                  <td className="sticky left-0 z-10 bg-surface px-4 py-2">
                    <div className="flex items-center gap-2.5">
                      <span className="grid h-7 w-7 place-items-center rounded-md bg-surface-2 text-xs font-semibold">
                        {t.table_number ?? "–"}
                      </span>
                      <div>
                        <div className="font-medium">{t.team.name}</div>
                        <div className={`text-xs ${onStage < MIN_PLAYERS ? "text-danger" : "text-muted"}`}>
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
                      <td key={q} className="px-1 py-1.5 text-center">
                        <button
                          onClick={() => {
                            setCursor({ t: ti, q });
                            toggle(t, q);
                          }}
                          disabled={!editable}
                          title={isCounted ? "" : "Bu savolda 3 o'yinchidan kam — hisobga olinmaydi"}
                          className={`h-8 w-8 rounded-lg text-lg font-bold leading-none transition ${
                            v === true
                              ? "bg-accent-soft text-accent"
                              : v === false
                                ? "bg-surface-2 text-muted"
                                : "border border-dashed border-line text-muted/40"
                          } ${isCounted ? "" : "cell-uncounted opacity-50"} ${
                            q === sheet.current_question && editable ? "ring-2 ring-accent" : ""
                          } ${cursor && editable && cursor.t === ti && cursor.q === q ? "outline outline-2 outline-offset-2 outline-gold" : ""} ${
                            editable ? "hover:scale-105" : "cursor-default"
                          }`}
                        >
                          {v === true ? "+" : v === false ? "−" : "·"}
                        </button>
                      </td>
                    );
                  })}
                  <td className="px-3 py-2 text-center text-lg font-bold">{t.points}</td>
                  <td className="px-3 py-2 text-center text-muted">{t.rating_j}</td>
                  <td className="px-3 py-2 text-center">
                    <PlaceCell place={t.place} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
      <p className="text-xs text-muted">
        Katakni bosing: <b>+</b> to&apos;g&apos;ri ↔ <b>−</b> noto&apos;g&apos;ri. SR — savollar reytingi yig&apos;indisi (J). Klaviatura: strelkalar — katak tanlash, <b>1</b>/Enter — +, <b>0</b> — −
        (keyin avtomatik keyingi jamoaga o&apos;tadi). Chiziqli katak — o&apos;sha savolda jamoada 3 o&apos;yinchidan kam bo&apos;lgan, ball
        hisobga olinmaydi (Nizom 3.6, 4.3). Jadval har {POLL_MS / 1000} soniyada yangilanadi.
      </p>

      {/* Tarkib */}
      <Card>
        <CardHeader
          title={`${round}-raund tarkibi`}
          subtitle="Bir vaqtda ko'pi bilan 6 o'yinchi. Raund boshlangach almashtirib bo'lmaydi, kech kelgan o'yinchi joriy savoldan qo'shiladi (Nizom 5.2, 4.3)."
        />
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
                run(() => api(`zakovat/games/${id}/lineup`, { method: "POST", body: { team_id: t.team.id, round_no: round, user_id: userId } }))
              }
              onRemove={(entryId) => run(() => api(`zakovat/games/${id}/lineup/${entryId}/remove`, { method: "POST" }))}
              onCopy={() =>
                run(() =>
                  api(`zakovat/games/${id}/lineup/copy`, { method: "POST", body: { team_id: t.team.id, from_round: round - 1, to_round: round } }),
                )
              }
            />
          ))}
        </div>
      </Card>

      {/* Apellyatsiyalar */}
      {(g.status === "preliminary" || g.status === "final") && (
        <Card>
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                Apellyatsiyalar {pendingAppeals.length > 0 && <Badge tone="amber">{pendingAppeals.length} ta kutmoqda</Badge>}
              </span>
            }
            subtitle="Faqat sardor beradi; yakuniy natija tasdiqlanguncha (Nizom 7.2–7.4)"
          />
          <ul className="divide-y divide-line">
            {appeals.map((a) => (
              <li key={a.id} className="flex flex-wrap items-start justify-between gap-3 px-5 py-4">
                <div className="max-w-3xl text-sm">
                  <div className="flex items-center gap-2 font-medium">
                    {a.team.name} · {a.number}-savol
                    <Badge tone={a.status === "pending" ? "amber" : a.status === "accepted" ? "green" : "red"}>
                      {a.status === "pending" ? "Kutmoqda" : a.status === "accepted" ? "Qabul qilindi" : "Rad etildi"}
                    </Badge>
                  </div>
                  <p className="mt-1.5">{a.content}</p>
                  <p className="text-muted">Dalil: {a.evidence}</p>
                  {a.decision_reason && <p className="text-muted">Qaror: {a.decision_reason}</p>}
                </div>
                {isTg && a.status === "pending" && g.status === "preliminary" && (
                  <div className="flex gap-2">
                    {[true, false].map((accept) => (
                      <Button
                        key={String(accept)}
                        variant={accept ? "success" : "danger"}
                        onClick={() => {
                          const reason = window.prompt(accept ? "Qabul qilish sababi:" : "Rad etish sababi:");
                          if (reason?.trim()) run(() => api(`zakovat/appeals/${a.id}/decide`, { method: "POST", body: { accept, reason } }));
                        }}
                      >
                        {accept ? "Qabul qilish" : "Rad etish"}
                      </Button>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
          {appeals.length === 0 && <Empty>Apellyatsiya yo&apos;q</Empty>}
        </Card>
      )}
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
    <div className="rounded-xl border border-line bg-bg-elev/60 p-3.5">
      <div className="mb-2.5 flex items-center justify-between">
        <span className="font-medium">{team.team.name}</span>
        <Badge tone={entries.length < MIN_PLAYERS ? "red" : "green"}>
          {entries.length}/{MAX_ON_STAGE}
        </Badge>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {entries.map((e) => (
          <span key={e.id} className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-2.5 py-1 text-xs">
            {e.user.name}
            {e.from_question > roundFirst && <span className="text-warning">({e.from_question}-savoldan)</span>}
            {canRemove && (
              <button onClick={() => onRemove(e.id)} className="text-muted hover:text-danger" title="Olib tashlash">
                ✕
              </button>
            )}
          </span>
        ))}
        {entries.length === 0 && <span className="text-xs text-muted">Tarkib kiritilmagan</span>}
      </div>
      {editable && (
        <div className="mt-3 flex flex-wrap gap-2">
          <select
            disabled={full || available.length === 0}
            value=""
            onChange={(ev) => ev.target.value && onAdd(Number(ev.target.value))}
            className="field w-auto py-1 text-xs disabled:opacity-40"
          >
            <option value="">+ O&apos;yinchi qo&apos;shish</option>
            {available.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          {round > 1 && prevCount > 0 && entries.length === 0 && (
            <Button variant="soft" className="py-1 text-xs" onClick={onCopy}>
              {round - 1}-raund tarkibini ko&apos;chirish
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
