import { useEffect, useState } from "react";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { listTargets, type Target, type TargetPage } from "./api";
import type { TargetKind } from "./state";
export function ScheduleTargetPicker({
  kind,
  value,
  selected,
  onChange,
}: {
  kind: TargetKind;
  value: string;
  selected: Target | null;
  onChange: (id: string) => void;
}) {
  const auth = useAuth();
  const [remembered, setRemembered] = useState<Target | null>(selected);
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    page: TargetPage | null;
    error: boolean;
  } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const key = JSON.stringify([kind, q, offset, attempt]);
  const current = result?.key === key ? result : null;
  const page = current?.page;
  const error = current?.error ?? false;
  useEffect(() => {
    const c = new AbortController();
    void listTargets(kind, q, offset, c.signal)
      .then((p) => {
        if (!c.signal.aborted) setResult({ key, page: p, error: false });
      })
      .catch((e: unknown) => {
        if (c.signal.aborted) return;
        if (e instanceof ApiError && e.status === 401) auth.sessionExpired();
        else setResult({ key, page: null, error: true });
      });
    return () => {
      c.abort();
    };
  }, [kind, q, offset, key, auth]);
  const choices = page?.items ?? [];
  const retained =
    remembered?.id === value
      ? remembered
      : selected?.id === value
        ? selected
        : null;
  const all =
    retained && !choices.some((c) => c.id === retained.id)
      ? [retained, ...choices]
      : choices;
  return (
    <div className="schedule-target-picker">
      <label className="field">
        Find collection record
        <input
          type="search"
          value={q}
          maxLength={200}
          onChange={(e) => {
            setQ(e.target.value);
            setOffset(0);
          }}
        />
      </label>
      {error ? (
        <p role="alert">
          Could not load collection records.{" "}
          <button
            type="button"
            onClick={() => {
              setAttempt((a) => a + 1);
            }}
          >
            Retry records
          </button>
        </p>
      ) : page ? (
        <>
          <ReferencePicker
            label="Target record"
            choices={all.map((c) => ({
              id: c.id,
              label: c.label,
              retired: c.lifecycle !== null && c.lifecycle !== "active",
              ...(c.lifecycle ? { inactiveLabel: c.lifecycle } : {}),
            }))}
            value={value}
            onChange={(id) => {
              setRemembered(all.find((c) => c.id === id) ?? null);
              onChange(id);
            }}
            required
          />
          <div className="button-row">
            <button
              type="button"
              disabled={!offset}
              onClick={() => {
                setOffset((o) => Math.max(0, o - 50));
              }}
            >
              Previous records
            </button>
            <span>{page.total} matching records</span>
            <button
              type="button"
              disabled={offset + 50 >= page.total}
              onClick={() => {
                setOffset((o) => o + 50);
              }}
            >
              Next records
            </button>
          </div>
        </>
      ) : (
        <p role="status">Loading collection records…</p>
      )}
    </div>
  );
}
