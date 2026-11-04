import {
  useEffect,
  useId,
  useRef,
  useState,
  type MouseEvent,
  type RefObject,
  type SyntheticEvent,
} from "react";

import { Icon } from "../components/Icon";
import { TaskDialog } from "../components/TaskDialog";
import { entryHref } from "../events/entryRequest";
import { requestJson } from "../auth/api";
import { searchKindLabels, type SearchResponse } from "../collection/searchApi";
import { labelRoute } from "./labelRoute";
import { recordContext } from "./recordContext";

// Recording workflows that already have their own routes (as in the Journal's Record menu).
const workflows = [
  {
    label: "Record harvest",
    href: "#/harvests?action=create",
    icon: "harvest",
  },
  { label: "Record sowing", href: "#/sowings?action=create", icon: "sprout" },
  { label: "Complete scheduled work", href: "#/schedule", icon: "calendar" },
] as const;

type Hit = SearchResponse["groups"][number]["items"][number];
const recordKinds = ["plant", "plant_group", "sowing"] as const;

/** A Sowing opens its germination form; a Plant or Plant group its Journal entry form. */
function hitHref(hit: Hit) {
  return hit.kind === "sowing"
    ? entryHref(`#/sowings/${hit.id}?tab=germination`)
    : entryHref(
        `#/${hit.kind === "plant" ? "plants" : "plant-groups"}/${hit.id}?tab=events`,
      );
}

/** The existing global search, limited to the record kinds that have entry forms. */
function useRecordSearch(query: string) {
  const trimmed = query.trim();
  const [answer, setAnswer] = useState<{
    query: string;
    hits: Hit[] | null;
  } | null>(null);
  useEffect(() => {
    if (trimmed.length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ q: trimmed, limit: "8" });
      for (const kind of recordKinds) params.append("kind", kind);
      requestJson<SearchResponse>(`/api/v1/search?${params.toString()}`, {
        signal: controller.signal,
      })
        .then((response) => {
          setAnswer({
            query: trimmed,
            hits: response.groups
              .flatMap((group) => group.items)
              .filter((hit) =>
                (recordKinds as readonly string[]).includes(hit.kind),
              ),
          });
        })
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === "AbortError")
            return;
          setAnswer({ query: trimmed, hits: null });
        });
    }, 200);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [trimmed]);
  const current = answer?.query === trimmed ? answer : null;
  if (trimmed.length < 2)
    return { hits: [], message: "Type at least two characters." };
  if (!current) return { hits: [], message: "Searching…" };
  if (!current.hits)
    return {
      hits: [],
      message: "Search is unavailable. Open the record from Plants or Sowings.",
    };
  return {
    hits: current.hits,
    message: current.hits.length
      ? `${String(current.hits.length)} matching ${current.hits.length === 1 ? "record" : "records"}`
      : `No Plant, Plant group or Sowing matches “${trimmed}”.`,
  };
}

interface Detector {
  detect: (source: HTMLVideoElement) => Promise<{ rawValue: string }[]>;
}
type DetectorConstructor = new (options: { formats: string[] }) => Detector;
function detectorClass(): DetectorConstructor | null {
  const candidate = (window as { BarcodeDetector?: DetectorConstructor })
    .BarcodeDetector;
  // Undefined outside secure contexts (for example a plain-HTTP LAN address).
  const media = (navigator as { mediaDevices?: MediaDevices }).mediaDevices;
  return candidate && typeof media?.getUserMedia === "function"
    ? candidate
    : null;
}

/**
 * Reads a label QR code with the browser's own BarcodeDetector and camera. Offered only where
 * both exist (no library, no upload, nothing leaves the device); elsewhere the phone camera
 * opens label links directly, and a USB scanner types into the label field.
 */
function CameraScan({ onRoute }: { onRoute: (route: string) => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const [state, setState] = useState<
    "idle" | "starting" | "scanning" | "denied" | "unrecognised"
  >("idle");
  const stream = useRef<MediaStream | null>(null);
  useEffect(
    () => () => {
      stream.current?.getTracks().forEach((track) => {
        track.stop();
      });
    },
    [],
  );
  const Detector = detectorClass();
  if (!Detector) return null;
  async function start() {
    if (!Detector) return;
    setState("starting");
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
    } catch {
      setState("denied");
      return;
    }
    const element = video.current;
    if (!element) return;
    element.srcObject = stream.current;
    await element.play().catch(() => undefined);
    setState("scanning");
    const detector = new Detector({ formats: ["qr_code"] });
    const tick = async () => {
      if (!stream.current?.active) return;
      const codes = await detector.detect(element).catch(() => []);
      for (const code of codes) {
        const route = labelRoute(code.rawValue);
        if (route) {
          stream.current.getTracks().forEach((track) => {
            track.stop();
          });
          onRoute(route);
          return;
        }
        setState("unrecognised");
      }
      window.setTimeout(() => void tick(), 250);
    };
    void tick();
  }
  return (
    <div className="wb-scan">
      <video
        ref={video}
        className="wb-scan__video"
        hidden={state !== "scanning" && state !== "unrecognised"}
        muted
        playsInline
        aria-label="Camera preview"
      />
      {state === "idle" || state === "denied" ? (
        <button
          type="button"
          className="button--secondary"
          onClick={() => void start()}
        >
          <Icon name="tag" />
          Scan with camera
        </button>
      ) : null}
      <p className="field-help" role="status">
        {state === "starting"
          ? "Starting the camera…"
          : state === "scanning"
            ? "Point the camera at a Florabase label."
            : state === "unrecognised"
              ? "That code is not a Florabase label. Try another label."
              : state === "denied"
                ? "The camera is unavailable or permission was declined."
                : ""}
      </p>
    </div>
  );
}

