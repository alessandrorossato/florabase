import { afterEach, expect, test } from "vitest";
import {
  mediaDirectoryHash,
  mediaDetailHash,
  mediaOffset,
  navigateMedia,
  rememberMediaCard,
} from "./navigation";

afterEach(() => {
  window.history.replaceState(null, "", "#/media");
});
test("detail carries only supported filters and a valid page; direct reload recovers the same directory", () => {
  window.history.replaceState(
    null,
    "",
    "#/media?q=leaf&kind=local&association=linked&target=supplier&offset=24&returnTo=https://evil.test",
  );
  const expected =
    "#/media?q=leaf&kind=local&association=linked&target=supplier&offset=24";
  expect(mediaDirectoryHash()).toBe(expected);
  const detail = mediaDetailHash("asset");
  expect(detail).toBe(expected.replace("#/media", "#/media/asset"));
  expect(mediaDirectoryHash(detail)).toBe(expected);
  rememberMediaCard("asset");
  expect(window.history.state).toMatchObject({ mediaFocus: "asset" });
  navigateMedia(detail);
  navigateMedia(expected, "asset");
  expect(window.location.hash).toBe(expected);
  expect(window.history.state).toMatchObject({ mediaFocus: "asset" });
});
test.each([
  "-24",
  "25",
  "24.0",
  "NaN",
  "Infinity",
  "9999999999999999999999",
  "2400000000",
])("invalid offset %s cannot reach the API", (value) => {
  expect(mediaOffset(`#/media?offset=${value}`)).toBe(0);
});
