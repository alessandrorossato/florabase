import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { ReferencePicker } from "./ReferencePicker";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

test("a stale blur callback cannot close a refocused picker", () => {
  vi.useFakeTimers();
  render(
    <>
      <ReferencePicker
        label="Botanical identity"
        choices={[]}
        value=""
        onChange={() => undefined}
        onCreate={() => undefined}
        createLabel="Create identity"
      />
      <input aria-label="Lot label" />
    </>,
  );

  const picker = screen.getByRole("combobox", {
    name: "Botanical identity",
  });
  fireEvent.focus(picker);
  expect(picker).toHaveAttribute("aria-expanded", "true");

  fireEvent.blur(picker);
  fireEvent.focus(picker);
  expect(picker).toHaveAttribute("aria-expanded", "true");

  act(() => {
    vi.runAllTimers();
  });
  expect(picker).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("button", { name: "Create identity" })).toBeVisible();
});

test("focus can move from the input to a picker action", () => {
  vi.useFakeTimers();
  render(
    <ReferencePicker
      label="Botanical identity"
      choices={[]}
      value=""
      onChange={() => undefined}
      onCreate={() => undefined}
      createLabel="Create identity"
    />,
  );

  const picker = screen.getByRole("combobox", {
    name: "Botanical identity",
  });
  fireEvent.focus(picker);
  const create = screen.getByRole("button", { name: "Create identity" });
  fireEvent.blur(picker, { relatedTarget: create });
  fireEvent.focus(create);

  act(() => {
    vi.runAllTimers();
  });
  expect(picker).toHaveAttribute("aria-expanded", "true");
  expect(create).toBeVisible();
});

test("focus stays within the picker and closes after it leaves", () => {
  render(
    <>
      <ReferencePicker
        label="Botanical identity"
        choices={[{ id: "identity", label: "Passiflora edulis" }]}
        value=""
        onChange={() => undefined}
        onCreate={() => undefined}
        createLabel="Create identity"
      />
      <input aria-label="Lot label" />
    </>,
  );

  const picker = screen.getByRole("combobox", {
    name: "Botanical identity",
  });
  const outside = screen.getByRole("textbox", { name: "Lot label" });
  fireEvent.focus(picker);
  const option = screen.getByRole("button", { name: "Passiflora edulis" });
  const create = screen.getByRole("button", { name: "Create identity" });

  fireEvent.blur(picker, { relatedTarget: option });
  fireEvent.focus(option);
  expect(picker).toHaveAttribute("aria-expanded", "true");

  fireEvent.blur(option, { relatedTarget: create });
  fireEvent.focus(create);
  expect(picker).toHaveAttribute("aria-expanded", "true");

  fireEvent.blur(create, { relatedTarget: outside });
  fireEvent.focus(outside);
  expect(picker).toHaveAttribute("aria-expanded", "false");
});

test("Escape closes the menu from an internal action", () => {
  render(
    <ReferencePicker
      label="Botanical identity"
      choices={[]}
      value=""
      onChange={() => undefined}
      onCreate={() => undefined}
      createLabel="Create identity"
    />,
  );

  const picker = screen.getByRole("combobox", {
    name: "Botanical identity",
  });
  fireEvent.focus(picker);
  const create = screen.getByRole("button", { name: "Create identity" });
  fireEvent.keyDown(create, { key: "Escape" });

  expect(picker).toHaveFocus();
  expect(picker).toHaveAttribute("aria-expanded", "false");
});

test("required reference state remains exposed after selection; optional references stay optional", () => {
  const props = {
    label: "Botanical identity",
    choices: [{ id: "identity", label: "Passiflora edulis" }],
    onChange: () => undefined,
  };
  const { rerender } = render(<ReferencePicker {...props} value="" required />);
  expect(
    screen.getByRole("combobox", { name: "Botanical identity" }),
  ).toBeRequired();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  rerender(<ReferencePicker {...props} value="identity" required />);
  expect(
    screen.getByRole("combobox", { name: "Botanical identity" }),
  ).toHaveAttribute("aria-required", "true");
  expect(screen.getByLabelText("Botanical identity")).toHaveValue(
    "Passiflora edulis",
  );
  rerender(<ReferencePicker {...props} value="identity" />);
  expect(
    screen.getByRole("combobox", { name: "Botanical identity" }),
  ).not.toBeRequired();
});

test("listbox keyboard navigation selects a reference and preserves input focus and ARIA state", async () => {
  const user = userEvent.setup();
  const onChange = vi.fn();
  render(
    <ReferencePicker
      label="Storage location"
      choices={[
        { id: "shelf", label: "Indoor shelf" },
        { id: "bed", label: "Garden bed" },
        { id: "frame", label: "Cold frame" },
      ]}
      value=""
      onChange={onChange}
    />,
  );
  const control = screen.getByRole("combobox", { name: "Storage location" });
  await user.click(control);
  const list = screen.getByRole("listbox");
  expect(control).toHaveAttribute("aria-controls", list.id);
  expect(control).toHaveAttribute("aria-expanded", "true");
  await user.keyboard("{ArrowDown}");
  expect(control).toHaveAttribute("aria-activedescendant", `${list.id}-bed`);
  await user.keyboard("{ArrowUp}");
  expect(control).toHaveAttribute("aria-activedescendant", `${list.id}-shelf`);
  await user.keyboard("{Enter}");
  expect(onChange).toHaveBeenCalledExactlyOnceWith("shelf");
  expect(control).toHaveFocus();
  expect(control).toHaveAttribute("aria-expanded", "false");
  expect(control).not.toHaveAttribute("aria-activedescendant");
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
});

test("Escape dismisses an open picker before its enclosing task and option-button selection restores focus", async () => {
  const user = userEvent.setup();
  const outerEscape = vi.fn();
  const change = vi.fn();
  render(
    <div onKeyDown={outerEscape}>
      <ReferencePicker
        label="Supplier"
        choices={[{ id: "supplier", label: "Garden exchange" }]}
        value=""
        onChange={change}
      />
    </div>,
  );
  const control = screen.getByRole("combobox", { name: "Supplier" });
  await user.click(control);
  await user.keyboard("{Escape}");
  expect(control).toHaveAttribute("aria-expanded", "false");
  expect(control).toHaveFocus();
  expect(outerEscape).not.toHaveBeenCalled();
  await user.keyboard("{ArrowDown}");
  await user.tab();
  expect(screen.getByRole("button", { name: "Garden exchange" })).toHaveFocus();
  await user.keyboard("{Enter}");
  expect(change).toHaveBeenCalledExactlyOnceWith("supplier");
  expect(control).toHaveFocus();
  expect(control).toHaveAttribute("aria-expanded", "false");
});
