import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
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
