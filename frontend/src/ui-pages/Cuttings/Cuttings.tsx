import { useRef, useState } from "react";
import { useAuth } from "../../auth/context";
import {
  DirectoryCard,
  DirectoryInspector,
  DirectoryPage,
  DirectoryRecords,
  DirectoryRow,
  DirectoryViewSwitcher,
} from "../../components/DirectoryPage";
import {
  DirectoryFilterSelect,
  DirectorySearch,
  DirectoryTools,
} from "../../components/DirectoryTools";
import { PageHeader } from "../../components/ReferenceUI";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/WorkspaceUI";
import { useDirectoryPresentation } from "../../components/directoryPresentation";
import { useRecordName } from "../../components/recordPresentation";
import { formatPartialDate } from "../../events/eventData";
import type { LocationResponse } from "../../locations/api";
import { SavedViews } from "../../saved-views/SavedViews";
import { defaults } from "../../saved-views/state";
import { useDirectoryView } from "../../saved-views/useDirectoryView";
import { CuttingForm } from "./CuttingForm";
import { AttemptPage, LotPage } from "./CuttingDetails";
import {
  attempts,
  countLabel,
  lots,
  materialLabels,
  rootingLabel,
  sourceLabels,
  useCuttingData,
  type Attempt,
  type Lot,
} from "./api";

type Filter =
  | "lifecycle"
  | "material_type"
  | "source_kind"
  | "location_id"
  | "has_known_mother";
const filters: Record<Filter, string> = {
  lifecycle: "Status",
  material_type: "Material",
  source_kind: "Source",
  location_id: "Location",
  has_known_mother: "Known mother",
};
const pageSize = 50;
const options = (labels: Record<string, string>) =>
  Object.entries(labels).map(([value, label]) => ({ value, label }));

export function Cuttings({
  route,
  id,
  identityId,
  sourceId,
  sourceType,
}: {
  route?: string;
  id?: string;
  identityId?: string;
  sourceId?: string;
  sourceType?: "plant" | "plant_group";
}) {
  const { state } = useAuth();
  if (state.status !== "authenticated") return null;
  const token = state.csrfToken;
  if (route === "new")
    return (
      <CuttingForm
        token={token}
        identityId={identityId}
        sourceId={sourceId}
        sourceType={sourceType}
      />
    );
  if (route === "lots" && id) return <LotPage key={id} id={id} token={token} />;
  if (route === "attempts" && id)
    return <AttemptPage key={id} id={id} token={token} />;
  return <CuttingsDirectory sourceId={sourceId} sourceType={sourceType} />;
}

