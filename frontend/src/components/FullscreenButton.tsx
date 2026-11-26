import { Icon } from "./Icon";
import "./fullscreen.css";

/** The toggle for useFullscreen; it names what it enlarges for assistive technology. */
export function FullscreenButton({
  active,
  toggle,
  label,
}: {
  active: boolean;
  toggle: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      className="button--secondary fullscreen-toggle"
      aria-label={active ? `Exit full screen ${label}` : `Full screen ${label}`}
      title={active ? "Exit full screen (Esc)" : "Full screen"}
      onClick={toggle}
    >
      <Icon name={active ? "close" : "maximize"} />
      <span>{active ? "Exit full screen" : "Full screen"}</span>
    </button>
  );
}
