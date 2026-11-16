"use client";

// Zakovat — o'yinlar: ro'yxat, ro'yxatdan o'tish arizalari, yangi o'yin, mavsum jadvali.

import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi, usePerms } from "@/lib/hooks";
import { REG_STATUS, type Game, type Registration } from "@/lib/types";
import { Badge, Button, Card, CardHeader, Empty, Field, formatDate, LinkButton, Notice, PageTitle } from "../ui";
import { GameStatusBadge } from "./common";

const MONTHS = ["yan", "fev", "mar", "apr", "may", "iyn", "iyl", "avg", "sen", "okt", "noy", "dek"];

export default function ZakovatGames() {
  const perms = usePerms();
  const tg = perms.zakovatTg;
  const staff = tg || perms.zakovatScorer;
  const games = useApi<Game[]>("zakovat/games");
  const act = useAction();
  const [openId, setOpenId] = useState<number | null>(null);
  const [form, setForm] = useState<"none" | "game" | "schedule">("none");

  const reload = games.reload;

  return (
    <>
      <PageTitle
        title="O'yinlar"
        subtitle="Colba ligasi — har oyning 3-shanbasi (Nizom 1.2)"
        actions={
          tg && (
            <>
              <Button variant="ghost" onClick={() => setForm(form === "schedule" ? "none" : "schedule")}>
                🗓 Mavsum jadvali
              </Button>
              <Button onClick={() => setForm(form === "game" ? "none" : "game")}>+ Yangi o&apos;yin</Button>
            </>
          )
        }
      />
      <Notice error={act.error ?? games.error} notice={act.notice} onClose={act.clear} />

      {form === "game" && (
        <NewGameForm
          onDone={() => {
            setForm("none");
            reload();
          }}
          act={act}
        />
      )}
      {form === "schedule" && (
        <ScheduleForm
          onDone={() => {
            setForm("none");
            reload();
          }}
          act={act}
        />
      )}

      <Card>
        <div className="divide-y divide-line">
          {(games.data ?? []).map((g) => (
            <div key={g.id}>
              <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
                <div className="flex items-center gap-4">
                  <div className="grid h-12 w-12 place-items-center rounded-xl bg-surface-2 text-center leading-tight">
                    <span>
                      <span className="block text-lg font-bold">{new Date(g.starts_at).getDate()}</span>
                      <span className="block text-[10px] uppercase text-muted">{MONTHS[new Date(g.starts_at).getMonth()]}</span>
                    </span>
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2 font-medium">
                      {g.title}
                      {g.kind !== "league" && <Badge>{g.kind === "practice" ? "Mashq" : "Qo'shimcha"}</Badge>}
                      <GameStatusBadge status={g.status} />
                    </div>
                    <div className="text-sm text-muted">
                      {formatDate(g.starts_at)}
                      {g.venue && ` · ${g.venue}`} · {g.approved_teams} jamoa
                      {g.max_teams ? ` / ${g.max_teams}` : ""}
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {tg && g.status === "planned" && (
                    <Button
                      variant="soft"
                      disabled={act.busy}
                      onClick={() =>
                        act.run(() => api(`zakovat/games/${g.id}/open-registration`, { method: "POST" }), "Ro'yxatdan o'tish ochildi").then(reload)
                      }
                    >
                      Ro&apos;yxatni ochish
                    </Button>
                  )}
                  {staff && g.status !== "planned" && (
                    <Button variant="ghost" onClick={() => setOpenId(openId === g.id ? null : g.id)}>
                      Arizalar {openId === g.id ? "▴" : "▾"}
                    </Button>
                  )}
                  {staff && g.approved_teams > 0 && (
                    <LinkButton href={`/zakovat/${g.id}/sheet`} variant="primary">
                      Jadval
                    </LinkButton>
                  )}
                  {g.approved_teams > 0 && (
                    <LinkButton href={`/ekran/${g.id}`} target="_blank">
                      Ekran ↗
                    </LinkButton>
                  )}
                </div>
              </div>
              {openId === g.id && <Registrations gameId={g.id} canApprove={tg} onChange={reload} />}
            </div>
          ))}
        </div>
        {games.data?.length === 0 && <Empty>O&apos;yinlar yo&apos;q. Mavsum jadvalini yarating.</Empty>}
      </Card>
    </>
  );
}

