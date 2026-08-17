import type { NextConfig } from "next";

export const API_PROXY_SOURCE = "/api/v1/:path*";

const backendOrigin = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      {
        source: API_PROXY_SOURCE,
        destination: `${backendOrigin}/api/v1/:path*/`,
      },
    ];
  },
};

export default nextConfig;
