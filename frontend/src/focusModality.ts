/**
 * Records whether the operator last used the keyboard or a pointer, on <html data-input>.
 * Route changes move focus to the page or record heading (tabindex="-1") so screen readers
 * announce it. Browsers treat that programmatic focus as focus-visible on a direct load, which
 * drew a large ring around titles nobody tabbed to. The ring now shows on those headings only
 * after keyboard use (see foundation.css); interactive controls are unaffected.
 */
export function trackInputModality(
  root: HTMLElement = document.documentElement,
) {
  const keyboard = (event: KeyboardEvent) => {
    if (["Shift", "Control", "Alt", "Meta"].includes(event.key)) return;
    root.dataset.input = "keyboard";
  };
  const pointer = () => {
    root.dataset.input = "pointer";
  };
  document.addEventListener("keydown", keyboard, true);
  document.addEventListener("pointerdown", pointer, true);
  return () => {
    document.removeEventListener("keydown", keyboard, true);
    document.removeEventListener("pointerdown", pointer, true);
  };
}
