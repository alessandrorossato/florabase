import { useEffect, useRef, useState } from "react";
import {
  decimalToDms,
  dmsToDecimal,
  type CoordinateAxis,
  type DmsCoordinate,
} from "./coordinates";

export function CoordinateFields({
  latitude,
  longitude,
  disabled,
  onChange,
}: {
  latitude: string;
  longitude: string;
  disabled: boolean;
  onChange: (latitude: string, longitude: string) => void;
}) {
  const [mode, setMode] = useState<"decimal" | "dms">("decimal");
  const [parts, setParts] = useState({
    latitude: decimalToDms(latitude, "latitude"),
    longitude: decimalToDms(longitude, "longitude"),
  });
  const lat = useRef<HTMLInputElement>(null),
    lon = useRef<HTMLInputElement>(null);
  useEffect(() => {
    lat.current?.setCustomValidity(
      mode === "dms"
        ? (dmsToDecimal(parts.latitude, "latitude").error ?? "")
        : "",
    );
    lon.current?.setCustomValidity(
      mode === "dms"
        ? (dmsToDecimal(parts.longitude, "longitude").error ?? "")
        : "",
    );
  }, [parts, mode]);
  function switchMode(next: "decimal" | "dms") {
    if (next === mode) return;
    if (next === "decimal") {
      const first = dmsToDecimal(parts.latitude, "latitude").error
        ? lat
        : dmsToDecimal(parts.longitude, "longitude").error
          ? lon
          : null;
      if (first) {
        first.current?.reportValidity();
        first.current?.focus();
        return;
      }
    } else
      setParts({
        latitude: decimalToDms(latitude, "latitude"),
        longitude: decimalToDms(longitude, "longitude"),
      });
    setMode(next);
  }
  function update(
    axis: CoordinateAxis,
    key: keyof DmsCoordinate,
    value: string,
  ) {
    const next = { ...parts, [axis]: { ...parts[axis], [key]: value } };
    setParts(next);
    const a = dmsToDecimal(next.latitude, "latitude"),
      b = dmsToDecimal(next.longitude, "longitude");
    if (!a.error && !b.error) onChange(a.value, b.value);
  }
  return (
    <div className="coordinate-editor field--full">
      <fieldset className="coordinate-mode">
        <legend>Coordinate input</legend>
        <label>
          <input
            type="radio"
            name="coordinate-mode"
            checked={mode === "decimal"}
            disabled={disabled}
            onChange={() => {
              switchMode("decimal");
            }}
          />
          Decimal degrees
        </label>
        <label>
          <input
            type="radio"
            name="coordinate-mode"
            checked={mode === "dms"}
            disabled={disabled}
            onChange={() => {
              switchMode("dms");
            }}
          />
          Degrees / minutes / seconds
        </label>
      </fieldset>
      <div className="coordinate-fields">
        {(["latitude", "longitude"] as const).map((axis) => {
          const title = axis === "latitude" ? "Latitude" : "Longitude";
          return mode === "decimal" ? (
            <div className="field" key={axis}>
              <label htmlFor={`site-${axis}`}>{title} (WGS84 decimal)</label>
              <input
                id={`site-${axis}`}
                type="number"
                step="any"
                min={axis === "latitude" ? -90 : -180}
                max={axis === "latitude" ? 90 : 180}
                disabled={disabled}
                value={axis === "latitude" ? latitude : longitude}
                onChange={(event) => {
                  onChange(
                    axis === "latitude" ? event.currentTarget.value : latitude,
                    axis === "longitude"
                      ? event.currentTarget.value
                      : longitude,
                  );
                }}
              />
            </div>
          ) : (
            <fieldset className="dms-coordinate" key={axis}>
              <legend>{title}</legend>
              <div className="dms-parts">
                {(["degrees", "minutes", "seconds"] as const).map((key) => (
                  <div className="field" key={key}>
                    <label htmlFor={`site-${axis}-${key}`}>
                      {key[0].toUpperCase() + key.slice(1)}
                    </label>
                    <input
                      id={`site-${axis}-${key}`}
                      ref={
                        key === "degrees"
                          ? axis === "latitude"
                            ? lat
                            : lon
                          : undefined
                      }
                      aria-describedby={`site-${axis}-dms-help`}
                      type="number"
                      min={0}
                      max={
                        key === "degrees"
                          ? axis === "latitude"
                            ? 90
                            : 180
                          : key === "minutes"
                            ? 59
                            : undefined
                      }
                      step={key === "seconds" ? "any" : "1"}
                      disabled={disabled}
                      value={parts[axis][key]}
                      onChange={(event) => {
                        update(axis, key, event.currentTarget.value);
                      }}
                    />
                  </div>
                ))}
                <div className="field">
                  <label htmlFor={`site-${axis}-direction`}>Hemisphere</label>
                  <select
                    id={`site-${axis}-direction`}
                    disabled={disabled}
                    value={parts[axis].direction}
                    onChange={(event) => {
                      update(axis, "direction", event.currentTarget.value);
                    }}
                  >
                    {(axis === "latitude" ? ["N", "S"] : ["E", "W"]).map(
                      (value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ),
                    )}
                  </select>
                </div>
              </div>
              <p className="field-help" id={`site-${axis}-dms-help`}>
                {dmsToDecimal(parts[axis], axis).error ??
                  "Minutes 0–59; seconds 0 to less than 60. Stored as WGS84 decimal degrees."}
              </p>
            </fieldset>
          );
        })}
      </div>
    </div>
  );
}