function Registrations({ gameId, canApprove, onChange }: { gameId: number; canApprove: boolean; onChange: () => void }) {
  const regs = useApi<Registration[]>(`zakovat/games/${gameId}/registrations`);
  const act = useAction();
  return (
    <div className="border-t border-line bg-bg-elev/50 px-5 py-3">
      <Notice error={act.error ?? regs.error} onClose={act.clear} />
      <table className="table">
        <thead>
          <tr>
            <th>Stol</th>
            <th>Jamoa</th>
            <th>Holat</th>
            <th>Ariza vaqti</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {(regs.data ?? []).map((r) => (
            <tr key={r.id}>
              <td>{r.table_number ?? "—"}</td>
              <td className="font-medium">{r.team.name}</td>
              <td>
                <Badge tone={r.status === "approved" ? "green" : r.status === "pending" || r.status === "waitlist" ? "amber" : "gray"}>
                  {REG_STATUS[r.status]}
                </Badge>
              </td>
              <td className="text-muted">{formatDate(r.created_at)}</td>
              <td className="text-right">
                {canApprove && (r.status === "pending" || r.status === "waitlist") && (
                  <Button
                    variant="success"
                    disabled={act.busy}
                    onClick={async () => {
                      await act.run(() => api(`zakovat/registrations/${r.id}/approve`, { method: "POST" }));
                      regs.reload();
                      onChange();
                    }}
                  >
                    Tasdiqlash
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {regs.data?.length === 0 && <Empty>Ariza yo&apos;q</Empty>}
    </div>
  );
}

type Act = ReturnType<typeof useAction>;

function NewGameForm({ onDone, act }: { onDone: () => void; act: Act }) {
  const [v, setV] = useState({ title: "", starts_at: "", venue: "", kind: "league", max_teams: "", rounds: "3", qpr: "12" });
  const set = (k: keyof typeof v) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setV({ ...v, [k]: e.target.value });
  return (
    <Card>
      <CardHeader title="Yangi o'yin" subtitle="Liga o'yini ball beradi, mashq o'yini bermaydi" />
      <form
        className="grid gap-4 p-5 md:grid-cols-3"
        onSubmit={async (e) => {
          e.preventDefault();
          const ok = await act.run(
            () =>
              api("zakovat/games", {
                method: "POST",
                body: {
                  title: v.title,
                  starts_at: new Date(v.starts_at).toISOString(),
                  venue: v.venue,
                  kind: v.kind,
                  max_teams: v.max_teams ? Number(v.max_teams) : null,
                  rounds: Number(v.rounds),
                  questions_per_round: Number(v.qpr),
                },
              }),
            "O'yin yaratildi",
          );
          if (ok) onDone();
        }}
      >
        <Field label="Nomi">
          <input className="field" required value={v.title} onChange={set("title")} placeholder="Masalan: 4-tur" />
        </Field>
        <Field label="Boshlanish vaqti">
          <input className="field" type="datetime-local" required value={v.starts_at} onChange={set("starts_at")} />
        </Field>
        <Field label="Turi">
          <select className="field" value={v.kind} onChange={set("kind")}>
            <option value="league">Liga o&apos;yini</option>
            <option value="practice">Mashq (ball bermaydi)</option>
          </select>
        </Field>
        <Field label="Joyi">
          <input className="field" value={v.venue} onChange={set("venue")} placeholder="Zal nomi" />
        </Field>
        <Field label="Maksimal jamoalar" hint="Zal sig'imi (Nizom 4.1). Bo'sh — cheklovsiz">
          <input className="field" type="number" min={1} value={v.max_teams} onChange={set("max_teams")} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Raundlar">
            <input className="field" type="number" min={1} max={10} value={v.rounds} onChange={set("rounds")} />
          </Field>
          <Field label="Savollar/raund">
            <input className="field" type="number" min={1} max={50} value={v.qpr} onChange={set("qpr")} />
          </Field>
        </div>
        <div className="md:col-span-3">
          <Button type="submit" disabled={act.busy}>
            Yaratish
          </Button>
        </div>
      </form>
    </Card>
  );
}

function ScheduleForm({ onDone, act }: { onDone: () => void; act: Act }) {
  const [time, setTime] = useState("15:00");
  const [venue, setVenue] = useState("");
  const [months, setMonths] = useState<number[]>([9, 10, 11, 12, 1, 2, 3, 4, 5]);
  const names = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"];
  const order = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8];
  return (
    <Card>
      <CardHeader title="Mavsum jadvali" subtitle="Tanlangan oylarning 3-shanbasiga liga o'yinlari yaratiladi. Mavjud o'yinlar takrorlanmaydi." />
      <form
        className="space-y-4 p-5"
        onSubmit={async (e) => {
          e.preventDefault();
          const ok = await act.run(
            () => api("zakovat/games/generate-schedule", { method: "POST", body: { start_time: time, venue, months } }),
            "Jadval yaratildi",
          );
          if (ok) onDone();
        }}
      >
        <div className="flex flex-wrap gap-2">
          {order.map((m) => {
            const on = months.includes(m);
            return (
              <button
                type="button"
                key={m}
                onClick={() => setMonths(on ? months.filter((x) => x !== m) : [...months, m])}
                className={`rounded-lg border px-3 py-1.5 text-sm ${on ? "border-accent bg-accent-soft text-accent" : "border-line text-muted"}`}
              >
                {names[m - 1]}
              </button>
            );
          })}
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <Field label="Boshlanish vaqti">
            <input className="field" type="time" value={time} onChange={(e) => setTime(e.target.value)} />
          </Field>
          <Field label="Joyi">
            <input className="field" value={venue} onChange={(e) => setVenue(e.target.value)} />
          </Field>
        </div>
        <Button type="submit" disabled={act.busy || months.length === 0}>
          Jadvalni yaratish
        </Button>
      </form>
    </Card>
  );
}
