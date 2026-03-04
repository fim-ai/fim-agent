import type { NextConfig } from "next";

const API_BACKEND = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  // Use separate output dir for production builds so `next build`
  // doesn't nuke the dev server's .next/ directory mid-HMR.
  distDir: process.env.NODE_ENV === "production" ? ".next-build" : ".next",
  allowedDevOrigins: ["192.168.9.114"],
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_BACKEND}/api/:path*` },
    ];
  },
};

export default nextConfig;
