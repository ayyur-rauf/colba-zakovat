"use client";

// Boshqaruv — akkauntlar: tasdiq kutayotganlarni xodimga bog'lab tasdiqlash, bloklash.

import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import { Badge, Button, Card, Empty, formatDate, Notice, PageTitle } from "../ui";

type Account = {
  id: number;
  name: string;
  status: "pending" | "active" | "blocked";
  is_superuser: boolean;
  display_name: string;
  email: string;
  employee: { id: number; full_name: string; branch: string; is_active: boolean } | null;
  identities: string[];
  date_joined: string;
  last_login: string | null;
};
type AccountList = { counts: Record<Account["status"], number>; items: Account[] };
type EmpOption = { id: number; full_name: string; branch: { name: string }; account: unknown };

const LABEL = { pending: "Tasdiq kutmoqda", active: "Faol", blocked: "Bloklangan" } as const;
const PROVIDER: Record<string, string> = { email: "Email", google: "Google", telegram: "Telegram" };

export default function AdminAccounts() {
  const [status, setStatus] = useState<Account["status"] | "">("pending");
  const [q, setQ] = useState("");
  const list = useApi<AccountList>(`manage/users?${new URLSearchParams({ ...(status && { status }), ...(q && { q }) })}`);
  const act = useAction();
  const counts = list.data?.counts;

  return (
    <>
      <PageTitle
        title="Akkauntlar"
        subtitle="Xodimlar ro'yxatida topilmagan kishi kirsa, akkaunti 'tasdiq kutmoqda' holatida qoladi — uni xodimga bog'lab tasdiqlang"
      />
      <Notice error={act.error ?? list.error} notice={act.notice} onClose={act.clear} />
      <div className="flex flex-wrap items-center gap-2">
        {(["pending", "active", "blocked", ""] as const).map((s) => (
          <button
            key={s || "all"}
            onClick={() => setStatus(s)}
            className={`rounded-lg px-3 py-1.5 text-sm ${status === s ? "bg-accent-soft text-accent" : "text-muted hover:text-fg"}`}
          >
            {s ? LABEL[s] : "Hammasi"}
            {s && counts ? <span className="ml-1 text-xs opacity-70">{counts[s]}</span> : null}
          </button>
        ))}
        <input className="field ml-auto max-w-xs" placeholder="Qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      <div className="space-y-3">
        {(list.data?.items ?? []).map((u) => (
          <AccountRow key={u.id} u={u} act={act} onChange={list.reload} />
        ))}
      </div>
      {list.data?.items.length === 0 && (
        <Card>
          <Empty>{status === "pending" ? "Tasdiq kutayotgan akkaunt yo'q 🎉" : "Akkaunt topilmadi"}</Empty>
        </Card>
      )}
    </>
  );
}

function AccountRow({ u, act, onChange }: { u: Account; act: ReturnType<typeof useAction>; onChange: () => void }) {
  const [linking, setLinking] = useState(false);
  const [search, setSearch] = useState(u.display_name.replace(/^Telegram: @/, ""));
  const emps = useApi<{ items: EmpOption[] }>(linking ? `manage/employees?account=no&active=1&q=${encodeURIComponent(search)}` : null);
  const post = (action: string, body?: unknown, ok?: string) =>
    act.run(() => api(`manage/users/${u.id}/${action}`, { method: "POST", body: body ?? {} }), ok).then(onChange);

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 font-medium">
            {u.employee?.full_name ?? u.display_name ?? u.name}
            <Badge tone={u.status === "active" ? "green" : u.status === "blocked" ? "red" : "amber"}>{LABEL[u.status]}</Badge>
            {u.is_superuser && <Badge tone="gold">superuser</Badge>}
          </div>
          <div className="mt-0.5 text-xs text-muted">
            {u.employee ? `${u.employee.branch}` : "Xodimga bog'lanmagan"}
            {u.identities.length > 0 && ` · Kirish: ${u.identities.map((p) => PROVIDER[p] ?? p).join(", ")}`}
            {` · Ro'yxatdan: ${formatDate(u.date_joined)}`}
            {u.last_login && ` · Oxirgi kirish: ${formatDate(u.last_login)}`}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {u.status === "pending" &&
            (u.employee ? (
              <Button variant="success" disabled={act.busy} onClick={() => post("approve", {}, "Tasdiqlandi")}>
                Tasdiqlash
              </Button>
            ) : (
              <Button variant="soft" onClick={() => setLinking(!linking)}>
                Xodimga bog&apos;lash
              </Button>
            ))}
          {u.status !== "blocked" ? (
            <Button
              variant="ghost"
              disabled={act.busy}
              onClick={() => window.confirm("Akkaunt bloklansinmi? U darhol tizimdan chiqariladi.") && post("block", {}, "Bloklandi")}
            >
              Bloklash
            </Button>
          ) : (
            <Button variant="ghost" disabled={act.busy} onClick={() => post("unblock", {}, "Blokdan chiqarildi")}>
              Blokdan chiqarish
            </Button>
          )}
        </div>
      </div>
      {linking && (
        <div className="mt-3 rounded-xl border border-line bg-bg-elev/60 p-3">
          <input className="field mb-2" autoFocus placeholder="Xodim ismi" value={search} onChange={(e) => setSearch(e.target.value)} />
          <ul className="max-h-60 space-y-1 overflow-y-auto">
            {(emps.data?.items ?? []).map((e) => (
              <li key={e.id} className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-surface-2">
                <span className="text-sm">
                  {e.full_name} <span className="text-muted">· {e.branch.name}</span>
                </span>
                <Button variant="success" className="py-1 text-xs" disabled={act.busy} onClick={() => post("approve", { employee_id: e.id }, "Bog'landi va tasdiqlandi")}>
                  Bog&apos;lash va tasdiqlash
                </Button>
              </li>
            ))}
          </ul>
          {emps.data?.items.length === 0 && <p className="px-3 py-2 text-sm text-muted">Akkaunt ochmagan faol xodim topilmadi</p>}
        </div>
      )}
    </Card>
  );
}
