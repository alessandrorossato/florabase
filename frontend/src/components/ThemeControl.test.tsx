import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { ThemeControl } from "./ThemeControl";
import { AppearanceSettings } from "../appearance/AppearanceSettings";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
test("footer cycles real System, Light, Dark, System and persists without changing palette", async () => {
  window.florabaseAppearance.setPalette("herbarium");
  const fetch = vi.spyOn(globalThis, "fetch");
  render(<ThemeControl />);
  const user = userEvent.setup();
  for (const [index, mode] of ["system", "light", "dark", "system"].entries()) {
    const button = screen.getByRole("button", { name: /Appearance:/ });
    expect(button).not.toHaveAttribute("title");
    expect(button.querySelector("svg")).toHaveAttribute(
      "data-appearance",
      mode,
    );
    expect(button).toHaveAccessibleName(/Herbarium/);
    expect(document.documentElement).toHaveAttribute(
      "data-palette",
      "herbarium",
    );
    expect(document.documentElement).toHaveAttribute(
      "data-appearance",
      mode === "dark" ? "dark" : "light",
    );
    expect(button).not.toHaveAttribute("aria-expanded");
    if (index < 3) await user.click(button);
  }
  expect(
    JSON.parse(localStorage.getItem("florabase.appearance.v1") ?? "{}"),
  ).toEqual({ version: 1, palette: "herbarium", appearance: "system" });
  expect(fetch).not.toHaveBeenCalled();
});

test("keyboard cycling retains focus; Settings, two footer instances and palette synchronize", async () => {
  render(
    <>
      <ThemeControl />
      <ThemeControl />
      <AppearanceSettings />
    </>,
  );
  const user = userEvent.setup();
  await user.tab();
  const first = screen.getAllByRole("button", { name: /Appearance:/ })[0];
  expect(first).toHaveFocus();
  await user.keyboard("{Enter}");
  expect(first).toHaveFocus();
  expect(screen.getByRole("radio", { name: "Light" })).toBeChecked();
  await user.keyboard(" ");
  expect(screen.getByRole("radio", { name: "Dark" })).toBeChecked();
  await user.click(screen.getByRole("radio", { name: /Mineral/ }));
  for (const control of screen.getAllByRole("button", {
    name: /Appearance:/,
  })) {
    expect(control).toHaveAccessibleName(
      "Appearance: Dark, Mineral. Switch to System.",
    );
  }
  expect(screen.getByRole("radio", { name: /Mineral/ })).toHaveFocus();
  await user.click(screen.getByRole("radio", { name: "System" }));
  expect(screen.getByRole("status")).toHaveTextContent(
    "System · currently Light",
  );
});
