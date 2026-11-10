/**
 * Executes the real public/sw.js in an isolated VM context with fake Cache Storage and network,
 * then dispatches install/activate/fetch events. These are behavioural tests of the shipped worker,
 * not of a re-implementation.
 */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { describe, expect, it, vi } from "vitest";

const ORIGIN = "https://florabase.example.test";
const SOURCE = fs.readFileSync(
  path.resolve(__dirname, "../../public/sw.js"),
  "utf-8",
);
const PRECACHE = [
  "/offline.html",
  "/offline.css",
  "/offline.js",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-maskable-192.png",
  "/icons/icon-maskable-512.png",
  "/icons/apple-touch-icon.png",
  "/icons/icon.svg",
  "/favicon.ico",
  "/favicon.svg",
];

interface FakeRequest {
  url: string;
  method: string;
  mode: string;
}
type Network = (request: FakeRequest) => Promise<Response>;
type Listener = (event: Record<string, unknown>) => void;

function keyOf(request: FakeRequest | string) {
  return typeof request === "string"
    ? request
    : new URL(request.url).pathname + new URL(request.url).search;
}

function loadWorker(initialNetwork: Network) {
  let network = initialNetwork;
  const listeners = new Map<string, Listener>();
  const store = new Map<string, Map<string, Response>>();
  const networkCalls: string[] = [];
  const openCache = (name: string) => {
    let entries = store.get(name);
    if (!entries) {
      entries = new Map();
      store.set(name, entries);
    }
    const cache = entries;
    return {
      addAll: async (paths: string[]) => {
        for (const p of paths) {
          const response = await network({
            url: ORIGIN + p,
            method: "GET",
            mode: "cors",
          });
          if (!response.ok) throw new TypeError(`precache failed: ${p}`);
          cache.set(p, response);
        }
      },
      put: (request: FakeRequest | string, response: Response) => {
        cache.set(keyOf(request), response);
        return Promise.resolve();
      },
    };
  };
  const caches = {
    open: (name: string) => Promise.resolve(openCache(name)),
    keys: () => Promise.resolve([...store.keys()]),
    delete: (name: string) => Promise.resolve(store.delete(name)),
    match: (request: FakeRequest | string) => {
      const key = keyOf(request);
      for (const entries of store.values()) {
        const hit = entries.get(key);
        if (hit) return Promise.resolve(hit.clone());
      }
      return Promise.resolve(undefined);
    },
  };
  const clients = { claim: vi.fn(() => Promise.resolve()) };
  const self = {
    location: new URL(`${ORIGIN}/sw.js`),
    clients,
    skipWaiting: vi.fn(() => Promise.resolve()),
    addEventListener: (type: string, listener: Listener) => {
      listeners.set(type, listener);
    },
  };
  const context = vm.createContext({
    self,
    caches,
    URL,
    Response,
    fetch: (request: FakeRequest) => {
      networkCalls.push(`${request.method} ${keyOf(request)}`);
      return network(request);
    },
  });
  vm.runInContext(SOURCE, context);

  const lifecycle = async (type: "install" | "activate") => {
    let pending: Promise<unknown> = Promise.resolve();
    listeners.get(type)?.({
      waitUntil: (promise: Promise<unknown>) => {
        pending = promise;
      },
    });
    await pending;
  };
  const dispatchFetch = (
    pathOrUrl: string,
    { method = "GET", mode = "cors" }: { method?: string; mode?: string } = {},
  ): Promise<Response> | undefined => {
    let responded: Promise<Response> | undefined;
    const url = pathOrUrl.startsWith("http") ? pathOrUrl : ORIGIN + pathOrUrl;
    let pendingWaitUntil: Promise<unknown> = Promise.resolve();
    listeners.get("fetch")?.({
      request: { url, method, mode },
      respondWith: (response: Promise<Response>) => {
        responded = Promise.resolve(response);
      },
      waitUntil: (promise: Promise<unknown>) => {
        pendingWaitUntil = Promise.resolve(promise);
      },
    });
    void pendingWaitUntil;
    return responded;
  };
  const cachedKeys = () =>
    [...store.values()].flatMap((entries) => [...entries.keys()]);
  return {
    self,
    store,
    networkCalls,
    lifecycle,
    dispatchFetch,
    cachedKeys,
    setNetwork: (next: Network) => {
      network = next;
    },
  };
}

const online: Network = (request) =>
  Promise.resolve(
    new Response(`live ${keyOf(request)}`, {
      status: 200,
      headers: { "Content-Type": "text/plain" },
    }),
  );
