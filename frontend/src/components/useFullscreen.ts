import { useCallback, useEffect, useState } from "react";

/**
 * Shows one map or diagram over the whole window (UI-POLISH-004). This is an in-page overlay,
 * not the browser Fullscreen API, so app dialogs, tooltips and popovers stay visible above it
 * and it works on phones that have no element fullscreen. While it is on, everything outside
 * the frame is inert, so Tab and screen readers stay inside it. Escape leaves it unless another
 * control already used that Escape (a preview, a selection, a search field). Maps that size
 * themselves from the window are told to measure again when it changes.
 */
export function useFullscreen<T extends HTMLElement = HTMLElement>() {
  const [active, setActive] = useState(false);
  // A callback ref (state) rather than a ref object, so the frame can be read in the effect.
  const [frame, setFrame] = useState<T | null>(null);
  const [changes, setChanges] = useState(0);
  const toggle = useCallback(() => {
    setChanges((value) => value + 1);
    setActive((value) => !value);
  }, []);
  useEffect(() => {
    if (changes > 0) window.dispatchEvent(new Event("resize"));
  }, [changes]);
  useEffect(() => {
    if (!active || !frame) return;
    document.documentElement.classList.add("has-fullscreen-frame");
    const made: Element[] = [];
    for (
      let node: Element | null = frame;
      node && node !== document.body;
      node = node.parentElement
    )
      for (const sibling of node.parentElement?.children ?? [])
        if (sibling !== node && !sibling.hasAttribute("inert")) {
          sibling.setAttribute("inert", "");
          made.push(sibling);
        }
    const leave = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select, [contenteditable]")) return;
      setChanges((value) => value + 1);
      setActive(false);
    };
    document.addEventListener("keydown", leave);
    return () => {
      document.documentElement.classList.remove("has-fullscreen-frame");
      document.removeEventListener("keydown", leave);
      for (const element of made) element.removeAttribute("inert");
    };
  }, [active, frame]);
  return {
    active,
    toggle,
    /** Pass as the framed element's ref. */
    setFrame,
    /** Add to the framed element's class list. */
    frameClass: active
      ? " fullscreen-frame is-fullscreen"
      : " fullscreen-frame",
  };
}
