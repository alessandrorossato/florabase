import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
  type SyntheticEvent,
} from "react";
import { BulkCheckbox, BulkSelect, BulkToolbar } from "../bulk/BulkLocation";
import { useBulkSelection } from "../bulk/useBulkSelection";
import { ActionButton, ActionLink } from "../components/Action";
import "../components/collection-directory.css";
import "../components/collection-page.css";
import "../components/collection-visual.css";
import { DetailEmptyState } from "../components/DetailEmptyState";
import {
  DirectoryCard,
  DirectoryPage,
  DirectoryRecordActions,
  DirectoryRecordContent,
  DirectoryRecords,
  DirectoryRow,
  DirectoryTrigger,
  DirectoryViewSwitcher,
  DirectoryWorkspace,
} from "../components/DirectoryPage";
import { useDirectoryPresentation } from "../components/directoryPresentation";
import { DirectoryResults } from "../components/DirectoryResults";
import {
  DirectoryFilterSelect,
  DirectoryTools,
} from "../components/DirectoryTools";
import { EditWorkspace } from "../components/EditWorkspace";
import { FieldLabel } from "../components/FieldLabel";
import { FormSections } from "../components/FormSections";
import { firstValidationField } from "../components/formValidation";
import {
  usePublishRecordIdentities,
  useRecordName,
} from "../components/recordPresentation";
import { OverflowMenu } from "../components/ReferenceUI";
import { useRecordDetailFocus } from "../components/useRecordDetailFocus";
import { useCollectionPageReturnFocus } from "../components/useCollectionPageReturnFocus";
import { useDirectoryPagination } from "../components/useDirectoryPagination";
import { DirectorySortSelect } from "../components/DirectorySort";
import { sortDirectory } from "../components/directorySort";
import { useEditRoute } from "../components/useEditRoute";
import { LifecycleStatus, StatusBadge } from "../components/WorkspaceUI";
import { BotanicalIdentityFilter } from "../harvests/BotanicalIdentityFilter";
import { labelComposerHref } from "../labels/labelData";
import { CreationReversal } from "../propagation/CreationReversal";
import { PotOnLauncher } from "../propagation/PotOnDialog";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { RecordAlmanac } from "../timeline/RecordAlmanac";
import { JournalScope } from "../events/JournalScope";
import { JournalEntryCount } from "../events/JournalEntryCount";
import { useJournalEntryCount } from "../events/useJournalEntryCount";
import { usePhotoCount } from "../photos/usePhotoCount";
import { harvestsHref } from "./plantDescendants";
import { daysLabel, daysSince } from "../components/keyFactValues";
import { LineageStrip } from "../lineage/LineageStrip";
import {
  ancestryKinds,
  descendantCounts,
  descendantSummaryLabel,
  useDirectDescendants,
} from "../lineage/useRecordedLineage";
import {
  PlantEntryDateField,
  PlantEssentialsFields,
  PlantNotesField,
} from "./PlantFormFields";

import {
  ApiError,
  activeCsrfToken,
  isExpectedAuthCancellation,
  isPresentationRetainedState,
  requestJson,
} from "../auth/api";
import { useAuth } from "../auth/context";
import {
  listBotanicalIdentities,
  type BotanicalIdentityResponse,
} from "../botanical-identities/api";
import {
  Breadcrumbs,
  DetailContext,
  DetailHeader,
  DetailTabs,
  RecordDescendants,
  RecordOverview,
  WorkspaceIntro,
  DetailLoading,
  DetailPage,
  SpecimenLabel,
  SpecimenPlate,
  type SpecimenRow,
} from "../components/CollectionUI";
import {
  closeCollectionPage,
  collectionPageParent,
  isRecordTaskNavigation,
  openCollectionPage,
  setRecordRoute,
} from "../components/recordNavigation";
import { BotanicalName, DirectorySearch } from "../components/ReferenceUI";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import { EventJournal } from "../events/EventJournal";
import {
  listGeographicPlaces,
  type GeographicPlaceResponse,
} from "../geographic-places/api";
import { LineagePanel } from "../lineage/LineagePanel";
import { listLocations, type LocationResponse } from "../locations/api";
import type { PrimaryPhoto } from "../photos/api";
import { PhotosSection } from "../photos/PhotosSection";
import { RecordVisual } from "../photos/RecordVisual";
import {
  listProvenanceSites,
  type ProvenanceSiteResponse,
} from "../provenance-sites/api";
import { PartialDateField } from "../seed-lots/PartialDateField";
import {
  hasDateDraft,
  invalidDateControls,
  invalidDateErrorField,
} from "../seed-lots/dateControls";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import { listSowings, type SowingResponse } from "../sowings/api";
import { listSuppliers, type SupplierResponse } from "../suppliers/api";
import {
  createPlant,
  createPlantGroup,
  extractPlantFromGroup,
  getPlant,
  getPlantGroup,
  getPlantReintegrationEligibility,
  listPlantGroups,
  listPlants,
  plantValidationMessages,
  reintegratePlant,
  transferPlant,
  transferPlantGroup,
  updatePlant,
  updatePlantGroup,
  type DirectOriginKind,
  type PartialDate,
  type PlantCreate,
  type PlantGroupCreate,
  type PlantGroupLifecycle,
  type PlantGroupResponse,
  type PlantLifecycle,
  type PlantReintegrationEligibility,
  type PlantReintegrationResponse,
  type PlantResponse,
} from "./api";

type RecordKind = "plant" | "group";
type PlantRecord =
  | { kind: "plant"; value: PlantResponse }
  | { kind: "group"; value: PlantGroupResponse };
type CollectionState =
  | { status: "loading" }
  | { status: "ready"; records: PlantRecord[] }
  | { status: "error" };
type DetailState =
  | { status: "idle" }
  | { status: "loading"; key: string }
  | { status: "ready"; record: PlantRecord }
  | { status: "error"; key: string };
type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "success"; message: string }
  | { status: "error"; messages: string[]; field?: string };
type QuantityKind = "unknown" | "exact" | "approximate";
type OriginMode = "direct" | "sowing";
type TransferState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "error"; message: string };
type ReintegrationState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; eligibility: PlantReintegrationEligibility }
  | { status: "error" };
type ReintegrationMutationState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "error"; message: string };

interface References {
  identities: BotanicalIdentityResponse[];
  sowings: SowingResponse[];
  suppliers: SupplierResponse[];
  places: GeographicPlaceResponse[];
  locations: LocationResponse[];
  sites: ProvenanceSiteResponse[];
}

interface FormState {
  botanicalIdentityId: string;
  label: string;
  originMode: OriginMode;
  sowingId: string;
  directOriginKind: DirectOriginKind;
  directOriginDetail: string;
  supplierId: string;
  provenanceId: string;
  provenanceSiteId: string;
  locationId: string;
  collectionEntryDate: PartialDate | null;
  lifecycle: PlantLifecycle | PlantGroupLifecycle;
  quantityKind: QuantityKind;
  quantityValue: string;
  notes: string;
}

const plantLifecycleLabels: Record<PlantLifecycle, string> = {
  active: "Active",
  reversed: "Reversed",
  reintegrated: "Reintegrated",
  transferred: "Transferred",
  dead: "Dead",
  lost: "Lost",
  discarded: "Discarded",
};
const groupLifecycleLabels: Record<PlantGroupLifecycle, string> = {
  active: "Active",
  reversed: "Reversed",
  transferred: "Transferred",
  completed: "Completed",
  dead: "Dead",
  lost: "Lost",
  discarded: "Discarded",
};
const originLabels: Record<DirectOriginKind, string> = {
  purchased: "Purchased",
  gift_exchange: "Gift / exchange",
  collection_produced: "Collection produced",
  other: "Other",
  unknown: "Unknown",
};

function recordKey(record: PlantRecord): string {
  return `${record.kind}:${record.value.id}`;
}

function blankForm(): FormState {
  return {
    botanicalIdentityId: "",
    label: "",
    originMode: "direct",
    sowingId: "",
    directOriginKind: "unknown",
    directOriginDetail: "",
    supplierId: "",
    provenanceId: "",
    provenanceSiteId: "",
    locationId: "",
    collectionEntryDate: null,
    lifecycle: "active",
    quantityKind: "unknown",
    quantityValue: "",
    notes: "",
  };
}

function formFrom(record: PlantRecord): FormState {
  const value = record.value;
  const quantity = record.kind === "group" ? record.value.quantity : null;
  return {
    botanicalIdentityId: value.botanical_identity_id,
    label: value.label ?? "",
    originMode: value.originating_sowing_id ? "sowing" : "direct",
    sowingId: value.originating_sowing_id ?? "",
    directOriginKind: value.direct_origin_kind ?? "unknown",
    directOriginDetail: value.direct_origin_detail ?? "",
    supplierId: value.supplier_id ?? "",
    provenanceId: value.material_provenance_place_id ?? "",
    provenanceSiteId: value.provenance_site_id ?? "",
    locationId: value.location_id ?? "",
    collectionEntryDate: value.collection_entry_date,
    lifecycle: value.lifecycle,
    quantityKind: quantity
      ? quantity.is_approximate
        ? "approximate"
        : "exact"
      : "unknown",
    quantityValue: quantity ? String(quantity.value) : "",
    notes: value.notes ?? "",
  };
}

function commonPayload(form: FormState) {
  const direct = form.originMode === "direct";
  return {
    botanical_identity_id: form.botanicalIdentityId,
    label: form.label || null,
    originating_sowing_id: direct ? null : form.sowingId || null,
    direct_origin_kind: direct ? form.directOriginKind : null,
    direct_origin_detail:
      direct && form.directOriginKind === "other"
        ? form.directOriginDetail || null
        : null,
    supplier_id: direct ? form.supplierId || null : null,
    material_provenance_place_id: direct ? form.provenanceId || null : null,
    provenance_site_id: direct ? form.provenanceSiteId || null : null,
    location_id: form.locationId || null,
    collection_entry_date: form.collectionEntryDate,
    notes: form.notes || null,
  };
}

function plantPayload(form: FormState): PlantCreate {
  return {
    ...commonPayload(form),
    lifecycle: form.lifecycle as PlantLifecycle,
  };
}

function groupPayload(form: FormState): PlantGroupCreate {
  return {
    ...commonPayload(form),
    lifecycle: form.lifecycle as PlantGroupLifecycle,
    quantity:
      form.quantityKind === "unknown"
        ? null
        : {
            value: Number(form.quantityValue),
            is_approximate: form.quantityKind === "approximate",
          },
  };
}

function dateLabel(date: PartialDate | null): string {
  if (!date) return "Not recorded";
  const year = String(date.year).padStart(4, "0");
  if (date.precision === "year") return year;
  const month = String(date.month).padStart(2, "0");
  if (date.precision === "month") return `${year}-${month}`;
  return `${year}-${month}-${String(date.day).padStart(2, "0")}`;
}

function quantityLabel(record: PlantRecord): string | null {
  if (record.kind === "plant") return null;
  const quantity = record.value.quantity;
  if (!quantity) return "Quantity unknown";
  return `${quantity.is_approximate ? "About " : ""}${String(quantity.value)} ${quantity.value === 1 ? "plant" : "plants"}`;
}

function extractionQuantityExplanation(group: PlantGroupResponse): string {
  if (group.lifecycle !== "active")
    return "This group is no longer active. Extraction cannot continue.";
  if (!group.quantity)
    return "Group quantity is unknown and will remain unknown.";
  if (group.quantity.is_approximate)
    return "Approximate group quantity will remain unchanged.";
  if (group.quantity.value === 1)
    return "This is the last exact member. The group will become Completed.";
  return `Group count: ${String(group.quantity.value)} → ${String(group.quantity.value - 1)}`;
}

function lifecycleLabel(record: PlantRecord): string {
  return record.kind === "plant"
    ? plantLifecycleLabels[record.value.lifecycle]
    : groupLifecycleLabels[record.value.lifecycle];
}

function sowingChoice(sowing: SowingResponse): string {
  const label = sowing.label ? ` · ${sowing.label}` : "";
  const lot = sowing.seed_lot.label ? ` · lot ${sowing.seed_lot.label}` : "";
  return `${sowing.seed_lot.botanical_identity_display_label}${label}${lot} · ${sowing.lifecycle}`;
}

/** Plant record tabs; inside JournalScope so the Journal count shares the Journal request. */
function PlantDetailTabs({
  target,
  id,
  photoCount,
  selected,
  onSelect,
}: {
  target: "plant" | "group";
  id: string;
  photoCount: number | null;
  selected: string;
  onSelect: (next: string) => void;
}) {
  const journalCount = useJournalEntryCount(target, id);
  return (
    <DetailTabs
      tabs={[
        { id: "overview", label: "Overview" },
        { id: "events", label: "Journal", count: journalCount },
        { id: "photos", label: "Photos", count: photoCount },
        { id: "lineage", label: "Lineage" },
      ]}
      selected={selected}
      onSelect={onSelect}
    />
  );
}

