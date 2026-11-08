import type { NextConfig } from "next";

const isExport = process.env.OUTPUT_MODE === "export" || process.env.NEXT_EXPORT === "true";
const cleanBasePath = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/^\/+|\/+$/g, "");
const basePath = cleanBasePath ? `/${cleanBasePath}` : undefined;
const backendUrl = process.env.INTERNAL_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  output: isExport ? "export" : "standalone",
  reactStrictMode: true,
  trailingSlash: isExport ? true : false,
  basePath: basePath,
  images: {
    unoptimized: true,
  },
  ...(isExport
    ? {}
    : {
        async rewrites() {
          return [
            {
              source: "/api/backend/:path*",
              destination: `${backendUrl}/api/v1/:path*`,
            },
            {
              source: "/api/v1/:path*",
              destination: `${backendUrl}/api/v1/:path*`,
            },
            {
              source: "/health",
              destination: `${backendUrl}/health`,
            },
          ];
        },
      }),
};

export default nextConfig;
