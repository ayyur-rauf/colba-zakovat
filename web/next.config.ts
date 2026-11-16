import type { NextConfig } from "next";

// Backend (Django) manzili. Brauzer /api/... ga murojaat qiladi, Next uni backendga uzatadi —
// shu tufayli CORS kerak emas va token boshqa domenga chiqmaydi.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8100";

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
