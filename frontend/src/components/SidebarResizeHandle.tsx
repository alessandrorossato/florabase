import { useEffect, useRef, useState } from "react";

import { sidebarWidthLimit } from "./sidebarWidth";

const minimum = 220;
export function SidebarResizeHandle({
  width,
  onResize,
}: {
  width: number;
  onResize: (width: number) => void;
}) {
  const dragging = useRef<number | null>(null);
  const [maximum, setMaximum] = useState(() =>
    sidebarWidthLimit(window.innerWidth),
  );
  useEffect(() => {
    const resize = () => {
      setMaximum(sidebarWidthLimit(window.innerWidth));
    };
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
    };
  }, []);
  const clamp = (value: number) =>
    Math.max(minimum, Math.min(sidebarWidthLimit(window.innerWidth), value));
  return (
    <div
      className="sidebar-resizer"
      role="separator"
      tabIndex={0}
      aria-label="Resize navigation"
      aria-orientation="vertical"
      aria-valuemin={minimum}
      aria-valuemax={maximum}
      aria-valuenow={width}
      aria-valuetext={`${String(width)} pixels`}
      title="Drag to resize navigation; use arrow keys to adjust"
      onPointerDown={(event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        dragging.current = event.pointerId;
        event.currentTarget.setPointerCapture(event.pointerId);
      }}
      onPointerMove={(event) => {
        if (dragging.current !== event.pointerId) return;
        const left =
          event.currentTarget.parentElement?.getBoundingClientRect().left ?? 0;
        onResize(clamp(Math.round(event.clientX - left)));
      }}
      onPointerUp={(event) => {
        dragging.current = null;
        if (event.currentTarget.hasPointerCapture(event.pointerId))
          event.currentTarget.releasePointerCapture(event.pointerId);
      }}
      onLostPointerCapture={() => {
        dragging.current = null;
      }}
      onPointerCancel={() => {
        dragging.current = null;
      }}
      onKeyDown={(event) => {
        const next =
          event.key === "ArrowLeft"
            ? width - (event.shiftKey ? 32 : 8)
            : event.key === "ArrowRight"
              ? width + (event.shiftKey ? 32 : 8)
              : event.key === "Home"
                ? minimum
                : event.key === "End"
                  ? sidebarWidthLimit(window.innerWidth)
                  : null;
        if (next !== null) {
          event.preventDefault();
          onResize(clamp(next));
        }
      }}
    />
  );
}
