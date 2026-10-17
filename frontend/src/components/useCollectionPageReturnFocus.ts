import { useEffect } from "react";

/** Restore the logical workflow parent after its normal route has rendered. */
export function useCollectionPageReturnFocus(ready: boolean) {
  useEffect(() => {
    if (!ready) return;
    const state: unknown = window.history.state;
    if (
      !state ||
      typeof state !== "object" ||
      !("collectionReturnFocus" in state)
    )
      return;
    const target = state.collectionReturnFocus;
    if (target !== "create" && target !== "extract") return;
    const frame = requestAnimationFrame(() => {
      document
        .querySelector<HTMLElement>(`[data-collection-return="${target}"]`)
        ?.focus();
    });
    return () => {
      cancelAnimationFrame(frame);
    };
  }, [ready]);
}