function Detail({
  record,
  locations,
  headingRef,
  onEventTargetRefresh,
  onEdit,
  onReturnToList,
  onPrimaryChanged,
  primaryActions,
  potOnAction,
  extractedPlants,
  initialTab,
  reversalAction,
  moreActions,
  moreTrigger,
}: {
  record: PlantRecord;
  locations: LocationResponse[];
  headingRef: RefObject<HTMLHeadingElement | null>;
  onEventTargetRefresh: () => Promise<void>;
  onEdit: (trigger: HTMLButtonElement) => void;
  onReturnToList?: () => void;
  onPrimaryChanged?: (photo: PrimaryPhoto | null) => void;
  primaryActions?: ReactNode;
  potOnAction?: ReactNode;
  extractedPlants: PlantResponse[];
  initialTab?: string;
  reversalAction?: ReactNode;
  moreActions?: ReactNode;
  moreTrigger: RefObject<HTMLButtonElement | null>;
}) {
  const recordName = useRecordName();
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();

  const value = record.value;
  const [harvestCounts, setHarvestCounts] = useState<{
    key: string;
    harvests: number;
    singleHarvestId: string | null;
  } | null>(null);
  const offspringKey = `${record.kind}:${value.id}:${value.updated_at}`;
  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    const harvestParam =
      record.kind === "plant" ? "plant_id" : "plant_group_id";
    void requestJson<{ id?: string }[]>(
      `/api/v1/harvests?${harvestParam}=${encodeURIComponent(value.id)}`,
      { capability, signal: controller.signal },
    )
      .then((harvestsData) => {
        if (controller.signal.aborted) return;
        const harvestList = Array.isArray(harvestsData) ? harvestsData : [];
        setHarvestCounts({
          key: offspringKey,
          harvests: harvestList.length,
          singleHarvestId:
            harvestList.length === 1 && typeof harvestList[0]?.id === "string"
              ? harvestList[0].id
              : null,
        });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(error))
          return;
        if (error instanceof ApiError && error.status === 401) sessionExpired();
      });
    return () => {
      controller.abort();
    };
  }, [
    authorized,
    capability,
    offspringKey,
    record.kind,
    sessionExpired,
    value.id,
  ]);
  // Recorded descendants come from the same children endpoint as the lineage strip, so the
  // Overview line and the strip always count the same records.
  // One read, shared with the lineage strip below, so both always show the same counts.
  const [descendants] = useDirectDescendants(
    ancestryKinds[record.kind === "plant" ? "plants" : "plant-groups"],
    value.id,
    value.updated_at,
  );
  const descendantKinds =
    descendants.status !== "ready"
      ? []
      : descendants.value.items.length < descendants.value.total
        ? null
        : descendantCounts(descendants.value);
  const counts = harvestCounts?.key === offspringKey ? harvestCounts : null;
  const originatingGroup =
    record.kind === "plant" ? record.value.originating_plant_group : null;
  const allowedTabs = ["overview", "events", "photos", "lineage"];
  const tabOf = (value?: string) =>
    value && allowedTabs.includes(value) ? value : "overview";
  const [tab, setTab] = useState(() => tabOf(initialTab));
  const photoCount = usePhotoCount(
    record.kind === "plant" ? "plant" : "plant_group",
    value.id,
    tab,
  );
  // Follow later route changes on the same mounted record (a link or Record sheet action to
  // ?tab=lineage while this record is open); useState only reads the first value. Edit
  // routes are handled by the edit workspace and leave the selected section alone.
  const [lastRouteTab, setLastRouteTab] = useState(initialTab);
  if (lastRouteTab !== initialTab) {
    setLastRouteTab(initialTab);
    if (initialTab !== "edit") setTab(tabOf(initialTab));
  }
  const route = record.kind === "plant" ? "plants" : "plant-groups";
  // One fact block (the specimen label), replacing At a glance, Managed group and Origin and
  // provenance. Indirect sources (the Seed lot behind a Sowing) are left to the lineage strip.
  const specimenRows: SpecimenRow[] = [
    {
      label:
        value.lifecycle === "active" ? "Location" : "Last recorded location",
      value: value.location ? (
        <a href={`#/locations/${value.location.id}`}>
          {value.location.display_path}
        </a>
      ) : (
        "Not recorded"
      ),
      unknown: !value.location,
    },
    ...(record.kind === "group"
      ? [
          {
            label:
              value.lifecycle === "active"
                ? "Current quantity"
                : "Recorded quantity",
            value: quantityLabel(record),
          },
        ]
      : []),
    {
      label: "Origin",
      value: value.originating_propagation_attempt_id ? (
        <a
          href={`#/cuttings/attempts/${value.originating_propagation_attempt_id}`}
        >
          Rooted from cuttings
        </a>
      ) : originatingGroup ? (
        "Extracted from group"
      ) : value.originating_sowing ? (
        "From sowing"
      ) : (
        originLabels[value.direct_origin_kind ?? "unknown"]
      ),
      unknown:
        !value.originating_propagation_attempt_id &&
        !originatingGroup &&
        !value.originating_sowing &&
        (value.direct_origin_kind ?? "unknown") === "unknown",
    },
    // The record's own direct source stays here even if lineage cannot load; the
    // lineage strip adds the rest of the recorded path (for example the Seed lot).
    ...(originatingGroup
      ? [
          {
            label: "Source group",
            value: (
              <a href={`#/plant-groups/${originatingGroup.id}`}>
                {recordName(originatingGroup, "Unlabelled plant group")}
              </a>
            ),
          },
          {
            label: "Group identity",
            value: originatingGroup.botanical_identity.display_label,
          },
        ]
      : value.originating_sowing
        ? [
            {
              label: "Source sowing",
              value: (
                <a href={`#/sowings/${value.originating_sowing.id}`}>
                  {recordName(value.originating_sowing, "Unlabelled Sowing")}
                </a>
              ),
            },
          ]
        : []),
    ...(!originatingGroup &&
    !value.originating_sowing &&
    value.direct_origin_kind === "other" &&
    value.direct_origin_detail
      ? [{ label: "Origin detail", value: value.direct_origin_detail }]
      : []),
    ...(!originatingGroup && !value.originating_sowing && value.supplier
      ? [
          {
            label: "Supplier",
            value: (
              <a href={`#/suppliers/${value.supplier.id}`}>
                {value.supplier.name}
              </a>
            ),
          },
        ]
      : []),
    ...(!originatingGroup &&
    !value.originating_sowing &&
    value.material_provenance
      ? [
          {
            label: "Material provenance",
            value: value.material_provenance.display_path,
          },
        ]
      : []),
    ...(!originatingGroup && !value.originating_sowing && value.provenance_site
      ? [
          {
            label: "Provenance site",
            value: (
              <a href={`#/geography/${value.provenance_site.id}`}>
                {value.provenance_site.geographic_place_path
                  ? `${value.provenance_site.geographic_place_path} → `
                  : ""}
                {value.provenance_site.name}
              </a>
            ),
          },
        ]
      : []),
    {
      label: "Collection entry",
      value: dateLabel(value.collection_entry_date),
      unknown: !value.collection_entry_date,
    },
  ];
  return (
    <JournalScope version={value.updated_at}>
      <DetailPage className="plant-detail">
        <Breadcrumbs
          items={[
            { label: "Collection", href: "#/dashboard" },
            {
              label: "Plants",
              href: "#/plants",
              onClick: onReturnToList
                ? (event) => {
                    if (
                      !event.metaKey &&
                      !event.ctrlKey &&
                      !event.shiftKey &&
                      !event.altKey &&
                      event.button === 0
                    ) {
                      event.preventDefault();
                      onReturnToList();
                    }
                  }
                : undefined,
            },
            {
              label: recordName(
                value,
                record.kind === "plant"
                  ? "Unlabelled plant"
                  : "Unlabelled plant group",
              ),
            },
          ]}
        />
        <DetailHeader
          headingRef={headingRef}
          keyFacts={
            record.kind === "plant"
              ? [
                  {
                    label: "in collection",
                    value: (() => {
                      const days = daysSince(value.collection_entry_date);
                      if (days !== null) return daysLabel(days);
                      return value.collection_entry_date
                        ? `since ${dateLabel(value.collection_entry_date)}`
                        : "Date not recorded";
                    })(),
                  },
                  {
                    label: "journal entries",
                    value: <JournalEntryCount target="plant" id={value.id} />,
                  },
                  {
                    label: "harvests",
                    value: counts ? String(counts.harvests) : "…",
                  },
                ]
              : [
                  {
                    label: "plants",
                    value: quantityLabel(record) ?? "Quantity unknown",
                  },
                  {
                    label: "extracted",
                    value: String(extractedPlants.length),
                  },
                  {
                    label: "journal entries",
                    value: <JournalEntryCount target="group" id={value.id} />,
                  },
                  {
                    label: "harvests",
                    value: counts ? String(counts.harvests) : "…",
                  },
                ]
          }
          plate={
            <SpecimenPlate
              addPhoto={{
                href: `#/${route}/${value.id}?tab=photos`,
                onSelect: () => {
                  setTab("photos");
                },
              }}
            >
              <RecordVisual
                photo={value.primary_photo}
                showSource
                label={
                  value.label ??
                  (record.kind === "plant" ? "plant" : "plant group")
                }
                identity={value.botanical_identity}
                kind={record.kind}
              />
            </SpecimenPlate>
          }
          label={
            <SpecimenLabel
              kind={record.kind === "plant" ? "Plant" : "Plant group"}
              rows={specimenRows}
            />
          }
          eyebrow={record.kind === "plant" ? "Plant" : "Plant group"}
          title={recordName(
            value,
            record.kind === "plant"
              ? "Unlabelled plant"
              : "Unlabelled plant group",
          )}
          secondary={
            <a href={`#/identities/${value.botanical_identity.id}`}>
              {value.botanical_identity.display_label}
            </a>
          }
          status={
            <LifecycleStatus state={value.lifecycle}>
              {lifecycleLabel(record)}
            </LifecycleStatus>
          }
          lineage={
            <LineageStrip
              currentKind={record.kind === "plant" ? "plant" : "plant_group"}
              key={value.updated_at}
              kind={record.kind === "plant" ? "plants" : "plant-groups"}
              id={value.id}
              current={
                record.kind === "plant" ? "This Plant" : "This Plant group"
              }
              fullHref={`#/${route}/${value.id}?tab=lineage`}
              onLineageTab={tab === "lineage"}
              descendantsSummary={
                descendants.status === "ready"
                  ? descendantSummaryLabel(descendants.value)
                  : null
              }
              onFull={() => {
                setTab("lineage");
              }}
            />
          }
          primaryActions={
            record.kind === "plant" ? (
              <a
                className="button-link"
                data-collection-return="harvest"
                href={`#/harvests?action=create&sourceType=plant&source=${value.id}`}
              >
                Record harvest
              </a>
            ) : value.lifecycle === "active" ? (
              primaryActions
            ) : undefined
          }
          secondaryActions={
            record.kind === "plant" ? (
              value.lifecycle === "active" ? (
                <a
                  className="button-link button--secondary"
                  href={`#/cuttings/new?sourceType=plant&source=${value.id}&identity=${value.botanical_identity_id}`}
                >
                  Take cuttings
                </a>
              ) : undefined
            ) : (
              <>
                {value.lifecycle === "active" && potOnAction}
                <a
                  className="button-link button--secondary"
                  data-collection-return="harvest"
                  href={`#/harvests?action=create&sourceType=plant_group&source=${value.id}`}
                >
                  Record harvest
                </a>
              </>
            )
          }
          editLabel={`Edit ${record.kind === "plant" ? "Plant" : "Plant group"}`}
          onEdit={(event) => {
            onEdit(event.currentTarget);
          }}
          overflow={
            reversalAction ?? (
              <OverflowMenu
                ariaLabel="More record actions"
                triggerRef={moreTrigger}
              >
                {moreActions}
              </OverflowMenu>
            )
          }
        />
        <PlantDetailTabs
          target={record.kind}
          id={value.id}
          photoCount={photoCount}
          selected={tab}
          onSelect={(next) => {
            setTab(next);
            window.history.replaceState(
              null,
              "",
              `#/${route}/${value.id}?tab=${next}`,
            );
          }}
        />
        {tab === "overview" && (
          <div
            id="panel-overview"
            className="detail-tab-panel"
            role="tabpanel"
            aria-labelledby="tab-overview"
          >
            <RecordOverview
              facts={
                <>
                  <RecordDescendants
                    headingId="plant-descendants-title"
                    // A failed children read only drops those counts; the Lineage
                    // tab reports the failure and offers a retry.
                    loading={descendants.status === "loading" && !counts}
                    items={[
                      // A group's extracted Plants come from its recorded extractions
                      // (retained and reintegrated ones included), not only the first
                      // page of children.
                      ...(record.kind === "group"
                        ? [
                            {
                              label: `${String(extractedPlants.length)} ${extractedPlants.length === 1 ? "extracted plant" : "extracted plants"}`,
                              href: `#/${route}/${value.id}?tab=lineage`,
                              onClick: () => {
                                setTab("lineage");
                              },
                            },
                          ]
                        : []),
                      ...(descendantKinds === null &&
                      descendants.status === "ready"
                        ? [
                            {
                              label: `${String(descendants.value.total)} recorded from this`,
                              href: `#/${route}/${value.id}?tab=lineage`,
                              onClick: () => {
                                setTab("lineage");
                              },
                            },
                          ]
                        : []),
                      ...(descendantKinds
                        ? descendantKinds
                            .filter(
                              ({ kind }) =>
                                record.kind !== "group" || kind !== "plant",
                            )
                            .map(({ kind, label }) => ({
                              label,
                              href:
                                kind === "vegetative_lot"
                                  ? `#/cuttings?sourceType=${record.kind === "plant" ? "plant" : "plant_group"}&source=${value.id}`
                                  : `#/${route}/${value.id}?tab=lineage`,
                              onClick:
                                kind === "vegetative_lot"
                                  ? undefined
                                  : () => {
                                      setTab("lineage");
                                    },
                            }))
                        : []),
                      ...(counts
                        ? [
                            {
                              label: `${String(counts.harvests)} ${counts.harvests === 1 ? "harvest" : "harvests"}`,
                              // No filtered Harvest list exists: one harvest opens directly,
                              // several open the identity's Harvests, none is plain text.
                              href: harvestsHref(
                                counts,
                                value.botanical_identity_id,
                              ),
                            },
                          ]
                        : []),
                    ]}
                    lineageHref={`#/${route}/${value.id}?tab=lineage`}
                    onOpenLineage={() => {
                      setTab("lineage");
                    }}
                  />
                  {value.notes && (
                    <section
                      className="plant-fact-group"
                      aria-labelledby="plant-notes-title"
                    >
                      <h4 id="plant-notes-title">Notes</h4>
                      <p className="preserve-lines">{value.notes}</p>
                    </section>
                  )}
                </>
              }
              almanac={
                <RecordAlmanac
                  kind={record.kind === "plant" ? "plant" : "plant_group"}
                  id={value.id}
                  current={value.lifecycle === "active"}
                  journal={{
                    target: record.kind,
                    href: `#/${route}/${value.id}?tab=events`,
                    onOpen: () => {
                      setTab("events");
                    },
                  }}
                />
              }
            />
          </div>
        )}
        {tab === "events" && (
          <div
            id="panel-events"
            className="detail-tab-panel"
            role="tabpanel"
            aria-labelledby="tab-events"
          >
            <EventJournal
              key={`${record.kind}:${value.id}:${value.updated_at}`}
              targetKind={record.kind}
              targetId={value.id}
              targetLabel={recordName(
                value,
                record.kind === "plant"
                  ? "Unlabelled plant"
                  : "Unlabelled plant group",
              )}
              locations={locations}
              onTargetRefresh={onEventTargetRefresh}
            />
          </div>
        )}
        {tab === "lineage" && (
          <div
            id="panel-lineage"
            className="detail-tab-panel"
            role="tabpanel"
            aria-labelledby="tab-lineage"
          >
            <LineagePanel
              key={value.updated_at}
              kind={record.kind === "plant" ? "plants" : "plant-groups"}
              id={value.id}
            />
            {record.kind === "group" && (
              <section aria-label="Extraction history">
                <h4>Extracted Plants</h4>
                {extractedPlants.length ? (
                  <ul className="plant-related-list">
                    {extractedPlants.map((plant) => (
                      <li key={plant.id}>
                        <a href={`#/plants/${plant.id}?tab=lineage`}>
                          {recordName(plant, "Unlabelled plant")}
                        </a>
                        <span>{plant.botanical_identity.display_label}</span>
                        <span>{plantLifecycleLabels[plant.lifecycle]}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <DetailEmptyState>No extracted plants.</DetailEmptyState>
                )}
              </section>
            )}
          </div>
        )}
        {tab === "photos" && (
          <div
            id="panel-photos"
            className="detail-tab-panel"
            role="tabpanel"
            aria-labelledby="tab-photos"
          >
            <PhotosSection
              presentation="compact"
              key={`${record.kind}:${value.id}`}
              target={record.kind === "plant" ? "plant" : "plant_group"}
              targetId={value.id}
              targetLabel={recordName(
                value,
                record.kind === "plant"
                  ? "Unlabelled plant"
                  : "Unlabelled plant group",
              )}
              primaryPhoto={value.primary_photo}
              onPrimaryChanged={onPrimaryChanged}
            />
          </div>
        )}
      </DetailPage>
    </JournalScope>
  );
}

const plantPage = {
  eyebrow: "Collection",
  title: "Plants",
  directory: true,
  titleId: "plants-title",
  description: "Your plants and growing groups.",
};

interface BrowserNavigation extends EventTarget {
  currentEntry?: { index: number };
}

interface BrowserNavigateEvent extends Event {
  destination: { url: string; sameDocument: boolean };
  hashChange: boolean;
  navigationType: string;
}

function browserNavigation(): BrowserNavigation | undefined {
  return (window as Window & { navigation?: BrowserNavigation }).navigation;
}

function browserHistoryIndex(): number | undefined {
  return browserNavigation()?.currentEntry?.index;
}

function plantCreationKey(hash: string): string | null {
  const [path, query] = hash.split("?", 2);
  const params = new URLSearchParams(query);
  if (path !== "#/plants" || params.get("action") !== "create") return null;
  const kind = params.get("kind");
  return `${kind === "plant" || kind === "group" ? kind : ""}:${params.get("identity") ?? ""}`;
}

function currentCreationParent(): string | undefined {
  const state = window.history.state as {
    collectionPageParent?: string;
  } | null;
  return state?.collectionPageParent;
}

export function PlantScreen({
  initialId,
  initialKind = "plant",
  initialTypeFilter = "all",
  initialTab,
  initialIdentityId,
  initialCreationKind,
  initialExtractionId,
  startCreating = false,
  registerFormDeparture,
}: {
  initialId?: string;
  initialKind?: RecordKind;
  initialTypeFilter?: "all" | RecordKind;
  initialTab?: string;
  initialIdentityId?: string;
  initialCreationKind?: RecordKind;
  initialExtractionId?: string;
  startCreating?: boolean;
  registerFormDeparture?: (guard: () => boolean) => () => void;
} = {}) {
  const recordName = useRecordName();

  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const presentation = useDirectoryPresentation("plants");
  const DirectoryItem =
    presentation.view === "list" ? DirectoryRow : DirectoryCard;
  const directoryList = useRef<HTMLUListElement | null>(null);

  const [collection, setCollection] = useState<CollectionState>({
    status: "loading",
  });
  const [references, setReferences] = useState<References | null>(null);
  const scientificNames = useMemo(
    () =>
      new Map<string, string>(
        references?.identities.map((identity) => [
          identity.id,
          identity.scientific_name,
        ]) ?? [],
      ),
    [references],
  );
  usePublishRecordIdentities(references?.identities);
  const [attempt, setAttempt] = useState(0);
  const [detailAttempt, setDetailAttempt] = useState(0);
  const [reversalRevision, setReversalRevision] = useState(0);
  const [detail, setDetail] = useState<DetailState>({ status: "idle" });
  const [selectedKey, setSelectedKey] = useState<string | null>(
    initialId ? `${initialKind}:${initialId}` : null,
  );
  const routedKey = initialId ? `${initialKind}:${initialId}` : null;
  const lastRoutedKey = useRef(routedKey);
  const [mobileDetail, setMobileDetail] = useState(Boolean(initialId));
  const view = useDirectoryView(
    "plants",
    () => {
      setSelectedKey(null);
      setMobileDetail(false);
    },
    { type: initialTypeFilter },
  );
  const lifecycleFilter = view.state.lifecycle;
  const setLifecycleFilter = (value: "active" | "history" | "all") => {
    view.update("lifecycle", value);
  };
  const typeFilter = view.state.type;
  const setTypeFilter = (value: "all" | RecordKind) => {
    view.update("type", value);
  };
  const identityFilter = view.state.identity_id;
  const search = view.state.q;
  const setSearch = (value: string) => {
    view.update("q", value);
  };

  const [editing, setEditing] = useState(false);
  const [creationKind, setCreationKind] = useState<RecordKind | null>(null);
  const [form, setForm] = useState<FormState>(blankForm);
  const formElement = useRef<HTMLFormElement>(null);
  const addAnother = useRef(false);
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const [extractionSource, setExtractionSource] =
    useState<PlantGroupResponse | null>(null);
  const [transferTarget, setTransferTarget] = useState<PlantRecord | null>(
    null,
  );
  const [transferDate, setTransferDate] = useState<PartialDate | null>(null);
  const [transferRecipient, setTransferRecipient] = useState("");
  const [transferNotes, setTransferNotes] = useState("");
  const [transferState, setTransferState] = useState<TransferState>({
    status: "idle",
  });
  const [reintegration, setReintegration] = useState<ReintegrationState>({
    status: "idle",
  });
  const [reintegrationOpen, setReintegrationOpen] = useState(false);
  const [reintegrationMutation, setReintegrationMutation] =
    useState<ReintegrationMutationState>({ status: "idle" });
  const feedback = useRef<HTMLDivElement>(null);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const editorHeading = useRef<HTMLHeadingElement>(null);
  const extractionTrigger = useRef<HTMLButtonElement | null>(null);
  const recordMoreTrigger = useRef<HTMLButtonElement>(null);
  const transferTrigger = useRef<HTMLElement | null>(null);
  const reintegrationTrigger = useRef<HTMLButtonElement | null>(null);
  const transferDialog = useRef<HTMLDivElement | null>(null);
  const reintegrationDialog = useRef<HTMLDivElement | null>(null);
  const selectedTrigger = useRef<HTMLButtonElement | null>(null);
  const editBaseline = useRef("");
  const editTrigger = useRef<HTMLButtonElement | null>(null);
  const directEditHandled = useRef(false);
  const canDiscardEdit = useCallback(
    () =>
      save.status !== "saving" &&
      ((JSON.stringify(form) === editBaseline.current &&
        !hasDateDraft(formElement.current)) ||
        window.confirm("Discard unsaved plant changes?")),
    [form, save.status],
  );
  const edit = useEditRoute({
    routeIsEdit: initialTab === "edit",
    canDismiss: canDiscardEdit,
    onDismiss: () => {
      setEditing(false);
      setSave((current) =>
        current.status === "success" ? current : { status: "idle" },
      );
      if (!edit.modal && selectedKey)
        setRecordRoute(
          `#/${selectedKey.startsWith("group:") ? "plant-groups" : "plants"}/${selectedKey.split(":")[1]}`,
          true,
        );
    },
  });
  const prepareEditDeparture = edit.prepareDeparture;
  useEffect(() => {
    if (!editing || !selectedKey || extractionSource) return;
    return registerFormDeparture?.(prepareEditDeparture);
  }, [
    editing,
    selectedKey,
    extractionSource,
    registerFormDeparture,
    prepareEditDeparture,
  ]);
  const contextualCreationKey = useRef<string | null>(null);
  const creationBaseline = useRef("");
  const creationHash = useRef("");
  const creationHistoryIndex = useRef<number | undefined>(undefined);
  const creationParent = useRef<string | undefined>(undefined);
  const creationRestoring = useRef(false);
  const creationRouteKey = startCreating
    ? `${initialCreationKind ?? ""}:${initialIdentityId ?? ""}`
    : null;
  const {
    expanded: creationExpanded,
    triggerRef: creationTriggerRef,
    panelRef: creationPanelRef,
    open: openCreation,
    close: closeCreation,
    focusFirst: focusCreation,
  } = useCreationDisclosure();
  const previousCreateRoute = useRef(startCreating);
  useEffect(() => {
    if (previousCreateRoute.current && !startCreating && creationExpanded) {
      setEditing(false);
      setMobileDetail(false);
      setCreationKind(null);
      setSave({ status: "idle" });
      closeCreation();
    }
    previousCreateRoute.current = startCreating;
    if (!startCreating) {
      contextualCreationKey.current = null;
      creationBaseline.current = "";
      creationHash.current = "";
      creationRestoring.current = false;
    }
  }, [startCreating, creationExpanded, closeCreation]);
  useCollectionPageReturnFocus(
    Boolean(references) &&
      !editing &&
      (!initialId || detail.status === "ready"),
  );

  useEffect(() => {
    if (initialExtractionId) {
      lastRoutedKey.current = null;
      return;
    }
    if (edit.modal) {
      lastRoutedKey.current = routedKey;
      return;
    }
    if (!routedKey && lastRoutedKey.current) {
      lastRoutedKey.current = null;
      const timeout = window.setTimeout(() => {
        setMobileDetail(false);
      }, 0);
      return () => {
        window.clearTimeout(timeout);
      };
    }
    if (!routedKey || routedKey === lastRoutedKey.current) return;
    lastRoutedKey.current = routedKey;
    directEditHandled.current = false;
    if (routedKey === selectedKey) {
      // Browser Forward must reopen retained Details without resetting workflow feedback.
      const timeout = window.setTimeout(() => {
        setMobileDetail(true);
      }, 0);
      return () => {
        window.clearTimeout(timeout);
      };
    }
    const timeout = window.setTimeout(() => {
      setExtractionSource(null);
      setDetail({ status: "loading", key: routedKey });
      setSelectedKey(routedKey);
      setMobileDetail(true);
      setEditing(false);
      setCreationKind(null);
      setSave({ status: "idle" });
    }, 0);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [routedKey, selectedKey, edit.modal, initialExtractionId]);

  const extractionRouteStarted = useRef<string | undefined>(undefined);
  const extractionRouteSource =
    collection.status === "ready"
      ? collection.records.find(
          (record) =>
            record.kind === "group" && record.value.id === initialExtractionId,
        )
      : undefined;
  const extractionRouteError =
    initialExtractionId && collection.status === "ready"
      ? extractionRouteSource?.kind !== "group"
        ? "Florabase could not find the source Plant group."
        : extractionRouteSource.value.lifecycle !== "active"
          ? "Plants can only be extracted from an active group."
          : ""
      : "";
  useEffect(() => {
    if (!initialExtractionId) {
      if (extractionRouteStarted.current) {
        setExtractionSource(null);
        setEditing(false);
        setCreationKind(null);
        closeCreation({ returnFocus: false });
      }
      extractionRouteStarted.current = undefined;
      return;
    }
    if (
      collection.status !== "ready" ||
      !references ||
      extractionRouteStarted.current === initialExtractionId
    )
      return;
    const source = collection.records.find(
      (record) =>
        record.kind === "group" && record.value.id === initialExtractionId,
    );
    if (source?.kind !== "group" || source.value.lifecycle !== "active") return;
    const timeout = window.setTimeout(() => {
      extractionRouteStarted.current = initialExtractionId;
      setExtractionSource(source.value);
      setSelectedKey(null);
      setDetail({ status: "idle" });
      setCreationKind("plant");
      setEditing(true);
      setMobileDetail(true);
      setForm({
        ...blankForm(),
        botanicalIdentityId: source.value.botanical_identity_id,
        locationId: source.value.location_id ?? "",
      });
      setSave({ status: "idle" });
      openCreation();
    }, 0);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [
    initialExtractionId,
    collection,
    references,
    openCreation,
    closeCreation,
  ]);
  const isCreationActive = editing && !selectedKey && !extractionSource;

  const canDiscardCreation = useCallback(
    () =>
      save.status !== "saving" &&
      ((JSON.stringify(form) === creationBaseline.current &&
        !hasDateDraft(formElement.current)) ||
        window.confirm("Discard unsaved plant changes?")),
    [form, save.status],
  );

  useEffect(() => {
    if (!isCreationActive || !creationBaseline.current) return;
    const unregister = registerFormDeparture?.(canDiscardCreation);
    const navigation = browserNavigation();
    const guardNativeNavigation = (event: Event) => {
      const next = event as BrowserNavigateEvent;
      if (
        !creationBaseline.current ||
        creationRestoring.current ||
        !next.cancelable ||
        !next.destination.sameDocument ||
        (!next.hashChange && next.navigationType !== "traverse")
      )
        return;
      const hash = new URL(next.destination.url).hash;
      if (plantCreationKey(hash) === contextualCreationKey.current) return;
      // A cancellation before traversal also prevents Chromium from
      // restoring persisted form values into the still-mounted editor.
      if (!canDiscardCreation()) event.preventDefault();
      else creationBaseline.current = "";
    };
    const guardDeparture = (event: Event) => {
      if (isRecordTaskNavigation(event)) return;
      if (window.location.hash === creationHash.current) {
        creationRestoring.current = false;
        return;
      }
      if (creationRestoring.current) {
        event.stopImmediatePropagation();
        return;
      }
      if (
        plantCreationKey(window.location.hash) === contextualCreationKey.current
      ) {
        creationHash.current = window.location.hash;
        creationHistoryIndex.current = browserHistoryIndex();
        return;
      }
      if (!creationBaseline.current) return;
      if (canDiscardCreation()) {
        // A traversal can dispatch both popstate and hashchange before React
        // replaces this form. The second event needs no further approval.
        creationBaseline.current = "";
        return;
      }
      event.stopImmediatePropagation();
      const currentIndex = browserHistoryIndex();
      const sourceIndex = creationHistoryIndex.current;
      if (
        sourceIndex !== undefined &&
        currentIndex !== undefined &&
        sourceIndex !== currentIndex
      ) {
        creationRestoring.current = true;
        window.history.go(sourceIndex - currentIndex);
      } else if (
        currentIndex === undefined &&
        event.type === "popstate" &&
        window.location.hash === creationParent.current &&
        (window.history.state as { collectionReturnFocus?: string } | null)
          ?.collectionReturnFocus === "create"
      ) {
        // Older browsers can identify the parent entry inserted by
        // openCollectionPage even without the Navigation API's indices.
        creationRestoring.current = true;
        window.history.forward();
      } else if (creationHash.current) {
        window.history.replaceState(
          window.history.state,
          "",
          creationHash.current,
        );
      }
    };
    navigation?.addEventListener("navigate", guardNativeNavigation);
    window.addEventListener("popstate", guardDeparture, true);
    window.addEventListener("hashchange", guardDeparture, true);
    return () => {
      unregister?.();
      navigation?.removeEventListener("navigate", guardNativeNavigation);
      window.removeEventListener("popstate", guardDeparture, true);
      window.removeEventListener("hashchange", guardDeparture, true);
    };
  }, [isCreationActive, canDiscardCreation, registerFormDeparture]);

  useEffect(() => {
    if (
      !startCreating ||
      !references ||
      !creationRouteKey ||
      contextualCreationKey.current === creationRouteKey
    )
      return;
    contextualCreationKey.current = creationRouteKey;
    creationHash.current = window.location.hash;
    creationHistoryIndex.current = browserHistoryIndex();
    creationParent.current = currentCreationParent();
    creationRestoring.current = false;
    const nextForm: FormState = {
      ...blankForm(),
      botanicalIdentityId: initialIdentityId ?? "",
    };
    creationBaseline.current = JSON.stringify(nextForm);
    setExtractionSource(null);
    setSelectedKey(null);
    setDetail({ status: "idle" });
    setCreationKind(initialCreationKind ?? null);
    setEditing(true);
    setMobileDetail(true);
    setForm(nextForm);
    setSave({ status: "idle" });
    openCreation();
  }, [
    creationRouteKey,
    initialCreationKind,
    initialIdentityId,
    openCreation,
    references,
    startCreating,
  ]);

  useEffect(() => {
    if (editing && !edit.modal) editorHeading.current?.focus();
  }, [editing, extractionSource, creationKind, edit.modal]);

  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    Promise.all([
      listPlants(capability, controller.signal),
      listPlantGroups(capability, controller.signal),
      listBotanicalIdentities(capability, controller.signal),
      listSowings(capability, controller.signal),
      listSuppliers(capability, controller.signal),
      listGeographicPlaces(capability, controller.signal),
      listLocations(capability, controller.signal),
      listProvenanceSites(capability, controller.signal),
    ])
      .then(
        ([
          plants,
          groups,
          identities,
          sowings,
          suppliers,
          places,
          locations,
          sites,
        ]) => {
          const records: PlantRecord[] = [
            ...plants.map((value): PlantRecord => ({ kind: "plant", value })),
            ...groups.map((value): PlantRecord => ({ kind: "group", value })),
          ];
          setCollection({ status: "ready", records });
          setReferences({
            identities,
            sowings,
            suppliers,
            places,
            locations,
            sites,
          });
          setSelectedKey((current) =>
            current && records.some((record) => recordKey(record) === current)
              ? current
              : null,
          );
        },
      )
      .catch((error: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(error))
          return;
        if (error instanceof ApiError && error.status === 401) sessionExpired();
        else setCollection({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [authorized, capability, sessionExpired, attempt]);

  useEffect(() => {
    if (!selectedKey || !authorized) return;
    if (detail.status === "ready" && recordKey(detail.record) === selectedKey)
      return;
    const [kind, id] = selectedKey.split(":", 2) as [RecordKind, string];
    const controller = new AbortController();
    const request =
      kind === "plant"
        ? getPlant(id, capability, controller.signal)
        : getPlantGroup(id, capability, controller.signal);
    void request
      .then((value) => {
        const record = { kind, value } as PlantRecord;
        setReintegration(
          record.kind === "plant" && record.value.originating_plant_group_id
            ? { status: "loading" }
            : { status: "idle" },
        );
        setDetail({ status: "ready", record });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(error))
          return;
        if (error instanceof ApiError && error.status === 401) sessionExpired();
        else setDetail({ status: "error", key: selectedKey });
      });
    return () => {
      controller.abort();
    };
  }, [
    authorized,
    capability,
    sessionExpired,
    detail,
    detailAttempt,
    selectedKey,
  ]);

  useEffect(() => {
    if (
      !authorized ||
      !mobileDetail ||
      detail.status !== "ready" ||
      detail.record.kind !== "plant" ||
      !detail.record.value.originating_plant_group_id
    )
      return;
    const controller = new AbortController();
    void getPlantReintegrationEligibility(
      detail.record.value.id,
      capability,
      controller.signal,
    )
      .then((eligibility) => {
        setReintegration({ status: "ready", eligibility });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(error))
          return;
        if (error instanceof ApiError && error.status === 401) sessionExpired();
        else setReintegration({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [authorized, capability, sessionExpired, detail, mobileDetail]);

  useEffect(() => {
    if (!transferTarget && transferTrigger.current) {
      if (transferTrigger.current.isConnected) transferTrigger.current.focus();
      transferTrigger.current = null;
    }
  }, [transferTarget]);

  useEffect(() => {
    if (!reintegrationOpen && reintegrationTrigger.current) {
      if (reintegrationTrigger.current.isConnected)
        reintegrationTrigger.current.focus();
      reintegrationTrigger.current = null;
    }
  }, [reintegrationOpen]);

  useEffect(() => {
    if (save.status === "error") feedback.current?.focus();
  }, [save]);

  useRecordDetailFocus({
    recordKey: mobileDetail ? selectedKey : null,
    detailReady:
      detail.status === "ready" && recordKey(detail.record) === selectedKey,
    directoryReady: collection.status === "ready",
    paused: editing || edit.modal || creationExpanded,
    headingRef: detailHeading,
    directoryRef: directoryList,
    fallbackId: "plant-search",
  });

  const records = useMemo(
    () => (collection.status === "ready" ? collection.records : []),
    [collection],
  );
  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return records.filter((record) => {
      if (
        identityFilter &&
        record.value.botanical_identity_id !== identityFilter
      )
        return false;
      const value = record.value;
      const lifecycleMatch =
        lifecycleFilter === "all" ||
        (lifecycleFilter === "active"
          ? value.lifecycle === "active"
          : value.lifecycle !== "active");
      const typeMatch = typeFilter === "all" || record.kind === typeFilter;
      const sowing = value.originating_sowing_id
        ? references?.sowings.find(
            ({ id }) => id === value.originating_sowing_id,
          )
        : undefined;
      const originatingGroup =
        record.kind === "plant" ? record.value.originating_plant_group : null;
      const textMatch =
        !query ||
        [
          value.botanical_identity.display_label,
          value.label,
          value.location?.display_path,
          value.supplier?.name,
          value.originating_sowing?.label,
          value.originating_sowing?.botanical_identity_display_label,
          originatingGroup?.label,
          originatingGroup?.botanical_identity.display_label,
          sowing?.seed_lot.label,
        ].some((item) => item?.toLocaleLowerCase().includes(query));
      return lifecycleMatch && typeMatch && textMatch;
    });
  }, [
    identityFilter,
    lifecycleFilter,
    records,
    references,
    search,
    typeFilter,
  ]);

  const ordered = sortDirectory(
    filtered,
    view.state.sort,
    (record) => recordName(record.value, ""),
    (record) => record.value.collection_entry_date,
  );
  const pagination = useDirectoryPagination(
    ordered,
    JSON.stringify(view.state) +
      ordered.map((record) => recordKey(record)).join(","),
  );
  const visible = pagination.visible;
  const bulkChoices = visible.map((record) => ({
    kind:
      record.kind === "plant" ? ("plant" as const) : ("plant_group" as const),
    id: record.value.id,
    label: `${record.kind === "plant" ? "Plant" : "Plant group"} · ${recordName(record.value, record.value.botanical_identity.display_label)}`,
    eligible: record.value.lifecycle === "active",
  }));
  const bulk = useBulkSelection(
    JSON.stringify(view.state) + String(initialId) + String(editing),
    bulkChoices,
    true,
  );
  const selected =
    detail.status === "ready" && recordKey(detail.record) === selectedKey
      ? detail.record
      : !mobileDetail && !editing
        ? (records.find((record) => recordKey(record) === selectedKey) ?? null)
        : null;
  useEffect(() => {
    if (initialTab !== "edit") {
      directEditHandled.current = false;
      return;
    }
    if (edit.modal) {
      directEditHandled.current = true;
      return;
    }
    if (
      directEditHandled.current ||
      !selected ||
      recordKey(selected) !== routedKey
    )
      return;
    directEditHandled.current = true;
    const timer = window.setTimeout(() => {
      const values = formFrom(selected);
      editBaseline.current = JSON.stringify(values);
      setForm(values);
      setEditing(true);
      setMobileDetail(true);
    }, 0);
    return () => {
      window.clearTimeout(timer);
    };
  }, [initialTab, edit.modal, selected, routedKey]);

  if (!references && collection.status === "loading")
    return (
      <section
        className="workspace plants-workspace"
        aria-labelledby="plants-title"
      >
        <WorkspaceIntro {...plantPage} contextOnly={Boolean(initialId)} />
        {initialId && (
          <div className="workspace-context-actions">
            <a
              className="button-link button--secondary plant-back"
              href="#/plants"
            >
              ← Back to Plants
            </a>
          </div>
        )}
        {initialId ? (
          <DetailLoading
            eyebrow="Plants"
            label="Loading Plants…"
            parents={[
              { label: "Collection", href: "#/dashboard" },
              { label: "Plants", href: "#/plants" },
            ]}
            className="plant-detail"
          />
        ) : (
          <p role="status">Loading Plants…</p>
        )}
      </section>
    );
  if (collection.status === "error" || !references)
    return (
      <section
        className="workspace plants-workspace"
        aria-labelledby="plants-title"
      >
        <WorkspaceIntro {...plantPage} />
        <div className="notice notice--error" role="alert">
          <p>Florabase could not load the Plant collection or its choices.</p>
          <button
            type="button"
            onClick={() => {
              setAttempt((value) => value + 1);
            }}
          >
            Retry
          </button>
        </div>
      </section>
    );
  if (!isPresentationRetainedState(auth.state)) return null;
  const csrfToken = activeCsrfToken(auth.state);
  const pending = save.status === "saving";

  const formKind = extractionSource
    ? "plant"
    : (selected?.kind ?? creationKind);
  const extractedEdit =
    !extractionSource &&
    selected?.kind === "plant" &&
    Boolean(selected.value.originating_plant_group_id);
  const cuttingEdit = Boolean(
    selected?.value.originating_propagation_attempt_id,
  );

  function startCreate() {
    const nextForm = blankForm();
    contextualCreationKey.current = ":";
    creationHash.current = "#/plants?action=create";
    creationBaseline.current = JSON.stringify(nextForm);
    creationRestoring.current = false;
    openCollectionPage("#/plants?action=create");
    creationHistoryIndex.current = browserHistoryIndex();
    creationParent.current = currentCreationParent();
    setExtractionSource(null);
    setSelectedKey(null);
    setDetail({ status: "idle" });
    setCreationKind(null);
    setEditing(true);
    setMobileDetail(true);
    setForm(nextForm);
    setSave({ status: "idle" });
    openCreation();
  }

  function chooseCreationKind(kind: RecordKind) {
    const nextHash = `#/plants?action=create&kind=${kind}${initialIdentityId ? `&identity=${encodeURIComponent(initialIdentityId)}` : ""}`;
    const nextForm: FormState = {
      ...blankForm(),
      botanicalIdentityId: initialIdentityId ?? "",
    };
    contextualCreationKey.current = `${kind}:${initialIdentityId ?? ""}`;
    creationHash.current = nextHash;
    creationBaseline.current = JSON.stringify(nextForm);
    creationRestoring.current = false;
    setRecordRoute(nextHash, true, window.history.state);
    creationHistoryIndex.current = browserHistoryIndex();
    setCreationKind(kind);
    setForm(nextForm);
    setSave({ status: "idle" });
  }

  function startEdit(record: PlantRecord, trigger: HTMLButtonElement) {
    editTrigger.current = trigger;
    directEditHandled.current = true;
    setSelectedKey(recordKey(record));
    setDetail({ status: "ready", record });
    setExtractionSource(null);
    if (creationExpanded) closeCreation({ returnFocus: false });
    setCreationKind(null);
    const values = formFrom(record);
    editBaseline.current = JSON.stringify(values);
    setForm(values);
    setEditing(true);

    edit.open(
      `#/${record.kind === "plant" ? "plants" : "plant-groups"}/${record.value.id}?tab=edit`,
    );
    setSave({ status: "idle" });
  }

  function cancelEditor() {
    if (selected && !extractionSource) {
      edit.close();
      return;
    }
    if (
      !selected &&
      !extractionSource &&
      creationBaseline.current !== "" &&
      !canDiscardCreation()
    )
      return;
    creationBaseline.current = "";
    const wasExtraction = extractionSource !== null;
    setEditing(false);
    setExtractionSource(null);
    setSave({ status: "idle" });
    if (!selected) {
      setCreationKind(null);
      setMobileDetail(false);
      closeCreation();
      closeCollectionPage(
        extractionSource ? `#/plant-groups/${extractionSource.id}` : "#/plants",
      );
    } else if (wasExtraction) {
      window.setTimeout(() => extractionTrigger.current?.focus(), 0);
    } else {
      window.setTimeout(() => detailHeading.current?.focus(), 0);
    }
  }

  function selectRecord(record: PlantRecord, trigger: HTMLButtonElement) {
    setExtractionSource(null);
    if (creationExpanded) closeCreation({ returnFocus: false });
    const key = recordKey(record);
    selectedTrigger.current = trigger;
    if (key !== selectedKey) {
      setDetail({ status: "loading", key });
    } else if (detail.status === "error") {
      setDetail({ status: "loading", key });
      setDetailAttempt((value) => value + 1);
    }
    setSelectedKey(key);
    setMobileDetail(true);
    setRecordRoute(
      `#/${record.kind === "plant" ? "plants" : "plant-groups"}/${record.value.id}`,
    );
    setEditing(false);
    setCreationKind(null);
    setSave({ status: "idle" });
  }

  function returnToList() {
    const trigger = selectedTrigger.current;
    if (creationExpanded) closeCreation({ returnFocus: false });
    setSelectedKey(null);
    setDetail({ status: "idle" });
    setMobileDetail(false);
    setEditing(false);
    setRecordRoute("#/plants", true);
    window.setTimeout(() => {
      (trigger?.isConnected ? trigger : directoryList.current)?.focus();
    }, 0);
  }

  function startExtraction(group: PlantGroupResponse) {
    const parent = window.location.hash.startsWith(`#/plant-groups/${group.id}`)
      ? window.location.hash
      : `#/plant-groups/${group.id}`;
    openCollectionPage(`#/plants?action=extract&source=${group.id}`, parent);
  }

  function startTransfer(record: PlantRecord) {
    transferTrigger.current = recordMoreTrigger.current;
    setTransferTarget(record);
    setTransferDate(null);
    setTransferRecipient("");
    setTransferNotes("");
    setTransferState({ status: "idle" });
  }

  async function submitTransfer(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!transferTarget || transferState.status === "saving" || !csrfToken)
      return;
    setTransferState({ status: "saving" });
    try {
      const payload = {
        occurred_on: transferDate,
        recipient: transferRecipient.trim() || null,
        notes: transferNotes.trim() || null,
      };
      let authoritative: PlantRecord;
      if (transferTarget.kind === "plant") {
        const result = await transferPlant(
          transferTarget.value.id,
          payload,
          csrfToken,
          capability,
        );
        authoritative = { kind: "plant", value: result.plant };
      } else {
        const result = await transferPlantGroup(
          transferTarget.value.id,
          payload,
          csrfToken,
          capability,
        );
        authoritative = { kind: "group", value: result.plant_group };
      }
      const [plants, groups] = await Promise.all([
        listPlants(capability),
        listPlantGroups(capability),
      ]);
      setCollection({
        status: "ready",
        records: [
          ...plants.map((value): PlantRecord => ({ kind: "plant", value })),
          ...groups.map((value): PlantRecord => ({ kind: "group", value })),
        ],
      });
      setDetail({ status: "ready", record: authoritative });
      setSelectedKey(recordKey(authoritative));
      setTransferTarget(null);
      setSave({
        status: "success",
        message:
          authoritative.kind === "plant"
            ? "Plant was transferred and remains available in history."
            : "The entire Plant group was transferred and remains available in history.",
      });
    } catch (error: unknown) {
      if (isExpectedAuthCancellation(error)) {
        setTransferState({ status: "idle" });
        return;
      }
      if (error instanceof ApiError && error.status === 401) {
        setTransferState({ status: "idle" });
        sessionExpired();
        return;
      }
      setTransferState({
        status: "error",
        message:
          error instanceof ApiError && error.status === 409
            ? "This record is no longer active. Reload it before trying again."
            : "Florabase could not transfer this record. Check the details and try again.",
      });
    }
  }

  async function applyReintegrationResult(result: PlantReintegrationResponse) {
    const [plants, groups] = await Promise.all([
      listPlants(capability),
      listPlantGroups(capability),
    ]);
    const authoritative: PlantRecord = { kind: "plant", value: result.plant };
    setCollection({
      status: "ready",
      records: [
        ...plants.map((value): PlantRecord => ({ kind: "plant", value })),
        ...groups.map((value): PlantRecord => ({ kind: "group", value })),
      ],
    });
    setDetail({ status: "ready", record: authoritative });
    setSelectedKey(recordKey(authoritative));
    setSave({
      status: "success",
      message:
        "Plant was reintegrated. Its record and observations remain in history, and the original group snapshot was restored.",
    });
    window.location.hash = `/plants/${result.plant.id}`;
  }

  async function submitReintegration() {
    if (
      selected?.kind !== "plant" ||
      reintegration.status !== "ready" ||
      reintegrationMutation.status === "saving" ||
      !csrfToken
    )
      return;
    setReintegrationMutation({ status: "saving" });
    try {
      const result = await reintegratePlant(
        selected.value.id,
        reintegration.eligibility.status === "confirmation_required",
        csrfToken,
        capability,
      );
      await applyReintegrationResult(result);
      setReintegrationOpen(false);
      setReintegrationMutation({ status: "idle" });
    } catch (error: unknown) {
      if (isExpectedAuthCancellation(error)) {
        setReintegrationMutation({ status: "idle" });
        return;
      }
      if (error instanceof ApiError && error.status === 401) {
        setReintegrationMutation({ status: "idle" });
        sessionExpired();
        return;
      }
      setReintegrationMutation({
        status: "error",
        message:
          error instanceof ApiError && error.status === 409
            ? "Reintegration is no longer safe. Close this dialog and review the updated eligibility details."
            : "Florabase could not reintegrate this Plant. Check the connection and try again.",
      });
    }
  }

  function updateForm<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function refreshEventTarget(kind: RecordKind, id: string) {
    const [target, plants, groups] = await Promise.all([
      kind === "plant"
        ? getPlant(id, capability)
        : getPlantGroup(id, capability),
      listPlants(capability),
      listPlantGroups(capability),
    ]);
    const authoritative = {
      kind,
      value: target,
    } as PlantRecord;
    setDetail({ status: "ready", record: authoritative });
    setCollection({
      status: "ready",
      records: [
        ...plants.map((value): PlantRecord => ({ kind: "plant", value })),
        ...groups.map((value): PlantRecord => ({ kind: "group", value })),
      ],
    });
  }

  function validate(): string[] {
    const errors: string[] = [];
    if (!form.botanicalIdentityId) errors.push("Choose a Botanical identity.");
    if (form.originMode === "sowing" && !form.sowingId)
      errors.push("Choose an originating Sowing.");
    if (
      form.directOriginKind === "other" &&
      form.originMode === "direct" &&
      !form.directOriginDetail.trim()
    )
      errors.push("Describe the other direct origin.");
    if (formKind === "group" && form.quantityKind !== "unknown") {
      const quantity = Number(form.quantityValue);
      if (
        form.quantityValue === "" ||
        !Number.isInteger(quantity) ||
        quantity < 0
      )
        errors.push("Group count must be zero or a positive whole number.");
      else if (form.quantityKind === "approximate" && quantity === 0)
        errors.push("Approximate group count must be greater than zero.");
      else if (
        quantity === 0 &&
        !["completed", "dead", "discarded"].includes(form.lifecycle)
      )
        errors.push(
          "Exact zero is only valid for completed, dead, or discarded groups.",
        );
    }
    return errors;
  }

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    const another = addAnother.current;
    addAnother.current = false;
    if (pending || !formKind || !csrfToken) return;
    const errors = [
      ...validate(),
      ...invalidDateControls(event.currentTarget).map(
        (control) => control.validationMessage,
      ),
    ];
    if (errors.length) {
      setSave({ status: "error", messages: errors });
      return;
    }
    const wasCreating = !selected;
    setSave({ status: "saving" });
    try {
      let authoritative: PlantRecord;
      if (extractionSource) {
        const result = await extractPlantFromGroup(
          extractionSource.id,
          {
            botanical_identity_id: form.botanicalIdentityId,
            location_id: form.locationId || null,
            label: form.label || null,
            collection_entry_date: form.collectionEntryDate,
            notes: form.notes || null,
          },
          csrfToken,
          capability,
        );
        authoritative = { kind: "plant", value: result.plant };
        setCollection((current) => ({
          status: "ready",
          records:
            current.status === "ready"
              ? [
                  authoritative,
                  ...current.records
                    .filter(
                      (record) =>
                        recordKey(record) !== recordKey(authoritative),
                    )
                    .map((record) =>
                      record.kind === "group" &&
                      record.value.id === result.plant_group.id
                        ? ({
                            kind: "group",
                            value: result.plant_group,
                          } satisfies PlantRecord)
                        : record,
                    ),
                ]
              : [
                  authoritative,
                  {
                    kind: "group",
                    value: result.plant_group,
                  } satisfies PlantRecord,
                ],
        }));
        setSelectedKey(recordKey(authoritative));
        setDetail({ status: "ready", record: authoritative });
        setEditing(false);
        setExtractionSource(null);
        setSave({
          status: "success",
          message: "Plant was extracted from the group.",
        });
        setRecordRoute(`#/plants/${authoritative.value.id}`, true);
        return;
      } else if (formKind === "plant") {
        const value = selected
          ? await updatePlant(
              selected.value.id,
              extractedEdit || cuttingEdit
                ? {
                    botanical_identity_id: form.botanicalIdentityId,
                    label: form.label || null,
                    collection_entry_date: form.collectionEntryDate,
                    location_id: form.locationId || null,
                    lifecycle: form.lifecycle as PlantLifecycle,
                    notes: form.notes || null,
                  }
                : plantPayload(form),
              csrfToken,
              capability,
            )
          : await createPlant(plantPayload(form), csrfToken, capability);
        authoritative = { kind: "plant", value };
      } else {
        const value = selected
          ? await updatePlantGroup(
              selected.value.id,
              cuttingEdit
                ? { ...groupPayload(form), direct_origin_kind: null }
                : groupPayload(form),
              csrfToken,
              capability,
            )
          : await createPlantGroup(groupPayload(form), csrfToken, capability);
        authoritative = { kind: "group", value };
      }
      const [plants, groups] = await Promise.all([
        listPlants(capability),
        listPlantGroups(capability),
      ]);
      setCollection({
        status: "ready",
        records: [
          ...plants.map((value): PlantRecord => ({ kind: "plant", value })),
          ...groups.map((value): PlantRecord => ({ kind: "group", value })),
        ],
      });
      if (wasCreating && another) {
        // Stay in the same create form; keep only the botanical identity.
        const nextForm: FormState = {
          ...blankForm(),
          botanicalIdentityId: form.botanicalIdentityId,
        };
        creationBaseline.current = JSON.stringify(nextForm);
        setForm(nextForm);
        setSave({
          status: "success",
          message: `${formKind === "plant" ? "Plant" : "Plant group"} was added to the collection. Add the next one.`,
        });
        window.setTimeout(focusCreation, 0);
        return;
      }
      setSelectedKey(recordKey(authoritative));
      setDetail({ status: "ready", record: authoritative });
      if (edit.modal) edit.close(true);
      setEditing(false);
      setCreationKind(null);
      if (wasCreating) closeCreation();
      setSave({
        status: "success",
        message: wasCreating
          ? `${formKind === "plant" ? "Plant" : "Plant group"} was added to the collection.`
          : `${formKind === "plant" ? "Plant" : "Plant group"} changes were saved.`,
      });
      if (!edit.modal)
        setRecordRoute(
          authoritative.kind === "plant"
            ? `#/plants/${authoritative.value.id}`
            : `#/plant-groups/${authoritative.value.id}`,
          wasCreating,
        );
    } catch (error: unknown) {
      if (isExpectedAuthCancellation(error)) {
        setSave({ status: "idle" });
      } else if (error instanceof ApiError && error.status === 401) {
        setSave({ status: "idle" });
        sessionExpired();
      } else if (error instanceof ApiError && error.status === 422) {
        setSave({
          status: "error",
          messages: plantValidationMessages(error),
          field: firstValidationField(error),
        });
      } else if (
        extractionSource &&
        error instanceof ApiError &&
        error.status === 409
      ) {
        try {
          const refreshed = await getPlantGroup(
            extractionSource.id,
            capability,
          );
          setExtractionSource(refreshed);
          setCollection((current) => ({
            status: "ready",
            records:
              current.status === "ready"
                ? current.records.map((record) =>
                    record.kind === "group" && record.value.id === refreshed.id
                      ? { kind: "group", value: refreshed }
                      : record,
                  )
                : [{ kind: "group", value: refreshed }],
          }));
        } finally {
          setSave({
            status: "error",
            messages: [
              "The Plant group changed before extraction. Its current state has been refreshed; review it and try again.",
            ],
          });
        }
      } else if (error instanceof ApiError && error.status === 403)
        setSave({
          status: "error",
          messages: [
            "Florabase could not authorize this change. Refresh and try again.",
          ],
        });
      else
        setSave({
          status: "error",
          messages: [
            "Florabase could not save or refresh this record. Check the connection and try again.",
          ],
        });
    }
  }

  const editor = editing ? (
    <EditWorkspace
      modal={edit.modal}
      title={formKind === "group" ? "Edit Plant group" : "Edit Plant"}
      returnFocusTo={editTrigger}
      onClose={() => {
        edit.close();
      }}
    >
      {creationExpanded && !creationKind ? (
        <div className="plant-kind-choice">
          <div className="seed-form-heading">
            <div>
              <p className="eyebrow">New collection record</p>
              <h3>What are you tracking?</h3>
            </div>
            <button
              type="button"
              className="button--secondary"
              onClick={() => {
                setEditing(false);
                setMobileDetail(false);
                closeCreation();
                closeCollectionPage("#/plants");
              }}
            >
              Cancel
            </button>
          </div>
          <p>
            Choose individual tracking for one specimen or group tracking for
            multiple individuals managed together.
          </p>
          <div className="plant-kind-actions">
            <button
              type="button"
              data-creation-focus
              onClick={() => {
                chooseCreationKind("plant");
              }}
            >
              <strong>Plant</strong>
              <span>One individually tracked specimen</span>
            </button>
            <button
              type="button"
              onClick={() => {
                chooseCreationKind("group");
              }}
            >
              <strong>Plant group</strong>
              <span>Multiple individuals managed as one record</span>
            </button>
          </div>
        </div>
      ) : formKind ? (
        <form
          ref={formElement}
          className="seed-form plant-form collection-form"
          onClickCapture={(event) => {
            if (!selected || !(event.target instanceof Element)) return;
            const link =
              event.target.closest<HTMLAnchorElement>('a[href^="#"]');
            if (
              link &&
              link.target !== "_blank" &&
              link.hash !== window.location.hash &&
              // Collection task links are approved once by the App handler.
              !(registerFormDeparture && collectionPageParent(link.hash)) &&
              !edit.prepareDeparture()
            )
              event.preventDefault();
          }}
          onSubmit={(event) => void submit(event)}
          noValidate
        >
          <Breadcrumbs
            items={[
              { label: "Plants", href: "#/plants" },
              ...(extractionSource
                ? [
                    {
                      label: recordName(extractionSource, "Source Plant group"),
                      href: `#/plant-groups/${extractionSource.id}`,
                    },
                  ]
                : []),
              {
                label: extractionSource
                  ? "Extract plant"
                  : selected
                    ? "Edit record"
                    : "New record",
              },
            ]}
          />
          <DetailHeader
            eyebrow={formKind === "plant" ? "Plant" : "Plant group"}
            title={
              extractionSource
                ? "Extract plant"
                : selected
                  ? `Edit ${formKind === "plant" ? "Plant" : "Plant group"}`
                  : `Record ${formKind === "plant" ? "Plant" : "Plant group"}`
            }
            headingRef={editorHeading}
            secondary={
              selected && (
                <DetailContext
                  items={[
                    {
                      label: "Record",
                      value: recordName(selected.value, "Unlabelled record"),
                    },
                    {
                      label: "Botanical identity",
                      value: selected.value.botanical_identity.display_label,
                    },
                  ]}
                />
              )
            }
          />
          {extractionSource && (
            <dl
              className="extraction-source-summary"
              aria-label="Extraction summary"
            >
              <div>
                <dt>From</dt>
                <dd>
                  <a href={`#/plant-groups/${extractionSource.id}`}>
                    {recordName(extractionSource, "Unlabelled Plant group")}
                  </a>
                </dd>
              </div>
              <div>
                <dt>Result</dt>
                <dd>Individual Plant</dd>
              </div>
              <div>
                <dt>Group quantity</dt>
                <dd>{extractionQuantityExplanation(extractionSource)}</dd>
              </div>
            </dl>
          )}
          <p className="field-help plant-task-hint">
            {formKind === "plant"
              ? "One individually tracked specimen; no quantity is recorded."
              : "Multiple individuals of one botanical identity managed together. Keep an uncertain count approximate or unknown."}
          </p>
          <FormSections
            key={
              selectedKey ??
              extractionSource?.id ??
              `new:${creationRouteKey ?? formKind}`
            }
            mode={selected && !extractionSource ? "edit" : "page"}
            disabled={pending}
            error={save.status === "error" ? save : undefined}
            errorFields={[
              invalidDateErrorField,
              { match: /supplier/i, selector: "#plant-supplier" },
              { match: /location/i, selector: "#plant-location" },
              {
                match: /provenance site/i,
                selector: "#plant-provenance-site",
              },
              { match: /provenance/i, selector: "#plant-provenance" },
              { match: /identity/i, selector: '[role="combobox"]' },
              {
                match: /sowing/i,
                selector: '[data-form-panel="origin"] [role="combobox"]',
              },
              {
                match: /origin detail|other direct origin/i,
                selector: "#plant-origin-detail",
              },
              {
                match: /count|quantity|exact zero/i,
                selector: "#plant-quantity-value",
              },
              { match: /notes/i, selector: "#plant-notes" },
              {
                match: /collection entry/i,
                selector: "#plant-entry-date-year",
              },
              { match: /label/i, selector: "#plant-label" },
              { match: /lifecycle/i, selector: "#plant-lifecycle" },
            ]}
            panels={[
              {
                id: "essentials",
                label: "Essentials",
                content: (
                  <>
                    <ReferencePicker
                      key={`${selectedKey ?? "new"}-${formKind}-identity`}
                      label="Botanical identity"
                      help="A shared botanical identity keeps the botanical name consistent across records; it does not establish lineage."
                      required
                      disabled={pending}
                      value={form.botanicalIdentityId}
                      onChange={(value) => {
                        updateForm("botanicalIdentityId", value);
                      }}
                      choices={references.identities.map((identity) => ({
                        id: identity.id,
                        label: identity.display_label,
                        scientificName: identity.scientific_name,
                      }))}
                    />
                    <PlantEssentialsFields
                      form={form}
                      updateForm={(key, value) => {
                        setForm((current) => ({
                          ...current,
                          [key]: value,
                        }));
                      }}
                      pending={pending}
                      locations={references.locations}
                      kind={formKind}
                    />
                  </>
                ),
              },
              {
                id: "origin",
                label: "Origin",
                content: (
                  <>
                    {!cuttingEdit && !extractionSource && !extractedEdit ? (
                      <>
                        <fieldset className="origin-mode-field field--full">
                          <legend className="sr-only">Origin</legend>
                          <label className="checkbox-label">
                            <input
                              type="radio"
                              name="origin-mode"
                              checked={form.originMode === "direct"}
                              disabled={pending}
                              onChange={() => {
                                setForm((current) => ({
                                  ...current,
                                  originMode: "direct",
                                  sowingId: "",
                                }));
                              }}
                            />
                            Direct / origin not tracked through a Sowing
                          </label>
                          <label className="checkbox-label">
                            <input
                              type="radio"
                              name="origin-mode"
                              checked={form.originMode === "sowing"}
                              disabled={pending}
                              onChange={() => {
                                setForm((current) => ({
                                  ...current,
                                  originMode: "sowing",
                                  directOriginKind: "unknown",
                                  directOriginDetail: "",
                                  supplierId: "",
                                  provenanceId: "",
                                }));
                              }}
                            />
                            Known Sowing
                          </label>
                        </fieldset>
                        {form.originMode === "sowing" ? (
                          <div className="field--full">
                            <ReferencePicker
                              key={`${selectedKey ?? "new"}-${formKind}-sowing`}
                              label="Originating Sowing"
                              required
                              disabled={pending}
                              value={form.sowingId}
                              onChange={(value) => {
                                updateForm("sowingId", value);
                              }}
                              choices={references.sowings
                                .filter(
                                  (sowing) =>
                                    sowing.lifecycle !== "reversed" ||
                                    sowing.id === form.sowingId,
                                )
                                .map((sowing) => ({
                                  id: sowing.id,
                                  label: sowingChoice(sowing),
                                }))}
                            />
                            <small>
                              Active and historical Sowings are available.
                              Choosing one never changes this record's Botanical
                              identity.
                            </small>
                          </div>
                        ) : (
                          <>
                            <div className="field">
                              <label htmlFor="plant-direct-origin">
                                Direct origin
                              </label>
                              <select
                                id="plant-direct-origin"
                                value={form.directOriginKind}
                                disabled={pending}
                                onChange={(event) => {
                                  const directOriginKind = event.currentTarget
                                    .value as DirectOriginKind;
                                  setForm((current) => ({
                                    ...current,
                                    directOriginKind,
                                    directOriginDetail:
                                      directOriginKind === "other"
                                        ? current.directOriginDetail
                                        : "",
                                  }));
                                }}
                              >
                                {(
                                  Object.keys(
                                    originLabels,
                                  ) as DirectOriginKind[]
                                ).map((kind) => (
                                  <option key={kind} value={kind}>
                                    {originLabels[kind]}
                                  </option>
                                ))}
                              </select>
                            </div>
                            {form.directOriginKind === "other" && (
                              <div className="field">
                                <FieldLabel
                                  htmlFor="plant-origin-detail"
                                  required
                                >
                                  Other origin detail
                                </FieldLabel>
                                <input
                                  id="plant-origin-detail"
                                  aria-required="true"
                                  value={form.directOriginDetail}
                                  disabled={pending}
                                  onChange={(event) => {
                                    updateForm(
                                      "directOriginDetail",
                                      event.currentTarget.value,
                                    );
                                  }}
                                />
                              </div>
                            )}
                            <ReferencePicker
                              id="plant-supplier"
                              label="Supplier"
                              help="Supplier does not establish biological origin."
                              placeholder="Not recorded"
                              disabled={pending}
                              choices={references.suppliers.map((supplier) => ({
                                id: supplier.id,
                                label: supplier.name,
                                retired: Boolean(supplier.retired_at),
                              }))}
                              value={form.supplierId}
                              onChange={(id) => {
                                updateForm("supplierId", id);
                              }}
                            />
                            <ReferencePicker
                              id="plant-provenance"
                              label="Material provenance"
                              help="Where the material originated or was collected."
                              placeholder="Not recorded"
                              disabled={pending}
                              choices={references.places.map((place) => ({
                                id: place.id,
                                label: place.display_path,
                                retired: Boolean(place.retired_at),
                              }))}
                              value={form.provenanceId}
                              onChange={(id) => {
                                updateForm("provenanceId", id);
                              }}
                            />
                            <ReferencePicker
                              id="plant-provenance-site"
                              label="Precise provenance site"
                              placeholder="Not recorded"
                              disabled={pending}
                              choices={references.sites.map((site) => ({
                                id: site.id,
                                label: `${site.geographic_place_path ? `${site.geographic_place_path} → ` : ""}${site.name}`,
                              }))}
                              value={form.provenanceSiteId}
                              onChange={(id) => {
                                updateForm("provenanceSiteId", id);
                              }}
                            />
                          </>
                        )}
                      </>
                    ) : (
                      <div className="field--full inherited-origin">
                        <strong>Origin is read-only.</strong>{" "}
                        {cuttingEdit
                          ? "This specimen was established from cuttings."
                          : extractionSource
                            ? `Inherited from ${recordName(extractionSource, "Unlabelled plant group")}.`
                            : `This Plant was extracted from ${selected?.kind === "plant" ? recordName(selected.value.originating_plant_group, "Unlabelled plant group") : "its Plant group"}.`}
                      </div>
                    )}
                    <PlantEntryDateField
                      form={form}
                      updateForm={(key, value) => {
                        setForm((current) => ({
                          ...current,
                          [key]: value,
                        }));
                      }}
                      pending={pending}
                    />
                  </>
                ),
              },
              {
                id: "lifecycle",
                label: "Lifecycle & notes",
                content: (
                  <>
                    {!extractionSource && (
                      <div className="field">
                        <label htmlFor="plant-lifecycle">Lifecycle</label>
                        <select
                          id="plant-lifecycle"
                          value={form.lifecycle}
                          disabled={pending}
                          onChange={(event) => {
                            updateForm(
                              "lifecycle",
                              event.currentTarget
                                .value as FormState["lifecycle"],
                            );
                          }}
                        >
                          {Object.entries(
                            formKind === "plant"
                              ? plantLifecycleLabels
                              : groupLifecycleLabels,
                          )
                            .filter(
                              ([value]) =>
                                (value !== "reversed" ||
                                  selected?.value.lifecycle === "reversed") &&
                                (value !== "reintegrated" ||
                                  (selected?.kind === "plant" &&
                                    selected.value.lifecycle ===
                                      "reintegrated")),
                            )
                            .map(([value, label]) => (
                              <option key={value} value={value}>
                                {label}
                              </option>
                            ))}
                        </select>
                      </div>
                    )}
                    <PlantNotesField
                      form={form}
                      updateForm={(key, value) => {
                        setForm((current) => ({
                          ...current,
                          [key]: value,
                        }));
                      }}
                      pending={pending}
                    />
                  </>
                ),
              },
            ]}
            submit={
              <>
                <button
                  type="submit"
                  disabled={
                    pending ||
                    (extractionSource !== null &&
                      extractionSource.lifecycle !== "active")
                  }
                >
                  {pending
                    ? "Saving…"
                    : extractionSource
                      ? "Extract plant"
                      : selected
                        ? "Save changes"
                        : `Record ${formKind === "plant" ? "Plant" : "Plant group"}`}
                </button>
                {!selected && !extractionSource && (
                  <button
                    type="submit"
                    className="button--secondary"
                    disabled={pending}
                    onClick={() => {
                      addAnother.current = true;
                    }}
                  >
                    Save and add another
                  </button>
                )}
              </>
            }
            cancel={
              <button
                type="button"
                className="button--secondary"
                disabled={pending}
                onClick={cancelEditor}
              >
                Cancel
              </button>
            }
          />
          {save.status === "error" && (
            <div
              className="notice notice--error"
              role="alert"
              tabIndex={-1}
              ref={feedback}
            >
              <ul>
                {save.messages.map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </div>
          )}
        </form>
      ) : null}
    </EditWorkspace>
  ) : null;

  const maintenanceActions = selected && (
    <>
      {selected.value.lifecycle === "active" && (
        <button
          type="button"
          onClick={() => {
            startTransfer(selected);
          }}
        >
          {selected.kind === "plant" ? "Transfer" : "Transfer group"}
        </button>
      )}
      {selected.kind === "group" && selected.value.lifecycle === "active" && (
        <a
          className="button-link button--secondary"
          href={`#/cuttings/new?sourceType=plant_group&source=${selected.value.id}&identity=${selected.value.botanical_identity_id}`}
        >
          Take cuttings
        </a>
      )}
      <ActionLink
        icon="print"
        className="button-link button--secondary"
        href={labelComposerHref(
          selected.kind === "plant" ? "plant" : "plant-group",
          selected.value.id,
        )}
      >
        Print label
      </ActionLink>
    </>
  );

  return (
    <DirectoryPage
      titleId="plants-title"
      className="plants-workspace"
      header={null}
      content={
        <>
          <div
            className="collection-context-page"
            inert={edit.modal}
            aria-hidden={edit.modal || undefined}
          >
            <WorkspaceIntro
              contextOnly={mobileDetail || (editing && !edit.modal)}
              {...plantPage}
              tools={
                !(mobileDetail || (editing && !edit.modal)) && (
                  <DirectoryTools
                    stableFilterSummary
                    context={
                      identityFilter ? (
                        <a href={`#/identities/${identityFilter}?tab=overview`}>
                          Return to botanical identity
                        </a>
                      ) : undefined
                    }
                    onReset={() => {
                      view.replace({
                        ...view.state,
                        identity_id: "",
                        lifecycle: "all",
                        type: "all",
                      });
                    }}
                    name="Plants"
                    search={
                      <DirectorySearch
                        hideLabel
                        id="plant-search"
                        label="Search Plants"
                        placeholder="Search records, identity or location"
                        value={search}
                        onChange={setSearch}
                      />
                    }
                    presentation={
                      <DirectoryViewSwitcher
                        value={presentation.view}
                        onChange={presentation.select}
                      />
                    }
                    sort={
                      <DirectorySortSelect
                        value={view.state.sort}
                        dateLabel="collection-entry date"
                        onChange={(value) => {
                          view.update("sort", value);
                        }}
                      />
                    }
                    savedViews={
                      <SavedViews
                        presentation="dialog"
                        surface="plants"
                        state={view.savedState}
                      />
                    }
                    filters={
                      <>
                        <BotanicalIdentityFilter
                          choices={Array.from(
                            new Map(
                              records.map((record) => [
                                record.value.botanical_identity_id,
                                {
                                  id: record.value.botanical_identity_id,
                                  label:
                                    record.value.botanical_identity
                                      .display_label,
                                },
                              ]),
                            ).values(),
                          )}
                          value={identityFilter}
                          onChange={(id) => {
                            view.update("identity_id", id);
                          }}
                        />
                        <DirectoryFilterSelect
                          label="Lifecycle"
                          value={lifecycleFilter}
                          onChange={setLifecycleFilter}
                          options={[
                            { value: "active", label: "Active" },
                            { value: "history", label: "History" },
                            { value: "all", label: "All" },
                          ]}
                        />
                        <DirectoryFilterSelect
                          label="Record type"
                          value={typeFilter}
                          onChange={setTypeFilter}
                          options={[
                            { value: "all", label: "All" },
                            { value: "plant", label: "Plants" },
                            { value: "group", label: "Groups" },
                          ]}
                        />
                      </>
                    }
                    activeFilters={[
                      ...(identityFilter
                        ? [
                            {
                              label: "Botanical identity",
                              value:
                                references.identities.find(
                                  ({ id }) => id === identityFilter,
                                )?.display_label ?? identityFilter,
                              onRemove: () => {
                                view.update("identity_id", "");
                              },
                            },
                          ]
                        : []),
                      ...(lifecycleFilter !== "all"
                        ? [
                            {
                              label: "Lifecycle",
                              value:
                                lifecycleFilter === "active"
                                  ? "Active"
                                  : "History",
                              onRemove: () => {
                                setLifecycleFilter("all");
                              },
                            },
                          ]
                        : []),
                      ...(typeFilter !== "all"
                        ? [
                            {
                              label: "Record type",
                              value:
                                typeFilter === "plant" ? "Plants" : "Groups",
                              onRemove: () => {
                                setTypeFilter("all");
                              },
                            },
                          ]
                        : []),
                    ]}
                    actions={
                      <>
                        <ActionButton
                          icon="add"
                          type="button"
                          ref={creationTriggerRef}
                          data-collection-return="create"
                          aria-expanded={creationExpanded}
                          aria-controls="new-plant-panel"
                          disabled={references.identities.length === 0}
                          onClick={() => {
                            if (creationExpanded) focusCreation();
                            else startCreate();
                          }}
                        >
                          New plant or group
                        </ActionButton>
                      </>
                    }
                  />
                )
              }
            />
            {extractionRouteError && !extractionSource && (
              <div role="alert">
                <p>{extractionRouteError}</p>
                <ActionLink icon="back" href="#/plants">
                  Back to Plants
                </ActionLink>
              </div>
            )}
            {references.identities.length === 0 && (
              <div className="notice" role="status">
                <p>
                  A Botanical identity is required before you can record a Plant
                  or Plant group.{" "}
                  <a href="#/identities">Open Botanical identities</a> to add
                  one.
                </p>
              </div>
            )}

            <DirectoryWorkspace
              className={
                mobileDetail || (editing && !edit.modal)
                  ? "is-detail-view"
                  : undefined
              }
            >
              {!(mobileDetail || (editing && !edit.modal)) &&
                collection.status === "ready" && (
                  <DirectoryResults
                    count={filtered.length}
                    total={records.length}
                    pagination={pagination}
                    actions={
                      <BulkSelect
                        selection={bulk}
                        visible={bulkChoices}
                        onStart={() => {
                          setSelectedKey(null);
                          setMobileDetail(false);
                          setDetail({ status: "idle" });
                        }}
                      />
                    }
                  />
                )}
              {!(mobileDetail || (editing && !edit.modal)) && (
                <section
                  className="seed-master plant-master"
                  aria-labelledby="plant-list-title"
                >
                  <div className="plant-directory-heading">
                    <h3 className="sr-only" id="plant-list-title">
                      Plants collection
                    </h3>
                  </div>
                  <BulkToolbar
                    selection={bulk}
                    visible={bulkChoices}
                    onSuccess={() => {
                      setSelectedKey(null);
                      setMobileDetail(false);
                      setDetail({ status: "idle" });
                      setAttempt((value) => value + 1);
                    }}
                  />
                  {records.length === 0 ? (
                    <div className="profile-empty">
                      <h4>No Plants recorded yet</h4>
                      {references.identities.length > 0 && (
                        <p>
                          Use New plant or group to record the first Plant or
                          Plant group.
                        </p>
                      )}
                    </div>
                  ) : visible.length === 0 ? (
                    <p>No Plants match this search and filter view.</p>
                  ) : (
                    <DirectoryRecords
                      view={presentation.view}
                      label="Plants collection"
                      photoTitles={presentation.view === "gallery"}
                      listRef={directoryList}
                    >
                      {visible.map((record, bulkIndex) => {
                        const value = record.value;
                        return (
                          <DirectoryItem
                            onClick={(event) => {
                              bulk.recordClick(event, bulkChoices[bulkIndex]);
                            }}
                            key={recordKey(record)}
                            previewId={recordKey(record)}
                            selected={
                              bulk.active
                                ? bulk.checked({
                                    kind:
                                      record.kind === "plant"
                                        ? "plant"
                                        : "plant_group",
                                    id: value.id,
                                  })
                                : selectedKey === recordKey(record)
                            }
                          >
                            <BulkCheckbox
                              selection={bulk}
                              choice={bulkChoices[bulkIndex]}
                            />
                            <DirectoryTrigger
                              type="button"
                              className="ui-directory-trigger"
                              description={`${lifecycleLabel(record)} · Open details`}
                              aria-pressed={selectedKey === recordKey(record)}
                              onClick={(event) => {
                                if (
                                  bulk.recordClick(
                                    event,
                                    bulkChoices[bulkIndex],
                                  )
                                )
                                  return;
                                selectRecord(record, event.currentTarget);
                              }}
                            >
                              <DirectoryRecordContent
                                visual={
                                  <RecordVisual
                                    showSource={presentation.view === "gallery"}
                                    photo={value.primary_photo ?? null}
                                    label={
                                      value.label ??
                                      (record.kind === "plant"
                                        ? "plant"
                                        : "plant group")
                                    }
                                    compact

                                    identity={value.botanical_identity}
                                    kind={record.kind}
                                  />
                                }
                                name={
                                  <>
                                    {recordName(
                                      value,
                                      value.botanical_identity.display_label,
                                    )}
                                  </>
                                }
                                secondary={
                                  <>
                                    <BotanicalName
                                      label={
                                        value.botanical_identity.display_label
                                      }
                                      scientificName={scientificNames.get(
                                        value.botanical_identity_id,
                                      )}
                                    />
                                  </>
                                }
                                summary={
                                  <>
                                    {record.kind === "plant"
                                      ? "Plant"
                                      : "Group"}
                                    {record.kind === "group" && (
                                      <strong
                                        className={
                                          record.value.quantity
                                            ? undefined
                                            : "ui-record-unknown"
                                        }
                                      >
                                        {quantityLabel(record)}
                                      </strong>
                                    )}
                                  </>
                                }
                                status={
                                  value.lifecycle === "active" ? (
                                    <StatusBadge compactState="active">
                                      Active
                                    </StatusBadge>
                                  ) : (
                                    <>
                                      <LifecycleStatus state={value.lifecycle}>
                                        {lifecycleLabel(record)}
                                      </LifecycleStatus>
                                    </>
                                  )
                                }
                              />
                            </DirectoryTrigger>
                            <DirectoryRecordActions
                              label={recordName(
                                value,
                                value.botanical_identity.display_label,
                              )}
                              onDetails={(trigger) => {
                                selectRecord(record, trigger);
                              }}
                              extraActions={
                                <ActionLink
                                  className="ui-directory-quick-action"
                                  icon="harvest"
                                  aria-label={`Record harvest from ${recordName(value, value.botanical_identity.display_label)}`}
                                  title="Record harvest"
                                  href={`#/harvests?action=create&sourceType=${record.kind === "plant" ? "plant" : "plant_group"}&source=${value.id}`}
                                >
                                  <span className="sr-only">
                                    Record harvest
                                  </span>
                                </ActionLink>
                              }
                              onEdit={(trigger) => {
                                setSelectedKey(recordKey(record));
                                startEdit(record, trigger);
                              }}
                            />
                          </DirectoryItem>
                        );
                      })}
                    </DirectoryRecords>
                  )}
                </section>
              )}
              {(creationExpanded || editing || mobileDetail) && (
                <section
                  id={creationExpanded ? "new-plant-panel" : undefined}
                  className={`seed-detail-pane plant-detail-pane${creationExpanded ? " seed-creation-panel" : ""}`}
                  ref={creationExpanded ? creationPanelRef : undefined}
                  aria-label="Plant detail and editor"
                >
                  {save.status === "success" && (
                    <div className="notice notice--success" role="status">
                      {save.message}
                    </div>
                  )}
                  {editing && !edit.modal ? (
                    editor
                  ) : detail.status === "loading" &&
                    (mobileDetail || !selected) ? (
                    <DetailLoading
                      eyebrow="Plants"
                      label="Loading Plant detail…"
                      parents={[
                        { label: "Collection", href: "#/dashboard" },
                        { label: "Plants", href: "#/plants" },
                      ]}
                      className="plant-detail"
                    />
                  ) : detail.status === "error" &&
                    (mobileDetail || !selected) ? (
                    <div className="notice notice--error" role="alert">
                      <p>Florabase could not load this record.</p>
                      <button
                        type="button"
                        onClick={() => {
                          if (selectedKey)
                            setDetail({ status: "loading", key: selectedKey });
                          setDetailAttempt((value) => value + 1);
                        }}
                      >
                        Retry detail
                      </button>
                    </div>
                  ) : selected ? (
                    mobileDetail ? (
                      <div className="selected-seed selected-plant">
                        <Detail
                          key={recordKey(selected)}
                          record={selected}
                          extractedPlants={records.flatMap((record) =>
                            record.kind === "plant" &&
                            record.value.originating_plant_group_id ===
                              selected.value.id
                              ? [record.value]
                              : [],
                          )}
                          onPrimaryChanged={(photo) => {
                            setDetail((current) =>
                              current.status === "ready" &&
                              recordKey(current.record) === recordKey(selected)
                                ? {
                                    status: "ready",
                                    record: {
                                      ...current.record,
                                      value: {
                                        ...current.record.value,
                                        primary_photo: photo,
                                      },
                                    } as PlantRecord,
                                  }
                                : current,
                            );
                            setCollection((current) =>
                              current.status === "ready"
                                ? {
                                    status: "ready",
                                    records: current.records.map((record) =>
                                      recordKey(record) === recordKey(selected)
                                        ? ({
                                            ...record,
                                            value: {
                                              ...record.value,
                                              primary_photo: photo,
                                            },
                                          } as PlantRecord)
                                        : record,
                                    ),
                                  }
                                : current,
                            );
                          }}
                          locations={references.locations}
                          headingRef={detailHeading}
                          onEventTargetRefresh={async () => {
                            try {
                              await refreshEventTarget(
                                selected.kind,
                                selected.value.id,
                              );
                            } finally {
                              setReversalRevision((value) => value + 1);
                            }
                          }}
                          onEdit={(trigger) => {
                            startEdit(selected, trigger);
                          }}
                          onReturnToList={returnToList}
                          primaryActions={
                            selected.kind === "group" &&
                            selected.value.lifecycle === "active" ? (
                              <button
                                ref={extractionTrigger}
                                data-collection-return="extract"
                                type="button"
                                onClick={() => {
                                  startExtraction(selected.value);
                                }}
                              >
                                Extract plant
                              </button>
                            ) : undefined
                          }
                          potOnAction={
                            selected.kind === "group" ? (
                              <PotOnLauncher
                                source={{
                                  kind: "group",
                                  group: selected.value,
                                }}
                                identities={references.identities}
                                locations={references.locations}
                                fallbackFocusTo={detailHeading}
                                onGroupUpdated={(updatedGroup, created) => {
                                  const authoritative: PlantRecord = {
                                    kind: "group",
                                    value: updatedGroup,
                                  };
                                  setDetail({
                                    status: "ready",
                                    record: authoritative,
                                  });
                                  setCollection((current) =>
                                    current.status === "ready"
                                      ? {
                                          ...current,
                                          records: [
                                            ...created.map(
                                              (plant): PlantRecord => ({
                                                kind: "plant",
                                                value: plant,
                                              }),
                                            ),
                                            ...current.records.map((record) =>
                                              recordKey(record) ===
                                              recordKey(authoritative)
                                                ? authoritative
                                                : record,
                                            ),
                                          ],
                                        }
                                      : current,
                                  );
                                  setReversalRevision((value) => value + 1);
                                }}
                              />
                            ) : undefined
                          }
                          moreActions={maintenanceActions}
                          moreTrigger={recordMoreTrigger}
                          reversalAction={
                            selected.value.originating_sowing_id && (
                              <CreationReversal
                                inMoreMenu
                                moreActions={maintenanceActions}
                                triggerRef={recordMoreTrigger}
                                key={`reversal:${recordKey(selected)}`}
                                kind={
                                  selected.kind === "plant"
                                    ? "plant"
                                    : "plant_group"
                                }
                                id={selected.value.id}
                                lifecycle={selected.value.lifecycle}
                                revision={`${selected.value.updated_at}:${String(reversalRevision)}`}
                                onReversed={(result) => {
                                  if ("seed_lot" in result) return;
                                  const authoritative: PlantRecord =
                                    "plant" in result
                                      ? { kind: "plant", value: result.plant }
                                      : {
                                          kind: "group",
                                          value: result.plant_group,
                                        };
                                  setDetail({
                                    status: "ready",
                                    record: authoritative,
                                  });
                                  setCollection((current) =>
                                    current.status === "ready"
                                      ? {
                                          ...current,
                                          records: current.records.map(
                                            (record) =>
                                              recordKey(record) ===
                                              recordKey(authoritative)
                                                ? authoritative
                                                : record,
                                          ),
                                        }
                                      : current,
                                  );
                                  setReferences((current) =>
                                    current
                                      ? {
                                          ...current,
                                          sowings: current.sowings.map(
                                            (sowing) =>
                                              sowing.id === result.sowing.id
                                                ? result.sowing
                                                : sowing,
                                          ),
                                        }
                                      : current,
                                  );
                                }}
                              />
                            )
                          }
                          initialTab={initialTab}
                        />
                        {selected.kind === "group" &&
                          selected.value.lifecycle !== "active" && (
                            <p className="field-help">
                              Plants can only be extracted from an active group.
                            </p>
                          )}
                        {selected.kind === "plant" &&
                          selected.value.originating_plant_group && (
                            <section
                              className="notice reintegration-panel"
                              aria-labelledby="reintegration-action-title"
                            >
                              <h4 id="reintegration-action-title">
                                Original Plant group
                              </h4>
                              <p>
                                <a
                                  href={`#/plant-groups/${selected.value.originating_plant_group.id}`}
                                >
                                  {recordName(
                                    selected.value.originating_plant_group,
                                    "Unlabelled plant group",
                                  )}
                                </a>
                              </p>
                              {selected.value.lifecycle === "reintegrated" ? (
                                <p>
                                  This Plant has been reintegrated and remains
                                  available as historical extraction evidence.
                                </p>
                              ) : reintegration.status === "loading" ? (
                                <p role="status">
                                  Checking reintegration eligibility…
                                </p>
                              ) : reintegration.status === "error" ? (
                                <p role="alert">
                                  Florabase could not check reintegration
                                  eligibility.
                                </p>
                              ) : reintegration.status === "ready" ? (
                                <>
                                  {reintegration.eligibility.status ===
                                    "blocked" && (
                                    <ul>
                                      {reintegration.eligibility.reasons.map(
                                        (reason) => (
                                          <li key={reason.code}>
                                            {reason.message}
                                          </li>
                                        ),
                                      )}
                                    </ul>
                                  )}
                                  {reintegration.eligibility.status ===
                                    "confirmation_required" && (
                                    <p>
                                      {
                                        reintegration.eligibility
                                          .retained_observations.length
                                      }{" "}
                                      observation(s) will remain on this
                                      historical Plant.
                                    </p>
                                  )}
                                  <button
                                    type="button"
                                    className="button--secondary"
                                    disabled={
                                      reintegration.eligibility.status ===
                                      "blocked"
                                    }
                                    onClick={(event) => {
                                      reintegrationTrigger.current =
                                        event.currentTarget;
                                      setReintegrationMutation({
                                        status: "idle",
                                      });
                                      setReintegrationOpen(true);
                                    }}
                                  >
                                    Reintegrate into group
                                  </button>
                                </>
                              ) : null}
                            </section>
                          )}
                      </div>
                    ) : null
                  ) : null}
                </section>
              )}
            </DirectoryWorkspace>
            {reintegrationOpen &&
              selected?.kind === "plant" &&
              selected.value.originating_plant_group &&
              reintegration.status === "ready" && (
                <div
                  className="dialog-backdrop"
                  role="presentation"
                  onMouseDown={(event) => {
                    if (
                      event.target === event.currentTarget &&
                      reintegrationMutation.status !== "saving"
                    )
                      setReintegrationOpen(false);
                  }}
                >
                  <div
                    className="context-dialog event-dialog"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="reintegration-title"
                    ref={reintegrationDialog}
                    onKeyDown={(event) => {
                      if (
                        event.key === "Escape" &&
                        reintegrationMutation.status !== "saving"
                      ) {
                        setReintegrationOpen(false);
                        return;
                      }
                      if (event.key !== "Tab" || !reintegrationDialog.current)
                        return;
                      const focusable = Array.from(
                        reintegrationDialog.current.querySelectorAll<HTMLElement>(
                          "button:not([disabled])",
                        ),
                      );
                      const first = focusable.at(0);
                      const last = focusable.at(-1);
                      if (event.shiftKey && document.activeElement === first) {
                        event.preventDefault();
                        last?.focus();
                      } else if (
                        !event.shiftKey &&
                        document.activeElement === last
                      ) {
                        event.preventDefault();
                        first?.focus();
                      }
                    }}
                  >
                    <h3 id="reintegration-title">
                      Reintegrate into original group?
                    </h3>
                    <p>
                      This Plant will stop being an active individual. Its
                      identity, lineage, notes, and recorded history will remain
                      available.
                    </p>
                    <p>
                      Florabase will restore the recorded pre-extraction state
                      of{" "}
                      <strong>
                        {recordName(
                          selected.value.originating_plant_group,
                          "Unlabelled plant group",
                        )}
                      </strong>{" "}
                      and add one reintegration record to that group.
                    </p>
                    {reintegration.eligibility.status ===
                      "confirmation_required" && (
                      <div className="notice">
                        <p>
                          Confirm that these observations should remain attached
                          to the historical Plant:
                        </p>
                        <ul>
                          {reintegration.eligibility.retained_observations.map(
                            (observation) => (
                              <li key={observation.id}>
                                {observation.kind}
                                {observation.notes
                                  ? ` — ${observation.notes}`
                                  : ""}
                              </li>
                            ),
                          )}
                        </ul>
                      </div>
                    )}
                    {reintegrationMutation.status === "error" && (
                      <div className="notice notice--error" role="alert">
                        {reintegrationMutation.message}
                      </div>
                    )}
                    <div className="actions">
                      <button
                        type="button"
                        autoFocus
                        disabled={reintegrationMutation.status === "saving"}
                        onClick={() => void submitReintegration()}
                      >
                        {reintegrationMutation.status === "saving"
                          ? "Reintegrating…"
                          : reintegration.eligibility.status ===
                              "confirmation_required"
                            ? "Confirm and reintegrate"
                            : "Reintegrate Plant"}
                      </button>
                      <button
                        type="button"
                        className="button--secondary"
                        disabled={reintegrationMutation.status === "saving"}
                        onClick={() => {
                          setReintegrationOpen(false);
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              )}
            {transferTarget && (
              <div
                className="dialog-backdrop"
                role="presentation"
                onMouseDown={(event) => {
                  if (
                    event.target === event.currentTarget &&
                    transferState.status !== "saving"
                  )
                    setTransferTarget(null);
                }}
              >
                <div
                  className="context-dialog event-dialog"
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="transfer-title"
                  ref={transferDialog}
                  onKeyDown={(event) => {
                    if (
                      event.key === "Escape" &&
                      transferState.status !== "saving"
                    ) {
                      setTransferTarget(null);
                      return;
                    }
                    if (event.key !== "Tab" || !transferDialog.current) return;
                    const focusable = Array.from(
                      transferDialog.current.querySelectorAll<HTMLElement>(
                        "button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])",
                      ),
                    );
                    const first = focusable.at(0);
                    const last = focusable.at(-1);
                    if (event.shiftKey && document.activeElement === first) {
                      event.preventDefault();
                      last?.focus();
                    } else if (
                      !event.shiftKey &&
                      document.activeElement === last
                    ) {
                      event.preventDefault();
                      first?.focus();
                    }
                  }}
                >
                  <h3 id="transfer-title">
                    {transferTarget.kind === "plant"
                      ? "Transfer"
                      : "Transfer group"}
                  </h3>
                  <p>
                    {transferTarget.kind === "plant"
                      ? "This Plant will leave the active collection but remain fully available in history."
                      : "The entire Plant group will leave the active collection. Its quantity and historical record will be preserved."}
                  </p>
                  {transferTarget.kind === "group" && (
                    <p className="notice">
                      There is no partial group transfer. To transfer one
                      individual, cancel and extract it as a Plant first.
                    </p>
                  )}
                  <form
                    className="event-form"
                    onSubmit={(event) => void submitTransfer(event)}
                  >
                    <PartialDateField
                      id="transfer-date"
                      label="Transfer date"
                      value={transferDate}
                      disabled={transferState.status === "saving"}
                      onChange={setTransferDate}
                    />
                    <div className="field">
                      <label htmlFor="transfer-recipient">Recipient</label>
                      <input
                        id="transfer-recipient"
                        autoFocus
                        maxLength={255}
                        value={transferRecipient}
                        disabled={transferState.status === "saving"}
                        onChange={(event) => {
                          setTransferRecipient(event.currentTarget.value);
                        }}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="transfer-notes">Notes</label>
                      <textarea
                        id="transfer-notes"
                        value={transferNotes}
                        disabled={transferState.status === "saving"}
                        onChange={(event) => {
                          setTransferNotes(event.currentTarget.value);
                        }}
                      />
                    </div>
                    {transferState.status === "error" && (
                      <div className="notice notice--error" role="alert">
                        {transferState.message}
                      </div>
                    )}
                    <div className="actions">
                      <button
                        type="submit"
                        disabled={transferState.status === "saving"}
                      >
                        {transferState.status === "saving"
                          ? "Transferring…"
                          : transferTarget.kind === "plant"
                            ? "Transfer Plant"
                            : "Transfer entire group"}
                      </button>
                      <button
                        type="button"
                        className="button--secondary"
                        disabled={transferState.status === "saving"}
                        onClick={() => {
                          setTransferTarget(null);
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
          {edit.modal && editor}
        </>
      }
    />
  );
}
