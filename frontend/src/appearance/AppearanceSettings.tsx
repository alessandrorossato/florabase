import {
  appearanceLabels,
  paletteLabels,
  useAppearance,
  type Appearance,
  type Palette,
} from "./theme";

const palettes: Palette[] = ["botanical", "herbarium", "mineral"];
const appearances: Appearance[] = ["system", "light", "dark"];

export function AppearanceSettings() {
  const {
    palette,
    appearance,
    effectiveAppearance,
    persistent,
    setPalette,
    setAppearance,
  } = useAppearance();
  return (
    <section
      className="settings-panel appearance-settings"
      aria-labelledby="settings-appearance-heading"
    >
      <h3 id="settings-appearance-heading">Appearance</h3>
      <p className="field-help">
        Applies immediately to this browser, including the sign-in screen.
      </p>
      <fieldset>
        <legend>Color theme</legend>
        <div className="appearance-options appearance-palettes">
          {palettes.map((value) => (
            <label key={value} className="appearance-option">
              <input
                type="radio"
                name="palette"
                value={value}
                checked={palette === value}
                onChange={() => {
                  setPalette(value);
                }}
              />
              <span
                className="appearance-preview"
                data-preview-palette={value}
                data-preview-appearance={effectiveAppearance}
                aria-hidden="true"
              >
                <span>Aa</span>
                <span className="appearance-preview__accent" />
              </span>
              <span>{paletteLabels[value]}</span>
              {palette === value && (
                <span className="appearance-selected" aria-hidden="true">
                  Selected
                </span>
              )}
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend>Appearance</legend>
        <div className="appearance-options">
          {appearances.map((value) => (
            <label key={value} className="appearance-option">
              <input
                type="radio"
                name="appearance"
                value={value}
                checked={appearance === value}
                onChange={() => {
                  setAppearance(value);
                }}
              />
              <span>{appearanceLabels[value]}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <p className="field-help" role="status">
        {appearance === "system"
          ? `System · currently ${appearanceLabels[effectiveAppearance]}.`
          : `${appearanceLabels[appearance]} appearance.`}
        {!persistent &&
          " This preference is temporary because browser storage is unavailable."}
      </p>
    </section>
  );
}
