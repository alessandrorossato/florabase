import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ActionButton, ActionLink, IconButton } from "./Action";
import { Icon } from "./Icon";
import { Tooltip } from "./Tooltip";
import { TaskDialog } from "./TaskDialog";
import { OverflowMenu } from "./ReferenceUI";

beforeEach(() => {
  // jsdom does not model the browser keyboard focus-visible heuristic.
  vi.spyOn(HTMLElement.prototype, "matches").mockImplementation(function (
    this: HTMLElement,
    selector,
  ) {
    return selector === ":focus-visible"
      ? document.activeElement === this
      : Element.prototype.matches.call(this, selector);
  });
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(
    function (this: HTMLElement) {
      return this.tagName === "BUTTON"
        ? new DOMRect(100, 200, 44, 44)
        : this.getAttribute("role") === "tooltip"
          ? new DOMRect(0, 0, 140, 32)
          : new DOMRect(0, 0, 1024, 768);
    },
  );
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});
function tick(ms: number) {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

test("one decorative icon grammar and native action/link refs, names and semantics", async () => {
  const ref = createRef<HTMLButtonElement>();
  const action = vi.fn();
  const view = render(
    <>
      <Icon name="search" />
      <ActionButton ref={ref} icon="edit" variant="secondary" onClick={action}>
        Edit seed lot
      </ActionButton>
      <ActionLink icon="back" href="#/seeds">
        Back to Seeds
      </ActionLink>
      <ActionButton variant="danger" disabled>
        Delete seed lot
      </ActionButton>
    </>,
  );
  const icons = view.container.querySelectorAll("svg");
  for (const icon of icons) {
    expect(icon).toHaveAttribute("stroke", "currentColor");
    expect(icon).toHaveAttribute("stroke-width", "1.75");
    expect(icon).toHaveAttribute("aria-hidden", "true");
    expect(icon).toHaveAttribute("focusable", "false");
  }
  const edit = screen.getByRole("button", { name: "Edit seed lot" });
  expect(ref.current).toBe(edit);
  await userEvent.click(edit);
  expect(action).toHaveBeenCalledOnce();
  expect(screen.getByRole("link", { name: "Back to Seeds" })).toHaveAttribute(
    "href",
    "#/seeds",
  );
  expect(
    screen.getByRole("button", { name: "Delete seed lot" }),
  ).toBeDisabled();
});

test("hover delay, cancellation and hover transfer keep concise descriptions dismissible and persistent", () => {
  vi.useFakeTimers();
  render(
    <IconButton
      icon="more"
      label="More actions for Basil"
      tooltip="More actions"
    />,
  );
  const button = screen.getByRole("button", { name: "More actions for Basil" });
  fireEvent.pointerEnter(button, { pointerType: "mouse" });
  tick(499);
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  fireEvent.pointerLeave(button);
  tick(600);
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  fireEvent.pointerEnter(button, { pointerType: "mouse" });
  tick(500);
  const tip = screen.getByRole("tooltip");
  expect(tip).toHaveTextContent("More actions");
  fireEvent.pointerLeave(button);
  tick(100);
  fireEvent.pointerEnter(tip);
  tick(5000);
  expect(tip).toBeInTheDocument();
  fireEvent.pointerLeave(tip);
  tick(150);
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
});

test("focus is immediate, merges description IDs, Escape suppresses reopening and activation retains focus", async () => {
  const ref = createRef<HTMLButtonElement>();
  const click = vi.fn();
  render(
    <>
      <p id="help">Existing help</p>
      <Tooltip content="Inspect additional actions">
        <button ref={ref} aria-describedby="help" onClick={click}>
          More actions for Basil
        </button>
      </Tooltip>
    </>,
  );
  const button = screen.getByRole("button");
  act(() => {
    button.focus();
  });
  const tip = screen.getByRole("tooltip");
  expect(button.getAttribute("aria-describedby")).toBe(`help ${tip.id}`);
  expect(button).toHaveFocus();
  expect(tip).not.toHaveAttribute("tabindex");
  fireEvent.keyDown(button, { key: "Escape" });
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  expect(button).toHaveAttribute("aria-describedby", "help");
  expect(button).toHaveFocus();
  fireEvent.pointerMove(button);
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  await userEvent.click(button);
  expect(click).toHaveBeenCalledOnce();
  expect(ref.current).toBe(button);
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  expect(button).not.toHaveAttribute("title");
});

test("touch does not intercept activation; native disabled and busy props survive adapters", () => {
  vi.useFakeTimers();
  const click = vi.fn();
  render(
    <>
      <IconButton
        icon="more"
        label="More actions"
        tooltip="Inspect record actions"
        onClick={click}
      />
      <IconButton
        icon="refresh"
        label="Refresh list"
        tooltip="Reload current list"
        disabled
        aria-busy="true"
      />
    </>,
  );
  const button = screen.getByRole("button", { name: "More actions" });
  fireEvent.pointerEnter(button, { pointerType: "touch" });
  fireEvent.pointerDown(button, { pointerType: "touch" });
  fireEvent.click(button);
  tick(1000);
  expect(click).toHaveBeenCalledOnce();
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Refresh list" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Refresh list" })).toHaveAttribute(
    "aria-busy",
    "true",
  );
});

