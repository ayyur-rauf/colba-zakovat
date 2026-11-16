import type { NextConfig } from "next";

// Backend (Django) manzili. Brauzer /api/... ga murojaat qiladi, Next uni backendga uzatadi —
// shu tufayli CORS kerak emas va token boshqa domenga chiqmaydi.
// Railway: BACKEND_URL — backend xizmatining manzili (masalan https://colba-backend.up.railway.app).
// Diqqat: qiymat build vaqtida o'qiladi — o'zgartirsangiz saytni qayta deploy qiling.
const BACKEND_URL = (process.env.BACKEND_URL ?? "http://127.0.0.1:8100").replace(/\/+$/, "");
if (process.env.NODE_ENV === "production" && !process.env.BACKEND_URL) {
  console.warn("[colba] BACKEND_URL berilmagan — API so'rovlari 127.0.0.1:8100 ga yuboriladi.");
}

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [
      // Django URL'lari "/" bilan tugaydi; mijoz yo'lni "/" siz yuboradi.
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*/` },
    ];
  },
};

export default nextConfig;
