import { useEffect, useRef, type RefObject } from "react";

/** Keep focus on the record across dedicated Details and its remounted directory row. */
export function useRecordDetailFocus({
  recordKey,
  detailReady,
  directoryReady,
  paused,
  headingRef,
  directoryRef,
  fallbackId,
}: {
  recordKey: string | null;
  detailReady: boolean;
  directoryReady: boolean;
  paused: boolean;
  headingRef: RefObject<HTMLHeadingElement | null>;
  directoryRef: RefObject<HTMLUListElement | null>;
  fallbackId: string;
}) {
  const lastRecord = useRef<string | null>(null);
  const focusedRecord = useRef<string | null>(null);
  useEffect(() => {
    // Domain editors and creation workflows retain their own focus ownership.
    if (paused) return;
    if (recordKey) {
      lastRecord.current = recordKey;
      if (!detailReady || focusedRecord.current === recordKey) return;
      const frame = requestAnimationFrame(() => {
        if (!headingRef.current) return;
        focusedRecord.current = recordKey;
        // A user who tabs elsewhere while data loads keeps that destination.
        if (document.activeElement === document.body)
          headingRef.current.focus();
      });
      return () => {
        cancelAnimationFrame(frame);
      };
    }
    focusedRecord.current = null;
    const previous = lastRecord.current;
    if (!previous || !directoryReady) return;
    const frame = requestAnimationFrame(() => {
      lastRecord.current = null;
      if (document.activeElement !== document.body) return;
      const directory = directoryRef.current;
      const row = Array.from(
        directory?.querySelectorAll<HTMLElement>("[data-preview-id]") ?? [],
      ).find((item) => item.dataset.previewId === previous);
      // Filtering, paging or record removal may have removed the original row.
      (
        row?.querySelector<HTMLButtonElement>(".ui-directory-trigger") ??
        directory ??
        document.getElementById(fallbackId)
      )?.focus();
    });
    return () => {
      cancelAnimationFrame(frame);
    };
  }, [
    recordKey,
    detailReady,
    directoryReady,
    paused,
    headingRef,
    directoryRef,
    fallbackId,
  ]);
}
