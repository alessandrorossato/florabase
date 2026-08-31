import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { BotanicalProfilePanel } from "../botanical-profiles/BotanicalProfilePanel";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import {
  conflictExistingId,
  createBotanicalIdentity,
  getBotanicalIdentity,
  listBotanicalIdentities,
  validationMessages,
  type BotanicalIdentityCreate,
  type BotanicalIdentityResponse,
} from "./api";

type DirectoryState =
  | { status: "loading" }
  | { status: "ready"; identities: BotanicalIdentityResponse[] }
  | { status: "error" };
type CreateState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "validation"; messages: string[] }
  | { status: "duplicate"; existingId: string | null }
  | { status: "loading-existing"; existingId: string }
  | { status: "error"; message: string }
  | { status: "created"; message: string };

function IdentityDetails({
  identity,
}: {
  identity: BotanicalIdentityResponse;
}) {
  return (
    <div className="identity-detail-stack">
      <article aria-labelledby="identity-title" className="identity-result">
        <p className="eyebrow">Selected botanical identity</p>
        <h3 id="identity-title">{identity.display_label}</h3>
        <dl>
          <div>
            <dt>Scientific name</dt>
            <dd>
              <i>{identity.scientific_name}</i>
            </dd>
          </div>
          {identity.cultivar_name && (
            <div>
              <dt>Cultivar</dt>
              <dd>{identity.cultivar_name}</dd>
            </div>
          )}
          {identity.common_name && (
            <div>
              <dt>Common name</dt>
              <dd>{identity.common_name}</dd>
            </div>
          )}
          <div className="identity-reference">
            <dt>Reference ID</dt>
            <dd>{identity.id}</dd>
          </div>
        </dl>
      </article>
      <BotanicalProfilePanel identityId={identity.id} key={identity.id} />
    </div>
  );
}

