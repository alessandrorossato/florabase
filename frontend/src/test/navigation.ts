import { screen, within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";

import { workspaces } from "../shell/navigation";

/**
 * Opens a section the way an operator does in the Workbench shell: use the link
 * in the context panel when the current workspace shows it, otherwise select the
 * owning workspace tab in the rail first (which also opens that workspace's home
 * page, or Today itself). Returns the clicked link or tab.
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
    const tab = screen.getByRole("tab", {
      name: new RegExp(`^${owner.label}`),
    });
    await user.click(tab);
    // The Today tab is the Today destination itself: it navigates without a panel link.
    if (owner.id === "today") return tab;
    primary = screen.getByRole("navigation", { name: "Primary navigation" });
    link = within(primary).getByRole("link", { name: label });
  }
  await user.click(link);
  return link;
}
