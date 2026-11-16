"use client";

// Kitobxonlik — kitoblar: ro'yxat va PDF yuklash (faqat tashkilotchi).

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi, usePerms } from "@/lib/hooks";
import type { Book } from "@/lib/types";
import { Button, Card, CardHeader, Empty, Field, Notice, PageTitle } from "../ui";

export default function KitobBooks() {
  const { kitobOrganizer } = usePerms();
  const books = useApi<Book[]>(kitobOrganizer ? "kitob/books" : null);
  const act = useAction();
  const [adding, setAdding] = useState(false);

  if (!kitobOrganizer) {
    return (
      <Card>
        <Empty>Bu bo&apos;lim faqat tashkilotchilar uchun.</Empty>
      </Card>
    );
  }

  return (
    <>
      <PageTitle
        title="Kitoblar"
        subtitle="PDF fayllar ochiq havolada emas — faqat tizimga kirgan xodimga beriladi"
        actions={<Button onClick={() => setAdding(!adding)}>+ Kitob qo&apos;shish</Button>}
      />
      <Notice error={act.error ?? books.error} notice={act.notice} onClose={act.clear} />
      {adding && (
        <AddBook
          act={act}
          onDone={() => {
            setAdding(false);
            books.reload();
          }}
        />
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {(books.data ?? []).map((b) => (
          <Card key={b.id} className="overflow-hidden">
            <div className="grid aspect-[3/4] place-items-center bg-accent-soft">
              {b.cover ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={b.cover} alt={b.title} className="h-full w-full object-cover" />
              ) : (
                <span className="px-4 text-center text-lg font-semibold">{b.title}</span>
              )}
            </div>
            <div className="p-4">
              <div className="font-medium">{b.title}</div>
              <div className="text-sm text-muted">{b.author}</div>
              {b.description && <p className="mt-2 line-clamp-2 text-xs text-muted">{b.description}</p>}
            </div>
          </Card>
        ))}
      </div>
      {books.data?.length === 0 && (
        <Card>
          <Empty>Kitob yo&apos;q</Empty>
        </Card>
      )}
    </>
  );
}

function AddBook({ act, onDone }: { act: ReturnType<typeof useAction>; onDone: () => void }) {
  const formRef = useRef<HTMLFormElement>(null);
  const [rights, setRights] = useState(false);
  return (
    <Card>
      <CardHeader title="Yangi kitob" subtitle="Faqat tarqatish huquqi bor kitoblar: mualliflik muddati o'tgan, ruxsat olingan yoki sotib olingan" />
      <form
        ref={formRef}
        className="grid gap-4 p-5 md:grid-cols-2"
        onSubmit={async (e) => {
          e.preventDefault();
          const fd = new FormData(e.currentTarget);
          fd.set("rights_confirmed", rights ? "true" : "false");
          const cover = fd.get("cover");
          if (cover instanceof File && cover.size === 0) fd.delete("cover");
          const ok = await act.run(() => api("kitob/books", { method: "POST", body: fd }), "Kitob qo'shildi");
          if (ok) onDone();
        }}
      >
        <Field label="Nomi">
          <input name="title" className="field" required />
        </Field>
        <Field label="Muallif">
          <input name="author" className="field" required />
        </Field>
        <Field label="Qisqa tavsif">
          <textarea name="description" className="field min-h-20" />
        </Field>
        <div className="space-y-4">
          <Field label="PDF fayl" hint="50 MB gacha">
            <input name="pdf" type="file" accept="application/pdf" required className="field file:mr-3 file:rounded-md file:border-0 file:bg-accent-soft file:px-3 file:py-1 file:text-accent" />
          </Field>
          <Field label="Muqova (ixtiyoriy)">
            <input name="cover" type="file" accept="image/*" className="field file:mr-3 file:rounded-md file:border-0 file:bg-surface-2 file:px-3 file:py-1 file:text-fg" />
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm md:col-span-2">
          <input type="checkbox" checked={rights} onChange={(e) => setRights(e.target.checked)} className="accent-[var(--accent)]" />
          Bu kitobni xodimlarga tarqatish huquqimiz bor
        </label>
        <div className="md:col-span-2">
          <Button type="submit" disabled={act.busy || !rights}>
            Yuklash
          </Button>
        </div>
      </form>
    </Card>
  );
}