test("viewport collision flips and shifts; a hidden or scrolled-out trigger dismisses without moving focus", () => {
  render(
    <IconButton
      icon="more"
      label="Record actions"
      tooltip="Additional record operations"
    />,
  );
  const button = screen.getByRole("button");
  vi.spyOn(button, "getBoundingClientRect").mockReturnValue(
    new DOMRect(0, 0, 44, 44),
  );
  act(() => {
    button.focus();
  });
  const tip = screen.getByRole("tooltip");
  expect(tip.style.left).toBe("8px");
  expect(tip.style.top).toBe("52px");
  vi.spyOn(button, "getBoundingClientRect").mockReturnValue(
    new DOMRect(0, -100, 44, 44),
  );
  fireEvent.scroll(window);
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  expect(button).toHaveFocus();
});

test("unmount cancels pending timers and removes an open tooltip description and overlay", () => {
  vi.useFakeTimers();
  const view = render(
    <IconButton icon="close" label="Close" tooltip="Close this panel" />,
  );
  const button = screen.getByRole("button");
  fireEvent.pointerEnter(button, { pointerType: "mouse" });
  view.unmount();
  tick(1000);
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
});

test("one Escape dismisses tooltip, then menu, then native dialog, preserving trigger focus", async () => {
  const close = vi.fn();
  const user = userEvent.setup();
  render(
    <TaskDialog title="Record dialog" onClose={close}>
      <OverflowMenu ariaLabel="Record operations">
        <IconButton
          icon="edit"
          label="Inspect record"
          tooltip="Inspect this record's source"
        />
      </OverflowMenu>
    </TaskDialog>,
  );
  await user.click(screen.getByRole("button", { name: "Record operations" }));
  const inspect = screen.getByRole("button", { name: "Inspect record" });
  act(() => {
    inspect.focus();
  });
  expect(screen.getByRole("tooltip").closest("dialog")).toBe(
    screen.getByRole("dialog"),
  );
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  expect(
    screen.getByRole("group", { name: "Record operations menu" }),
  ).toBeInTheDocument();
  expect(close).not.toHaveBeenCalled();
  expect(inspect).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(
    screen.queryByRole("group", { name: "Record operations menu" }),
  ).not.toBeInTheDocument();
  expect(close).not.toHaveBeenCalled();
  expect(
    screen.getByRole("button", { name: "Record operations" }),
  ).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(close).toHaveBeenCalledOnce();
});

test("native cancel dismisses a tooltip before invoking modal dismissal", () => {
  const close = vi.fn();
  render(
    <TaskDialog title="Modal" onClose={close}>
      <IconButton
        icon="more"
        label="Record actions"
        tooltip="Inspect other operations"
      />
    </TaskDialog>,
  );
  const button = screen.getByRole("button");
  act(() => {
    button.focus();
  });
  expect(screen.getByRole("tooltip")).toBeInTheDocument();
  fireEvent(
    screen.getByRole("dialog"),
    new Event("cancel", { cancelable: true }),
  );
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  expect(close).not.toHaveBeenCalled();
  fireEvent(
    screen.getByRole("dialog"),
    new Event("cancel", { cancelable: true }),
  );
  expect(close).toHaveBeenCalledOnce();
});

test("creation choosers stay visibly labelled and preserve keyboard navigation", async () => {
  render(
    <OverflowMenu label="+ New record" ariaLabel="New record">
      <button type="button">New seed lot</button>
    </OverflowMenu>,
  );
  const trigger = screen.getByRole("button", { name: "New record" });
  expect(trigger).toHaveTextContent("New record");
  expect(trigger.querySelectorAll(":scope > svg")).toHaveLength(2);
  expect(trigger.querySelector(".control-icon-button__label")).toBeNull();
  trigger.focus();
  await userEvent.keyboard("{ArrowDown}");
  expect(
    await screen.findByRole("button", { name: "New seed lot" }),
  ).toBeInTheDocument();
});
