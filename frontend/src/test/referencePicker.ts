import { within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";

/** Choose a ReferencePicker option by its visible label (FN-04 typeahead pickers). */
export async function pickReference(
  user: UserEvent,
  input: HTMLElement,
  option: string | RegExp,
) {
  await user.click(input);
  // A chosen value filters the menu to itself; clear it to see every option.
  if ((input as HTMLInputElement).value) await user.clear(input);
  const listbox = document.getElementById(
    input.getAttribute("aria-controls") ?? "",
  );
  if (!listbox) throw new Error("reference menu did not open");
  await user.click(within(listbox).getByRole("button", { name: option }));
}

/** Clear a ReferencePicker back to its empty ("Not recorded") value. */
export async function clearReference(user: UserEvent, input: HTMLElement) {
  await user.clear(input);
  await user.keyboard("{Escape}");
}
