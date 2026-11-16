import { Suspense } from "react";
import LoginForm from "@/components/LoginForm";

// Sahifa tizimga kirgandan keyin brauzerda chiziladi — oldindan chizish tekshiruvi kerak emas.
export const instant = false;

export default function LoginPage() {
  return (
    <main className="flex flex-1 items-center justify-center p-6">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
