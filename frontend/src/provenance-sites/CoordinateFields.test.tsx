import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { FormSections } from "../components/FormSections";
import { CoordinateFields } from "./CoordinateFields";
afterEach(cleanup);
function Harness({ save }: { save: (lat: string, lon: string) => void }) {
  const [values, setValues] = useState({
    lat: "38.166666666667",
    lon: "13.350123456789",
  });
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        save(values.lat, values.lon);
      }}
    >
      <FormSections
        panels={[
          {
            id: "coordinates",
            label: "Coordinates",
            content: (
              <CoordinateFields
                latitude={values.lat}
                longitude={values.lon}
                disabled={false}
                onChange={(lat, lon) => {
                  setValues({ lat, lon });
                }}
              />
            ),
          },
          { id: "notes", label: "Notes", content: <p>Finish</p> },
        ]}
        submit={<button type="submit">Save</button>}
        cancel={null}
      />
    </form>
  );
}
test("toggling coordinate modes alone preserves original decimal precision", async () => {
  const user = userEvent.setup(),
    save = vi.fn();
  render(<Harness save={save} />);
  await user.click(screen.getByLabelText("Degrees / minutes / seconds"));
  expect(
    screen.getByLabelText("Degrees", { selector: "#site-latitude-degrees" }),
  ).toHaveValue(38);
  await user.click(screen.getByLabelText("Decimal degrees"));
  expect(screen.getByLabelText("Latitude (WGS84 decimal)")).toHaveValue(
    38.166666666667,
  );
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(save).toHaveBeenCalledWith("38.166666666667", "13.350123456789");
});
test("DMS submits signed decimals and reveals/focuses hidden invalid boundary combinations", async () => {
  const user = userEvent.setup(),
    save = vi.fn();
  render(<Harness save={save} />);
  await user.click(screen.getByLabelText("Degrees / minutes / seconds"));
  await user.selectOptions(
    screen.getByLabelText("Hemisphere", {
      selector: "#site-latitude-direction",
    }),
    "S",
  );
  await user.selectOptions(
    screen.getByLabelText("Hemisphere", {
      selector: "#site-longitude-direction",
    }),
    "W",
  );
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(save).toHaveBeenCalledOnce();
  expect(Number(save.mock.calls[0][0])).toBeCloseTo(-38.166666666667, 11);
  await user.click(screen.getByRole("tab", { name: "Coordinates" }));
  const degrees = screen.getByLabelText("Degrees", {
    selector: "#site-latitude-degrees",
  });
  await user.clear(degrees);
  await user.type(degrees, "90");
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  await user.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => {
    expect(screen.getByRole("tab", { name: "Coordinates" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
  expect(degrees).toHaveFocus();
  expect(save).toHaveBeenCalledOnce();
});
