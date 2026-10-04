import { BotanicalIdentityFilter } from "./BotanicalIdentityFilter";
import { useEffect, useId, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { TaskDialog } from "../components/TaskDialog";
import { DirectorySearch } from "../components/ReferenceUI";
import { formatPartialDate } from "../events/eventData";
import {
  type Harvest,
  type HarvestItem,
  materials,
  identityChoices,
} from "./api";
import { InventoryDialog } from "./InventoryDialog";
import {
  dispositionHistory,
  dispositionKinds,
  inventoryError,
  inventoryList,
  remainingLabel,
  removeInventory,
  type Disposition,
  type Inventory,
} from "./inventoryApi";

function History({ inventory }: { inventory: Inventory }) {
  const auth = useAuth();
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<Disposition[] | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    void dispositionHistory(inventory.id, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setRows(data);
          setError(false);
        }
      })
      .catch((failure: unknown) => {
        if (!controller.signal.aborted) {
          if (failure instanceof ApiError && failure.status === 401)
            auth.sessionExpired();
          else setError(true);
        }
      });
    return () => {
      controller.abort();
    };
  }, [open, inventory.id, inventory.updated_at, attempt, auth]);
  return (
    <div className="inventory-history">
      <button
        type="button"
        className="button--secondary"
        aria-expanded={open}
        onClick={() => {
          setOpen((v) => !v);
        }}
      >
        {open ? "Hide" : "Show"} disposition history
      </button>
      {open &&
        (error ? (
          <p role="alert">
            Could not load history.{" "}
            <button
              type="button"
              onClick={() => {
                setAttempt((v) => v + 1);
              }}
            >
              Retry history
            </button>
          </p>
        ) : !rows ? (
          <p role="status">Loading disposition history…</p>
        ) : (
          <ol aria-label="Disposition history">
            {rows.map((row) => (
              <li key={row.id}>
                <strong>
                  {dispositionKinds.find((k) => k.id === row.kind)?.label}
                </strong>
                <span>
                  {formatPartialDate(row.occurred_on)} ·{" "}
                  {row.mode === "use_all"
                    ? "All remaining"
                    : remainingLabel({
                        state: "active",
                        quantity: row.quantity,
                      })}
                </span>
                <span>Before: {remainingLabel(row.before)}</span>
                <span>After: {remainingLabel(row.after)}</span>
                {row.notes && <p className="preserve-lines">{row.notes}</p>}
              </li>
            ))}
          </ol>
        ))}
    </div>
  );
}
export function StoredMaterialSection({ harvest }: { harvest: Harvest }) {
  const auth = useAuth();
  const [rows, setRows] = useState<Inventory[] | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editor, setEditor] = useState<{
    item: HarvestItem;
    inventory?: Inventory;
    disposition?: boolean;
  } | null>(null);
  const [removing, setRemoving] = useState<Inventory | null>(null);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void inventoryList(controller.signal, harvest.id)
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
          else
            setError(
              "Could not load stored material. Retry before managing inventory.",
            );
        }
      });
    return () => {
      controller.abort();
    };
  }, [harvest.id, harvest.updated_at, attempt, auth]);
  async function remove() {
    if (!removing || pending) return;
    setPending(true);
    try {
      await removeInventory(
        removing.id,
        auth.state.status === "authenticated" ? auth.state.csrfToken : "",
      );
      setRemoving(null);
      setNotice(
        "Inventory tracking removed. Collected material stays recorded.",
      );
      setAttempt((v) => v + 1);
    } catch (failure: unknown) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else setError(inventoryError(failure));
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="stored-material-section" aria-label="Stored material">
      <h4>Stored material</h4>
      <p className="field-help">
        Remaining now is managed separately from the collected quantity.
      </p>
      {error && (
        <p role="alert">
          {error}{" "}
          <button
            type="button"
            onClick={() => {
              setAttempt((v) => v + 1);
            }}
          >
            Retry stored material
          </button>
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      {!rows && !error && <p role="status">Loading stored material…</p>}
      {rows && (
        <ol className="harvest-items">
          {harvest.items.map((item) => {
            const inventory = rows.find(
              (row) => row.harvest_item_id === item.id,
            );
            return (
              <li key={item.id}>
                <strong>
                  {materials.find((m) => m.id === item.material_kind)?.label}
                </strong>
                {item.description && (
                  <p className="preserve-lines">{item.description}</p>
                )}
                <span>
                  {inventory
                    ? `${inventory.state === "active" ? "Active · " : ""}Remaining now: ${remainingLabel(inventory)}`
                    : "Not tracked"}
                </span>
                {inventory?.location && (
                  <a href={`#/locations/${inventory.location.id}`}>
                    Storage: {inventory.location.display_path}
                  </a>
                )}
                <div className="actions">
                  {!inventory ? (
                    <button
                      type="button"
                      onClick={() => {
                        setEditor({ item });
                      }}
                    >
                      Track stored material
                    </button>
                  ) : (
                    <>
                      {inventory.state === "active" && (
                        <button
                          type="button"
                          onClick={() => {
                            setEditor({ item, inventory, disposition: true });
                          }}
                        >
                          Record disposition
                        </button>
                      )}
                      <button
                        type="button"
                        className="button--secondary"
                        onClick={() => {
                          setEditor({ item, inventory });
                        }}
                      >
                        Edit stored material
                      </button>
                      {!inventory.has_dispositions && (
                        <button
                          type="button"
                          className="button--secondary"
                          onClick={() => {
                            setError(null);
                            setRemoving(inventory);
                          }}
                        >
                          Remove tracking
                        </button>
                      )}
                    </>
                  )}
                </div>
                {inventory?.has_dispositions && (
                  <>
                    <p className="field-help">
                      Tracking is retained because this material has disposition
                      history.
                    </p>
                    <History inventory={inventory} />
                  </>
                )}
              </li>
            );
          })}
        </ol>
      )}
      {editor && (
        <InventoryDialog
          {...editor}
          onClose={() => {
            setEditor(null);
          }}
          onSaved={() => {
            setEditor(null);
            setNotice("Stored material saved.");
            setAttempt((v) => v + 1);
          }}
        />
      )}
      {removing && (
        <TaskDialog
          title="Remove inventory tracking"
          onClose={() => {
            if (!pending) setRemoving(null);
          }}
        >
          <h3>Remove inventory tracking?</h3>
          <p>
            This material has no disposition history. Its collected quantity
            remains in the Harvest.
          </p>
          <div className="actions">
            <button
              type="button"
              disabled={pending}
              onClick={() => {
                void remove();
              }}
            >
              Remove tracking
            </button>
            <button
              type="button"
              disabled={pending}
              className="button--secondary"
              onClick={() => {
                setRemoving(null);
              }}
            >
              Cancel
            </button>
          </div>
          {error && <p role="alert">{error}</p>}
        </TaskDialog>
      )}
    </section>
  );
}

export function StoredMaterialDirectory() {
  const auth = useAuth();
  const id = useId();
  const [rows, setRows] = useState<Inventory[] | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState("");
  const [state, setState] = useState("active");
  const [material, setMaterial] = useState("");
  const [location, setLocation] = useState("");
  const [identity, setIdentity] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void inventoryList(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setRows(data);
          setError(false);
        }
      })
      .catch((failure: unknown) => {
        if (!controller.signal.aborted) {
          if (failure instanceof ApiError && failure.status === 401)
            auth.sessionExpired();
          else setError(true);
        }
      });
    return () => {
      controller.abort();
    };
  }, [attempt, auth]);
  const filtered = rows?.filter(
    (row) =>
      (!identity || row.source.botanical_identity.id === identity) &&
      (!state || row.state === state) &&
      (!material || row.material_kind === material) &&
      (!location || row.location?.id === location) &&
      `${row.harvest_title} ${row.source.display_name} ${row.source.botanical_identity.display_label} ${row.description ?? ""}`
        .toLocaleLowerCase()
        .includes(query.trim().toLocaleLowerCase()),
  );
  const locations = [
    ...new Map(
      rows?.flatMap((row) =>
        row.location ? [[row.location.id, row.location] as const] : [],
      ) ?? [],
    ).values(),
  ];
  return (
    <div className="stored-material-directory">
      <h3>Stored material</h3>
      <p>
        Current stored remainder from explicitly tracked Harvest material lines.
      </p>
      <div className="harvest-filters">
        <DirectorySearch
          id={`${id}-search`}
          label="Search stored material"
          placeholder="Harvest, source or botanical identity"
          value={query}
          onChange={setQuery}
        />
        <BotanicalIdentityFilter
          choices={identityChoices(rows?.map((row) => row.source) ?? [])}
          value={identity}
          onChange={setIdentity}
        />
        <div className="field">
          <label htmlFor={`${id}-state`}>State</label>
          <select
            id={`${id}-state`}
            value={state}
            onChange={(event) => {
              setState(event.currentTarget.value);
            }}
          >
            <option value="active">Active material</option>
            <option value="depleted">Depleted material</option>
            <option value="">All states</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${id}-material`}>Material</label>
          <select
            id={`${id}-material`}
            value={material}
            onChange={(event) => {
              setMaterial(event.currentTarget.value);
            }}
          >
            <option value="">All materials</option>
            {materials.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field stored-material-location-filter">
          <label htmlFor={`${id}-location`}>Storage Location</label>
          <select
            id={`${id}-location`}
            value={location}
            onChange={(event) => {
              setLocation(event.currentTarget.value);
            }}
          >
            <option value="">All Locations</option>
            {locations.map((l) => (
              <option key={l.id} value={l.id}>
                {l.display_path}
              </option>
            ))}
          </select>
        </div>
      </div>
      {error && (
        <p role="alert">
          Could not load stored material.{" "}
          <button
            type="button"
            onClick={() => {
              setAttempt((v) => v + 1);
            }}
          >
            Retry
          </button>
        </p>
      )}
      {!rows && !error && <p role="status">Loading stored material…</p>}
      {filtered && (
        <>
          <p className="directory-summary">
            {filtered.length} tracked material{" "}
            {filtered.length === 1 ? "line" : "lines"}
          </p>
          {!filtered.length ? (
            <p className="empty-state">
              {rows?.length
                ? "No stored material matches these filters."
                : "No stored material tracked yet. Open a Harvest and choose Track stored material."}
            </p>
          ) : (
            <ul
              className="harvest-directory"
              aria-label="Stored material directory"
            >
              {filtered.map((row) => (
                <li key={row.id}>
                  <a
                    className="harvest-directory-row"
                    href={`#/harvests/${row.harvest_id}`}
                  >
                    <span className="harvest-row-content">
                      <strong>
                        {
                          materials.find((m) => m.id === row.material_kind)
                            ?.label
                        }{" "}
                        · {remainingLabel(row)}
                      </strong>
                      <span>{row.harvest_title}</span>
                      <span>
                        {row.source.botanical_identity.display_label} ·{" "}
                        {row.source.display_name} · {row.source.lifecycle}
                      </span>
                      {row.description && <span>{row.description}</span>}
                      <span>
                        {row.location?.display_path ??
                          "Storage Location not recorded"}
                      </span>
                    </span>
                    <span className="harvest-row-meta">
                      {row.state === "active" ? "Active" : "Depleted"}
                      <small>Open source Harvest</small>
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
