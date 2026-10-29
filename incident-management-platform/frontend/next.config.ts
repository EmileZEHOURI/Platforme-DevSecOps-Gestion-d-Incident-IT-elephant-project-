import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  async rewrites() {
    const backend = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
    if (!backend) return [];
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backend.replace(/\/$/, "")}/:path*`,
      },
    ];
  },
};

export default nextConfig;
