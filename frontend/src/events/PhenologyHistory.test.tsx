import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import type { EventResponse } from "./api";
import { PhenologyHistory } from "./PhenologyHistory";
afterEach(cleanup);

const base: EventResponse = {
  id: "event",
  kind: "observation",
  occurred_on: null,
  notes: null,
  target: {
    type: "plant",
    id: "plant",
    label: "Fig",
    lifecycle: "dead",
    botanical_identity: { id: "identity", display_label: "Ficus carica" },
  },
  destination_location_id: null,
  destination_location: null,
  recipient: null,
  resulting_plant_id: null,
  resulting_plant: null,
  measurement_corrections: [],
  created_at: "2026-09-30T00:00:00Z",
  updated_at: "2026-09-30T00:00:00Z",
};
type Phase = NonNullable<EventResponse["phenology"]>["phase"];
const day = (year: number, month: number, d: number) =>
  ({ precision: "day", year, month, day: d }) as const;
let serial = 0;
function staged(
  kind: EventResponse["kind"],
  occurred_on: EventResponse["occurred_on"],
  phase: Phase | null,
  approximate = false,
): EventResponse {
  serial += 1;
  return {
    ...base,
    id: `event-${String(serial)}`,
    kind,
    occurred_on,
    phenology: phase ? { phase, date_is_approximate: approximate } : null,
  };
}

const events = [
  // Three successive years of flowering; 2026 only known to the month.
  staged("flowering", day(2024, 5, 20), "flowering_onset"),
  staged(
    "fruiting",
    { precision: "month", year: 2024, month: 8 },
    "fruit_ripening",
  ),
  // Two flowering onsets in 2025 and no fruiting observation that year.
  staged("flowering", day(2025, 9, 2), "flowering_onset"),
  staged("flowering", day(2025, 5, 14), "flowering_onset"),
  staged(
    "flowering",
    { precision: "month", year: 2026, month: 5 },
    "flowering_onset",
  ),
  staged("fruiting", day(2026, 9, 2), "fruit_ripening", true),
  // Incomplete dates and a pre-existing stage-less flowering entry.
  staged("observation", { precision: "year", year: 2023 }, "leaf_fall"),
  staged("flowering", day(2023, 6, 1), null),
  staged("observation", null, "dormancy_entry"),
  // Not phenology: an ordinary note and a measurement.
  staged("observation", day(2025, 1, 1), null),
  {
    ...staged("measurement", day(2025, 6, 1), null),
    measurement: {
      quantity: "height" as const,
      value: "40",
      unit: "cm" as const,
      is_approximate: false,
    },
  },
];

function year(name: string) {
  return screen.getByRole("group", { name });
}

test("year-by-year phenology shows recorded evidence only, at its recorded precision", async () => {
  const onShow = vi.fn();
  render(
    <PhenologyHistory
      targetId="plant"
      events={events}
      onRecord={vi.fn()}
      onShow={onShow}
    />,
  );
  const section = screen.getByRole("region", { name: "Phenology" });
  // Newest year first, undated observations last.
  expect(
    within(section)
      .getAllByRole("heading", { level: 6 })
      .map((heading) => heading.textContent),
  ).toEqual(["2026", "2025", "2024", "2023", "Date not recorded"]);

  expect(
    within(year("2024"))
      .getByText(/Flowering began/)
      .closest("li"),
  ).toHaveTextContent("Flowering began: 20 May");
  expect(
    within(year("2024"))
      .getByText(/Fruit ripening/)
      .closest("li"),
  ).toHaveTextContent("Fruit ripening: Aug");
  // Repeated flowering is listed in seasonal order, not merged.
  expect(
    within(year("2025"))
      .getByText(/Flowering began/)
      .closest("li"),
  ).toHaveTextContent("Flowering began: 14 May, 2 Sep");
  // Absence of a record is never absence of the stage.
  expect(
    within(year("2025")).getByText("No “Fruit ripening” observation recorded"),
  ).toBeInTheDocument();
  expect(section).not.toHaveTextContent(
    /no fruiting|no flowering|first flowering ever/i,
  );
  expect(
    within(year("2026"))
      .getByText(/Flowering began/)
      .closest("li"),
  ).toHaveTextContent("Flowering began: May");
  expect(
    within(year("2026"))
      .getByText(/Fruit ripening/)
      .closest("li"),
  ).toHaveTextContent("Fruit ripening: about 2 Sep");
  // A year-only date is never placed in a month.
  expect(
    within(year("2023"))
      .getByText(/Leaf loss/)
      .closest("li"),
  ).toHaveTextContent("Leaf loss: month not recorded");
  expect(
    year("2023").querySelectorAll(".phenology-months .phenology-mark"),
  ).toHaveLength(1);
  expect(
    within(year("2023")).getByText(/Flowering, stage not recorded/),
  ).toBeInTheDocument();
  expect(
    within(year("Date not recorded"))
      .getByText(/Entering dormancy/)
      .closest("li"),
  ).toHaveTextContent("Entering dormancy: date not recorded");
  // A month-only observation is drawn across its month, not as a day dot.
  expect(year("2026").querySelectorAll(".phenology-mark--month")).toHaveLength(
    1,
  );
  // Notes and measurements are not phenology.
  expect(section).not.toHaveTextContent("1 Jan");
  expect(section).not.toHaveTextContent("40 cm");

  // Each date links to its underlying Journal entry by keyboard.
  const user = userEvent.setup();
  within(year("2025"))
    .getByRole("button", {
      name: "Flowering began, 2 Sep 2025: show Journal entry",
    })
    .focus();
  await user.keyboard("{Enter}");
  expect(onShow).toHaveBeenCalledWith(events[2]);
});

test("an empty phenology history invites recording without implying absence", async () => {
  const onRecord = vi.fn();
  render(
    <PhenologyHistory
      targetId="plant"
      events={[events[9]]}
      onRecord={onRecord}
      onShow={vi.fn()}
    />,
  );
  expect(
    screen.getByText(/No phenology observations recorded yet/),
  ).toBeInTheDocument();
  await userEvent
    .setup()
    .click(screen.getByRole("button", { name: "Record phenology" }));
  expect(onRecord).toHaveBeenCalledOnce();
});