const offline: Network = () => Promise.reject(new TypeError("Failed to fetch"));
const statusNetwork =
  (status: number): Network =>
  () =>
    Promise.resolve(new Response(`upstream ${String(status)}`, { status }));

async function installedWorker() {
  const worker = loadWorker(online);
  await worker.lifecycle("install");
  await worker.lifecycle("activate");
  worker.networkCalls.length = 0;
  return worker;
}

describe("service worker lifecycle", () => {
  it("precaches exactly the public shell assets and activates without waiting", async () => {
    const worker = loadWorker(online);
    await worker.lifecycle("install");

    expect(worker.cachedKeys().sort()).toEqual([...PRECACHE].sort());
    expect(worker.self.skipWaiting).toHaveBeenCalledOnce();
  });

  it("removes previous Florabase caches and claims clients without navigating them", async () => {
    const worker = loadWorker(online);
    worker.store.set("florabase-shell-v0", new Map([["/old", new Response()]]));
    await worker.lifecycle("install");
    await worker.lifecycle("activate");

    expect([...worker.store.keys()]).toEqual(["florabase-shell-v1"]);
    expect(worker.self.clients.claim).toHaveBeenCalledOnce();
    // Only claim() exists on the fake clients object: any matchAll()/navigate()/reload attempt
    // would throw, and the source must not contain one either.
    expect(SOURCE).not.toMatch(/matchAll|\.navigate\(|location\.reload/);
  });

  it("fails installation rather than caching an incomplete shell", async () => {
    const worker = loadWorker(statusNetwork(404));
    await expect(worker.lifecycle("install")).rejects.toThrow(
      /precache failed/,
    );
    expect(worker.self.skipWaiting).not.toHaveBeenCalled();
  });
});

describe("requests the service worker must never handle", () => {
  it.each([
    ["/api/v1/auth/session", "GET"],
    ["/api/v1/auth/csrf", "GET"],
    ["/api/v1/auth/login", "POST"],
    ["/api/v1/auth/logout", "POST"],
    ["/api/v1/plants?search=aloe", "GET"],
    ["/api/v1/plants/01900000-0000-7000-8000-000000000001", "PATCH"],
    ["/api/v1/plants/01900000-0000-7000-8000-000000000001", "DELETE"],
    ["/api/v1/attachments/01900000-0000-7000-8000-000000000002/content", "GET"],
    ["/api/v1/collection-photos/x/thumbnail", "GET"],
    ["/api/v1/seed-lots", "PUT"],
    ["/runtime-config.js", "GET"],
    ["/release.json", "GET"],
    ["/appearance.js", "GET"],
    ["/healthz", "GET"],
    ["/assets/index-CHHWvZAu.js", "GET"],
    ["/assets/PlantScreen-Dlivt0O5.js", "GET"],
    ["/", "POST"],
    ["https://tile.openstreetmap.org/3/4/2.png", "GET"],
    ["https://api.gbif.org/v1/species/match", "GET"],
  ])("leaves %s (%s) to the browser network stack", async (url, method) => {
    const worker = await installedWorker();
    const before = worker.cachedKeys().sort();

    expect(worker.dispatchFetch(url, { method })).toBeUndefined();
    expect(worker.networkCalls).toEqual([]);
    expect(worker.cachedKeys().sort()).toEqual(before);
  });

  it("does not intercept an API request even when it is a navigation", async () => {
    const worker = await installedWorker();
    expect(
      worker.dispatchFetch("/api/v1/exports/collection.csv", {
        mode: "navigate",
      }),
    ).toBeUndefined();
  });
});

describe("navigation policy", () => {
  it("is network-first and never stores navigation responses", async () => {
    const worker = await installedWorker();
    const before = worker.cachedKeys().sort();

    const response = await worker.dispatchFetch("/?view=plants", {
      mode: "navigate",
    });

    expect(await response?.text()).toBe("live /?view=plants");
    expect(worker.networkCalls).toEqual(["GET /?view=plants"]);
    expect(worker.cachedKeys().sort()).toEqual(before);
  });

  it("passes authentication and application errors through unchanged", async () => {
    const worker = await installedWorker();
    for (const status of [401, 403, 404, 500]) {
      worker.setNetwork(statusNetwork(status));
      const response = await worker.dispatchFetch("/", { mode: "navigate" });
      expect(response?.status).toBe(status);
    }
  });

  it("serves the static unavailable page when the network fails", async () => {
    const worker = await installedWorker();
    worker.setNetwork(offline);

    const response = await worker.dispatchFetch("/", { mode: "navigate" });

    expect(await response?.text()).toBe("live /offline.html");
  });

  it.each([502, 503, 504])(
    "serves the static unavailable page while a proxy reports %i",
    async (status) => {
      const worker = await installedWorker();
      worker.setNetwork(statusNetwork(status));

      const response = await worker.dispatchFetch("/", { mode: "navigate" });

      expect(await response?.text()).toBe("live /offline.html");
    },
  );

  it("still answers when the fallback page was never cached", async () => {
    const worker = loadWorker(offline);
    const failed = await worker.dispatchFetch("/", { mode: "navigate" });
    expect(failed?.status).toBe(503);

    worker.setNetwork(statusNetwork(502));
    const proxied = await worker.dispatchFetch("/", { mode: "navigate" });
    expect(await proxied?.text()).toBe("upstream 502");
  });
});

describe("public shell assets", () => {
  it("refreshes icons from the network before using the cache", async () => {
    const worker = await installedWorker();
    worker.setNetwork(() =>
      Promise.resolve(new Response("new icon", { status: 200 })),
    );

    const fresh = await worker.dispatchFetch("/icons/icon-192.png");
    expect(await fresh?.text()).toBe("new icon");
    await Promise.resolve();
    await Promise.resolve();

    worker.setNetwork(offline);
    const cached = await worker.dispatchFetch("/icons/icon-192.png");
    expect(await cached?.text()).toBe("new icon");
  });

  it.each([502, 503, 504])(
    "serves cached shell assets when a proxy reports %i during an outage",
    async (status) => {
      const worker = await installedWorker();
      worker.setNetwork(statusNetwork(status));

      const css = await worker.dispatchFetch("/offline.css");
      const js = await worker.dispatchFetch("/offline.js");
      expect(await css?.text()).toBe("live /offline.css");
      expect(await js?.text()).toBe("live /offline.js");
    },
  );

  it("does not cache redirected shell asset responses", async () => {
    const worker = await installedWorker();
    worker.setNetwork(() =>
      Promise.resolve({
        status: 200,
        ok: true,
        redirected: true,
        clone: () => new Response("redirected", { status: 200 }),
        text: () => Promise.resolve("redirected"),
      } as unknown as Response),
    );

    const res = await worker.dispatchFetch("/offline.js");
    expect(await res?.text()).toBe("redirected");

    worker.setNetwork(offline);
    const cached = await worker.dispatchFetch("/offline.js");
    expect(await cached?.text()).toBe("live /offline.js");
  });

  it("returns a network error for an uncached shell asset while offline", async () => {
    const worker = loadWorker(offline);
    const response = await worker.dispatchFetch("/icons/icon-512.png");
    expect(response?.type).toBe("error");
  });

  it("only ever holds the public shell assets after mixed traffic", async () => {
    const worker = await installedWorker();
    for (const [url, mode, method] of [
      ["/api/v1/auth/session", "cors", "GET"],
      ["/api/v1/attachments/a/content", "no-cors", "GET"],
      ["/", "navigate", "GET"],
      ["/?record=plant", "navigate", "GET"],
      ["/assets/index-CHHWvZAu.js", "cors", "GET"],
      ["/icons/icon-512.png", "no-cors", "GET"],
      ["/manifest.webmanifest", "cors", "GET"],
      ["/api/v1/plants", "cors", "POST"],
    ]) {
      await worker.dispatchFetch(url, { mode, method });
    }
    await Promise.resolve();

    for (const key of worker.cachedKeys()) {
      expect(PRECACHE).toContain(key);
    }
  });
});

describe("unavailable page content", () => {
  const publicDir = path.resolve(__dirname, "../../public");
  const offlineHtml = fs.readFileSync(
    path.join(publicDir, "offline.html"),
    "utf-8",
  );
  const offlineCss = fs.readFileSync(
    path.join(publicDir, "offline.css"),
    "utf-8",
  );
  const offlineJs = fs.readFileSync(
    path.join(publicDir, "offline.js"),
    "utf-8",
  );

  it("explains the situation and offers a CSP-safe retry without inline handlers or storage", () => {
    expect(offlineHtml).toContain("Florabase cannot be reached");
    expect(offlineHtml).toContain("Retry connection");
    expect(offlineHtml).toContain('<link rel="stylesheet" href="/offline.css"');
    expect(offlineHtml).toContain('<script src="/offline.js" defer>');
    expect(offlineHtml).not.toMatch(/\son\w+=|<style/i);
    expect(offlineJs).not.toMatch(/fetch\(|Storage/i);
    expect(offlineCss).toContain("prefers-color-scheme: dark");
  });

  it("contains no private or authenticated material", () => {
    for (const content of [offlineHtml, offlineCss, offlineJs]) {
      expect(content).not.toMatch(/csrf|session|token|cookie|\/api\//i);
    }
  });
});
