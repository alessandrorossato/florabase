import {
  GridLayer,
  Util,
  type Coords,
  type DoneCallback,
  type Map as LeafletMap,
} from "leaflet";
import {
  acquireProtectedRequestCapability,
  type ProtectedRequestCapability,
} from "../auth/api";

export const EMPTY_TILE = Util.emptyImageUrl;
export interface TileStatus {
  failed: number;
  missing: number;
  pending: number;
}
interface Job {
  image: HTMLImageElement;
  coords: Coords;
  done: DoneCallback;
  controller: AbortController;
  attempts: number;
  state: "pending" | "ready" | "failed" | "missing";
  timer?: ReturnType<typeof setTimeout>;
  objectUrl?: string;
}
/** Only explicit provider-enabled URLs may fill a cache miss; cache playback never falls back. */
export class EvidenceTiles extends GridLayer {
  private jobs = new Map<HTMLElement, Job>();
  private capability: ProtectedRequestCapability;
  private unsubscribeAuth?: () => void;
  private suspendedByAuth = false;
  private attached = false;
  constructor(
    private url: (coords: Coords) => string,
    private report: (status: TileStatus) => void,
  ) {
    super({
      attribution:
        'Occurrence data: <a href="https://www.gbif.org" rel="noreferrer">GBIF.org</a> and contributing publishers',
      maxNativeZoom: 16,
      opacity: 0.82,
    });
    this.capability = acquireProtectedRequestCapability();
    this.suspendedByAuth =
      !this.capability.isRevoked() && !this.capability.isAuthorized();
    this.on("tileunload", (event: { tile: HTMLElement }) => {
      const job = this.jobs.get(event.tile);
      if (job) this.dispose(job);
      this.jobs.delete(event.tile);
      this.notify();
    });
    this.unsubscribeAuth = this.capability.subscribeInvalidation(() => {
      if (this.capability.isRevoked()) {
        this.suspendedByAuth = false;
        const unsub = this.unsubscribeAuth;
        this.unsubscribeAuth = undefined;
        unsub?.();
        this.cancel();
        return;
      }
      if (!this.capability.isAuthorized()) {
        this.suspendedByAuth = true;
        this.cancel();
        return;
      }
      if (this.suspendedByAuth) {
        this.suspendedByAuth = false;
        if (this.attached) this.redraw();
      }
    });
  }
  override onAdd(map: LeafletMap): this {
    this.attached = !this.capability.isRevoked();
    return super.onAdd(map);
  }
  override onRemove(map: LeafletMap): this {
    this.attached = false;
    this.unsubscribeAuth?.();
    this.unsubscribeAuth = undefined;
    this.capability.revoke();
    this.cancel();
    return super.onRemove(map);
  }
  private notify() {
    const jobs = [...this.jobs.values()];
    this.report({
      failed: jobs.filter((j) => j.state === "failed").length,
      missing: jobs.filter((j) => j.state === "missing").length,
      pending: jobs.filter((j) => j.state === "pending").length,
    });
  }
  override createTile(coords: Coords, done: DoneCallback): HTMLElement {
    const image = document.createElement("img");
    image.alt = "";
    image.src = EMPTY_TILE;
    const job: Job = {
      image,
      coords,
      done,
      controller: new AbortController(),
      attempts: 0,
      state: "pending",
    };
    this.jobs.set(image, job);
    void this.load(job);
    return image;
  }
  private cancelled(job: Job): boolean {
    return job.controller.signal.aborted;
  }
  private async load(job: Job): Promise<void> {
    if (!this.capability.isAuthorized() || this.cancelled(job)) {
      job.state = "failed";
      job.done(
        new Error(
          this.capability.isRevoked()
            ? "Occurrence tile capability revoked"
            : "Occurrence tile suspended",
        ),
        job.image,
      );
      this.notify();
      return;
    }
    const originatingEpoch = this.capability.getEpoch();
    job.state = "pending";
    this.notify();
    try {
      const response = await fetch(this.url(job.coords), {
        credentials: "same-origin",
        signal: job.controller.signal,
      });
      if (
        this.cancelled(job) ||
        !this.capability.isAuthorized() ||
        originatingEpoch !== this.capability.getEpoch()
      ) {
        return;
      }
      if (response.status === 401) {
        job.state = "failed";
        this.capability.notifyUnauthorized(originatingEpoch);
        job.done(
          new Error("Occurrence tile authentication required"),
          job.image,
        );
        this.notify();
        return;
      }
      if (response.status === 204) {
        job.state = "ready";
        job.done(undefined, job.image);
        this.notify();
        return;
      }
      if (!response.ok) {
        if (
          [502, 503, 504].includes(response.status) &&
          job.attempts < 2 &&
          this.capability.isAuthorized() &&
          originatingEpoch === this.capability.getEpoch()
        ) {
          const retryAfter = Number(response.headers.get("Retry-After"));
          const delay =
            Number.isFinite(retryAfter) && retryAfter > 0
              ? Math.min(retryAfter * 1000, 10000)
              : [500, 1500][job.attempts];
          job.attempts++;
          job.timer = setTimeout(() => {
            if (
              !this.cancelled(job) &&
              this.capability.isAuthorized() &&
              originatingEpoch === this.capability.getEpoch()
            ) {
              void this.load(job);
            }
          }, delay);
          return;
        }
        job.state = [404, 409].includes(response.status) ? "missing" : "failed";
        job.done(
          new Error(`Occurrence tile HTTP ${String(response.status)}`),
          job.image,
        );
        this.notify();
        return;
      }
      const blob = await response.blob();
      if (
        this.cancelled(job) ||
        !this.capability.isAuthorized() ||
        originatingEpoch !== this.capability.getEpoch()
      ) {
        return;
      }
      job.objectUrl = URL.createObjectURL(blob);
      job.image.onload = () => {
        if (!job.controller.signal.aborted) {
          job.state = "ready";
          job.done(undefined, job.image);
          this.notify();
        }
      };
      job.image.onerror = () => {
        if (!job.controller.signal.aborted) {
          job.state = "failed";
          job.done(new Error("Invalid tile image"), job.image);
          this.notify();
        }
      };
      job.image.src = job.objectUrl;
    } catch {
      if (job.controller.signal.aborted) return;
      if (
        job.attempts < 2 &&
        this.capability.isAuthorized() &&
        originatingEpoch === this.capability.getEpoch()
      ) {
        job.attempts++;
        job.timer = setTimeout(() => {
          if (
            !this.cancelled(job) &&
            this.capability.isAuthorized() &&
            originatingEpoch === this.capability.getEpoch()
          ) {
            void this.load(job);
          }
        }, job.attempts * 1000);
      } else {
        job.state = "failed";
        job.done(new Error("Occurrence tile unavailable"), job.image);
        this.notify();
      }
    }
  }
  retryFailed(): void {
    if (!this.capability.isAuthorized()) return;
    for (const job of this.jobs.values())
      if (job.state === "failed" || job.state === "missing") {
        job.controller.abort();
        if (job.timer) clearTimeout(job.timer);
        if (job.objectUrl) URL.revokeObjectURL(job.objectUrl);
        job.controller = new AbortController();
        job.attempts = 0;
        void this.load(job);
      }
  }
  private dispose(job: Job) {
    job.controller.abort();
    if (job.timer) clearTimeout(job.timer);
    if (job.objectUrl) URL.revokeObjectURL(job.objectUrl);
    job.image.onload = null;
    job.image.onerror = null;
  }
  cancel(): void {
    for (const job of this.jobs.values()) this.dispose(job);
    this.jobs.clear();
    this.notify();
  }
}