export function RecordSheet({
  hash,
  follow,
  onNavigate,
  onClose,
  returnFocusTo,
}: {
  hash: string;
  follow: (event: MouseEvent<HTMLAnchorElement>, href: string) => void;
  onNavigate: (href: string) => void;
  onClose: () => void;
  returnFocusTo?: RefObject<HTMLElement | null>;
}) {
  const context = recordContext(hash);
  const [query, setQuery] = useState("");
  const search = useRecordSearch(query);
  const [label, setLabel] = useState("");
  const [labelError, setLabelError] = useState(false);
  const labelId = useId();
  function openLabel(route: string) {
    onClose();
    onNavigate(route);
  }
  function submitLabel(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    const route = labelRoute(label);
    if (route) openLabel(route);
    else setLabelError(true);
  }
  return (
    <TaskDialog
      title="Record"
      className="wb-sheet wb-record"
      onClose={onClose}
      dismissOnBackdrop
      returnFocusTo={returnFocusTo}
    >
      <div className="wb-sheet__header">
        <h2>Record</h2>
        <button type="button" className="button--secondary" onClick={onClose}>
          Close
        </button>
      </div>

      {context && (
        <nav className="wb-record__group" aria-label={`This ${context.noun}`}>
          <p className="wb-record__title" aria-hidden="true">
            This {context.noun}
          </p>
          {context.actions.map((action) => (
            <a
              key={action.href}
              href={action.href}
              className="wb-record__action"
              onClick={(event) => {
                follow(event, action.href);
                onClose();
              }}
            >
              <Icon name={action.icon} />
              {action.label}
            </a>
          ))}
        </nav>
      )}

      <section className="wb-record__group" aria-labelledby={`${labelId}-pick`}>
        <h3 id={`${labelId}-pick`} className="wb-record__title">
          Another record
        </h3>
        <label className="field">
          Find a Plant, Plant group or Sowing
          <input
            type="search"
            value={query}
            autoComplete="off"
            aria-describedby={`${labelId}-pick-status`}
            onChange={(event) => {
              setQuery(event.target.value);
            }}
          />
        </label>
        <p id={`${labelId}-pick-status`} className="field-help" role="status">
          {search.message}
        </p>
        {search.hits.length > 0 && (
          <ul className="wb-record__results" aria-label="Matching records">
            {search.hits.map((hit) => {
              const href = hitHref(hit);
              return (
                <li key={`${hit.kind}:${hit.id}`}>
                  <a
                    href={href}
                    className="wb-record__action"
                    onClick={(event) => {
                      follow(event, href);
                      onClose();
                    }}
                  >
                    <span>
                      {hit.title}
                      <span className="wb-record__hint">
                        {searchKindLabels[hit.kind]} ·{" "}
                        {hit.kind === "sowing"
                          ? "germination observation"
                          : "Journal entry"}
                      </span>
                    </span>
                  </a>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="wb-record__group" aria-labelledby={`${labelId}-qr`}>
        <h3 id={`${labelId}-qr`} className="wb-record__title">
          Open a label
        </h3>
        <form className="wb-record__label" onSubmit={submitLabel} noValidate>
          <label className="field">
            Label link
            <input
              value={label}
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              aria-invalid={labelError || undefined}
              aria-describedby={labelError ? `${labelId}-error` : undefined}
              onChange={(event) => {
                setLabel(event.target.value);
                setLabelError(false);
              }}
            />
          </label>
          <button type="submit" className="button--secondary">
            Open
          </button>
        </form>
        {labelError && (
          <p id={`${labelId}-error`} className="field-error" role="alert">
            Not a Florabase label link. Labels open a Seed lot, Plant, Plant
            group or stored material.
          </p>
        )}
        <CameraScan onRoute={openLabel} />
      </section>

      <nav className="wb-record__group" aria-label="Other recording">
        <p className="wb-record__title" aria-hidden="true">
          Other recording
        </p>
        {workflows.map((workflow) => (
          <a
            key={workflow.href}
            href={workflow.href}
            className="wb-record__action"
            onClick={(event) => {
              follow(event, workflow.href);
              onClose();
            }}
          >
            <Icon name={workflow.icon} />
            {workflow.label}
          </a>
        ))}
      </nav>
    </TaskDialog>
  );
}
