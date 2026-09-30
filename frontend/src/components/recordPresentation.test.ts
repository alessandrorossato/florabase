import { expect, test } from "vitest";
import { recordDisplayName } from "./recordPresentation";
const identity = {
  id: "identity",
  display_label: "Abelmoschus esculentus ‘Burgundy’",
  scientific_name: "Abelmoschus esculentus",
  cultivar_name: "Burgundy",
  common_name: "Okra Burgundy",
  created_at: "",
  updated_at: "",
};
test("display names prefer explicit, common, useful cultivar, scientific, then generic without mutating labels", () => {
  const record = { label: null, botanical_identity: identity };
  expect(recordDisplayName({ ...record, label: " My packet " }, "Seed")).toBe(
    "My packet",
  );
  expect(recordDisplayName(record, "Seed")).toBe("Okra Burgundy");
  expect(
    recordDisplayName(
      { ...record, botanical_identity: { ...identity, common_name: null } },
      "Seed",
    ),
  ).toBe("Burgundy");
  expect(
    recordDisplayName(
      {
        ...record,
        botanical_identity: {
          ...identity,
          common_name: null,
          cultivar_name: identity.scientific_name,
        },
      },
      "Seed",
    ),
  ).toBe(identity.scientific_name);
  expect(recordDisplayName({ label: null }, "Seed")).toBe("Seed");
  expect(record.label).toBeNull();
});
test("summary and Sowing references resolve through the shared identity metadata index", () => {
  const identities = new Map([[identity.id, identity]]);
  expect(
    recordDisplayName(
      {
        botanical_identity: {
          id: identity.id,
          display_label: identity.display_label,
        },
      },
      "Plant",
      identities,
    ),
  ).toBe("Okra Burgundy");
  expect(
    recordDisplayName(
      {
        seed_lot: {
          botanical_identity_id: identity.id,
          botanical_identity_display_label: identity.display_label,
        },
      },
      "Sowing",
      identities,
    ),
  ).toBe("Okra Burgundy");
});
