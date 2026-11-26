import { useCallback, useEffect, useState } from "react";

/**
 * Shows one map or diagram over the whole window (UI-POLISH-004). This is an in-page overlay,
 * not the browser Fullscreen API, so app dialogs, tooltips and popovers stay visible above it
 * and it works on phones that have no element fullscreen. Escape leaves it. Maps that size
 * themselves from the window are told to measure again on each change.
 */
export function useFullscreen() {
  const [active, setActive] = useState(false);
  const toggle = useCallback(() => {
    setActive((value) => !value);
  }, []);
  useEffect(() => {
    window.dispatchEvent(new Event("resize"));
    if (!active) return;
    document.documentElement.classList.add("has-fullscreen-frame");
    const leave = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !event.defaultPrevented) setActive(false);
    };
    document.addEventListener("keydown", leave);
    return () => {
      document.documentElement.classList.remove("has-fullscreen-frame");
      document.removeEventListener("keydown", leave);
    };
  }, [active]);
  return {
    active,
    toggle,
    /** Add to the framed element's class list. */
    frameClass: active
      ? " fullscreen-frame is-fullscreen"
      : " fullscreen-frame",
  };
}
