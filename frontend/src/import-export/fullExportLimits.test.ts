import { expect, test } from "vitest";

import {
  NATIVE_PHOTO_EXPORT_LIMIT_BYTES,
  photosTooLargeForApp,
} from "./fullExportLimits";

test("only the native app refuses photo exports above the limit", () => {
  const above = NATIVE_PHOTO_EXPORT_LIMIT_BYTES + 1;
  expect(photosTooLargeForApp(true, above)).toBe(true);
  expect(photosTooLargeForApp(true, NATIVE_PHOTO_EXPORT_LIMIT_BYTES)).toBe(
    false,
  );
  expect(photosTooLargeForApp(true, undefined)).toBe(false);
  expect(photosTooLargeForApp(false, above)).toBe(false);
});
