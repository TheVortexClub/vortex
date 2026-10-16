// /api and /v1 are forwarded to the Vortex API by server.mjs (not by Next rewrites, which
// cut long streams at 30 s and drop the client IP).

/** @type {import("next").NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  compress: false, // keep SSE token streams unbuffered
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
};

export default nextConfig;
