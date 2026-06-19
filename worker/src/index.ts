/**
 * Cloudflare Worker: edge cache + CORS in front of service-render.
 *
 * Per spec 1.1, the worker's role here is "cache/CORS in front of our own
 * service" (not a proxy to an undocumented Google endpoint, which was the
 * v1 design). Only /transliterate and /render are proxied — both are
 * checkout-adjacent but not checkout-blocking themselves (the PDP block
 * degrades to "no suggestions" on failure, per spec 1.5/2.5).
 */

export interface Env {
  SERVICE_RENDER_ORIGIN: string;
  ALLOWED_ORIGIN: string;
}

const PROXIED_PATHS = new Set(["/transliterate", "/render"]);

// /transliterate responses are cacheable by (text, lang, topk) since the
// backend is deterministic-ish for a given input; /render is NOT cached
// because each render produces a fresh render_id (spec Section 0 — every
// approved render must be individually traceable).
const CACHE_TTL_SECONDS: Record<string, number> = {
  "/transliterate": 300,
};

function corsHeaders(allowedOrigin: string): HeadersInit {
  return {
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders(env.ALLOWED_ORIGIN) });
    }

    if (!PROXIED_PATHS.has(url.pathname)) {
      return new Response("not found", { status: 404 });
    }

    if (request.method !== "POST") {
      return new Response("method not allowed", { status: 405 });
    }

    const ttl = CACHE_TTL_SECONDS[url.pathname];
    const cache = caches.default;

    // Build a cache key from the request body since these are POSTs (the
    // Cache API only keys on GET-shaped Requests by default).
    let cacheKey: Request | null = null;
    if (ttl) {
      const body = await request.clone().text();
      const keyUrl = new URL(request.url);
      keyUrl.searchParams.set("_body_hash", await sha256Hex(body));
      cacheKey = new Request(keyUrl.toString(), { method: "GET" });

      const cached = await cache.match(cacheKey);
      if (cached) {
        const resp = new Response(cached.body, cached);
        Object.entries(corsHeaders(env.ALLOWED_ORIGIN)).forEach(([k, v]) => resp.headers.set(k, v as string));
        return resp;
      }
    }

    const originUrl = `${env.SERVICE_RENDER_ORIGIN}${url.pathname}`;
    const originResp = await fetch(originUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.clone().text(),
    });

    const respHeaders = new Headers(originResp.headers);
    Object.entries(corsHeaders(env.ALLOWED_ORIGIN)).forEach(([k, v]) => respHeaders.set(k, v as string));

    if (ttl && originResp.ok && cacheKey) {
      respHeaders.set("Cache-Control", `public, max-age=${ttl}`);
      const toCache = new Response(await originResp.clone().text(), { headers: respHeaders, status: originResp.status });
      ctx.waitUntil(cache.put(cacheKey, toCache.clone()));
    }

    return new Response(originResp.body, { status: originResp.status, headers: respHeaders });
  },
};

async function sha256Hex(text: string): Promise<string> {
  const data = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
