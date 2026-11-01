import { screen, within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";

export async function selectDirectoryFilter(
  user: UserEvent,
  label: string,
  value: string,
) {
  if (!screen.queryByRole("button", { name: /^Filters(?: \(\d+\))?$/ })) {
    const back = screen.queryByRole("button", {
      name: /Back to (seed lots|Sowings|Plants)/,
    });
    if (back) await user.click(back);
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
