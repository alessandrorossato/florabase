import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  NativeFileActionUnavailableError,
  type ProtectedRequestCapability,
} from "../auth/api";
import {
  cleanupNativeSharedCache,
  NATIVE_SHARED_CACHE_DIR,
  openNativeProtectedBlob,
  printNativePage,
  registerNativeImageViewerHandler,
  sanitizeShareFilename,
  shareNativeBlob,
} from "./fileActions";
import { NativeImageViewer } from "./NativeImageViewer";

type CapacitorWindow = typeof globalThis & { Capacitor?: unknown };

function createMockCapability(initiallyAuthorized = true) {
  let authorized = initiallyAuthorized;
  const listeners = new Set<() => void>();
  const capability = {
    isAuthorized: () => authorized,
    subscribeInvalidation: (listener: () => void) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  } as unknown as ProtectedRequestCapability;

  return {
    capability,
    invalidate: () => {
      authorized = false;
      for (const listener of listeners) {
        listener();
      }
    },
  };
}

describe("native file actions, image viewer, and printing", () => {
  afterEach(() => {
    cleanup();
    registerNativeImageViewerHandler(null);
    delete (globalThis as CapacitorWindow).Capacitor;
    vi.restoreAllMocks();
  });

  it("sanitizes filenames and infers missing extensions safely", () => {
    expect(sanitizeShareFilename("../../etc/passwd", "text/csv")).toBe(
      "passwd.csv",
    );
    expect(sanitizeShareFilename("plants-export.csv", "text/csv")).toBe(
      "plants-export.csv",
    );
    expect(sanitizeShareFilename("...hidden", "image/jpeg")).toBe("hidden.jpg");
    expect(sanitizeShareFilename("  ", "application/pdf")).toBe(
      "florabase-file.pdf",
    );
  });

  it("writes base64 into CACHE/shared and invokes Share plugin", async () => {
    const writeFile = vi.fn().mockResolvedValue({
      uri: "file:///cache/shared/plants.csv",
    });
    const getUri = vi.fn();
    const share = vi.fn().mockResolvedValue({ activityType: "files" });
    (globalThis as CapacitorWindow).Capacitor = {
      isNativePlatform: () => true,
      Plugins: {
        Filesystem: { writeFile, getUri, deleteFile: vi.fn(), rmdir: vi.fn() },
        Share: { share },
      },
    };

    const blob = new Blob(["id,name\n1,Monstera\n"], { type: "text/csv" });
    const result = await shareNativeBlob({
      blob,
      filename: "plants.csv",
      contentType: "text/csv",
    });

    expect(result).toBe("plants.csv");
    expect(writeFile).toHaveBeenCalledWith({
      path: `${NATIVE_SHARED_CACHE_DIR}/plants.csv`,
      data: btoa("id,name\n1,Monstera\n"),
      directory: "CACHE",
      recursive: true,
    });
    expect(share).toHaveBeenCalledWith({
      title: "plants.csv",
      files: ["file:///cache/shared/plants.csv"],
      dialogTitle: "plants.csv",
    });
  });

  it("treats Android share sheet cancellation as a clean no-error return", async () => {
    (globalThis as CapacitorWindow).Capacitor = {
      isNativePlatform: () => true,
      Plugins: {
        Filesystem: {
          writeFile: vi
            .fn()
            .mockResolvedValue({ uri: "file:///cache/shared/doc.pdf" }),
          getUri: vi.fn(),
          deleteFile: vi.fn(),
          rmdir: vi.fn(),
        },
        Share: {
          share: vi.fn().mockRejectedValue(new Error("Share canceled")),
        },
      },
    };

    const filename = await shareNativeBlob({
      blob: new Blob(["%PDF"], { type: "application/pdf" }),
      filename: "doc.pdf",
      contentType: "application/pdf",
    });
    expect(filename).toBe("doc.pdf");
  });

  it("throws NativeFileActionUnavailableError when native plugins are absent", async () => {
    await expect(
      shareNativeBlob({
        blob: new Blob(["csv"], { type: "text/csv" }),
        filename: "plants.csv",
      }),
    ).rejects.toThrow(NativeFileActionUnavailableError);
  });

  it("cleans up the dedicated shared cache directory on startup", async () => {
    const rmdir = vi.fn().mockResolvedValue(undefined);
    (globalThis as CapacitorWindow).Capacitor = {
      isNativePlatform: () => true,
      Plugins: {
        Filesystem: {
          writeFile: vi.fn(),
          getUri: vi.fn(),
          deleteFile: vi.fn(),
          rmdir,
        },
      },
    };

    await cleanupNativeSharedCache();
    expect(rmdir).toHaveBeenCalledWith({
      path: NATIVE_SHARED_CACHE_DIR,
      directory: "CACHE",
      recursive: true,
    });
  });

  it("routes images to NativeImageViewer and non-images to share sheet", async () => {
    const handler = vi.fn();
    registerNativeImageViewerHandler(handler);
    const { capability } = createMockCapability();

    const imageBlob = new Blob(["jpg-bytes"], { type: "image/jpeg" });
    await openNativeProtectedBlob({
      blob: imageBlob,
      filename: "leaf",
      contentType: "image/jpeg",
      capability,
    });
    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler.mock.calls[0]?.[0]).toMatchObject({
      blob: imageBlob,
      filename: "leaf.jpg",
      contentType: "image/jpeg",
    });

    const share = vi.fn().mockResolvedValue({});
    (globalThis as CapacitorWindow).Capacitor = {
      isNativePlatform: () => true,
      Plugins: {
        Filesystem: {
          writeFile: vi
            .fn()
            .mockResolvedValue({ uri: "file:///cache/shared/labels.pdf" }),
          getUri: vi.fn(),
          deleteFile: vi.fn(),
          rmdir: vi.fn(),
        },
        Share: { share },
      },
    };
    await openNativeProtectedBlob({
      blob: new Blob(["%PDF"], { type: "application/pdf" }),
      filename: "labels",
      contentType: "application/pdf",
      capability,
    });
    expect(share).toHaveBeenCalledTimes(1);
  });

  it("NativeImageViewer revokes object URLs on unmount and invalidation and shares bytes without refetching", async () => {
    const user = userEvent.setup();
    const createObjectURL = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:native-photo-1");
    const revokeObjectURL = vi
      .spyOn(URL, "revokeObjectURL")
      .mockImplementation(() => undefined);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const writeFile = vi
      .fn()
      .mockResolvedValue({ uri: "file:///cache/shared/specimen.jpg" });
    const share = vi.fn().mockResolvedValue({});
    (globalThis as CapacitorWindow).Capacitor = {
      isNativePlatform: () => true,
      Plugins: {
        Filesystem: {
          writeFile,
          getUri: vi.fn(),
          deleteFile: vi.fn(),
          rmdir: vi.fn(),
        },
        Share: { share },
      },
    };

    const { capability, invalidate } = createMockCapability();
    const onClose = vi.fn();
    const blob = new Blob(["raw-photo-bytes"], { type: "image/jpeg" });

    const { unmount } = render(
      <NativeImageViewer
        request={{
          blob,
          filename: "specimen.jpg",
          contentType: "image/jpeg",
          capability,
        }}
        onClose={onClose}
      />,
    );

    expect(
      await screen.findByRole("dialog", { name: "specimen.jpg" }),
    ).toBeVisible();
    expect(createObjectURL).toHaveBeenCalledWith(blob);

    // Sharing reuses the exact in-memory Blob bytes without calling fetch().
    await user.click(screen.getByRole("button", { name: /share \/ save/i }));
    await waitFor(() => {
      expect(share).toHaveBeenCalledTimes(1);
    });
    expect(writeFile).toHaveBeenCalledWith({
      path: `${NATIVE_SHARED_CACHE_DIR}/specimen.jpg`,
      data: btoa("raw-photo-bytes"),
      directory: "CACHE",
      recursive: true,
    });
    expect(fetchSpy).not.toHaveBeenCalled();

    // Auth invalidation immediately revokes the object URL and closes the viewer.
    invalidate();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:native-photo-1");
    expect(onClose).toHaveBeenCalledTimes(1);

    unmount();
    // Revoke is idempotent (called once).
    expect(revokeObjectURL).toHaveBeenCalledTimes(1);
  });

  it("invokes WebPrint plugin when available and rejects clearly when absent", async () => {
    await expect(printNativePage("Florabase Labels")).rejects.toThrow(
      NativeFileActionUnavailableError,
    );

    const print = vi.fn().mockResolvedValue(undefined);
    (globalThis as CapacitorWindow).Capacitor = {
      isNativePlatform: () => true,
      Plugins: { WebPrint: { print } },
    };
    await printNativePage("Florabase Labels");
    expect(print).toHaveBeenCalledWith({ jobName: "Florabase Labels" });
  });
});
