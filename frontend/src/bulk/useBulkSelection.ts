import { useEffect, useId, useState, type MouseEvent } from "react";
import type { BulkReference } from "./api";
import { isFreshDirectoryNavigation } from "../components/recordNavigation";
export interface BulkChoice extends BulkReference {
  label: string;
  eligible: boolean;
}
export const bulkKey = (row: BulkReference) => `${row.kind}:${row.id}`;
export const BULK_LIMIT = 100;

/** Local explicit IDs; never part of URL/Saved View state. */
export function useBulkSelection(
  directoryScope: string,
  visible: BulkChoice[],
  preservePresentationSelection = false,
) {
  const entryId = useId();
  const scope =
    directoryScope +
    "|" +
    visible.map((row) => `${bulkKey(row)}:${String(row.eligible)}`).join("|");
  const [selection, setSelection] = useState({
    scope,
    active: false,
    keys: [] as string[],
    dialog: false,
  });
  if (selection.scope !== scope)
    setSelection({ scope, active: false, keys: [], dialog: false });
  const current =
    selection.scope === scope
      ? selection
      : { scope, active: false, keys: [], dialog: false };
  const selected = visible.filter((row) => current.keys.includes(bulkKey(row)));
  const cancel = () => {
    setSelection({ scope, active: false, keys: [], dialog: false });
  };
  useEffect(() => {
    const canonicalHash = () => {
      const [path, query] = window.location.hash.split("?", 2);
      const params = new URLSearchParams(query);
      params.delete("view");
      return `${path}?${params}`;
    };
    const currentHash = canonicalHash();
    const reset = (event: Event) => {
      if (
        preservePresentationSelection &&
        !isFreshDirectoryNavigation(event) &&
        canonicalHash() === currentHash
      )
        return;
      setSelection({ scope, active: false, keys: [], dialog: false });
    };
    window.addEventListener("hashchange", reset);
    window.addEventListener("popstate", reset);
    return () => {
      window.removeEventListener("hashchange", reset);
      window.removeEventListener("popstate", reset);
    };
  }, [scope, preservePresentationSelection]);
  return {
    recordClick: (event: MouseEvent<HTMLElement>, row: BulkChoice) => {
      if (event.defaultPrevented || event.button !== 0) return false;
      const button =
        event.target instanceof Element ? event.target.closest("button") : null;
      if (button && !button.matches(".ui-directory-trigger")) return false;
      const target = event.target;
      if (
        target instanceof Element &&
        target.closest(
          "a, input, select, textarea, label, .ui-directory-record-actions",
        )
      )
        return false;
      if (!current.active && !event.ctrlKey && !event.metaKey) return false;
      event.preventDefault();
      if (!row.eligible) return true;
      const key = bulkKey(row);
      const keys = current.keys.includes(key)
        ? current.keys.filter((value) => value !== key)
        : current.keys.length < BULK_LIMIT
          ? [...current.keys, key]
          : current.keys;
      setSelection({ ...current, active: true, keys });
      return true;
    },
    entryId,
    focusEntry: () => {
      document.getElementById(entryId)?.focus();
    },
    active: current.active,
    selected,
    dialog: current.dialog,
    cancel,
    start: () => {
      setSelection({ scope, active: true, keys: [], dialog: false });
    },
    clear: () => {
      setSelection({ ...current, keys: [] });
    },
    selectVisible: () => {
      const eligible = visible.filter((row) => row.eligible);
      if (eligible.length <= BULK_LIMIT)
        setSelection({ ...current, keys: eligible.map(bulkKey) });
    },
    openDialog: () => {
      setSelection({ ...current, dialog: true });
    },
    closeDialog: () => {
      setSelection({ ...current, dialog: false });
    },
    toggle: (row: BulkChoice) => {
      const key = bulkKey(row);
      if (!row.eligible) return;
      const keys = current.keys.includes(key)
        ? current.keys.filter((value) => value !== key)
        : current.keys.length < BULK_LIMIT
          ? [...current.keys, key]
          : current.keys;
      setSelection({ ...current, keys });
    },
    checked: (row: BulkReference) => current.keys.includes(bulkKey(row)),
  };
}
export type BulkSelection = ReturnType<typeof useBulkSelection>;
