import { useCallback, useEffect, useRef, useState } from "react";

const firstFieldSelector =
  "input:not([type='hidden']):not([disabled]), select:not([disabled]), textarea:not([disabled]), button[data-creation-focus]:not([disabled])";

export function useCreationDisclosure() {
  const [expanded, setExpanded] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const focusFirst = useCallback(() => {
    panelRef.current?.querySelector<HTMLElement>(firstFieldSelector)?.focus();
  }, []);

  useEffect(() => {
    if (!expanded) return;
    focusFirst();
  }, [expanded, focusFirst]);

  function open() {
    setExpanded(true);
  }

  function close({ returnFocus = true } = {}) {
    setExpanded(false);
    if (returnFocus)
      window.setTimeout(() => {
        triggerRef.current?.focus();
      }, 0);
  }

  return { expanded, triggerRef, panelRef, open, close, focusFirst };
}
