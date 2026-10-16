import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { setRecordRoute } from "./recordNavigation";

/** Contextual edits add one normal hash-history entry; direct URLs have no background. */
export function useEditRoute({
  canDismiss,
  onDismiss,
  routeIsEdit,
}: {
  canDismiss: () => boolean;
  onDismiss: () => void;
  routeIsEdit: boolean;
}) {
  const [modal, setModal] = useState(false);
  const editHash = useRef("");
  const approved = useRef(false);
  const restoring = useRef(false);
  const leaving = useRef(false);
  const previousRoute = useRef(routeIsEdit);
  useLayoutEffect(() => {
    const departed = previousRoute.current && !routeIsEdit;
    previousRoute.current = routeIsEdit;
    if (!modal || !departed || leaving.current) return;
    if (!approved.current && !canDismiss()) {
      restoring.current = true;
      window.history.forward();
      return;
    }
    leaving.current = true;
    setModal(false);
    onDismiss();
  }, [routeIsEdit, modal, canDismiss, onDismiss]);
  useEffect(() => {
    if (!modal) return;
    const back = (event: Event) => {
      if (window.location.hash === editHash.current) {
        restoring.current = false;
        return;
      }
      if (restoring.current) {
        event.stopImmediatePropagation();
        return;
      }
      if (leaving.current) return;
      if (!approved.current && !canDismiss()) {
        // Refuse the departure before App reads it. Restore the existing forward entry,
        // retaining this draft rather than replacing history or inventing a new route.
        event.stopImmediatePropagation();
        restoring.current = true;
        window.history.forward();
        return;
      }
      approved.current = false;
      leaving.current = true;
      setModal(false);
      onDismiss();
    };
    window.addEventListener("popstate", back, true);
    window.addEventListener("hashchange", back, true);
    return () => {
      window.removeEventListener("popstate", back, true);
      window.removeEventListener("hashchange", back, true);
    };
  }, [modal, canDismiss, onDismiss]);
  return {
    modal,
    open(hash: string) {
      editHash.current = hash;
      approved.current = false;
      restoring.current = false;
      leaving.current = false;
      setModal(true);
      setRecordRoute(hash);
    },
    prepareDeparture() {
      if (!canDismiss()) return false;
      approved.current = true;
      return true;
    },
    close(force = false) {
      if (!force && !canDismiss()) return;
      if (modal) {
        approved.current = true;
        leaving.current = true;
        setModal(false);
        onDismiss();
        window.history.back();
      } else onDismiss();
    },
  };
}
