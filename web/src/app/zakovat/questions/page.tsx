import { Suspense } from "react";
import QuestionBank from "@/components/zakovat/QuestionBank";

// Sahifa tizimga kirgandan keyin brauzerda chiziladi — oldindan chizish tekshiruvi kerak emas.
export const instant = false;

export default function Page() {
  return (
    <Suspense fallback={<div className="p-10 text-center text-muted">Yuklanmoqda…</div>}>
      <QuestionBank />
    </Suspense>
  );
}
