import { screen, within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";

import { workspaces } from "../shell/navigation";

/**
 * Opens a section the way an operator does in the Workbench shell: use the link
 * in the context panel when the current workspace shows it, otherwise select the
 * owning workspace tab in the rail first. Returns the clicked link.
 */
export async function openSection(user: UserEvent, label: string) {
  let primary = await screen.findByRole("navigation", {
    name: "Primary navigation",
  });
  let link = within(primary).queryByRole("link", { name: label });
  if (!link) {
    const owner = workspaces.find((workspace) =>
      workspace.destinations.some(
        (item) =>
          item.label === label ||
          item.children?.some((child) => child.label === label),
      ),
    );
    if (!owner) throw new Error(`No workspace contains "${label}"`);
    await user.click(
      screen.getByRole("tab", { name: new RegExp(`^${owner.label}`) }),
    );
    primary = screen.getByRole("navigation", { name: "Primary navigation" });
    link = within(primary).getByRole("link", { name: label });
  }
  await user.click(link);
  return link;
}
