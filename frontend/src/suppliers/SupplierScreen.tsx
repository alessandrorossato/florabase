import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import {
  createSupplier,
  listSuppliers,
  setSupplierRetired,
  supplierValidationMessages,
  updateSupplier,
  type SupplierCreate,
  type SupplierResponse,
  type SupplierUpdate,
} from "./api";

type DirectoryState =
  | { status: "loading" }
  | { status: "ready"; suppliers: SupplierResponse[] }
  | { status: "error" };
type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "success"; message: string }
  | { status: "validation"; messages: string[] }
  | { status: "error"; message: string };

const kindLabels: Record<SupplierResponse["kind"], string> = {
  seller: "Seller",
  nursery: "Nursery",
  supermarket: "Supermarket",
  person: "Person",
  exchange: "Exchange",
  other: "Other",
};

function payloadFrom(form: HTMLFormElement): SupplierCreate {
  const data = new FormData(form);
  const value = (name: string) => {
    const item = data.get(name);
    return typeof item === "string" ? item : "";
  };
  return {
    name: value("name"),
    kind: value("kind") as SupplierCreate["kind"],
    ...(value("website") ? { website: value("website") } : {}),
    ...(value("email") ? { email: value("email") } : {}),
    ...(value("phone") ? { phone: value("phone") } : {}),
    ...(value("notes") ? { notes: value("notes") } : {}),
  };
}

