import type { ReactNode, SVGProps } from "react";

const shapes = {
  eye: (
    <>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  document: (
    <>
      <path d="M5 3h10l4 4v14H5ZM14 3v5h5M8 12h8M8 16h6" />
    </>
  ),
  overview: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </>
  ),
  seed: (
    <>
      <rect x="5" y="2" width="14" height="20" rx="1" />
      <path d="M5 6h14M9 16c-3-4 3-8 6-5 3 4-3 8-6 5Zm0 0 6-5" />
    </>
  ),
  sprout: (
    <>
      <path d="M12 21V11M12 15C5 15 3 11 3 5c6 0 9 3 9 10ZM12 11c0-5 3-8 9-8 0 6-3 9-9 8Z" />
    </>
  ),
  plant: (
    <>
      <path d="M19 3C6 2 2 10 7 17c8 5 14-4 12-14ZM4 21 15 8" />
    </>
  ),
  harvest: (
    <>
      <path d="M3 10h18l-3 11H6ZM7 10l5-8 5 8M9 14v3m6-3v3" />
    </>
  ),
  pin: (
    <>
      <path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z" />
      <circle cx="12" cy="10" r="3" />
    </>
  ),
  journal: (
    <>
      <path d="M5 3h15v18H5ZM8 3v18M3 7h4M3 12h4M3 17h4M11 8h6M11 12h6" />
    </>
  ),
  history: (
    <>
      <path d="M3 11a9 9 0 1 1 2 7M3 4v7h7M12 7v5l4 2" />
    </>
  ),
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M7 2v6m10-6v6M3 11h18M7 15h2m6 0h2M7 18h2" />
    </>
  ),
  flower: (
    <>
      <path d="M12 8C5-1 1 8 8 12c-9 7 0 13 4 4 6 9 14 0 4-4 8-6 0-13-4-4Z" />
      <circle cx="12" cy="12" r="2" />
    </>
  ),
  taxonomy: (
    <>
      <rect x="9" y="2" width="6" height="5" rx="1" />
      <rect x="2" y="17" width="6" height="5" rx="1" />
      <rect x="16" y="17" width="6" height="5" rx="1" />
      <path d="M12 7v5M5 17v-5h14v5" />
    </>
  ),
  image: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="8" cy="8" r="2" />
      <path d="m3 18 6-6 4 4 4-7 4 6" />
    </>
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <ellipse cx="12" cy="12" rx="4" ry="9" />
      <path d="M3 12h18M5 6h14M5 18h14" />
    </>
  ),
  store: (
    <>
      <path d="M3 10h18l-2-7H5ZM5 10v11h14V10M9 21v-7h6v7M3 10c0 4 4 4 5 1 1 3 6 3 7 0 1 3 6 3 6-1" />
    </>
  ),
  parcel: (
    <>
      <path d="m3 6 9-4 9 4v12l-9 4-9-4ZM3 6l9 4 9-4M12 10v12M8 4l9 4v5" />
    </>
  ),
  tag: (
    <>
      <path d="M3 3h9l10 10-9 9L3 12Z" />
      <circle cx="8" cy="8" r="1.5" />
    </>
  ),
  exchange: <path d="M3 7h17l-4-4m4 4-4 4M21 17H4l4-4m-4 4 4 4" />,
  gear: (
    <>
      <path d="m9 3 1-1h4l1 3 3 1 3-1 2 4-2 2v3l2 2-2 4-3-1-3 1-1 3h-4l-1-3-3-1-3 1-2-4 2-2v-3L1 9l2-4 3 1Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  list: (
    <>
      <path d="M8 5h13M8 12h13M8 19h13M3 5h1M3 12h1M3 19h1" />
    </>
  ),
  gallery: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </>
  ),
  maximize: <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5" />,
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
