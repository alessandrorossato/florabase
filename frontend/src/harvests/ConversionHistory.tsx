import { useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { TaskDialog } from "../components/TaskDialog";
import {
  listConversions,
  reversalEligibility,
  reverseConversion,
  type Conversion,
  type Eligibility,
} from "./conversionApi";
import { inventoryError, remainingLabel } from "./inventoryApi";

export function ConversionHistory({
  kind,
  id,
  onChanged,
  refreshKey,
}: {
  kind: "inventory_id" | "seed_lot_id";
  id: string;
  onChanged?: () => void;
  refreshKey?: string;
}) {
  const auth = useAuth();
  const [open, setOpen] = useState(kind === "seed_lot_id");
  const [rows, setRows] = useState<Conversion[] | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Conversion | null>(null);
  const [eligibility, setEligibility] = useState<Eligibility | null>(null);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    void listConversions(kind, id, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setRows(data);
          setError(null);
        }
      })
      .catch((failure: unknown) => {
        if (!controller.signal.aborted) {
          if (failure instanceof ApiError && failure.status === 401)
            auth.sessionExpired();
          else setError("Could not load Seed lot conversions.");
        }
      });
    return () => {
      controller.abort();
    };
  }, [open, kind, id, attempt, refreshKey, auth]);
  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    void reversalEligibility(selected.id, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setEligibility(data);
      })
      .catch((failure: unknown) => {
        if (!controller.signal.aborted) {
          if (failure instanceof ApiError && failure.status === 401)
            auth.sessionExpired();
          else setError("Could not check undo eligibility. Close and retry.");
        }
      });
    return () => {
      controller.abort();
    };
  }, [selected, auth]);
  async function undo() {
    if (!selected || pending) return;
    setPending(true);
    try {
      await reverseConversion(
        selected.id,
        auth.state.status === "authenticated" ? auth.state.csrfToken : "",
      );
      setSelected(null);
      setAttempt((v) => v + 1);
      onChanged?.();
    } catch (failure: unknown) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else {
        setError(inventoryError(failure));
        setEligibility({
          status: "blocked",
          reasons: [inventoryError(failure)],
        });
      }
    } finally {
      setPending(false);
    }
  }
  return (
    <section aria-label="Seed lot conversion history">
      {kind === "inventory_id" ? (
        <button
          type="button"
          className="button--secondary"
          aria-expanded={open}
          onClick={() => {
            setOpen((v) => !v);
          }}
        >
          {open ? "Hide" : "Show"} Seed lot conversions
        </button>
      ) : (
        <h4>Harvested seed origin</h4>
      )}
      {open && (
        <>
          {error && (
            <p role="alert">
              {error}{" "}
              <button
                type="button"
                onClick={() => {
                  setAttempt((v) => v + 1);
                }}
              >
                Retry conversions
              </button>
            </p>
          )}
          {!rows && !error ? (
            <p role="status">Loading Seed lot conversions…</p>
          ) : rows?.length === 0 ? (
            <p>No Seed lot conversions recorded.</p>
          ) : (
            <ul>
              {rows?.map((row) => (
                <li key={row.id}>
                  <a href={`#/seeds/${row.seed_lot_id}`}>
                    {row.seed_lot_label ?? "Seed lot"}
                  </a>{" "}
                  · {row.status === "reversed" ? "Reversed" : "Created"}
                  <p>
                    Transferred:{" "}
                    {row.quantity
                      ? `${row.quantity.is_approximate ? "About " : ""}${row.quantity.value} ${row.quantity.kind === "seed_count" ? "seeds" : (row.quantity.unit ?? "")}`
                      : "Unknown quantity"}
                  </p>
                  <a href={`#/harvests/${row.harvest_id}`}>
                    Open originating Harvest and stored material
                  </a>
                  {row.status === "applied" && (
                    <div className="actions">
                      <button
                        type="button"
                        className="button--secondary"
                        onClick={() => {
                          setSelected(row);
                          setEligibility(null);
                          setError(null);
                        }}
                      >
                        Undo Seed lot creation
                      </button>
                    </div>
                  )}
                  {row.reversed_at && (
                    <p>Undone {new Date(row.reversed_at).toLocaleString()}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      {selected && (
        <TaskDialog
          title="Undo Seed lot creation"
          onClose={() => {
            if (!pending) setSelected(null);
          }}
        >
          <h3>Undo Seed lot creation?</h3>
          <p>
            The Seed lot will remain in history as Reversed, with its producer
            and Harvest links. Source stored material will return to its
            captured prior state: {remainingLabel(selected.before)}. Conversion
            and disposition evidence stays recorded.
          </p>
          <p>
            Later source changes or unresolved dependent use can block undo.
          </p>
          {!eligibility ? (
            error ? (
              <p role="alert">{error}</p>
            ) : (
              <p role="status">Checking whether undo is safe…</p>
            )
          ) : eligibility.status === "blocked" ? (
            <div role="alert">
              <p>Undo is unavailable.</p>
              <ul>
                {eligibility.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p>Current material and Seed lot state permit undo.</p>
          )}
          <div className="actions">
            <button
              type="button"
              className="button--danger"
              disabled={pending || eligibility?.status !== "safe"}
              onClick={() => {
                void undo();
              }}
            >
              {pending ? "Undoing…" : "Confirm undo"}
            </button>
            <button
              type="button"
              className="button--secondary"
              disabled={pending}
              onClick={() => {
                setSelected(null);
              }}
            >
              Cancel
            </button>
          </div>
        </TaskDialog>
      )}
    </section>
  );
}
