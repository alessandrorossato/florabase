import { screen, within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";

export async function selectDirectoryFilter(
  user: UserEvent,
  label: string,
  value: string,
) {
  if (!screen.queryByRole("button", { name: /^Filters(?: \(\d+\))?$/ })) {
    const breadcrumb = screen.queryByRole("navigation", {
      name: "Breadcrumb",
    });
    const crumb = breadcrumb
      ? within(breadcrumb).queryByRole("link", {
          name: /^(Seeds|Sowings|Plants)$/,
        })
      : null;
    if (crumb) await user.click(crumb);
  }
  await user.click(
    await screen.findByRole("button", { name: /^Filters(?: \(\d+\))?$/ }),
  );
  const drawer = screen.getByRole("dialog", { name: / filters$/ });
  await user.selectOptions(
    within(drawer).getByRole("combobox", { name: label }),
    value,
  );
  await user.click(within(drawer).getByRole("button", { name: "Done" }));
}
