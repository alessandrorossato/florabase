import { expect } from "vitest";
import { screen } from "@testing-library/react";
import type userEvent from "@testing-library/user-event";

/** Create exposes named regions together; Edit retains direct section tabs. */
export async function openFormSection(
  user: ReturnType<typeof userEvent.setup>,
  name: string,
) {
  const region = screen.queryByRole("region", { name });
  if (region) expect(region).toBeVisible();
  else await user.click(screen.getByRole("tab", { name }));
}
