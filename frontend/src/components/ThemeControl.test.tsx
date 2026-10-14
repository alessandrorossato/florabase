import { useState } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { ThemeControl, type ThemePreview } from "./ThemeControl";
function Preview() {
  const [mode, setMode] = useState<ThemePreview>("System");
  return <ThemeControl mode={mode} onPreviewChange={setMode} />;
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
test("icon cycles System, Light, Dark, System with truthful labels and no theme/persistence mutation", async () => {
  const local = vi.spyOn(Storage.prototype, "setItem");
  const fetch = vi.spyOn(globalThis, "fetch");
  const root = document.documentElement.outerHTML.split("<body")[0];
  const view = render(<Preview />);
  const user = userEvent.setup();
  for (const [index, mode] of ["System", "Light", "Dark", "System"].entries()) {
    const button = screen.getByRole("button", {
      name: `Theme preview: ${mode}. Theme switching is not enabled yet.`,
    });
    expect(button).toHaveAttribute("title", button.getAttribute("aria-label"));
    expect(button).toHaveTextContent("");
    expect(button.querySelector("svg")).toHaveAttribute(
      "data-preview",
      mode.toLowerCase(),
    );
    expect(button).not.toHaveAttribute("aria-expanded");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
    if (index < 3) await user.click(button);
  }
  expect(local).not.toHaveBeenCalled();
  expect(fetch).not.toHaveBeenCalled();
  expect(document.documentElement.outerHTML.split("<body")[0]).toBe(root);
  view.unmount();
  render(<Preview />);
  expect(
    screen.getByRole("button", { name: /Theme preview: System/ }),
  ).toBeInTheDocument();
});
test("native keyboard activation advances icons and keeps focus on the single button", async () => {
  render(<Preview />);
  const user = userEvent.setup();
  await user.tab();
  expect(
    screen.getByRole("button", { name: /Theme preview: System/ }),
  ).toHaveFocus();
  await user.keyboard("{Enter}");
  expect(
    screen.getByRole("button", { name: /Theme preview: Light/ }),
  ).toHaveFocus();
  await user.keyboard(" ");
  expect(
    screen.getByRole("button", { name: /Theme preview: Dark/ }),
  ).toHaveFocus();
});
