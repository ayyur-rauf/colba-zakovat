import { Suspense } from "react";
import ModuleShell from "@/components/ModuleShell";

// Sahifa tizimga kirgandan keyin brauzerda chiziladi — oldindan chizish tekshiruvi kerak emas.
export const instant = false;

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={null}>
      <ModuleShell moduleKey="kitobxonlik">{children}</ModuleShell>
    </Suspense>
  );
}
