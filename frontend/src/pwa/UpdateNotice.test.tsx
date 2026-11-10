import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UpdateNotice } from "./UpdateNotice";
import {
  fetchReleaseFingerprint,
  RELEASE_URL,
  watchForNewRelease,
} from "./releaseWatcher";

function releaseResponse(version: string, revision = "abc123") {
  return new Response(JSON.stringify({ version, revision, source: "x" }), {
    headers: { "Content-Type": "application/json" },
  });
}

function setVisibility(state: DocumentVisibilityState) {
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    get: () => state,
  });
  document.dispatchEvent(new Event("visibilitychange"));
}

async function flush() {
  for (let i = 0; i < 5; i += 1) await Promise.resolve();
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  setVisibility("visible");
});

describe("fetchReleaseFingerprint", () => {
  it("reads the unauthenticated release identity without credentials or caching", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(releaseResponse("0.1.0-beta.6"));

    await expect(fetchReleaseFingerprint(fetchImpl)).resolves.toBe(
      "0.1.0-beta.6+abc123",
    );
    expect(fetchImpl).toHaveBeenCalledWith(RELEASE_URL, {
      cache: "no-store",
      credentials: "omit",
      headers: { Accept: "application/json" },
    });
  });

  it.each([
    ["a missing release file", () => new Response("", { status: 404 })],
    [
      "the SPA HTML fallback of a development server",
      () => new Response("<!doctype html><html></html>", { status: 200 }),
    ],
    [
      "an unexpected JSON shape",
      () => new Response(JSON.stringify({ version: 6 }), { status: 200 }),
    ],
  ])("ignores %s", async (_label, makeResponse) => {
    const fetchImpl = vi.fn().mockResolvedValue(makeResponse());
    await expect(fetchReleaseFingerprint(fetchImpl)).resolves.toBeNull();
  });

  it("ignores network failures", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError("offline"));
    await expect(fetchReleaseFingerprint(fetchImpl)).resolves.toBeNull();
  });
});

describe("watchForNewRelease", () => {
  it("announces once when the server release changes after the app becomes visible", async () => {
    let served = "0.1.0-beta.6";
    const fetchImpl = vi.fn(() => Promise.resolve(releaseResponse(served)));
    const onUpdateAvailable = vi.fn();
    const stop = watchForNewRelease({ onUpdateAvailable, fetchImpl });
    await flush();

    setVisibility("visible");
    await flush();
    expect(onUpdateAvailable).not.toHaveBeenCalled();

    served = "0.1.0-beta.7";
    setVisibility("hidden");
    await flush();
    setVisibility("visible");
    await flush();
    expect(onUpdateAvailable).toHaveBeenCalledOnce();

    setVisibility("visible");
    await flush();
    expect(onUpdateAvailable).toHaveBeenCalledOnce();
    stop();
  });

  it("detects a rebuilt image with the same version but a new revision", async () => {
    let revision = "aaa111";
    const fetchImpl = vi.fn(() =>
      Promise.resolve(releaseResponse("0.1.0-beta.6", revision)),
    );
    const onUpdateAvailable = vi.fn();
    const stop = watchForNewRelease({ onUpdateAvailable, fetchImpl });
    await flush();

    revision = "bbb222";
    window.dispatchEvent(new Event("online"));
    await flush();
    expect(onUpdateAvailable).toHaveBeenCalledOnce();
    stop();
  });

  it("establishes the baseline after a temporary outage instead of announcing", async () => {
    const fetchImpl = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockResolvedValue(releaseResponse("0.1.0-beta.6"));
    const onUpdateAvailable = vi.fn();
    const stop = watchForNewRelease({ onUpdateAvailable, fetchImpl });
    await flush();

    window.dispatchEvent(new Event("online"));
    await flush();
    window.dispatchEvent(new Event("online"));
    await flush();
    expect(fetchImpl).toHaveBeenCalledTimes(3);
    expect(onUpdateAvailable).not.toHaveBeenCalled();
    stop();
  });

  it("checks periodically only while visible and stops cleanly", async () => {
    vi.useFakeTimers();
    const fetchImpl = vi.fn(() =>
      Promise.resolve(releaseResponse("0.1.0-beta.6")),
    );
    const stop = watchForNewRelease({
      onUpdateAvailable: vi.fn(),
      fetchImpl,
      intervalMs: 1000,
    });
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchImpl).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1000);
    expect(fetchImpl).toHaveBeenCalledTimes(2);

    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => "hidden",
    });
    await vi.advanceTimersByTimeAsync(3000);
    expect(fetchImpl).toHaveBeenCalledTimes(2);

    stop();
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => "visible",
    });
    await vi.advanceTimersByTimeAsync(3000);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });
});

describe("UpdateNotice", () => {
  function controllableWatch() {
    let announce: () => void = () => undefined;
    const stop = vi.fn();
    const watch = vi.fn(
      ({ onUpdateAvailable }: { onUpdateAvailable: () => void }) => {
        announce = onUpdateAvailable;
        return stop;
      },
    );
    return {
      watch,
      stop,
      announce: () => {
        announce();
      },
    };
  }

  it("keeps an empty live status region mounted without a visible banner until update", () => {
    const { watch } = controllableWatch();
    render(<UpdateNotice watch={watch} />);
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
    expect(
      screen.queryByRole("complementary", { name: "Florabase update" }),
    ).not.toBeInTheDocument();
  });

  it("asks before reloading and never reloads on its own", async () => {
    const { watch, announce } = controllableWatch();
    const reload = vi.fn();
    render(<UpdateNotice watch={watch} reload={reload} />);
    const liveStatus = screen.getByRole("status");

    act(() => {
      announce();
    });
    expect(liveStatus).toHaveTextContent(/new version of florabase/i);
    expect(liveStatus).toHaveTextContent(/save any open changes/i);
    expect(
      screen.getByRole("complementary", { name: "Florabase update" }),
    ).toBeInTheDocument();
    expect(reload).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Reload now" }));
    expect(reload).toHaveBeenCalledOnce();
  });

  it("can be dismissed without reloading", async () => {
    const { watch, announce } = controllableWatch();
    const reload = vi.fn();
    render(<UpdateNotice watch={watch} reload={reload} />);

    act(() => {
      announce();
    });
    await userEvent.click(await screen.findByRole("button", { name: "Later" }));
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
    expect(
      screen.queryByRole("complementary", { name: "Florabase update" }),
    ).not.toBeInTheDocument();
    expect(reload).not.toHaveBeenCalled();
  });

  it("stops watching when unmounted", () => {
    const { watch, stop } = controllableWatch();
    const { unmount } = render(<UpdateNotice watch={watch} />);
    unmount();
    expect(stop).toHaveBeenCalled();
  });
});
