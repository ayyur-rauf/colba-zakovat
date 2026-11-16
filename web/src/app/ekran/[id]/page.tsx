import { Suspense } from "react";
import BigScreen from "@/components/zakovat/BigScreen";

// Sahifa tizimga kirgandan keyin brauzerda chiziladi — oldindan chizish tekshiruvi kerak emas.
export const instant = false;

export default function ScreenPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <BigScreen />
    </Suspense>
  );
}
