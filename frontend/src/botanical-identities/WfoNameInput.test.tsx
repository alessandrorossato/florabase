import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { acquireTestAuth } from "../test/auth";
import { WfoNameInput } from "./WfoNameInput";

afterEach(() => {
  vi.restoreAllMocks();
});

const taxon = (scientific_name: string) => ({
  source_taxon_id: scientific_name,
  parent_source_taxon_id: null,
  scientific_name,
  authorship: "L.",
  rank: "species",
  taxonomic_status: "accepted",
  accepted_source_taxon_id: null,
});

test("suggests unique WFO names for a two-character prefix and survives an unavailable index", async () => {
  const { capability } = await acquireTestAuth();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
    new Response(
      JSON.stringify(
        ["Ficus carica", "Ficus carica", "Ficus lyrata"].map((name) => ({
          taxon: taxon(name),
          classification: [],
        })),
      ),
      { headers: { "Content-Type": "application/json" } },
    ),
  );
  render(
    <WfoNameInput id="name" name="scientific_name" capability={capability} />,
  );
  const input = screen.getByRole("combobox");
  const user = userEvent.setup();
  await user.type(input, "F");
  expect(fetch).not.toHaveBeenCalled();
  await user.type(input, "i");
  await waitFor(() => {
    expect(
      [...document.querySelectorAll("#name-wfo-suggestions option")].map(
        (option) => option.getAttribute("value"),
      ),
    ).toEqual(["Ficus carica", "Ficus lyrata"]);
  });
  expect(fetch.mock.calls[0]?.[0]).toBe(
    "/api/v1/explore/taxonomy/candidates?q=Fi",
  );

  fetch.mockResolvedValueOnce(new Response("{}", { status: 503 }));
  await user.type(input, "c");
  await waitFor(() => {
    expect(
      document.querySelectorAll("#name-wfo-suggestions option"),
    ).toHaveLength(0);
  });
  expect(input).toHaveValue("Fic");
});
