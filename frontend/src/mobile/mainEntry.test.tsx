import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const registerServiceWorkerMock = vi.fn(() => Promise.resolve(null));
const createRootRenderMock = vi.fn();
const createRootMock = vi.fn(() => ({ render: createRootRenderMock }));

vi.mock("../pwa/registerServiceWorker", () => ({
  registerServiceWorker: registerServiceWorkerMock,
}));

vi.mock("./NativeServerOnboarding", () => ({
  NativeServerOnboarding: () => null,
}));

vi.mock("react-dom/client", () => ({
  createRoot: createRootMock,
}));

vi.mock("../App.tsx", () => ({
  App: () => null,
}));

vi.mock("../pwa/UpdateNotice", () => ({
  UpdateNotice: () => null,
}));

vi.mock("../focusModality", () => ({
  trackInputModality: vi.fn(),
}));

describe("main entrypoint native vs web bootstrap", () => {
  beforeEach(() => {
    vi.resetModules();
    registerServiceWorkerMock.mockClear();
    createRootMock.mockClear();
    createRootRenderMock.mockClear();
    document.body.innerHTML = '<div id="root"></div>';
    delete (globalThis as { Capacitor?: unknown }).Capacitor;
  });

  afterEach(() => {
    delete (globalThis as { Capacitor?: unknown }).Capacitor;
    document.body.innerHTML = "";
  });

  it("registers /sw.js and mounts web App + UpdateNotice in browser contexts", async () => {
    await import("../main");

    expect(registerServiceWorkerMock).toHaveBeenCalledOnce();
    expect(createRootMock).toHaveBeenCalledOnce();
    expect(createRootRenderMock).toHaveBeenCalledOnce();
  });

  it("skips registerServiceWorker and UpdateNotice and mounts NativeServerOnboarding in Capacitor native contexts", async () => {
    (globalThis as { Capacitor?: unknown }).Capacitor = {
      isNativePlatform: () => true,
      getPlatform: () => "android",
    };

    await import("../main");
    await vi.waitFor(() => {
      expect(createRootRenderMock).toHaveBeenCalledOnce();
    });

    expect(registerServiceWorkerMock).not.toHaveBeenCalled();
    expect(createRootMock).toHaveBeenCalledOnce();
  });
});
