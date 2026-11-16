"use client";

// Boshqaruv — barcha e'lonlar: yaratish, tahrirlash, yashirish, mahkamlash, o'chirish.

import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import type { Announcement, AnnouncementList } from "@/lib/types";
import { AnnouncementForm, AnnouncementItem } from "../Announcements";
import { Button, Card, Empty, Notice, PageTitle } from "../ui";

export default function AdminAnnouncements() {
  const list = useApi<AnnouncementList>("announcements?all=1");
  const act = useAction();
  const [editing, setEditing] = useState<Announcement | "new" | null>(null);
  const modules = list.data?.can_post ?? [];
  const patch = (a: Announcement, body: Partial<Announcement>, ok: string) =>
    act.run(() => api(`announcements/${a.id}`, { method: "PATCH", body }), ok).then(list.reload);

  return (
    <>
      <PageTitle
        title="E'lonlar"
        subtitle="Xodimlar bosh sahifada va tegishli modulda ko'radi. Mahkamlangan e'lonlar yuqorida turadi."
        actions={<Button onClick={() => setEditing("new")}>+ Yangi e&apos;lon</Button>}
      />
      <Notice error={act.error ?? list.error} notice={act.notice} onClose={act.clear} />
      {editing && (
        <AnnouncementForm
          modules={modules}
          initial={editing === "new" ? undefined : editing}
          onDone={() => {
            setEditing(null);
            list.reload();
          }}
          onCancel={() => setEditing(null)}
        />
      )}
      <div className="space-y-3">
        {(list.data?.items ?? []).map((a) => (
          <div key={a.id} className="flex flex-wrap items-start gap-3">
            <div className="min-w-0 flex-1">
              <AnnouncementItem a={a} />
            </div>
            <div className="flex gap-1.5">
              <Button variant="ghost" className="py-1 text-xs" onClick={() => setEditing(a)}>
                Tahrirlash
              </Button>
              <Button variant="ghost" className="py-1 text-xs" onClick={() => patch(a, { pinned: !a.pinned }, a.pinned ? "Mahkam olib tashlandi" : "Mahkamlandi")}>
                {a.pinned ? "Bo'shatish" : "📌"}
              </Button>
              <Button variant="ghost" className="py-1 text-xs" onClick={() => patch(a, { is_active: !a.is_active }, a.is_active ? "Yashirildi" : "Ko'rsatildi")}>
                {a.is_active ? "Yashirish" : "Ko'rsatish"}
              </Button>
              <Button
                variant="ghost"
                className="py-1 text-xs"
                onClick={() =>
                  window.confirm("E'lon o'chirilsinmi?") &&
                  act.run(() => api(`announcements/${a.id}`, { method: "DELETE" }), "O'chirildi").then(list.reload)
                }
              >
                🗑
              </Button>
            </div>
          </div>
        ))}
      </div>
      {list.data?.items.length === 0 && (
        <Card>
          <Empty>E&apos;lon yo&apos;q</Empty>
        </Card>
      )}
    </>
  );
}
