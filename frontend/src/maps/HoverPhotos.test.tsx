import {
  act,
  cleanup,
  render,
  renderHook,
  screen,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test } from "vitest";

import { HoverPhotoStrip, HoverPhotosToggle } from "./HoverPhotos";
import { useHoverPhotos } from "./useHoverPhotos";

afterEach(() => {
  cleanup();
  localStorage.clear();
});

test("the switch is off by default and remembered per page on this device", () => {
  const first = renderHook(() => useHoverPhotos("native-ranges"));
  expect(first.result.current[0]).toBe(false);
  act(() => {
    first.result.current[1](true);
  });
  expect(first.result.current[0]).toBe(true);
  expect(
    renderHook(() => useHoverPhotos("native-ranges")).result.current[0],
  ).toBe(true);
  expect(
    renderHook(() => useHoverPhotos("collection-origins")).result.current[0],
  ).toBe(false);
});

test("the switch is a labelled checkbox switch", async () => {
  const user = userEvent.setup();
  let value = false;
  render(
    <HoverPhotosToggle
      checked={false}
      onChange={(next) => {
        value = next;
      }}
    />,
  );
  await user.click(screen.getByRole("switch", { name: "Photos on hover" }));
  expect(value).toBe(true);
});

test("the strip shows at most four covers, then how many more", () => {
  const identities = Array.from({ length: 6 }, (_, index) => ({
    id: `id-${String(index)}`,
    display_label: `Plant ${String(index)}`,
  }));
  const { container } = render(
    <HoverPhotoStrip identities={identities} total={9} />,
  );
  expect(container.querySelectorAll(".hover-photos__thumb")).toHaveLength(4);
  expect(screen.getByText("+5")).toBeVisible();
  expect(
    screen.getByText("Plant 0, Plant 1, Plant 2, Plant 3, …"),
  ).toBeVisible();
  cleanup();
  const empty = render(<HoverPhotoStrip identities={[]} />);
  expect(empty.container).toBeEmptyDOMElement();
});
