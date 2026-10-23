import type { ReactNode, SVGProps } from "react";

const shapes = {
  menu: <path d="M3 6h18M3 12h18M3 18h18" />,
  "panel-close": (
    <>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M9 3v18m7-13-4 4 4 4" />
    </>
  ),
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m16 16 5 5" />
    </>
  ),
  filter: <path d="M3 4h18l-7 8v7l-4 2v-9Z" />,
  "saved-views": (
    <>
      <path d="M6 3h12v18l-6-4-6 4Z" />
      <path d="M9 7h6M9 10h6" />
    </>
  ),
  add: <path d="M12 4v16M4 12h16" />,
  edit: (
    <>
      <path d="m4 16-1 5 5-1L20 8l-4-4ZM13.5 6.5l4 4" />
      <path d="m16 4 1-1a2.8 2.8 0 0 1 4 4l-1 1" />
    </>
  ),
  more: (
    <>
      <circle cx="5" cy="12" r="1" />
      <circle cx="12" cy="12" r="1" />
      <circle cx="19" cy="12" r="1" />
    </>
  ),
  print: (
    <>
      <path d="M7 8V3h10v5M7 17H4V9h16v8h-3M7 14h10v7H7Z" />
      <path d="M16.5 11h.5" />
    </>
  ),
  refresh: (
    <>
      <path d="M20 10a8 8 0 0 0-14-5L3 8m0-5v5h5M4 14a8 8 0 0 0 14 5l3-3m0 5v-5h-5" />
    </>
  ),
  download: <path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5" />,
  // Horizontal sliders distinguish Settings from the funnel used by Filters.
  settings: (
    <>
      <path d="M3 6h4m4 0h10M3 12h10m4 0h4M3 18h2m4 0h12" />
      <circle cx="9" cy="6" r="2" />
      <circle cx="15" cy="12" r="2" />
      <circle cx="7" cy="18" r="2" />
    </>
  ),
  back: <path d="m10 5-7 7 7 7M3 12h18" />,
  "clear-selection": (
    <>
      <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M9 9l6 6m0-6-6 6" />
    </>
  ),
  layers: (
    <>
      <path d="m3 7 9-4 9 4-9 4ZM3 12l9 4 9-4M3 17l9 4 9-4" />
    </>
  ),
  "chevron-down": <path d="m6 9 6 6 6-6" />,
  "chevron-up": <path d="m6 15 6-6 6 6" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  monitor: (
    <>
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M12 16v5M8 21h8" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6 19 19M5 19l1.4-1.4M17.6 6.4 19 5" />
    </>
  ),
  moon: <path d="M20.9 13.1A9 9 0 0 1 10.9 3.1a9 9 0 1 0 10 10Z" />,
} satisfies Record<string, ReactNode>;
export type IconName = keyof typeof shapes;

export function Icon({
  name,
  shell = false,
  ...props
}: SVGProps<SVGSVGElement> & {
  name: IconName;
  shell?: boolean;
}) {
  return (
    <svg
      {...props}
      className={`control-icon${shell ? " control-icon--shell" : ""}`}
      data-icon={name}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {shapes[name]}
    </svg>
  );
}
