import {
  GridLayer,
  Util,
  type Coords,
  type DoneCallback,
  type Map as LeafletMap,
} from "leaflet";
import {
  ApiError,
  isExpectedAuthCancellation,
  requestProtectedBlob,
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
  private unsubscribeAuth?: () => void;
  private suspendedByAuth = false;
  private attached = false;
  private removed = false;
  constructor(
    private url: (coords: Coords) => string,
    private report: (status: TileStatus) => void,
    private capability: ProtectedRequestCapability,
  ) {
    super({
      attribution:
        'Occurrence data: <a href="https://www.gbif.org" rel="noreferrer">GBIF.org</a> and contributing publishers',
      maxNativeZoom: 16,
      opacity: 0.82,
    });
    this.suspendedByAuth = !this.capability.isAuthorized();
    this.on("tileunload", (event: { tile: HTMLElement }) => {
      const job = this.jobs.get(event.tile);
      if (job) this.dispose(job);
      this.jobs.delete(event.tile);
      this.notify();
    });
    this.unsubscribeAuth = this.capability.subscribeInvalidation(() => {
      if (this.removed) return;
      if (!this.capability.isAuthorized()) {
        this.suspendedByAuth = true;
        this.cancel(true);
        return;
      }
      if (this.suspendedByAuth) {
        this.suspendedByAuth = false;
        if (this.attached) this.redraw();
      }
    });
  }
  override onAdd(map: LeafletMap): this {
    this.removed = false;
    this.attached = true;
    return super.onAdd(map);
  }
  override onRemove(map: LeafletMap): this {
    this.removed = true;
    this.attached = false;
    this.unsubscribeAuth?.();
    this.unsubscribeAuth = undefined;
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
      job.done(new Error("Occurrence tile suspended"), job.image);
      this.notify();
      return;
    }
    job.state = "pending";
    this.notify();
    try {
      const result = await requestProtectedBlob(this.url(job.coords), {
        capability: this.capability,
        signal: job.controller.signal,
      });
      if (this.cancelled(job) || !this.capability.isAuthorized()) {
        return;
      }
      if (result.status === 204) {
        job.state = "ready";
        job.done(undefined, job.image);
        this.notify();
        return;
      }
      job.objectUrl = URL.createObjectURL(result.blob);
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
    } catch (error: unknown) {
      if (job.controller.signal.aborted) return;
      if (isExpectedAuthCancellation(error)) {
        job.state = "failed";
        job.done(
          error instanceof Error
            ? error
            : new Error("Occurrence tile suspended"),
          job.image,
        );
        this.notify();
        return;
      }
      if (error instanceof ApiError) {
        if (error.status === 401) {
          job.state = "failed";
          job.done(
            new Error("Occurrence tile authentication required"),
            job.image,
          );
          this.notify();
          return;
        }
        if (
          [502, 503, 504].includes(error.status) &&
          job.attempts < 2 &&
          this.capability.isAuthorized()
        ) {
          const retryAfter = Number(error.retryAfter);
          const delay =
            Number.isFinite(retryAfter) && retryAfter > 0
              ? Math.min(retryAfter * 1000, 10000)
              : [500, 1500][job.attempts];
          job.attempts++;
          job.timer = setTimeout(() => {
            if (!this.cancelled(job) && this.capability.isAuthorized()) {
              void this.load(job);
            }
          }, delay);
          return;
        }
        job.state = [404, 409].includes(error.status) ? "missing" : "failed";
        job.done(
          new Error(`Occurrence tile HTTP ${String(error.status)}`),
          job.image,
        );
        this.notify();
        return;
      }
      if (job.attempts < 2 && this.capability.isAuthorized()) {
        job.attempts++;
        job.timer = setTimeout(() => {
          if (!this.cancelled(job) && this.capability.isAuthorized()) {
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
  cancel(notifyPending = false): void {
    for (const job of this.jobs.values()) {
      const wasPending = job.state === "pending";
      this.dispose(job);
      if (notifyPending && wasPending) {
        job.done(new Error("Occurrence tile suspended"), job.image);
      }
    }
    this.jobs.clear();
    this.notify();
  }
}
