export type ThemePreview = "System" | "Light" | "Dark";
const modes: ThemePreview[] = ["System", "Light", "Dark"];

export function ThemeControl({
  mode,
  onPreviewChange,
}: {
  mode: ThemePreview;
  onPreviewChange: (mode: ThemePreview) => void;
}) {
  const label = `Theme preview: ${mode}. Theme switching is not enabled yet.`;
  return (
    <button
      type="button"
      className="theme-preview"
      aria-label={label}
      title={label}
      onClick={() => {
        onPreviewChange(modes[(modes.indexOf(mode) + 1) % modes.length]);
      }}
    >
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
        data-preview={mode.toLowerCase()}
      >
        {mode === "System" ? (
          <>
            <rect x="3" y="4" width="18" height="12" rx="2" />
            <path d="M12 16v5M8 21h8" />
          </>
        ) : mode === "Light" ? (
          <>
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6 19 19M5 19l1.4-1.4M17.6 6.4 19 5" />
          </>
        ) : (
          <path d="M20.9 13.1A9 9 0 0 1 10.9 3.1a9 9 0 1 0 10 10Z" />
        )}
      </svg>
    </button>
  );
}
