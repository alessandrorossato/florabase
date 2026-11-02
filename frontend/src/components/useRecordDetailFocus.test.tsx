import { StrictMode, useRef } from "react";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { useRecordDetailFocus } from "./useRecordDetailFocus";

afterEach(cleanup);

async function nextFrame() {
  await act(async () => {
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => {
        resolve();
      }),
    );
  });
}

function Surface({
  recordKey = null,
  ready = true,
  paused = false,
  rows = ["one", "two"],
}: {
  recordKey?: string | null;
  ready?: boolean;
  paused?: boolean;
  rows?: string[];
}) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const directoryRef = useRef<HTMLUListElement>(null);
  useRecordDetailFocus({
    recordKey,
    detailReady: ready,
    directoryReady: ready,
    paused,
    headingRef,
    directoryRef,
    fallbackId: "search",
  });
  return (
    <>
      <input id="search" aria-label="Search" />
      {recordKey ? (
        ready ? (
          <h3 ref={headingRef} tabIndex={-1}>
            Record {recordKey}
          </h3>
        ) : (
          <p role="status">Loading</p>
        )
      ) : rows.length === 0 ? (
        <p>No records</p>
      ) : (
        <ul aria-label="Records" ref={directoryRef} tabIndex={0}>
          {rows.map((id) => (
            <li key={id} data-preview-id={id}>
              <button className="ui-directory-trigger">Open {id}</button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

test("focus follows the loaded record and reconnects to the matching remounted row in StrictMode", async () => {
  const { rerender } = render(
    <StrictMode>
      <Surface />
    </StrictMode>,
  );
  screen.getByRole("button", { name: "Open two" }).focus();
  rerender(
    <StrictMode>
      <Surface recordKey="two" ready={false} />
    </StrictMode>,
  );
  expect(document.body).toHaveFocus();
  rerender(
    <StrictMode>
      <Surface recordKey="two" />
    </StrictMode>,
  );
  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "Record two" })).toHaveFocus();
  });
  rerender(
    <StrictMode>
      <Surface />
    </StrictMode>,
  );
  await waitFor(() => {
    expect(screen.getByRole("button", { name: "Open two" })).toHaveFocus();
  });
});

test("a removed or filtered return row falls back to the connected directory", async () => {
  const { rerender } = render(<Surface recordKey="two" />);
  await waitFor(() => {
    expect(screen.getByRole("heading")).toHaveFocus();
  });
  rerender(<Surface rows={["one"]} />);
  await waitFor(() => {
    expect(screen.getByRole("list", { name: "Records" })).toHaveFocus();
  });
});

test("loading, later refreshes and return navigation preserve intentional Search focus", async () => {
  const { rerender } = render(<Surface recordKey="one" ready={false} />);
  const search = screen.getByRole("textbox", { name: "Search" });
  search.focus();
  rerender(<Surface recordKey="one" />);
  await nextFrame();
  expect(search).toHaveFocus();
  rerender(<Surface recordKey="one" ready={false} />);
  rerender(<Surface recordKey="one" />);
  await nextFrame();
  expect(search).toHaveFocus();
  rerender(<Surface />);
  await nextFrame();
  expect(search).toHaveFocus();
});

test("an editor keeps focus ownership until it closes", async () => {
  const { rerender } = render(<Surface recordKey="one" paused />);
  const search = screen.getByRole("textbox", { name: "Search" });
  search.focus();
  rerender(<Surface recordKey="one" paused />);
  await nextFrame();
  expect(search).toHaveFocus();
  rerender(<Surface recordKey="one" />);
  await nextFrame();
  expect(search).toHaveFocus();
});

test("an empty returning directory falls back to its existing Search input", async () => {
  const { rerender } = render(<Surface recordKey="two" />);
  await waitFor(() => {
    expect(screen.getByRole("heading")).toHaveFocus();
  });
  rerender(<Surface rows={[]} />);
  await waitFor(() => {
    expect(screen.getByRole("textbox", { name: "Search" })).toHaveFocus();
  });
});
