"use client";

// Boshqaruv — rollar: kim qaysi modulda qanday vazifada.

import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import { Button, Card, CardHeader, Empty, Field, formatDate, Notice, PageTitle } from "../ui";

type Opt = { value: string; label: string };
type RoleRow = {
  id: number;
  user: { id: number; name: string; branch: string | null };
  role: string;
  role_label: string;
  module: string;
  module_label: string;
  season: string | null;
  granted_by: string | null;
  created_at: string;
};
type RolesData = { roles: Opt[]; modules: Opt[]; items: RoleRow[] };
type Season = { id: number; name: string; is_active: boolean };

// Qaysi rol qaysi modulda ma'noli
const ROLE_MODULES: Record<string, string[]> = {
  admin: ["core"],
  tg_member: ["zakovat"],
  host: ["zakovat"],
  second: ["zakovat"],
  scorer: ["zakovat"],
  organizer: ["kitobxonlik", "munozara", "sport"],
  reviewer: ["kitobxonlik", "munozara"],
};
const ROLE_HINT: Record<string, string> = {
  admin: "Butun platforma, Boshqaruv bo'limi",
  tg_member: "Zakovat: o'yin, jamoa, savollar, natija, apellyatsiya",
  host: "Zakovat: boshlovchi pulti, taymer",
  second: "Zakovat: taymer, joriy savol",
  scorer: "Zakovat: javoblar jadvali, tarkib",
  organizer: "Tur yaratish, kitoblar, natijani tasdiqlash",
  reviewer: "Izohlarni baholash",
};

export default function AdminRoles() {
  const data = useApi<RolesData>("manage/roles");
  const seasons = useApi<Season[]>("manage/seasons");
  const act = useAction();
  const [userQ, setUserQ] = useState("");
  const users = useApi<{ id: number; name: string; branch: string | null }[]>(userQ.length >= 2 ? `manage/users/search?q=${encodeURIComponent(userQ)}` : null);
  const [user, setUser] = useState<{ id: number; name: string } | null>(null);
  const [role, setRole] = useState("scorer");
  const [module, setModule] = useState("zakovat");
  const [season, setSeason] = useState("");

  const items = data.data?.items ?? [];
  const groups = (data.data?.modules ?? []).map((m) => ({ ...m, rows: items.filter((r) => r.module === m.value) })).filter((g) => g.rows.length);

  return (
    <>
      <PageTitle title="Rollar" subtitle="Rol modul doirasida beriladi; mavsum tanlansa — faqat o'sha mavsum uchun" />
      <Notice error={act.error ?? data.error} notice={act.notice} onClose={act.clear} />

      <Card>
        <CardHeader title="Rol berish" />
        <form
          className="grid gap-4 p-5 md:grid-cols-4"
          onSubmit={async (e) => {
            e.preventDefault();
            if (!user) return act.setError("Xodimni tanlang.");
            const ok = await act.run(
              () => api("manage/roles", { method: "POST", body: { user_id: user.id, role, module, season_id: season ? Number(season) : null } }),
              `${user.name} — rol berildi`,
            );
            if (ok) {
              setUser(null);
              setUserQ("");
              data.reload();
            }
          }}
        >
          <Field label="Xodim">
            {user ? (
              <div className="field flex items-center justify-between">
                {user.name}
                <button type="button" className="text-muted hover:text-fg" onClick={() => setUser(null)}>
                  ✕
                </button>
              </div>
            ) : (
              <div className="relative">
                <input className="field" placeholder="Ism (kamida 2 harf)" value={userQ} onChange={(e) => setUserQ(e.target.value)} />
                {users.data && userQ.length >= 2 && (
                  <ul className="card absolute z-10 mt-1 max-h-60 w-full overflow-y-auto p-1">
                    {users.data.map((u) => (
                      <li key={u.id}>
                        <button type="button" onClick={() => setUser(u)} className="w-full rounded-md px-3 py-1.5 text-left text-sm hover:bg-surface-2">
                          {u.name} <span className="text-muted">{u.branch}</span>
                        </button>
                      </li>
                    ))}
                    {users.data.length === 0 && <li className="px-3 py-1.5 text-sm text-muted">Topilmadi</li>}
                  </ul>
                )}
              </div>
            )}
          </Field>
          <Field label="Rol" hint={ROLE_HINT[role]}>
            <select
              className="field"
              value={role}
              onChange={(e) => {
                setRole(e.target.value);
                setModule(ROLE_MODULES[e.target.value][0]);
              }}
            >
              {(data.data?.roles ?? []).map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Modul">
            <select className="field" value={module} onChange={(e) => setModule(e.target.value)}>
              {(data.data?.modules ?? [])
                .filter((m) => ROLE_MODULES[role]?.includes(m.value))
                .map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="Mavsum" hint="Bo'sh — barcha mavsumlar">
            <select className="field" value={season} onChange={(e) => setSeason(e.target.value)}>
              <option value="">Barcha mavsumlar</option>
              {(seasons.data ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                  {s.is_active ? " (joriy)" : ""}
                </option>
              ))}
            </select>
          </Field>
          <div className="md:col-span-4">
            <Button type="submit" disabled={act.busy || !user}>
              Rol berish
            </Button>
          </div>
        </form>
      </Card>

      {groups.map((g) => (
        <Card key={g.value}>
          <CardHeader title={g.label} subtitle={`${g.rows.length} ta rol`} />
          <table className="table">
            <thead>
              <tr>
                <th>Xodim</th>
                <th>Rol</th>
                <th>Mavsum</th>
                <th>Kim berdi</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {g.rows.map((r) => (
                <tr key={r.id}>
                  <td>
                    <div className="font-medium">{r.user.name}</div>
                    <div className="text-xs text-muted">{r.user.branch}</div>
                  </td>
                  <td>{r.role_label}</td>
                  <td className="text-muted">{r.season ?? "Barchasi"}</td>
                  <td className="text-xs text-muted">
                    {r.granted_by ?? "—"}
                    <br />
                    {formatDate(r.created_at)}
                  </td>
                  <td className="text-right">
                    <Button
                      variant="ghost"
                      className="py-1 text-xs"
                      disabled={act.busy}
                      onClick={() =>
                        window.confirm(`${r.user.name} — "${r.role_label}" roli olib tashlansinmi?`) &&
                        act.run(() => api(`manage/roles/${r.id}`, { method: "DELETE" }), "Rol olib tashlandi").then(data.reload)
                      }
                    >
                      Olib tashlash
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ))}
      {data.data && items.length === 0 && (
        <Card>
          <Empty>Hali rol berilmagan</Empty>
        </Card>
      )}
    </>
  );
}
