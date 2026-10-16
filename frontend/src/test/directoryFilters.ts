import { screen, within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";

export async function selectDirectoryFilter(
  user: UserEvent,
  label: string,
  value: string,
) {
  if (!screen.queryByRole("button", { name: /^Filters(?: \(\d+\))?$/ })) {
    const back = screen.getByRole("button", {
      name: /Back to (seed lots|Sowings|Plants)/,
    });
    await user.click(back);
  }
  await user.click(
    screen.getByRole("button", { name: /^Filters(?: \(\d+\))?$/ }),
  );
  const drawer = screen.getByRole("dialog", { name: / filters$/ });
  await user.selectOptions(
    within(drawer).getByRole("combobox", { name: label }),
    value,
  );
  await user.click(within(drawer).getByRole("button", { name: "Done" }));
}
