import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { expect, test } from "vitest";
import {
  DirectoryTools,
  DirectorySearch,
  DirectoryFilterSelect,
} from "./DirectoryTools";

function DirectoryHarness() {
  const [search, setSearch] = useState("basil");
  const [lifecycle, setLifecycle] = useState("active");
  const [type, setType] = useState("group");
  return (
    <DirectoryTools
      name="Plants"
      search={
        <DirectorySearch
          id="search"
          label="Search Plants"
          placeholder="Search records"
          value={search}
          onChange={setSearch}
          hideLabel
        />
      }
      filters={
        <>
          <DirectoryFilterSelect
            label="Lifecycle"
            value={lifecycle}
            onChange={setLifecycle}
            options={[
              { value: "all", label: "All" },
              { value: "active", label: "Active" },
              { value: "history", label: "History" },
            ]}
          />
          <DirectoryFilterSelect
            label="Record type"
            value={type}
            onChange={setType}
            options={[
              { value: "all", label: "All" },
              { value: "group", label: "Groups" },
            ]}
          />
        </>
      }
      activeFilters={[
        ...(lifecycle !== "all"
          ? [
              {
                label: "Lifecycle",
                value: lifecycle,
                onRemove: () => {
                  setLifecycle("all");
                },
              },
            ]
          : []),
        ...(type !== "all"
          ? [
              {
                label: "Record type",
                value: type,
                onRemove: () => {
                  setType("all");
                },
              },
            ]
          : []),
      ]}
      onReset={() => {
        setLifecycle("all");
        setType("all");
      }}
    />
  );
}

test("live directory filters count dimensions, dismiss safely, reset together and preserve search", async () => {
  const user = userEvent.setup();
  render(<DirectoryHarness />);
  const trigger = screen.getByRole("button", { name: "Filters (2)" });
  await user.click(trigger);
  const drawer = screen.getByRole("dialog", { name: "Plants filters" });
  expect(within(drawer).getByRole("button", { name: "Close" })).toHaveFocus();
  await user.selectOptions(
    within(drawer).getByLabelText("Lifecycle"),
    "history",
  );
  expect(
    screen.getByRole("button", { name: "Remove lifecycle filter" }),
  ).toHaveTextContent("history");
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
  await user.click(trigger);
  await user.click(screen.getByRole("button", { name: "Reset filters" }));
  expect(
    screen.queryByRole("group", { name: "Active filters" }),
  ).not.toBeInTheDocument();
  expect(
    within(screen.getByRole("dialog")).getByLabelText("Lifecycle"),
  ).toHaveValue("all");
  expect(
    within(screen.getByRole("dialog")).getByLabelText("Record type"),
  ).toHaveValue("all");
  await user.click(screen.getByRole("button", { name: "Done" }));
  expect(screen.getByRole("searchbox", { name: "Search Plants" })).toHaveValue(
    "basil",
  );
  expect(screen.getByRole("button", { name: "Filters" })).toHaveFocus();
});
