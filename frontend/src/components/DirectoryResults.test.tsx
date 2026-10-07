import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { DirectoryResults } from "./DirectoryResults";

afterEach(cleanup);

test.each([
  [{ count: 0 }, "0 records"],
  [{ count: 1 }, "1 record"],
  [{ count: 3 }, "3 records"],
  [{ count: 24, total: 137 }, "24 of 137 records"],
  [{ count: 24, loadedOnly: true }, "24 shown"],
])("truthful quiet result metadata %j", (props, text) => {
  render(<DirectoryResults {...props} />);
  const count = screen.getByLabelText("Directory results");
  expect(count).toHaveTextContent(text);
  expect(count).not.toHaveAttribute("aria-live");
  expect(count).not.toHaveAttribute("role", "status");
});
