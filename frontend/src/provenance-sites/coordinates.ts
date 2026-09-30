export interface DmsCoordinate {
  degrees: string;
  minutes: string;
  seconds: string;
  direction: "N" | "S" | "E" | "W";
}
export type CoordinateAxis = "latitude" | "longitude";
export function decimalToDms(
  value: string,
  axis: CoordinateAxis,
): DmsCoordinate {
  const negative = Number(value) < 0 || value.trim().startsWith("-");
  const direction =
    axis === "latitude" ? (negative ? "S" : "N") : negative ? "W" : "E";
  if (!value.trim())
    return { degrees: "", minutes: "", seconds: "", direction };
  // Rounding at nine fractional seconds is below ordinary decimal-coordinate precision.
  const totalSeconds = Math.round(Math.abs(Number(value)) * 3600 * 1e9) / 1e9;
  const degrees = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds - degrees * 3600) / 60);
  const seconds =
    Math.round((totalSeconds - degrees * 3600 - minutes * 60) * 1e9) / 1e9;
  return {
    degrees: String(degrees),
    minutes: String(minutes),
    seconds: String(seconds),
    direction,
  };
}
export function dmsToDecimal(
  parts: DmsCoordinate,
  axis: CoordinateAxis,
): { value: string; error?: string } {
  const name = axis === "latitude" ? "Latitude" : "Longitude";
  if (
    ![parts.degrees, parts.minutes, parts.seconds].some((value) => value.trim())
  )
    return { value: "" };
  const degrees = Number(parts.degrees);
  const minutes = Number(parts.minutes || "0");
  const seconds = Number(parts.seconds || "0");
  const max = axis === "latitude" ? 90 : 180;
  if (
    !parts.degrees.trim() ||
    !Number.isInteger(degrees) ||
    degrees < 0 ||
    degrees > max
  )
    return {
      value: "",
      error: `${name} degrees must be a whole number from 0 to ${String(max)}.`,
    };
  if (!Number.isInteger(minutes) || minutes < 0 || minutes > 59)
    return {
      value: "",
      error: `${name} minutes must be a whole number from 0 to 59.`,
    };
  if (!Number.isFinite(seconds) || seconds < 0 || seconds >= 60)
    return {
      value: "",
      error: `${name} seconds must be at least 0 and less than 60.`,
    };
  if (degrees === max && (minutes !== 0 || seconds !== 0))
    return {
      value: "",
      error: `${name} at ${String(max)} degrees requires zero minutes and seconds.`,
    };
  const allowed = axis === "latitude" ? ["N", "S"] : ["E", "W"];
  if (!allowed.includes(parts.direction))
    return { value: "", error: `Choose a ${name.toLowerCase()} hemisphere.` };
  const sign = parts.direction === "S" || parts.direction === "W" ? -1 : 1;
  return { value: String(sign * (degrees + minutes / 60 + seconds / 3600)) };
}