export function BotanicalIdentityScreen() {
  const auth = useAuth();
  const [directory, setDirectory] = useState<DirectoryState>({
    status: "loading",
  });
  const [selected, setSelected] = useState<BotanicalIdentityResponse | null>(
    null,
  );
  const [filter, setFilter] = useState("");
  const [createState, setCreateState] = useState<CreateState>({
    status: "idle",
  });
  const [loadAttempt, setLoadAttempt] = useState(0);
  const feedbackRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const {
    expanded: creationExpanded,
    triggerRef: creationTriggerRef,
    panelRef: creationPanelRef,
    open: openCreation,
    close: closeCreation,
    focusFirst: focusCreation,
  } = useCreationDisclosure();
  const pending =
    createState.status === "submitting" ||
    createState.status === "loading-existing";

  useEffect(() => {
    const controller = new AbortController();
    void listBotanicalIdentities(controller.signal)
      .then((identities) => {
        setDirectory({ status: "ready", identities });
        setSelected((current) =>
          current === null
            ? null
            : (identities.find(({ id }) => id === current.id) ?? current),
        );
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
  }, [auth, loadAttempt]);

  useEffect(() => {
    if (["validation", "duplicate", "error"].includes(createState.status)) {
      feedbackRef.current?.focus();
    }
  }, [createState]);

  const filteredIdentities = useMemo(() => {
    if (directory.status !== "ready") return [];
    const query = filter.trim().toLocaleLowerCase();
    if (!query) return directory.identities;
    return directory.identities.filter((identity) =>
      [
        identity.display_label,
        identity.scientific_name,
        identity.cultivar_name,
        identity.common_name,
      ].some((value) => value?.toLocaleLowerCase().includes(query)),
    );
  }, [directory, filter]);

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrfToken = auth.state.csrfToken;

  async function refreshAndSelect(
    identity: BotanicalIdentityResponse,
  ): Promise<void> {
    const identities = await listBotanicalIdentities();
    setDirectory({ status: "ready", identities });
    setSelected(identities.find(({ id }) => id === identity.id) ?? identity);
  }

  async function submit(
    event: SyntheticEvent<HTMLFormElement, SubmitEvent>,
  ): Promise<void> {
    event.preventDefault();
    if (pending) return;
    const form = new FormData(event.currentTarget);
    const scientificName = form.get("scientific_name");
    const cultivarName = form.get("cultivar_name");
    const commonName = form.get("common_name");
    const payload: BotanicalIdentityCreate = {
      scientific_name: typeof scientificName === "string" ? scientificName : "",
      ...(typeof cultivarName === "string" && cultivarName !== ""
        ? { cultivar_name: cultivarName }
        : {}),
      ...(typeof commonName === "string" && commonName !== ""
        ? { common_name: commonName }
        : {}),
    };
    setCreateState({ status: "submitting" });
    try {
      const identity = await createBotanicalIdentity(payload, csrfToken);
      formRef.current?.reset();
      await refreshAndSelect(identity);
      setFilter("");
      setCreateState({
        status: "created",
        message: `${identity.display_label} was created and selected.`,
      });
      closeCreation();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 422) {
        setCreateState({
          status: "validation",
          messages: validationMessages(error),
        });
      } else if (error instanceof ApiError && error.status === 409) {
        setCreateState({
          status: "duplicate",
          existingId: conflictExistingId(error),
        });
      } else if (error instanceof ApiError && error.status === 403) {
        setCreateState({
          status: "error",
          message:
            "Florabase could not authorize this change. Refresh the page and try again.",
        });
      } else {
        setCreateState({
          status: "error",
          message:
            "Florabase could not save or refresh this botanical identity. Check the connection and try again.",
        });
      }
    }
  }

  async function selectExisting(existingId: string): Promise<void> {
    if (pending) return;
    const inDirectory =
      directory.status === "ready"
        ? directory.identities.find(({ id }) => id === existingId)
        : undefined;
    if (inDirectory) {
      setSelected(inDirectory);
      setFilter("");
      setCreateState({ status: "idle" });
      closeCreation();
      return;
    }
    setCreateState({ status: "loading-existing", existingId });
    try {
      const identity = await getBotanicalIdentity(existingId);
      await refreshAndSelect(identity);
      setFilter("");
      setCreateState({ status: "idle" });
      closeCreation();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 404) {
        setCreateState({
          status: "error",
          message:
            "The existing botanical identity could not be found. You can try creating it again.",
        });
      } else {
        setCreateState({
          status: "error",
          message:
            "Florabase could not load the existing botanical identity. Check the connection and try again.",
        });
      }
    }
  }

  return (
    <section aria-labelledby="botanical-identities-title" className="workspace">
      <div className="workspace-intro directory-heading">
        <div>
          <p className="eyebrow">Collection reference</p>
          <h2 id="botanical-identities-title">Botanical identities</h2>
          <p>
            Browse the botanical names used in this collection or add a new one.
          </p>
        </div>
        <button
          type="button"
          ref={creationTriggerRef}
          aria-expanded={creationExpanded}
          aria-controls="new-botanical-identity-panel"
          onClick={() => {
            if (creationExpanded) {
              focusCreation();
              return;
            }
            formRef.current?.reset();
            setCreateState({ status: "idle" });
            openCreation();
          }}
        >
          + New botanical identity
        </button>
      </div>
      <div className="directory-detail-grid">
        <div className="directory-column">
          <section
            aria-labelledby="identity-directory-title"
            className="identity-directory"
          >
            <h3 id="identity-directory-title">Identity directory</h3>
            <div className="field">
              <label htmlFor="identity-filter">
                Filter botanical identities
              </label>
              <input
                id="identity-filter"
                type="search"
                value={filter}
                onChange={(event) => {
                  setFilter(event.currentTarget.value);
                }}
                disabled={
                  directory.status !== "ready" ||
                  directory.identities.length === 0
                }
              />
            </div>
            {directory.status === "loading" && (
              <p aria-live="polite" className="notice">
                Loading botanical identities…
              </p>
            )}
            {directory.status === "error" && (
              <div className="notice notice--error" role="alert">
                <p>
                  Florabase could not load the botanical identity directory.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setDirectory({ status: "loading" });
                    setLoadAttempt((attempt) => attempt + 1);
                  }}
                >
                  Retry directory
                </button>
              </div>
            )}
            {directory.status === "ready" &&
              directory.identities.length === 0 && (
                <div className="empty-state">
                  <p>No botanical identities yet.</p>
                </div>
              )}
            {directory.status === "ready" &&
              directory.identities.length > 0 &&
              filteredIdentities.length === 0 && (
                <p className="notice" role="status">
                  No botanical identities match this filter.
                </p>
              )}
            {filteredIdentities.length > 0 && (
              <ul className="identity-list">
                {filteredIdentities.map((identity) => (
                  <li key={identity.id}>
                    <button
                      type="button"
                      className="identity-list-item"
                      aria-pressed={selected?.id === identity.id}
                      onClick={() => {
                        setSelected(identity);
                      }}
                    >
                      <span>{identity.display_label}</span>
                      {identity.common_name && (
                        <small>{identity.common_name}</small>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {creationExpanded && (
            <div
              id="new-botanical-identity-panel"
              className="creation-panel"
              ref={creationPanelRef}
            >
              <form
                aria-busy={createState.status === "submitting"}
                className="identity-form"
                ref={formRef}
                onSubmit={(event) => void submit(event)}
              >
                <h3>Create a botanical identity</h3>
                <div className="field">
                  <label htmlFor="scientific-name">Scientific name</label>
                  <input
                    id="scientific-name"
                    name="scientific_name"
                    required
                    maxLength={255}
                    disabled={pending}
                  />
                </div>
                <div className="field">
                  <label htmlFor="cultivar-name">Cultivar</label>
                  <input
                    id="cultivar-name"
                    name="cultivar_name"
                    maxLength={120}
                    aria-describedby="cultivar-hint"
                    disabled={pending}
                  />
                  <small id="cultivar-hint">
                    Enter the cultivar without quotation marks.
                  </small>
                </div>
                <div className="field">
                  <label htmlFor="common-name">Common name</label>
                  <input
                    id="common-name"
                    name="common_name"
                    maxLength={160}
                    disabled={pending}
                  />
                </div>
                <div className="actions">
                  <button type="submit" disabled={pending}>
                    {createState.status === "submitting"
                      ? "Creating botanical identity…"
                      : "Create botanical identity"}
                  </button>
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={pending}
                    onClick={() => {
                      formRef.current?.reset();
                      setCreateState({ status: "idle" });
                      closeCreation();
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </form>

              <div aria-live="polite">
                {createState.status === "submitting" && (
                  <p className="notice">Saving the botanical identity…</p>
                )}
                {createState.status === "loading-existing" && (
                  <p className="notice">
                    Loading the existing botanical identity…
                  </p>
                )}
                {createState.status === "created" && (
                  <p className="notice notice--success">
                    {createState.message}
                  </p>
                )}
                {createState.status === "validation" && (
                  <div
                    className="notice notice--error"
                    role="alert"
                    ref={feedbackRef}
                    tabIndex={-1}
                  >
                    <h3>Check the botanical identity</h3>
                    <ul>
                      {createState.messages.map((message) => (
                        <li key={message}>{message}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {createState.status === "duplicate" && (
                  <div
                    className="notice notice--duplicate"
                    role="status"
                    ref={feedbackRef}
                    tabIndex={-1}
                  >
                    <h3>This botanical identity already exists</h3>
                    <p>No duplicate was created.</p>
                    {createState.existingId && (
                      <button
                        type="button"
                        onClick={() => {
                          const existingId = createState.existingId;
                          if (existingId) void selectExisting(existingId);
                        }}
                      >
                        Select existing botanical identity
                      </button>
                    )}
                  </div>
                )}
                {createState.status === "error" && (
                  <div
                    className="notice notice--error"
                    role="alert"
                    ref={feedbackRef}
                    tabIndex={-1}
                  >
                    <p>{createState.message}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="identity-panel" aria-live="polite">
          {selected ? (
            <IdentityDetails identity={selected} />
          ) : (
            <div className="empty-state">
              <h3>Select a botanical identity</h3>
              <p>
                Choose a record from the directory to see its details and
                botanical profile.
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