function SupplierFields({
  supplier,
  disabled,
}: {
  supplier?: SupplierResponse;
  disabled: boolean;
}) {
  return (
    <>
      <div className="field">
        <label htmlFor={supplier ? "edit-supplier-name" : "new-supplier-name"}>
          Name
        </label>
        <input
          id={supplier ? "edit-supplier-name" : "new-supplier-name"}
          name="name"
          required
          maxLength={255}
          disabled={disabled}
          defaultValue={supplier?.name}
        />
      </div>
      <div className="field">
        <label htmlFor={supplier ? "edit-supplier-kind" : "new-supplier-kind"}>
          Kind
        </label>
        <select
          id={supplier ? "edit-supplier-kind" : "new-supplier-kind"}
          name="kind"
          required
          disabled={disabled}
          defaultValue={supplier?.kind ?? "seller"}
        >
          {Object.entries(kindLabels).map(([value, label]) => (
            <option value={value} key={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label
          htmlFor={supplier ? "edit-supplier-website" : "new-supplier-website"}
        >
          Website
        </label>
        <input
          id={supplier ? "edit-supplier-website" : "new-supplier-website"}
          name="website"
          type="url"
          maxLength={2048}
          disabled={disabled}
          defaultValue={supplier?.website ?? ""}
        />
      </div>
      <div className="field">
        <label
          htmlFor={supplier ? "edit-supplier-email" : "new-supplier-email"}
        >
          Email
        </label>
        <input
          id={supplier ? "edit-supplier-email" : "new-supplier-email"}
          name="email"
          type="email"
          maxLength={320}
          disabled={disabled}
          defaultValue={supplier?.email ?? ""}
        />
      </div>
      <div className="field">
        <label
          htmlFor={supplier ? "edit-supplier-phone" : "new-supplier-phone"}
        >
          Phone
        </label>
        <input
          id={supplier ? "edit-supplier-phone" : "new-supplier-phone"}
          name="phone"
          type="tel"
          maxLength={120}
          disabled={disabled}
          defaultValue={supplier?.phone ?? ""}
        />
      </div>
      <div className="field">
        <label
          htmlFor={supplier ? "edit-supplier-notes" : "new-supplier-notes"}
        >
          Notes
        </label>
        <textarea
          id={supplier ? "edit-supplier-notes" : "new-supplier-notes"}
          name="notes"
          maxLength={20000}
          rows={4}
          disabled={disabled}
          defaultValue={supplier?.notes ?? ""}
        />
      </div>
    </>
  );
}

export function SupplierScreen() {
  const auth = useAuth();
  const [directory, setDirectory] = useState<DirectoryState>({
    status: "loading",
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const [attempt, setAttempt] = useState(0);
  const createForm = useRef<HTMLFormElement>(null);
  const feedback = useRef<HTMLDivElement>(null);
  const {
    expanded: creationExpanded,
    triggerRef: creationTriggerRef,
    panelRef: creationPanelRef,
    open: openCreation,
    close: closeCreation,
    focusFirst: focusCreation,
  } = useCreationDisclosure();
  const pending = save.status === "saving";

  useEffect(() => {
    const controller = new AbortController();
    void listSuppliers(controller.signal)
      .then((suppliers) => {
        setDirectory({ status: "ready", suppliers });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setDirectory({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [auth, attempt]);

  useEffect(() => {
    if (save.status === "validation" || save.status === "error")
      feedback.current?.focus();
  }, [save]);

  const suppliers = useMemo(
    () => (directory.status === "ready" ? directory.suppliers : []),
    [directory],
  );
  const selected = suppliers.find(({ id }) => id === selectedId) ?? null;
  const visible = useMemo(() => {
    const query = filter.trim().toLocaleLowerCase();
    if (!query) return suppliers;
    return suppliers.filter((supplier) =>
      [supplier.name, supplier.website, supplier.email, supplier.phone].some(
        (value) => value?.toLocaleLowerCase().includes(query),
      ),
    );
  }, [filter, suppliers]);

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrfToken = auth.state.csrfToken;

  async function apply(
    action: () => Promise<SupplierResponse>,
    success: (supplier: SupplierResponse) => string,
  ) {
    setSave({ status: "saving" });
    try {
      const supplier = await action();
      const refreshed = await listSuppliers();
      setDirectory({ status: "ready", suppliers: refreshed });
      setSelectedId(supplier.id);
      setSave({ status: "success", message: success(supplier) });
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 422)
        setSave({
          status: "validation",
          messages: supplierValidationMessages(error),
        });
      else if (error instanceof ApiError && error.status === 403)
        setSave({
          status: "error",
          message:
            "Florabase could not authorize this change. Refresh the page and try again.",
        });
      else
        setSave({
          status: "error",
          message:
            "Florabase could not save or refresh this supplier. Check the connection and try again.",
        });
    }
  }

  function submitCreate(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (pending) return;
    const form = event.currentTarget;
    void apply(
      () => createSupplier(payloadFrom(form), csrfToken),
      (supplier) => {
        createForm.current?.reset();
        setFilter("");
        closeCreation();
        return `${supplier.name} was created and selected.`;
      },
    );
  }

  function submitUpdate(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (!selected || pending) return;
    const payload: SupplierUpdate = payloadFrom(event.currentTarget);
    void apply(
      () => updateSupplier(selected.id, payload, csrfToken),
      (supplier) => `${supplier.name} was updated.`,
    );
  }

  return (
    <section aria-labelledby="suppliers-title" className="workspace">
      <div className="workspace-intro directory-heading">
        <div>
          <p className="eyebrow">Collection reference</p>
          <h2 id="suppliers-title">Suppliers</h2>
          <p>Maintain the people and places that supply collection material.</p>
        </div>
        <button
          type="button"
          ref={creationTriggerRef}
          aria-expanded={creationExpanded}
          aria-controls="new-supplier-panel"
          onClick={() => {
            if (creationExpanded) {
              focusCreation();
              return;
            }
            createForm.current?.reset();
            setSave({ status: "idle" });
            openCreation();
          }}
        >
          + New supplier
        </button>
      </div>
      <div className="directory-detail-grid">
        <div className="directory-column">
          <section
            aria-labelledby="supplier-directory-title"
            className="identity-directory"
          >
            <h3 id="supplier-directory-title">Supplier directory</h3>
            <div className="field">
              <label htmlFor="supplier-filter">Filter suppliers</label>
              <input
                id="supplier-filter"
                type="search"
                value={filter}
                disabled={
                  directory.status !== "ready" || suppliers.length === 0
                }
                onChange={(event) => {
                  setFilter(event.currentTarget.value);
                }}
              />
            </div>
            {directory.status === "loading" && (
              <p aria-live="polite" className="notice">
                Loading suppliers…
              </p>
            )}
            {directory.status === "error" && (
              <div className="notice notice--error" role="alert">
                <p>Florabase could not load the supplier directory.</p>
                <button
                  type="button"
                  onClick={() => {
                    setDirectory({ status: "loading" });
                    setAttempt((value) => value + 1);
                  }}
                >
                  Retry directory
                </button>
              </div>
            )}
            {directory.status === "ready" && suppliers.length === 0 && (
              <div className="empty-state">
                <p>No suppliers yet.</p>
              </div>
            )}
            {directory.status === "ready" &&
              suppliers.length > 0 &&
              visible.length === 0 && (
                <p className="notice" role="status">
                  No suppliers match this filter.
                </p>
              )}
            {visible.length > 0 && (
              <ul className="identity-list">
                {visible.map((supplier) => (
                  <li key={supplier.id}>
                    <button
                      type="button"
                      className="identity-list-item"
                      aria-pressed={selectedId === supplier.id}
                      onClick={() => {
                        setSelectedId(supplier.id);
                        setSave({ status: "idle" });
                      }}
                    >
                      <span>
                        {supplier.name}{" "}
                        {supplier.retired_at && (
                          <span className="record-state">Retired</span>
                        )}
                      </span>
                      <small>
                        {kindLabels[supplier.kind]}
                        {supplier.email ? ` · ${supplier.email}` : ""}
                      </small>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
          {creationExpanded && (
            <div
              id="new-supplier-panel"
              className="creation-panel"
              ref={creationPanelRef}
            >
              <form
                className="identity-form"
                ref={createForm}
                aria-busy={pending}
                onSubmit={submitCreate}
              >
                <h3>Create a supplier</h3>
                <SupplierFields disabled={pending} />
                <div className="actions">
                  <button type="submit" disabled={pending}>
                    {pending ? "Saving supplier…" : "Create supplier"}
                  </button>
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={pending}
                    onClick={() => {
                      createForm.current?.reset();
                      setSave({ status: "idle" });
                      closeCreation();
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
        <div className="identity-panel" aria-live="polite">
          {selected ? (
            <article
              aria-labelledby="supplier-detail-title"
              className="identity-result"
            >
              <p className="eyebrow">Selected supplier</p>
              <h3 id="supplier-detail-title">{selected.name}</h3>
              {selected.retired_at && (
                <p className="notice notice--duplicate">
                  This supplier is retired.
                </p>
              )}
              <dl>
                <div>
                  <dt>Kind</dt>
                  <dd>{kindLabels[selected.kind]}</dd>
                </div>
                {selected.website && (
                  <div>
                    <dt>Website</dt>
                    <dd>
                      <a
                        href={selected.website}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Visit supplier website
                      </a>
                    </dd>
                  </div>
                )}
                {selected.email && (
                  <div>
                    <dt>Email</dt>
                    <dd>
                      <a href={`mailto:${selected.email}`}>{selected.email}</a>
                    </dd>
                  </div>
                )}
                {selected.phone && (
                  <div>
                    <dt>Phone</dt>
                    <dd>{selected.phone}</dd>
                  </div>
                )}
                {selected.notes && (
                  <div>
                    <dt>Notes</dt>
                    <dd className="preserve-lines">{selected.notes}</dd>
                  </div>
                )}
              </dl>
              <form
                key={`${selected.id}-${selected.updated_at}`}
                onSubmit={submitUpdate}
              >
                <h4>Edit supplier</h4>
                <SupplierFields supplier={selected} disabled={pending} />
                <div className="actions">
                  <button type="submit" disabled={pending}>
                    Save supplier
                  </button>
                  <button
                    className="button--secondary"
                    type="button"
                    disabled={pending}
                    onClick={() =>
                      void apply(
                        () =>
                          setSupplierRetired(
                            selected.id,
                            !selected.retired_at,
                            csrfToken,
                          ),
                        (supplier) =>
                          supplier.retired_at
                            ? `${supplier.name} was retired.`
                            : `${supplier.name} was reactivated.`,
                      )
                    }
                  >
                    {selected.retired_at
                      ? "Reactivate supplier"
                      : "Retire supplier"}
                  </button>
                </div>
              </form>
            </article>
          ) : (
            <div className="empty-state">
              <h3>Select a supplier</h3>
              <p>Choose a record from the directory to view or maintain it.</p>
            </div>
          )}
        </div>
      </div>
      <div aria-live="polite">
        {save.status === "saving" && (
          <p className="notice">Saving the supplier…</p>
        )}
        {save.status === "success" && (
          <p className="notice notice--success">{save.message}</p>
        )}
        {save.status === "validation" && (
          <div
            className="notice notice--error"
            role="alert"
            ref={feedback}
            tabIndex={-1}
          >
            <h3>Check the supplier</h3>
            <ul>
              {save.messages.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          </div>
        )}
        {save.status === "error" && (
          <div
            className="notice notice--error"
            role="alert"
            ref={feedback}
            tabIndex={-1}
          >
            <p>{save.message}</p>
          </div>
        )}
      </div>
    </section>
  );
}
