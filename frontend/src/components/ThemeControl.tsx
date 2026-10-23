import { Icon } from "./Icon";
import { Tooltip } from "./Tooltip";
import {
  appearanceLabels,
  paletteLabels,
  useAppearance,
} from "../appearance/theme";

export function ThemeControl() {
  const { palette, appearance, effectiveAppearance, cycleAppearance } =
    useAppearance();
  const mode = appearanceLabels[appearance];
  const next =
    appearance === "system"
      ? "Light"
      : appearance === "light"
        ? "Dark"
        : "System";
  const current =
    appearance === "system"
      ? `System (${appearanceLabels[effectiveAppearance]})`
      : mode;
  const label = `Appearance: ${current}, ${paletteLabels[palette]}. Switch to ${next}.`;
  return (
    <Tooltip content={`${current} appearance. Switch to ${next}.`}>
      <button
        type="button"
        className="theme-preview control-icon-button button--quiet"
        aria-label={label}
        onClick={cycleAppearance}
      >
        <Icon
          name={
            appearance === "system"
              ? "monitor"
              : appearance === "light"
                ? "sun"
                : "moon"
          }
          shell
          data-appearance={appearance}
        />
        <span className="control-icon-button__label">Appearance</span>
      </button>
    </Tooltip>
  );
}