function CuttingsDirectory({
  sourceId,
  sourceType,
}: {
  sourceId?: string;
  sourceType?: "plant" | "plant_group";
}) {
  const [offset, setOffset] = useState(0);
  const [preview, setPreview] = useState<string>();
  const directory = useDirectoryView("cuttings", () => {
    setOffset(0);
    setPreview(undefined);
  });
  const { state: selectedFilters } = directory;
  const { record_type: surface, q } = selectedFilters;
  const { view, select: setView } = useDirectoryPresentation("cuttings");
  const trigger = useRef<HTMLButtonElement | null>(null);
  const fallback = useRef<HTMLAnchorElement>(null);
  const recordName = useRecordName();
  const [locations] = useCuttingData<LocationResponse[]>("/api/v1/locations");
  const params = new URLSearchParams({
    q,
    limit: String(pageSize),
    offset: String(offset),
  });
  if (sourceId)
    params.set(
      sourceType === "plant_group"
        ? "mother_plant_group_id"
        : "mother_plant_id",
      sourceId,
    );
  for (const key of Object.keys(filters) as Filter[]) {
    const value = selectedFilters[key];
    if (
      !value ||
      (surface === "attempts" && !["lifecycle", "location_id"].includes(key))
    )
      continue;
    params.set(key, value);
  }
  const [data, retry] = useCuttingData<(Lot | Attempt)[]>(
    `${surface === "lots" ? lots : attempts}?${params}`,
  );
  const rows = data.state === "ready" ? data.value : [];
  const record = rows.find((item) => item.id === preview);
  const isLot = (item: Lot | Attempt): item is Lot => "material_type" in item;
  function label(item: Lot | Attempt) {
    return isLot(item)
      ? recordName(item, materialLabels[item.material_type])
      : (item.label ?? item.substrate ?? "Rooting attempt");
  }
  function detail(item: Lot | Attempt) {
    return isLot(item)
      ? `${materialLabels[item.material_type]} · ${sourceLabels[item.source_kind]} · ${countLabel(item.quantity)} remaining`
      : rootingLabel(item);
  }
  function clearPreview() {
    setPreview(undefined);
  }
  function setFilter(name: Filter, value: string) {
    directory.update(name, value);
    setOffset(0);
    clearPreview();
  }
  const choices = {
    lifecycle:
      surface === "lots"
        ? options({
            active: "Active",
            exhausted: "Exhausted",
            discarded: "Discarded",
            lost: "Lost",
            reversed: "Reversed",
          })
        : options({
            active: "Active",
            completed: "Completed",
            failed: "Failed",
            abandoned: "Abandoned",
            reversed: "Reversed",
          }),
    material_type: options(materialLabels),
    source_kind: options(sourceLabels),
    location_id:
      locations.state === "ready"
        ? locations.value.map((item) => ({
            value: item.id,
            label: item.display_path,
          }))
        : [],
    has_known_mother: options({ true: "Known", false: "Unknown" }),
  };
  const shownFilters = (Object.keys(filters) as Filter[]).filter(
    (name) =>
      surface === "lots" || name === "lifecycle" || name === "location_id",
  );
  const Row = view === "list" ? DirectoryRow : DirectoryCard;
  return (
    <DirectoryPage
      titleId="cuttings-title"
      header={
        <PageHeader
          titleId="cuttings-title"
          title="Cuttings"
          eyebrow="Collection"
          directory
          description={
            sourceId
              ? "Material and rooting attempts from the selected mother."
              : "Manage vegetative material and track rooting attempts."
          }
          tools={
            <DirectoryTools
              name="Cuttings"
              search={
                <DirectorySearch
                  id="cutting-search"
                  label="Search cuttings"
                  hideLabel
                  placeholder="Search cuttings…"
                  value={q}
                  maxLength={200}
                  onChange={(value) => {
                    directory.update("q", value);
                    setOffset(0);
                    clearPreview();
                  }}
                />
              }
              presentation={
                <DirectoryViewSwitcher value={view} onChange={setView} />
              }
              savedViews={
                <SavedViews
                  surface="cuttings"
                  state={directory.savedState}
                  presentation="dialog"
                />
              }
              actions={
                <a
                  className="button-link"
                  ref={fallback}
                  href={
                    sourceId
                      ? `#/cuttings/new?sourceType=${sourceType ?? "plant"}&source=${sourceId}`
                      : "#/cuttings/new"
                  }
                >
                  Take or add cuttings
                </a>
              }
              filters={shownFilters.map((name) => (
                <DirectoryFilterSelect
                  key={name}
                  label={filters[name]}
                  value={selectedFilters[name]}
                  options={[{ value: "", label: "All" }, ...choices[name]]}
                  onChange={(value) => {
                    setFilter(name, value);
                  }}
                />
              ))}
              activeFilters={shownFilters.flatMap((name) =>
                selectedFilters[name]
                  ? [
                      {
                        label: filters[name],
                        value:
                          choices[name].find(
                            (choice) => choice.value === selectedFilters[name],
                          )?.label ?? "Selected",
                        onRemove: () => {
                          setFilter(name, "");
                        },
                      },
                    ]
                  : [],
              )}
              onReset={() => {
                directory.replace({
                  ...defaults.cuttings,
                  record_type: surface,
                  q,
                });
                setOffset(0);
                clearPreview();
              }}
            />
          }
        />
      }
      content={
        <>
          <div
            className="actions"
            role="group"
            aria-label="Cuttings record type"
          >
            {(["lots", "attempts"] as const).map((item) => (
              <button
                key={item}
                type="button"
                className="button--secondary"
                aria-pressed={surface === item}
                onClick={() => {
                  if (surface === item) return;
                  directory.replace({
                    ...defaults.cuttings,
                    record_type: item,
                    q,
                  });
                  setOffset(0);
                  clearPreview();
                }}
              >
                {item === "lots" ? "Material lots" : "Rooting attempts"}
              </button>
            ))}
          </div>
          {data.state === "loading" && (
            <LoadingState>Loading cuttings…</LoadingState>
          )}
          {data.state === "error" && (
            <ErrorState onRetry={retry}>Could not load cuttings.</ErrorState>
          )}
          {data.state === "ready" &&
            (rows.length === 0 ? (
              <EmptyState>No cutting records match these filters.</EmptyState>
            ) : (
              <DirectoryRecords
                view={view}
                label={
                  surface === "lots" ? "Material lots" : "Rooting attempts"
                }
              >
                {rows.map((item) => (
                  <Row
                    key={item.id}
                    label={label(item)}
                    name={label(item)}
                    href={`#/cuttings/${surface}/${item.id}`}
                    metadata={detail(item)}
                    selected={preview === item.id}
                    status={
                      <span className="record-state">{item.lifecycle}</span>
                    }
                    previewRef={preview === item.id ? trigger : undefined}
                    onPreview={(element) => {
                      trigger.current = element;
                      setPreview(item.id);
                    }}
                  />
                ))}
              </DirectoryRecords>
            ))}
        </>
      }
      inspector={
        record && (
          <DirectoryInspector
            title={label(record)}
            onClose={clearPreview}
            returnFocusTo={trigger}
            fallbackFocusTo={fallback}
          >
            <p>{detail(record)}</p>
            <p>
              {formatPartialDate(
                isLot(record)
                  ? (record.taken_on ?? null)
                  : (record.started_on ?? null),
              )}
            </p>
            {record.notes && <p>{record.notes}</p>}
            <a
              className="button-link button--secondary"
              href={`#/cuttings/${surface}/${record.id}`}
            >
              Open details
            </a>
          </DirectoryInspector>
        )
      }
      pagination={
        (offset > 0 || rows.length === pageSize) && (
          <div className="actions">
            <button
              type="button"
              className="button--secondary"
              disabled={offset === 0}
              onClick={() => {
                clearPreview();
                setOffset(offset - pageSize);
              }}
            >
              Previous page
            </button>
            <button
              type="button"
              className="button--secondary"
              disabled={rows.length !== pageSize}
              onClick={() => {
                clearPreview();
                setOffset(offset + pageSize);
              }}
            >
              Next page
            </button>
          </div>
        )
      }
    />
  );
}
