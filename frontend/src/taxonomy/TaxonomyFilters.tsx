import { DirectoryFilterSelect } from "../components/DirectoryTools";
import { ActionButton } from "../components/Action";
import { recordCategories } from "../saved-views/state";
import { ancestry, graphIndex } from "./graph";
import type { Tree } from "./api";
import { scopes, recordLabels, type TaxonomyState } from "./state";

export function TaxonomyFilters({
  data,
  state,
  update,
}: {
  data?: Tree;
  state: TaxonomyState;
  update: (s: TaxonomyState) => void;
}) {
  const index = graphIndex(data?.nodes ?? []),
    path = ancestry(index, state.branch ?? "");
  const at = (rank: string) =>
    path.find((id) => index.nodes.get(id)?.taxon.rank === rank) ?? "";
  return (
    <>
      <DirectoryFilterSelect
        label="Collection representation"
        value={state.scope}
        options={scopes}
        onChange={(scope) => {
          update({ ...state, scope });
        }}
      />
      <p className="field-help">
        Living means active Plants or Plant groups and is included in Current.
        Historical means retained records with no Current evidence anywhere.
      </p>
      <fieldset className="taxonomy-filter-categories">
        <legend>Collection record types</legend>
        <p className="field-help">
          Selections use OR. None selected means all categories. Living + Seeds
          returns no identities.
        </p>
        {recordCategories.map((category) => (
          <label key={category}>
            <input
              type="checkbox"
              checked={state.record.includes(category)}
              onChange={(event) => {
                update({
                  ...state,
                  record: event.target.checked
                    ? [...state.record, category]
                    : state.record.filter((item) => item !== category),
                });
              }}
            />
            {recordLabels[category]}
          </label>
        ))}
      </fieldset>
      <fieldset>
        <legend>Taxonomic hierarchy</legend>
        {(
          [
            ["family", "Family"],
            ["genus", "Genus"],
            ["species", "Species"],
          ] as const
        ).map(([rank, label]) => {
          const parent =
            rank === "species"
              ? at("genus") || at("family")
              : rank === "genus"
                ? at("family")
                : "";
          const options = (data?.nodes ?? []).filter(
            (n) =>
              n.taxon.rank === rank &&
              (!parent ||
                ancestry(index, n.taxon.source_taxon_id).includes(parent)),
          );
          return (
            <DirectoryFilterSelect
              key={rank}
              label={label}
              value={at(rank)}
              options={[
                {
                  value: "",
                  label: `All represented ${rank === "family" ? "families" : rank === "genus" ? "genera" : "species"}`,
                },
                ...options.map((n) => ({
                  value: n.taxon.source_taxon_id,
                  label: n.taxon.scientific_name,
                })),
              ]}
              onChange={(id) => {
                update({
                  ...state,
                  branch: id || parent || undefined,
                  taxon: id || parent || state.taxon,
                  panel: undefined,
                  identity: undefined,
                });
              }}
            />
          );
        })}
        {state.branch && !index.nodes.has(state.branch) && (
          <p role="status">
            Focused branch is no longer eligible. Clear hierarchy focus to show
            available branches.
          </p>
        )}
        <p className="field-help">
          Source-backed branch focus applies to List and Tree. Selecting a
          parent clears downstream selections. It does not change collection
          eligibility or the selected taxon's counts.
        </p>
        {state.branch && (
          <ActionButton
            variant="quiet"
            onClick={() => {
              update({ ...state, branch: undefined });
            }}
          >
            Clear hierarchy focus
          </ActionButton>
        )}
      </fieldset>
      <fieldset>
        <legend>Taxonomic status</legend>
        <DirectoryFilterSelect
          label="Source placement"
          value={state.status ?? "all"}
          options={[
            { value: "all", label: "All identities" },
            { value: "accepted", label: "Accepted placement" },
            { value: "synonym", label: "Linked synonym placement" },
            { value: "unlinked", label: "Needs review / unlinked" },
          ]}
          onChange={(status) => {
            update({
              ...state,
              status: status === "all" ? undefined : status,
              panel: status === "unlinked" ? "unresolved" : undefined,
              identity: undefined,
            });
          }}
        />
        <p className="field-help">
          Only confirmed source evidence qualifies. Synonyms retain their local
          name and accepted placement; unresolved identities have no inferred
          branch. An absent source cannot validate saved placements.
        </p>
      </fieldset>
      <fieldset>
        <legend>Media availability</legend>
        <DirectoryFilterSelect
          label="Stored cover thumbnail"
          value={state.media ?? "all"}
          options={[
            { value: "all", label: "All identities" },
            { value: "with", label: "With stored cover thumbnail" },
            { value: "without", label: "Without stored cover thumbnail" },
          ]}
          onChange={(media) => {
            update({
              ...state,
              media: media === "all" ? undefined : media,
            });
          }}
        />
        <p className="field-help">
          Filters eligible identities and their represented branches. A
          remote-only or unavailable cover has no stored thumbnail; this does
          not mean the identity has no cover.
        </p>
      </fieldset>
      <fieldset className="taxonomy-filter-categories">
        <legend>Display preferences</legend>
        {state.view === "tree" ? (
          <>
            <DirectoryFilterSelect
              label="Show ranks through"
              value={state.through ?? "all"}
              options={[
                { value: "all", label: "Every source rank" },
                { value: "family", label: "Through family" },
                { value: "genus", label: "Through genus" },
                { value: "species", label: "Through species" },
              ]}
              onChange={(through) => {
                update({
                  ...state,
                  through: through === "all" ? undefined : through,
                });
              }}
            />
            <label>
              <input
                type="checkbox"
                checked={state.photos !== "hide"}
                onChange={(e) => {
                  update({
                    ...state,
                    photos: e.target.checked ? undefined : "hide",
                  });
                }}
              />
              Show representative node thumbnails
            </label>
            <p className="field-help">
              Tree depth limits the display, not identity counts. Intermediate
              source ranks retain their actual edges.
            </p>
          </>
        ) : (
          <label>
            <input
              type="checkbox"
              checked={state.ranks === "all"}
              onChange={(e) => {
                update({
                  ...state,
                  ranks: e.target.checked ? "all" : undefined,
                });
              }}
            />
            Show every source rank
          </label>
        )}
        <label>
          <input type="checkbox" checked disabled />
          Represented branches only
        </label>
        <p className="field-help">
          This collection-pruned API does not browse worldwide WFO taxonomy.
          Graph controls offer Focus selected branch.
        </p>
      </fieldset>
    </>
  );
}
