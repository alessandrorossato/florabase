import type { Target } from "./api";

/** Exact scientific fields, never guess name/cultivar boundaries from an operator label. */
export function ScheduleTargetLabel({ target }: { target: Target }) {
  return target.kind === "botanical_identity" && target.scientific_name ? (
    <>
      <i className="scientific-name">{target.scientific_name}</i>
      {target.cultivar_name ? ` ‘${target.cultivar_name}’` : ""}
    </>
  ) : (
    <>{target.label}</>
  );
}
