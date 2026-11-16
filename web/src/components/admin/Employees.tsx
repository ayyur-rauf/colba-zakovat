"use client";

// Boshqaruv — xodimlar ro'yxati va Excel'dan yuklash (avval tekshirish, keyin saqlash).

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import { Badge, Button, Card, CardHeader, Empty, Field, Notice, PageTitle, Stat } from "../ui";

type Emp = {
  id: number;
  full_name: string;
  branch: { id: number; name: string };
  position: string;
  phone: string;
  email: string;
  telegram: string;
  is_active: boolean;
  account: { id: number; status: string } | null;
};
type EmpList = {
  branches: { id: number; name: string }[];
  stats: { total: number; active: number; with_account: number };
  items: Emp[];
};
type ImportResult = {
  dry_run: boolean;
  saved: boolean;
  ok: boolean;
  summary: string;
  created: number;
  updated: number;
  unchanged: number;
  deactivated: number;
  errors: { row: number; reason: string }[];
  warnings: { row: number; reason: string }[];
};

export default function AdminEmployees() {
  const [q, setQ] = useState("");
  const [branch, setBranch] = useState("");
  const [active, setActive] = useState("1");
  const [account, setAccount] = useState("");
  const params = new URLSearchParams({ ...(q && { q }), ...(branch && { branch }), ...(active && { active }), ...(account && { account }) });
  const list = useApi<EmpList>(`manage/employees?${params}`);
  const act = useAction();
  const [importing, setImporting] = useState(false);
  const s = list.data?.stats;

  return (
    <>
      <PageTitle
        title="Xodimlar"
        subtitle="Faqat shu ro'yxatdagi xodimlar platformaga kira oladi"
        actions={<Button onClick={() => setImporting(!importing)}>⬆ Excel&apos;dan yuklash</Button>}
      />
      <Notice error={act.error ?? list.error} notice={act.notice} onClose={act.clear} />

      {importing && <ImportPanel onSaved={list.reload} />}

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Jami xodimlar" value={s?.total ?? "—"} />
        <Stat label="Ishlayapti" value={s?.active ?? "—"} />
        <Stat label="Akkaunt ochgan" value={s?.with_account ?? "—"} hint={s ? `${Math.round((s.with_account / Math.max(1, s.active)) * 100)}% faol xodimlardan` : undefined} />
      </div>

      <div className="flex flex-wrap gap-2">
        <input className="field max-w-xs" placeholder="Ism, email, lavozim" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="field w-auto" value={branch} onChange={(e) => setBranch(e.target.value)}>
          <option value="">Barcha filiallar</option>
          {(list.data?.branches ?? []).map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        <select className="field w-auto" value={active} onChange={(e) => setActive(e.target.value)}>
          <option value="1">Ishlayotganlar</option>
          <option value="0">Ishdan ketganlar</option>
          <option value="">Hammasi</option>
        </select>
        <select className="field w-auto" value={account} onChange={(e) => setAccount(e.target.value)}>
          <option value="">Akkaunt: hammasi</option>
          <option value="yes">Akkaunt ochgan</option>
          <option value="no">Hali ochmagan</option>
        </select>
      </div>

      <Card className="overflow-x-auto">
        <table className="table min-w-[760px]">
          <thead>
            <tr>
              <th>F.I.Sh.</th>
              <th>Filial</th>
              <th>Lavozim</th>
              <th>Aloqa</th>
              <th>Akkaunt</th>
              <th className="text-right">Holat</th>
            </tr>
          </thead>
          <tbody>
            {(list.data?.items ?? []).map((e) => (
              <tr key={e.id} className={e.is_active ? "" : "opacity-50"}>
                <td className="font-medium">{e.full_name}</td>
                <td>{e.branch.name}</td>
                <td className="text-muted">{e.position || "—"}</td>
                <td className="text-xs text-muted">
                  {[e.email, e.phone, e.telegram && "@" + e.telegram].filter(Boolean).join(" · ") || "—"}
                </td>
                <td>
                  {e.account ? (
                    <Badge tone={e.account.status === "active" ? "green" : e.account.status === "blocked" ? "red" : "amber"}>
                      {e.account.status === "active" ? "Faol" : e.account.status === "blocked" ? "Bloklangan" : "Kutmoqda"}
                    </Badge>
                  ) : (
                    <span className="text-xs text-muted">ochmagan</span>
                  )}
                </td>
                <td className="text-right">
                  <Button
                    variant="ghost"
                    className="py-1 text-xs"
                    disabled={act.busy}
                    onClick={() =>
                      (e.is_active ? window.confirm(`${e.full_name} — "ishdan ketgan" deb belgilansinmi? Akkaunti ishlamay qoladi.`) : true) &&
                      act
                        .run(() => api(`manage/employees/${e.id}`, { method: "PATCH", body: { is_active: !e.is_active } }), "Saqlandi")
                        .then(list.reload)
                    }
                  >
                    {e.is_active ? "Ishdan ketdi" : "Qaytarish"}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {list.data?.items.length === 0 && <Empty>Xodim topilmadi</Empty>}
      </Card>
    </>
  );
}

function ImportPanel({ onSaved }: { onSaved: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [deactivate, setDeactivate] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const act = useAction();

  const send = (dry: boolean) =>
    act.run(async () => {
      const fd = new FormData();
      fd.append("file", file!);
      fd.append("dry_run", dry ? "true" : "false");
      fd.append("deactivate_missing", deactivate ? "true" : "false");
      const r = await api<ImportResult>("manage/employees/import", { method: "POST", body: fd });
      setResult(r);
      if (r.saved) onSaved();
    });

  return (
    <Card>
      <CardHeader
        title="Excel'dan yuklash"
        subtitle="Birinchi qator — sarlavhalar: F.I.Sh., Filial (majburiy), Lavozim, Telefon, Email, Telegram. Xato bo'lsa hech narsa saqlanmaydi."
      />
      <div className="space-y-4 p-5">
        <Notice error={act.error} onClose={act.clear} />
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Fayl (.xlsx)">
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx"
              className="field file:mr-3 file:rounded-md file:border-0 file:bg-accent-soft file:px-3 file:py-1 file:text-accent"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setResult(null);
              }}
            />
          </Field>
          <label className="flex items-center gap-2 pb-2 text-sm">
            <input type="checkbox" checked={deactivate} onChange={(e) => setDeactivate(e.target.checked)} className="accent-[var(--accent)]" />
            Faylda yo&apos;q xodimlarni &quot;ishdan ketgan&quot; deb belgilash
          </label>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" disabled={!file || act.busy} onClick={() => send(true)}>
            1. Tekshirish
          </Button>
          <Button disabled={!file || act.busy || !result || !result.ok || !result.dry_run} onClick={() => send(false)}>
            2. Saqlash
          </Button>
        </div>

        {result && (
          <div className={`rounded-xl border p-4 text-sm ${result.ok ? "border-success/40 bg-success/10" : "border-danger/40 bg-danger/10"}`}>
            <div className="font-medium">
              {result.saved ? "✓ Saqlandi" : result.ok ? "Tekshiruv: xato yo'q — saqlash mumkin" : "Xatolar bor — hech narsa saqlanmadi"}
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge tone="green">Yangi: {result.created}</Badge>
              <Badge tone="amber">Yangilanadi: {result.updated}</Badge>
              <Badge>O&apos;zgarmaydi: {result.unchanged}</Badge>
              {result.deactivated > 0 && <Badge tone="red">Ishdan ketgan: {result.deactivated}</Badge>}
            </div>
            {result.errors.length > 0 && (
              <ul className="mt-3 space-y-1 text-danger">
                {result.errors.map((e, i) => (
                  <li key={i}>
                    {e.row}-qator: {e.reason}
                  </li>
                ))}
              </ul>
            )}
            {result.warnings.length > 0 && (
              <ul className="mt-3 space-y-1 text-warning">
                {result.warnings.map((e, i) => (
                  <li key={i}>
                    {e.row}-qator: {e.reason}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
