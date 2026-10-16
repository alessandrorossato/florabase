export function ExternalCopyChoice({ disabled }: { disabled: boolean }) {
  return (
    <div className="external-copy-choice">
      <label className="checkbox-label">
        <input
          type="checkbox"
          name="save_local_copy"
          defaultChecked
          disabled={disabled}
        />
        Save a local copy in Florabase
      </label>
      <p className="field-help">
        Florabase downloads a protected, persistent image. When disabled, keep
        this as an external reference only.
      </p>
    </div>
  );
}
