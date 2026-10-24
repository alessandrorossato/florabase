import { useEffect, useState, type MouseEvent } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  getIdentityCollection,
  type BotanicalIdentityCollectionResponse,
} from "../collection/api";
import { TaskDialog } from "../components/TaskDialog";
import { openCollectionPage } from "../components/recordNavigation";

/** Source choices use the same eligibility as the existing Sowing and Harvest forms. */
export function IdentitySourceAction({
  identityId,
  kind,
  dialogOnly = false,
  onDismiss,
}: {
  identityId: string;
  kind: "sowing" | "harvest";
  dialogOnly?: boolean;
  onDismiss?: () => void;
}) {
  const auth = useAuth();
  const [open, setOpen] = useState(dialogOnly);
  const [attempt, setAttempt] = useState(0);
  const [load, setLoad] = useState<
    | { status: "loading" | "error" }
    | { status: "ready"; value: BotanicalIdentityCollectionResponse }
  >({ status: "loading" });
  const title = kind === "sowing" ? "Start sowing" : "Record harvest";
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    void getIdentityCollection(identityId, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setLoad({ status: "ready", value });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setLoad({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [auth, identityId, open, attempt]);
  const choices =
    load.status !== "ready"
      ? []
      : kind === "sowing"
        ? load.value.seed_lots
            .filter((lot) => lot.lifecycle === "active")
            .map((lot) => ({
              id: lot.id,
              label: lot.label ?? "Unlabelled seed lot",
              context: `Active seed lot · ${lot.location?.display_path ?? "Location not recorded"} · ${lot.id.slice(-8)}`,
              href: `#/sowings?action=start&seedLot=${lot.id}`,
            }))
        : [
            ...load.value.plants.map((plant) => ({
              ...plant,
              type: "plant" as const,
            })),
            ...load.value.plant_groups.map((group) => ({
              ...group,
              type: "plant_group" as const,
            })),
          ].map((source) => ({
            id: source.id,
            label: source.label ?? source.botanical_identity.display_label,
            context: `${source.type === "plant" ? "Plant" : "Plant group"} · ${source.lifecycle} · ${source.location?.display_path ?? "Location not recorded"} · ${source.id.slice(-8)}`,
            href: `#/harvests?action=create&sourceType=${source.type}&source=${source.id}`,
          }));
  function launch(event: MouseEvent<HTMLAnchorElement>, href: string) {
    if (
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.altKey ||
      event.shiftKey
    )
      return;
    event.preventDefault();
    setOpen(false);
    onDismiss?.();
    openCollectionPage(href, window.location.hash);
  }
  return (
    <>
      {!dialogOnly && (
        <button
          type="button"
          className="button--secondary"
          onClick={() => {
            setLoad({ status: "loading" });
            setOpen(true);
          }}
        >
          {title}
        </button>
      )}
      {open && (
        <TaskDialog
          title={title}
          onClose={() => {
            setOpen(false);
            onDismiss?.();
          }}
        >
          <h3>{title}</h3>
          <p>
            {kind === "sowing"
              ? "Choose an active seed lot to preserve the sowing’s source and provenance."
              : "Choose the Plant or Plant group that produced this harvest. Historical and inactive sources remain available."}
          </p>
          {load.status === "loading" && (
            <p role="status">Loading eligible sources…</p>
          )}
          {load.status === "error" && (
            <div role="alert">
              <p>Florabase could not load source records.</p>
              <button
                type="button"
                onClick={() => {
                  setLoad({ status: "loading" });
                  setAttempt((n) => n + 1);
                }}
              >
                Retry sources
              </button>
            </div>
          )}
          {load.status === "ready" &&
            (choices.length ? (
              <ul className="identity-source-choices">
                {choices.map((choice) => (
                  <li key={choice.id}>
                    <a
                      href={choice.href}
                      onClick={(event) => {
                        launch(event, choice.href);
                      }}
                    >
                      {choice.label}
                    </a>
                    <small>{choice.context}</small>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="detail-empty-message">
                <p>
                  {kind === "sowing"
                    ? "No active seed lots are recorded for this identity. Create a seed lot before starting a sowing."
                    : "No Plants or Plant groups are recorded for this identity. Add the actual source before recording a harvest."}
                </p>
                <a
                  className="button-link button--secondary"
                  href={
                    kind === "sowing"
                      ? `#/seeds?action=create&identity=${identityId}`
                      : `#/plants?action=create&identity=${identityId}&kind=plant`
                  }
                  onClick={(event) => {
                    launch(event, event.currentTarget.hash);
                  }}
                >
                  {kind === "sowing" ? "Create seed lot" : "Add source plant"}
                </a>
                {kind === "harvest" && (
                  <a
                    href={`#/plants?action=create&identity=${identityId}&kind=group`}
                    onClick={(event) => {
                      launch(event, event.currentTarget.hash);
                    }}
                  >
                    Add source plant group
                  </a>
                )}
              </div>
            ))}
          <div className="form-actions">
            <button
              type="button"
              className="button--secondary"
              onClick={() => {
                setOpen(false);
                onDismiss?.();
              }}
            >
              Cancel
            </button>
          </div>
        </TaskDialog>
      )}
    </>
  );
}
