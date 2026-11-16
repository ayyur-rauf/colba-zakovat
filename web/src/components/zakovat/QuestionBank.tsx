"use client";

// Zakovat — savollar banki: qo'shish, tahrirlash, holat, qidiruv. Faqat Tashkiliy guruh.

import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi, usePerms } from "@/lib/hooks";
import { QUESTION_STATUS, type Question, type QuestionBank as Bank, type QuestionStatus } from "@/lib/types";
import { Badge, Button, Card, CardHeader, Empty, Field, Notice, PageTitle } from "../ui";

const STATUS_TONE = { draft: "gray", editing: "amber", approved: "green", used: "red" } as const;

export default function QuestionBank() {
  const { zakovatTg } = usePerms();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<"" | QuestionStatus>("");
  const [topic, setTopic] = useState("");
  const qs = new URLSearchParams({ ...(q && { q }), ...(status && { status }), ...(topic && { topic }) }).toString();
  const bank = useApi<Bank>(zakovatTg ? `zakovat/questions${qs ? "?" + qs : ""}` : null);
  const act = useAction();
  const [editing, setEditing] = useState<Question | "new" | null>(null);

  if (!zakovatTg) {
    return (
      <Card>
        <Empty>Savollar bankini faqat Tashkiliy guruh ko&apos;radi — savollar o&apos;yingacha maxfiy.</Empty>
      </Card>
    );
  }

  const counts = bank.data?.counts;
  return (
    <>
      <PageTitle
        title="Savollar banki"
        subtitle="Savollar o'yin boshlanguncha faqat Tashkiliy guruhga ko'rinadi. O'yindan keyin 'ishlatilgan' bo'ladi."
        actions={<Button onClick={() => setEditing("new")}>+ Yangi savol</Button>}
      />
      <Notice error={act.error ?? bank.error} notice={act.notice} onClose={act.clear} />

      {editing && (
        <QuestionForm
          initial={editing === "new" ? null : editing}
          topics={bank.data?.topics ?? []}
          act={act}
          onDone={() => {
            setEditing(null);
            bank.reload();
          }}
          onCancel={() => setEditing(null)}
        />
      )}

      <div className="flex flex-wrap items-center gap-2">
        <input className="field max-w-xs" placeholder="Qidirish: savol, javob, mavzu" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="field w-auto" value={topic} onChange={(e) => setTopic(e.target.value)}>
          <option value="">Barcha mavzular</option>
          {(bank.data?.topics ?? []).map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <div className="flex flex-wrap gap-1">
          {(["", "draft", "editing", "approved", "used"] as const).map((s) => (
            <button
              key={s || "all"}
              onClick={() => setStatus(s)}
              className={`rounded-lg px-3 py-1.5 text-sm ${status === s ? "bg-accent-soft text-accent" : "text-muted hover:text-fg"}`}
            >
              {s ? QUESTION_STATUS[s] : "Barchasi"}
              {s && counts ? <span className="ml-1 text-xs opacity-70">{counts[s]}</span> : null}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        {(bank.data?.items ?? []).map((item) => (
          <Card key={item.id} className="p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs">
                  <Badge tone={STATUS_TONE[item.status]}>{QUESTION_STATUS[item.status]}</Badge>
                  {item.topic && <Badge>{item.topic}</Badge>}
                  {item.difficulty && <span className="text-gold">{"★".repeat(item.difficulty)}</span>}
                  {item.assigned && (
                    <Badge tone="gold">
                      {item.assigned.game_title}, {item.assigned.number}-savol
                    </Badge>
                  )}
                </div>
                <p className="whitespace-pre-line">{item.text}</p>
                <p className="mt-2 text-sm">
                  <span className="text-muted">Javob:</span> <b className="text-success">{item.answer}</b>
                  {item.accepted_answers && <span className="text-muted"> · Qabul: {item.accepted_answers.replace(/\n/g, ", ")}</span>}
                </p>
                {item.comment && <p className="mt-1 text-sm text-muted">Izoh: {item.comment}</p>}
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => setEditing(item)}>
                  Tahrirlash
                </Button>
                {!item.assigned && item.status !== "used" && (
                  <Button
                    variant="ghost"
                    onClick={() =>
                      window.confirm("Savolni o'chirasizmi?") &&
                      act.run(() => api(`zakovat/questions/${item.id}`, { method: "DELETE" }), "O'chirildi").then(bank.reload)
                    }
                  >
                    🗑
                  </Button>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
      {bank.data?.items.length === 0 && (
        <Card>
          <Empty>Savol topilmadi</Empty>
        </Card>
      )}
    </>
  );
}

function QuestionForm({
  initial,
  topics,
  act,
  onDone,
  onCancel,
}: {
  initial: Question | null;
  topics: string[];
  act: ReturnType<typeof useAction>;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [v, setV] = useState({
    text: initial?.text ?? "",
    answer: initial?.answer ?? "",
    accepted_answers: initial?.accepted_answers ?? "",
    comment: initial?.comment ?? "",
    source: initial?.source ?? "",
    topic: initial?.topic ?? "",
    difficulty: initial?.difficulty ? String(initial.difficulty) : "",
    status: (initial?.status === "used" ? undefined : initial?.status) ?? "draft",
  });
  const set = (k: keyof typeof v) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setV({ ...v, [k]: e.target.value });

  return (
    <Card>
      <CardHeader title={initial ? "Savolni tahrirlash" : "Yangi savol"} />
      <form
        className="grid gap-4 p-5 md:grid-cols-2"
        onSubmit={async (e) => {
          e.preventDefault();
          const body = { ...v, difficulty: v.difficulty ? Number(v.difficulty) : null, ...(initial?.status === "used" ? { status: undefined } : {}) };
          const ok = await act.run(
            () => api(initial ? `zakovat/questions/${initial.id}` : "zakovat/questions", { method: initial ? "PATCH" : "POST", body }),
            "Saqlandi",
          );
          if (ok) onDone();
        }}
      >
        <div className="md:col-span-2">
          <Field label="Savol matni">
            <textarea className="field min-h-28" required value={v.text} onChange={set("text")} />
          </Field>
        </div>
        <Field label="Javob">
          <input className="field" required value={v.answer} onChange={set("answer")} />
        </Field>
        <Field label="Qabul qilinadigan javoblar" hint="Har birini yangi qatorga">
          <textarea className="field min-h-10" value={v.accepted_answers} onChange={set("accepted_answers")} />
        </Field>
        <Field label="Izoh (boshlovchi uchun)">
          <textarea className="field min-h-10" value={v.comment} onChange={set("comment")} />
        </Field>
        <Field label="Manba">
          <input className="field" value={v.source} onChange={set("source")} />
        </Field>
        <div className="grid grid-cols-3 gap-3 md:col-span-2">
          <Field label="Mavzu">
            <input className="field" list="topics" value={v.topic} onChange={set("topic")} />
            <datalist id="topics">
              {topics.map((t) => (
                <option key={t} value={t} />
              ))}
            </datalist>
          </Field>
          <Field label="Qiyinlik">
            <select className="field" value={v.difficulty} onChange={set("difficulty")}>
              <option value="">—</option>
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {"★".repeat(n)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Holat">
            <select className="field" value={v.status} disabled={initial?.status === "used"} onChange={set("status")}>
              {(["draft", "editing", "approved"] as const).map((s) => (
                <option key={s} value={s}>
                  {QUESTION_STATUS[s]}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="flex gap-2 md:col-span-2">
          <Button type="submit" disabled={act.busy}>
            Saqlash
          </Button>
          <Button type="button" variant="ghost" onClick={onCancel}>
            Bekor qilish
          </Button>
        </div>
      </form>
    </Card>
  );
}
