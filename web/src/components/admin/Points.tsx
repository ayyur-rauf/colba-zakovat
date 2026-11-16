"use client";

// Boshqaruv — ball reestri: barcha ball yozuvlari va qo'lda tuzatish (sabab bilan).
// Yozuvlar o'chirilmaydi — tuzatish yangi yozuv sifatida qo'shiladi.

import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import { Badge, Button, Card, CardHeader, Empty, Field, formatDate, Notice, PageTitle } from "../ui";

type Entry = {
  id: number;
  created_at: string;
  module: string;
  subject_type: "team" | "user";
  subject_id: number;
  subject: string;
  amount: number;
  reason: string;
  note: string;
  by: string;
};
type Ledger = { season: { id: number; name: string }; items: Entry[] };

export default function AdminPoints() {
  const [module, setModule] = useState("");
  const [q, setQ] = useState("");
  const ledger = useApi<Ledger>(`manage/points?${new URLSearchParams({ ...(module && { module }), ...(q && { q }) })}`);
  const [fixing, setFixing] = useState(false);

  return (
    <>
      <PageTitle
        title="Ball reestri"
        subtitle={`${ledger.data?.season.name ?? ""} · har bir ball qayerdan kelgani. Yozuvlar o'chirilmaydi — tuzatish alohida yozuv.`}
        actions={<Button onClick={() => setFixing(!fixing)}>± Qo&apos;lda tuzatish</Button>}
      />
      <Notice error={ledger.error} onClose={() => ledger.setError(null)} />
      {fixing && (
        <Correction
          onDone={() => {
            setFixing(false);
            ledger.reload();
          }}
        />
      )}
      <div className="flex flex-wrap gap-2">
        {[
          ["", "Hammasi"],
          ["zakovat", "Zakovat (jamoalar)"],
          ["kitobxonlik", "Kitobxonlik (xodimlar)"],
        ].map(([v, l]) => (
          <button
            key={v || "all"}
            onClick={() => setModule(v)}
            className={`rounded-lg px-3 py-1.5 text-sm ${module === v ? "bg-accent-soft text-accent" : "text-muted hover:text-fg"}`}
          >
            {l}
          </button>
        ))}
        <input className="field ml-auto max-w-xs" placeholder="Jamoa yoki xodim" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <Card className="overflow-x-auto">
        <table className="table min-w-[760px]">
          <thead>
            <tr>
              <th className="w-36">Vaqt</th>
              <th>Kimga</th>
              <th>Sabab</th>
              <th className="text-right">Ball</th>
              <th>Kiritgan</th>
            </tr>
          </thead>
          <tbody>
            {(ledger.data?.items ?? []).map((e) => (
              <tr key={e.id}>
                <td className="text-muted">{formatDate(e.created_at)}</td>
                <td>
                  <span className="font-medium">{e.subject}</span>{" "}
                  <Badge>{e.subject_type === "team" ? "jamoa" : "xodim"}</Badge>
                </td>
                <td>
                  {e.reason}
                  {e.note && <div className="text-xs text-muted">{e.note}</div>}
                </td>
                <td className={`text-right text-base font-semibold ${e.amount < 0 ? "text-danger" : "text-success"}`}>
                  {e.amount > 0 ? `+${e.amount}` : e.amount}
                </td>
                <td className="text-muted">{e.by}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {ledger.data?.items.length === 0 && <Empty>Yozuv yo&apos;q</Empty>}
      </Card>
    </>
  );
}

function Correction({ onDone }: { onDone: () => void }) {
  const act = useAction();
  const [type, setType] = useState<"team" | "user">("team");
  const [q, setQ] = useState("");
  const found = useApi<{ id: number; name: string; branch?: string }[]>(`manage/points/subjects?type=${type}&q=${encodeURIComponent(q)}`);
  const [subject, setSubject] = useState<{ id: number; name: string } | null>(null);
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");

  return (
    <Card>
      <CardHeader title="Qo'lda tuzatish" subtitle="Masalan: hisob xatosi, texnik nosozlik. Sabab jurnalga ham yoziladi." />
      <form
        className="grid gap-4 p-5 md:grid-cols-4"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!subject) return act.setError("Kimga ekanini tanlang.");
          const ok = await act.run(
            () =>
              api("manage/points", {
                method: "POST",
                body: {
                  module: type === "team" ? "zakovat" : "kitobxonlik",
                  subject_type: type,
                  subject_id: subject.id,
                  amount: Number(amount),
                  note,
                },
              }),
            "Tuzatish yozildi",
          );
          if (ok) onDone();
        }}
      >
        <div className="md:col-span-4">
          <Notice error={act.error} notice={act.notice} onClose={act.clear} />
        </div>
        <Field label="Turi">
          <select
            className="field"
            value={type}
            onChange={(e) => {
              setType(e.target.value as "team" | "user");
              setSubject(null);
            }}
          >
            <option value="team">Zakovat jamoasi</option>
            <option value="user">Kitobxonlik — xodim</option>
          </select>
        </Field>
        <Field label="Kimga">
          {subject ? (
            <div className="field flex items-center justify-between">
              {subject.name}
              <button type="button" className="text-muted" onClick={() => setSubject(null)}>
                ✕
              </button>
            </div>
          ) : (
            <div className="relative">
              <input className="field" placeholder="Qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
              {(found.data ?? []).length > 0 && (
                <ul className="card absolute z-10 mt-1 max-h-56 w-full overflow-y-auto p-1">
                  {(found.data ?? []).map((s) => (
                    <li key={s.id}>
                      <button type="button" className="w-full rounded-md px-3 py-1.5 text-left text-sm hover:bg-surface-2" onClick={() => setSubject(s)}>
                        {s.name} {s.branch && <span className="text-muted">· {s.branch}</span>}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </Field>
        <Field label="Ball" hint="Manfiy — ayirish, masalan -2">
          <input className="field" type="number" required value={amount} onChange={(e) => setAmount(e.target.value)} />
        </Field>
        <Field label="Sabab (majburiy)">
          <input className="field" required value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        <div className="md:col-span-4">
          <Button type="submit" disabled={act.busy || !subject || !amount || !note.trim()}>
            Yozish
          </Button>
        </div>
      </form>
    </Card>
  );
}
