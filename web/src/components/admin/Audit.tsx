"use client";

// Boshqaruv — harakatlar jurnali: kim, qachon, nima qildi (oxirgi 200 ta).

import { useState } from "react";
import { useApi } from "@/lib/hooks";
import { Card, Empty, formatDate, Notice, PageTitle } from "../ui";

type Entry = {
  id: number;
  created_at: string;
  actor: string;
  action: string;
  object_type: string;
  object_id: string;
  before: unknown;
  after: unknown;
  note: string;
};

// Amal kodlarini o'qiladigan matnga aylantirish
const ACTIONS: Record<string, string> = {
  "auth.identity_linked": "Kirish usuli bog'landi",
  "employees.imported": "Xodimlar ro'yxati yuklandi",
  "employee.updated": "Xodim o'zgartirildi",
  "user.approve": "Akkaunt tasdiqlandi",
  "user.block": "Akkaunt bloklandi",
  "user.unblock": "Akkaunt blokdan chiqarildi",
  "role.saved": "Rol berildi",
  "role.deleted": "Rol olib tashlandi",
  "season.created": "Mavsum yaratildi",
  "season.activated": "Joriy mavsum o'zgardi",
  "announcement.created": "E'lon yaratildi",
  "announcement.updated": "E'lon o'zgartirildi",
  "announcement.deleted": "E'lon o'chirildi",
  "zakovat.team_created": "Jamoa yaratildi",
  "zakovat.team_approved": "Jamoa tasdiqlandi",
  "zakovat.team_out": "Jamoa chiqdi / chetlatildi",
  "zakovat.game_updated": "O'yin o'zgartirildi",
  "zakovat.game_cancelled": "O'yin bekor qilindi",
  "zakovat.game_started": "O'yin boshlandi",
  "zakovat.preliminary_published": "Dastlabki natija e'lon qilindi",
  "zakovat.game_finalized": "Yakuniy natija tasdiqlandi",
  "zakovat.game_reopened": "Natija qayta ochildi",
  "zakovat.mark_changed": "Javob belgisi o'zgartirildi",
  "zakovat.appeal_submitted": "Apellyatsiya berildi",
  "zakovat.appeal_decided": "Apellyatsiya bo'yicha qaror",
  "zakovat.question_saved": "Savol saqlandi",
  "zakovat.question_deleted": "Savol o'chirildi",
  "kitob.round_created": "Kitobxonlik turi yaratildi",
  "kitob.book_added": "Kitob qo'shildi",
  "kitob.voting_started": "Ovoz berish boshlandi",
  "kitob.grading_started": "Baholash boshlandi",
  "kitob.review_graded": "Izoh baholandi",
  "kitob.extension_granted": "Muddat uzaytirildi",
  "zakovat.team_submitted": "Jamoa tasdiqqa yuborildi",
  "zakovat.team_renamed": "Jamoa nomi o'zgardi",
  "zakovat.member_invited": "O'yinchi taklif qilindi",
  "zakovat.member_joined": "O'yinchi jamoaga qo'shildi",
  "zakovat.member_removed": "O'yinchi jamoadan chiqdi",
  "zakovat.schedule_generated": "Mavsum jadvali yaratildi",
  "zakovat.registration_opened": "Ro'yxatdan o'tish ochildi",
  "zakovat.registered": "Jamoa o'yinga yozildi",
  "zakovat.registration_approved": "Ariza tasdiqlandi",
  "zakovat.lineup_added": "Tarkibga o'yinchi qo'shildi",
  "zakovat.lineup_removed": "Tarkibdan o'yinchi olindi",
  "zakovat.tiebreak_created": "Qo'shimcha o'yin yaratildi",
  "zakovat.game_created": "O'yin yaratildi",
  "kitob.voting_closed": "Ovoz berish yakunlandi",
  "kitob.results_approved": "Kitobxonlik natijalari tasdiqlandi",
};

const FILTERS = [
  ["", "Hammasi"],
  ["user", "Akkauntlar"],
  ["role", "Rollar"],
  ["zakovat", "Zakovat"],
  ["kitob", "Kitobxonlik"],
  ["announcement", "E'lonlar"],
];

export default function AdminAudit() {
  const [action, setAction] = useState("");
  const [q, setQ] = useState("");
  const log = useApi<Entry[]>(`manage/audit?${new URLSearchParams({ ...(action && { action }), ...(q && { q }) })}`);
  const [open, setOpen] = useState<number | null>(null);

  return (
    <>
      <PageTitle title="Harakatlar jurnali" subtitle="Muhim amallar yoziladi va o'zgartirib bo'lmaydi. Oxirgi 200 ta yozuv." />
      <Notice error={log.error} onClose={() => log.setError(null)} />
      <div className="flex flex-wrap items-center gap-2">
        {FILTERS.map(([v, l]) => (
          <button
            key={v || "all"}
            onClick={() => setAction(v)}
            className={`rounded-lg px-3 py-1.5 text-sm ${action === v ? "bg-accent-soft text-accent" : "text-muted hover:text-fg"}`}
          >
            {l}
          </button>
        ))}
        <input className="field ml-auto max-w-xs" placeholder="Izoh yoki amal bo'yicha" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <Card className="overflow-x-auto">
        <table className="table min-w-[720px]">
          <thead>
            <tr>
              <th className="w-40">Vaqt</th>
              <th>Kim</th>
              <th>Amal</th>
              <th>Izoh</th>
            </tr>
          </thead>
          <tbody>
            {(log.data ?? []).map((e) => (
              <tr key={e.id} className="cursor-pointer hover:bg-surface-2/60" onClick={() => setOpen(open === e.id ? null : e.id)}>
                <td className="text-muted">{formatDate(e.created_at)}</td>
                <td>{e.actor}</td>
                <td>
                  {ACTIONS[e.action] ?? e.action}
                  {open === e.id && (e.before != null || e.after != null) && (
                    <pre className="mt-2 max-w-xl overflow-x-auto rounded-lg bg-bg-elev p-2 text-xs text-muted">
                      {e.before != null && `oldin: ${JSON.stringify(e.before)}\n`}
                      {e.after != null && `keyin: ${JSON.stringify(e.after)}`}
                    </pre>
                  )}
                </td>
                <td className="text-muted">{e.note || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {log.data?.length === 0 && <Empty>Yozuv yo&apos;q</Empty>}
      </Card>
    </>
  );
}
