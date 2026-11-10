import { describe, expect, it, vi } from "vitest";

import { registerServiceWorker } from "./registerServiceWorker";

describe("registerServiceWorker", () => {
  it("does nothing when service workers are unsupported", async () => {
    await expect(registerServiceWorker(undefined)).resolves.toBeNull();
  });

  it("registers /sw.js at the root scope without HTTP-cached worker scripts", async () => {
    const registration = {} as ServiceWorkerRegistration;
    const register = vi.fn().mockResolvedValue(registration);
    const container = { register } as unknown as ServiceWorkerContainer;

    await expect(registerServiceWorker(container)).resolves.toBe(registration);
    expect(register).toHaveBeenCalledWith("/sw.js", {
      scope: "/",
      updateViaCache: "none",
    });
  });

  it("treats registration failure as progressive enhancement", async () => {
    const container = {
      register: vi.fn().mockRejectedValue(new Error("insecure context")),
    } as unknown as ServiceWorkerContainer;

    await expect(registerServiceWorker(container)).resolves.toBeNull();
  });

  it("is a no-op in the default jsdom environment without a service worker", async () => {
    await expect(registerServiceWorker()).resolves.toBeNull();
  });
});
