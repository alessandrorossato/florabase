import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ApiError } from "../auth/api";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { acquireTestAuth } from "../test/auth";
import {
  createBotanicalIdentity,
  getBotanicalIdentity,
  type BotanicalIdentityResponse,
} from "./api";
import { IdentityCreateDialog } from "./IdentityCreateDialog";

vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  createBotanicalIdentity: vi.fn(),
  getBotanicalIdentity: vi.fn(),
}));
vi.mock("../taxonomy/api", () => ({
  searchNames: vi.fn(() => Promise.resolve([])),
}));

let auth: AuthContextValue;
beforeEach(async () => {
  auth = (await acquireTestAuth({ csrfToken: "csrf" })).auth;
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const identity = {
  id: "identity",
  scientific_name: "Ocimum basilicum",
  display_label: "Ocimum basilicum",
} as BotanicalIdentityResponse;

function open(onCreated = vi.fn(), onClose = vi.fn()) {
  // A surrounding record form must never receive the dialog's submit.
  const outerSubmit = vi.fn((event: { preventDefault: () => void }) => {
    event.preventDefault();
  });
  render(
    <AuthContext.Provider value={auth}>
      <form onSubmit={outerSubmit}>
        <IdentityCreateDialog
          initialName="Ocimum basilicum"
          onClose={onClose}
          onCreated={onCreated}
        />
      </form>
    </AuthContext.Provider>,
  );
  return { onCreated, onClose, outerSubmit };
}

test("creates the identity from the typed name without submitting the record form", async () => {
  vi.mocked(createBotanicalIdentity).mockResolvedValue(identity);
  const { onCreated, outerSubmit } = open();
  const user = userEvent.setup();
  const dialog = screen.getByRole("dialog", {
    name: "Create botanical identity",
  });
  expect(screen.getByLabelText(/Scientific name/)).toHaveValue(
    "Ocimum basilicum",
  );
  await user.type(screen.getByLabelText("Common name"), "Basil");
  await user.click(screen.getByRole("button", { name: "Create identity" }));
  await waitFor(() => {
    expect(onCreated).toHaveBeenCalledWith(identity, false);
  });
  expect(createBotanicalIdentity).toHaveBeenCalledWith(
    {
      scientific_name: "Ocimum basilicum",
      cultivar_name: null,
      common_name: "Basil",
    },
    "csrf",
    auth.capability,
  );
  expect(outerSubmit).not.toHaveBeenCalled();
  expect(dialog.closest("form")).toBeNull();
});

test("an exact duplicate selects the existing identity", async () => {
  vi.mocked(createBotanicalIdentity).mockRejectedValue(
    new ApiError(409, null, { detail: { existing_id: "identity" } }),
  );
  vi.mocked(getBotanicalIdentity).mockResolvedValue(identity);
  const { onCreated } = open();
  await userEvent
    .setup()
    .click(screen.getByRole("button", { name: "Create identity" }));
  await waitFor(() => {
    expect(onCreated).toHaveBeenCalledWith(identity, true);
  });
  expect(getBotanicalIdentity).toHaveBeenCalledWith(
    "identity",
    auth.capability,
  );
});

test("validation errors stay in the dialog and Cancel closes it", async () => {
  vi.mocked(createBotanicalIdentity).mockRejectedValue(
    new ApiError(422, null, {
      detail: [
        {
          loc: ["body", "scientific_name"],
          msg: "must not be blank",
          type: "value_error",
        },
      ],
    }),
  );
  const { onCreated, onClose } = open();
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Create identity" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Scientific name cannot be blank.",
  );
  expect(onCreated).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(onClose).toHaveBeenCalled();
});
