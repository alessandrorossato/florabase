import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  classifyResourceUrl,
  isExpectedAuthCancellation,
  isPresentationRetainedState,
  requestProtectedBlob,
  type ProtectedRequestCapability,
} from "../auth/api";
import { useOptionalAuth } from "../auth/context";

export type ProtectedImageTargetRef = (node: HTMLElement | null) => void;

export interface ProtectedImageState {
  src: string | null;
  loading: boolean;
  failed: boolean;
  referrerPolicy: "no-referrer" | undefined;
}

interface LoadedBlob {
  url: string;
  objectUrl: string;
  capability: ProtectedRequestCapability;
}

export function useProtectedImage({
  rawUrl,
  lazy = true,
  onError,
}: {
  rawUrl: string | null | undefined;
  lazy?: boolean;
  onError?: (failedUrl: string) => void;
}): [ProtectedImageTargetRef, ProtectedImageState] {
  const auth = useOptionalAuth();
  const capability = auth?.capability;
  const authState = auth?.state;
  const authorized =
    authState?.status === "authenticated" &&
    Boolean(capability?.isAuthorized());
  const retained = authState ? isPresentationRetainedState(authState) : false;

  const classified = classifyResourceUrl(rawUrl);
  const protectedUrl =
    classified.kind === "protected-api" ? classified.url : null;

  const [element, setElement] = useState<HTMLElement | null>(null);
  const [intersected, setIntersected] = useState(false);
  const [loaded, setLoaded] = useState<LoadedBlob | null>(null);
  const [failedState, setFailedState] = useState<{
    url: string;
    capability: ProtectedRequestCapability;
  } | null>(null);
  const loadedRef = useRef<LoadedBlob | null>(null);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const isVisible =
    !lazy || typeof IntersectionObserver === "undefined" || intersected;

  useEffect(() => {
    return () => {
      if (loadedRef.current) {
        URL.revokeObjectURL(loadedRef.current.objectUrl);
        loadedRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!lazy || typeof IntersectionObserver === "undefined") return;
    if (!element || !protectedUrl || intersected) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setIntersected(true);
          observer.disconnect();
        }
      },
      { rootMargin: "200px" },
    );
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, [element, intersected, lazy, protectedUrl]);

  useEffect(() => {
    const active = loadedRef.current;
    if (!active) return;
    if (
      !retained ||
      active.url !== protectedUrl ||
      active.capability !== capability
    ) {
      URL.revokeObjectURL(active.objectUrl);
      loadedRef.current = null;
    }
  }, [capability, protectedUrl, retained]);

  useEffect(() => {
    if (!protectedUrl || !isVisible || !capability || !authorized) {
      return;
    }
    const existing = loadedRef.current;
    if (existing?.url === protectedUrl && existing.capability === capability) {
      return;
    }

    const controller = new AbortController();

    requestProtectedBlob(protectedUrl, {
      capability,
      signal: controller.signal,
    })
      .then(({ blob }) => {
        if (controller.signal.aborted) return;
        const objectUrl = URL.createObjectURL(blob);
        if (!capability.isAuthorized()) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        const nextLoaded: LoadedBlob = {
          url: protectedUrl,
          objectUrl,
          capability,
        };
        if (loadedRef.current) {
          URL.revokeObjectURL(loadedRef.current.objectUrl);
        }
        loadedRef.current = nextLoaded;
        setFailedState(null);
        setLoaded(nextLoaded);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (
          isExpectedAuthCancellation(error) ||
          (error instanceof ApiError && error.status === 401)
        ) {
          return;
        }
        setFailedState({ url: protectedUrl, capability });
        onErrorRef.current?.(protectedUrl);
      });

    return () => {
      controller.abort();
    };
  }, [authorized, capability, isVisible, protectedUrl]);

  if (
    classified.kind === "public-local" ||
    classified.kind === "local-blob" ||
    classified.kind === "external-https"
  ) {
    return [
      setElement,
      {
        src: classified.url,
        loading: false,
        failed: false,
        referrerPolicy:
          classified.kind === "external-https" ? "no-referrer" : undefined,
      },
    ];
  }

  if (classified.kind === "invalid") {
    return [
      setElement,
      {
        src: null,
        loading: false,
        failed: false,
        referrerPolicy: undefined,
      },
    ];
  }

  const matchesLoaded =
    loaded !== null &&
    loaded.url === classified.url &&
    capability !== undefined &&
    loaded.capability === capability &&
    retained;

  const matchesFailed =
    failedState !== null &&
    failedState.url === classified.url &&
    capability !== undefined &&
    failedState.capability === capability;

  const loading = isVisible && authorized && !matchesLoaded && !matchesFailed;

  return [
    setElement,
    {
      src: matchesLoaded ? loaded.objectUrl : null,
      loading,
      failed: matchesFailed,
      referrerPolicy: undefined,
    },
  ];
}
