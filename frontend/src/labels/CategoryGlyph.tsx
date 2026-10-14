import type { LabelKind } from "./labelData";
const paths: Record<LabelKind, string> = {
  "seed-lot": "M17 4C7 3 3 10 5 17c2 5 9 5 12-1 2-4 3-8 0-12ZM7 18 16 6",
  plant:
    "M12 21V10M12 14C4 15 3 9 3 6c7-1 9 3 9 8ZM12 10c0-6 5-8 9-7 0 5-3 8-9 7Z",
  "plant-group":
    "M5 21V12m7 9V8m7 13V12M5 12C0 12 1 7 1 7c4 0 5 2 4 5Zm7-4c-5 0-5-5-5-5 4 0 6 2 5 5Zm7 4c0-5 4-5 4-5 1 4-1 6-4 5Z",
  "stored-material":
    "M12 8c-8-5-13 9-5 13 3 1 4 0 5 0s2 1 5 0c8-4 3-18-5-13Zm0 0V3m0 3c2-5 7-4 7-4 0 5-4 5-7 4Z",
};
export function CategoryGlyph({
  kind,
  className = "",
}: {
  kind: LabelKind;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={`category-glyph ${className}`}
      aria-hidden="true"
      focusable="false"
    >
      <path
        d={paths[kind]}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
