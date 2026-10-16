// Vortex web server: serves the Next.js app and forwards /api, /v1 (and the API docs) to the
// Vortex API. Browsers and other devices only ever talk to this one address.
//
// Why not Next.js rewrites: they cut streams off after 30 s (long model answers) and drop the
// client IP that the API's per-IP rate limiter needs.
//
//   node server.mjs            development (hot reload)
//   node server.mjs --prod     production (after `next build`)

import http from "node:http";
import next from "next";

const prod = process.argv.includes("--prod");
const port = Number(process.env.PORT ?? 3000);
const host = process.env.HOST ?? "127.0.0.1";
const api = new URL(process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000");
const PROXIED = /^\/(?:api|v1)(?:\/|$)|^\/(?:docs|openapi\.json|health)$/;

const app = next({ dev: !prod, hostname: host, port });
const handle = app.getRequestHandler();
await app.prepare();

function proxy(req, res) {
  const clientIp = (req.socket.remoteAddress ?? "").replace(/^::ffff:/, "");
  const headers = {
    ...req.headers,
    host: api.host,
    // We are the edge: replace (never append to) whatever the client sent, so it can't be spoofed.
    "x-forwarded-for": clientIp,
    "x-forwarded-proto": "http",
  };
  const upstream = http.request(
    { hostname: api.hostname, port: api.port, path: req.url, method: req.method, headers },
    (upRes) => {
      res.writeHead(upRes.statusCode ?? 502, upRes.headers);
      upRes.pipe(res);
    },
  );
  upstream.on("error", () => {
    if (!res.headersSent) res.writeHead(502, { "content-type": "application/json" });
    res.end(
      JSON.stringify({
        error: {
          message: "O servidor do Vortex não está respondendo.",
          type: "server_error",
          code: "api_unreachable",
        },
      }),
    );
  });
  // Browser closed the tab mid-answer → drop the upstream request (the API stops generating).
  res.on("close", () => upstream.destroy());
  req.pipe(upstream);
}

http
  .createServer((req, res) => {
    const path = (req.url ?? "/").split("?")[0];
    if (PROXIED.test(path)) proxy(req, res);
    else void handle(req, res);
  })
  .listen(port, host, () => {
    console.log(`[vortex] web ${prod ? "(production)" : "(dev)"} on http://${host}:${port} → API ${api.origin}`);
  });
