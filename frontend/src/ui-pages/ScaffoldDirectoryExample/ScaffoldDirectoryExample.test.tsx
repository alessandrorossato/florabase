import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { LoadingState, ErrorState } from "../../components/WorkspaceUI";
import { ScaffoldDirectoryExample } from "./ScaffoldDirectoryExample";

afterEach(cleanup);
test("keyboard view switching retains search; request feedback uses the house states", async () => {
  const user = userEvent.setup();
  const { rerender } = render(<ScaffoldDirectoryExample />);
  await user.type(
    screen.getByRole("searchbox", { name: "Search records" }),
    "Aloe",
  );
  screen.getByRole("button", { name: "Gallery" }).focus();
  await user.keyboard(" ");
  expect(
    screen.getByRole("button", { name: "Gallery", pressed: true }),
  ).toHaveFocus();
  expect(screen.getByRole("searchbox")).toHaveValue("Aloe");
  rerender(
    <ScaffoldDirectoryExample
      feedback={<LoadingState>Loading records…</LoadingState>}
    />,
  );
  expect(screen.getByRole("status")).toHaveTextContent("Loading records");
  const retry = vi.fn();
  rerender(
    <ScaffoldDirectoryExample
      feedback={<ErrorState onRetry={retry}>Could not load records</ErrorState>}
    />,
  );
  await user.click(screen.getByRole("button", { name: "Retry" }));
  expect(retry).toHaveBeenCalledOnce();
  expect(screen.getByRole("searchbox")).toHaveValue("Aloe");
});
