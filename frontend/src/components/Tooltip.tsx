import {
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type HTMLAttributes,
  type ReactElement,
  type Ref,
} from "react";
import { createPortal } from "react-dom";
import { controlOverlayHost, registerControlLayer } from "./controlLayers";

type TriggerProps = HTMLAttributes<HTMLElement> & {
  ref?: Ref<HTMLElement>;
  disabled?: boolean;
  title?: string;
};

/** A noninteractive description on one native trigger; the trigger always owns its name. */
export function Tooltip({
  children,
  content,
  disabled = false,
}: {
  children: ReactElement<TriggerProps>;
  content: string;
  disabled?: boolean;
}) {
  const id = useId();
  const anchor = useRef<HTMLElement | null>(null);
  const wrapper = useRef<HTMLSpanElement | null>(null);
  const tip = useRef<HTMLDivElement | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const hovered = useRef(false);
  const tipHovered = useRef(false);
  const focused = useRef(false);
  const pointerFocus = useRef(false);
  const suppressed = useRef(false);
  const [open, setOpen] = useState(false);
  const [host, setHost] = useState<HTMLElement | null>(null);
  const [position, setPosition] = useState<{
    left: number;
    top: number;
  } | null>(null);
  const original = children.props;
  const cancelTimer = useCallback(() => {
    clearTimeout(timer.current);
    timer.current = undefined;
  }, []);
  const close = useCallback(
    (suppress = false) => {
      cancelTimer();
      if (suppress) suppressed.current = true;
      setOpen(false);
      setPosition(null);
    },
    [cancelTimer],
  );
  const available =
    !disabled &&
    !original.disabled &&
    original["aria-expanded"] !== true &&
    original["aria-expanded"] !== "true";
  const show = () => {
    cancelTimer();
    const trigger = wrapper.current?.firstElementChild;
    if (
      available &&
      !suppressed.current &&
      trigger instanceof HTMLElement &&
      !trigger.matches(":disabled")
    ) {
      anchor.current = trigger;
      setHost(controlOverlayHost(trigger));
      setOpen(true);
    }
  };
  const leave = () => {
    cancelTimer();
    timer.current = setTimeout(() => {
      if (!hovered.current && !tipHovered.current && !focused.current) close();
    }, 150);
  };
  useEffect(() => cancelTimer, [cancelTimer]);
  // Reset a pending opening when a chooser disables descriptions. This guarded
  // render adjustment prevents an old tooltip resurfacing when the chooser closes.
  if (!available && open) {
    setOpen(false);
    setPosition(null);
  }
  const visible = open && available;
  useLayoutEffect(() => {
    const trigger = anchor.current;
    const tooltip = tip.current;
    if (!visible || !trigger || !tooltip) return;
    // Manual popovers remain in the modal subtree and do not focus or light-dismiss other surfaces.
    if (typeof tooltip.showPopover === "function") tooltip.showPopover();
    const describe = () => {
      const ids =
        trigger
          .getAttribute("aria-describedby")
          ?.split(/\s+/)
          .filter(Boolean) ?? [];
      if (!ids.includes(id))
        trigger.setAttribute("aria-describedby", [...ids, id].join(" "));
    };
    describe();
    const place = () => {
      if (
        !trigger.isConnected ||
        trigger.closest('[hidden], [inert], [aria-hidden="true"]') ||
        trigger.closest("dialog:not([open])") ||
        getComputedStyle(trigger).visibility === "hidden" ||
        getComputedStyle(trigger).display === "none"
      ) {
        close();
        return;
      }
      const rect = trigger.getBoundingClientRect();
      const view = window.visualViewport;
      const leftEdge = (view?.offsetLeft ?? 0) + 8;
      const topEdge = (view?.offsetTop ?? 0) + 8;
      const rightEdge = leftEdge + (view?.width ?? window.innerWidth) - 16;
      const bottomEdge = topEdge + (view?.height ?? window.innerHeight) - 16;
      if (
        !rect.width ||
        !rect.height ||
        rect.bottom <= topEdge ||
        rect.top >= bottomEdge ||
        rect.right <= leftEdge ||
        rect.left >= rightEdge
      ) {
        close();
        return;
      }
      for (
        let parent = trigger.parentElement;
        parent && parent !== document.body;
        parent = parent.parentElement
      ) {
        if (
          /(auto|scroll|hidden|clip)/.test(
            `${getComputedStyle(parent).overflow} ${getComputedStyle(parent).overflowX} ${getComputedStyle(parent).overflowY}`,
          )
        ) {
          const box = parent.getBoundingClientRect();
          if (
            rect.bottom <= box.top ||
            rect.top >= box.bottom ||
            rect.right <= box.left ||
            rect.left >= box.right
          ) {
            close();
            return;
          }
        }
      }
      tooltip.style.maxWidth = `min(18rem, ${String(Math.max(16, rightEdge - leftEdge))}px)`;
      const box = tooltip.getBoundingClientRect();
      let left = rect.left + (rect.width - box.width) / 2;
      let top = rect.top - box.height - 8;
      if (top < topEdge) top = rect.bottom + 8;
      if (top + box.height > bottomEdge) {
        if (rect.right + 8 + box.width <= rightEdge) left = rect.right + 8;
        else if (rect.left - 8 - box.width >= leftEdge)
          left = rect.left - 8 - box.width;
        top = Math.max(topEdge, Math.min(top, bottomEdge - box.height));
      }
      left = Math.max(leftEdge, Math.min(left, rightEdge - box.width));
      setPosition((current) =>
        current?.left === left && current.top === top ? current : { left, top },
      );
    };
    place();
    const unregister = registerControlLayer({
      element: tooltip,
      priority: 3,
      dismiss: () => {
        close(true);
      },
    });
    const resize =
      typeof ResizeObserver === "undefined"
        ? undefined
        : new ResizeObserver(place);
    resize?.observe(trigger);
    resize?.observe(tooltip);
    const mutation = new MutationObserver(() => {
      describe();
      place();
    });
    // Watch ancestor visibility without observing our own positioning writes.
    for (
      let parent: HTMLElement | null = trigger;
      parent;
      parent = parent.parentElement
    )
      mutation.observe(parent, {
        attributes: true,
        attributeFilter: [
          "aria-describedby",
          "hidden",
          "inert",
          "aria-hidden",
          "open",
          "class",
          "style",
        ],
      });
    window.addEventListener("scroll", place, true);
    window.addEventListener("resize", place);
    window.visualViewport?.addEventListener("resize", place);
    window.visualViewport?.addEventListener("scroll", place);
    return () => {
      const descriptions = trigger
        .getAttribute("aria-describedby")
        ?.split(/\s+/)
        .filter((value) => value && value !== id)
        .join(" ");
      if (descriptions) trigger.setAttribute("aria-describedby", descriptions);
      else trigger.removeAttribute("aria-describedby");
      unregister();
      resize?.disconnect();
      mutation.disconnect();
      window.removeEventListener("scroll", place, true);
      window.removeEventListener("resize", place);
      window.visualViewport?.removeEventListener("resize", place);
      window.visualViewport?.removeEventListener("scroll", place);
      if (
        typeof tooltip.hidePopover === "function" &&
        tooltip.matches(":popover-open")
      )
        tooltip.hidePopover();
    };
  }, [visible, close, id]);
  return (
    <>
      <span
        className="tooltip-trigger"
        ref={wrapper}
        onPointerEnter={(event) => {
          if (
            event.pointerType === "touch" ||
            window.matchMedia("(hover: none), (any-pointer: coarse)").matches
          )
            return;
          hovered.current = true;
          suppressed.current = false;
          cancelTimer();
          timer.current = setTimeout(show, 500);
        }}
        onPointerLeave={() => {
          hovered.current = false;
          suppressed.current = false;
          leave();
        }}
        onPointerDownCapture={() => {
          pointerFocus.current = true;
          close(true);
        }}
        onFocusCapture={() => {
          const trigger = wrapper.current?.firstElementChild;
          if (
            !pointerFocus.current &&
            trigger instanceof HTMLElement &&
            trigger.matches(":focus-visible")
          ) {
            focused.current = true;
            show();
          }
        }}
        onBlurCapture={() => {
          focused.current = false;
          pointerFocus.current = false;
          suppressed.current = false;
          leave();
        }}
        onClickCapture={() => {
          close(true);
        }}
        onKeyDownCapture={(event) => {
          if (["Enter", " ", "ArrowDown", "ArrowUp"].includes(event.key))
            close(true);
        }}
      >
        {children}
      </span>
      {visible &&
        host &&
        createPortal(
          <div
            ref={tip}
            id={id}
            role="tooltip"
            popover={
              typeof HTMLElement.prototype.showPopover === "function"
                ? "manual"
                : undefined
            }
            className="controls-tooltip"
            style={{
              left: position?.left ?? 0,
              top: position?.top ?? 0,
              visibility: position ? "visible" : "hidden",
            }}
            onPointerEnter={() => {
              tipHovered.current = true;
              cancelTimer();
            }}
            onPointerLeave={() => {
              tipHovered.current = false;
              leave();
            }}
          >
            {content}
          </div>,
          host,
        )}
    </>
  );
}
