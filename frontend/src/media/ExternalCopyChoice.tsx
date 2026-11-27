import { useMediaDefaults } from "./useMediaDefaults";

export function ExternalCopyChoice({ disabled }: { disabled: boolean }) {
  const defaults = useMediaDefaults();
  return (
    <div className="external-copy-choice">
      <label className="checkbox-label">
        <input
          // Remount once the saved default arrives so it becomes the initial state.
          key={defaults ? "configured" : "built-in"}
          type="checkbox"
          name="save_local_copy"
          defaultChecked={defaults?.media_save_local_copy_default ?? true}
          disabled={disabled}
        />
        Save a local copy in Florabase
      </label>
      <p className="field-help">
        Florabase downloads a protected, persistent image when you save. When
        disabled, keep this as an external reference only.
      </p>
    </div>
  );
}
