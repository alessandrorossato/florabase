import { useEffect, useId, useState } from "react";
import type { BulkReference } from "./api";
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
    const reset = () => {
      setSelection({ scope, active: false, keys: [], dialog: false });
    };
    window.addEventListener("hashchange", reset);
    window.addEventListener("popstate", reset);
    return () => {
      window.removeEventListener("hashchange", reset);
      window.removeEventListener("popstate", reset);
    };
  }, [scope]);
  return {
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
