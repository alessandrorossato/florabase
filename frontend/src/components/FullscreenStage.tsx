import type { ReactNode } from "react";

import { FullscreenButton } from "./FullscreenButton";
import { useFullscreen } from "./useFullscreen";

/** A titled diagram section with a full-screen toggle beside its heading (UI-POLISH-004). */
export function FullscreenStage({
  className,
  title,
  titleId,
  label,
  children,
}: {
  className: string;
  title: ReactNode;
  titleId: string;
  /** What the toggle enlarges, for its accessible name. */
  label: string;
  children: ReactNode;
}) {
  const {
    active: fullscreenActive,
    toggle: toggleFullscreen,
    setFrame,
    frameClass,
  } = useFullscreen();
  return (
    <section
      ref={setFrame}
      className={`${className}${frameClass}`}
      aria-labelledby={titleId}
    >
      <div className="fullscreen-stage__header">
        <h3 id={titleId}>{title}</h3>
        <FullscreenButton
          active={fullscreenActive}
          toggle={toggleFullscreen}
          label={label}
        />
      </div>
      {children}
    </section>
  );
}
