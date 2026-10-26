import { OverflowMenu } from "../components/ReferenceUI";
import type { Identity } from "./api";
import type { TaxonomyState } from "./state";
import { identitySubset } from "./facets";
import { IdentityList } from "./IdentityList";

export function TaxonomyKpis({
  identities,
  state,
}: {
  identities: Identity[];
  state: TaxonomyState;
}) {
  return (
    <section
      className="taxonomy-coverage"
      aria-label="Collection representation counts"
    >
      <h4>Collection representation</h4>
      <div className="taxonomy-kpis">
        {(
          [
            ["represented", "Identities"],
            ["living", "Living"],
            ["current", "Current"],
            ["historical", "Historical"],
          ] as const
        ).map(([key, label]) => {
          const rows = identitySubset(identities, key);
          return (
            <OverflowMenu
              key={key}
              label={label}
              ariaLabel={`${label}: ${String(rows.length)}`}
              triggerContent={
                <>
                  <strong>{rows.length}</strong>
                  <span>{label}</span>
                </>
              }
              closeOnAction={false}
              popoverClassName="taxonomy-kpi-popover"
            >
              <h4>
                {label} · {rows.length}{" "}
                {rows.length === 1 ? "identity" : "identities"}
              </h4>
              <p className="field-help">
                Distinct identities under this taxon and the active filters.
                This does not change collection filters.
              </p>
              {rows.length ? (
                <IdentityList
                  key={`${key}:${state.taxon}`}
                  identities={rows}
                  state={state}
                />
              ) : (
                <p>
                  No {label.toLowerCase()} identities under this taxon and the
                  active filters.
                </p>
              )}
            </OverflowMenu>
          );
        })}
      </div>
      <p className="taxonomy-meta">
        Living is included in Current. Historical excludes Current. Counts are
        distinct identities.
      </p>
    </section>
  );
}
