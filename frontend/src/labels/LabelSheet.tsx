import { useMemo } from "react";
import { qrGeometry } from "./qrCode";

import { labelTypeNames, recordUrl, type LabelRecord } from "./labelData";

function PrintedLabel({
  record,
  canonicalOrigin,
}: {
  record: LabelRecord;
  canonicalOrigin: string | null;
}) {
  const url = recordUrl(record.kind, record.id, canonicalOrigin);
  const geometry = useMemo(() => qrGeometry(url), [url]);
  return (
    <article
      className="physical-label"
      aria-label={`${labelTypeNames[record.kind]}: ${record.botanicalName}`}
    >
      <div className="physical-label__text">
        <strong className="physical-label__name" title={record.botanicalName}>
          {record.botanicalName}
        </strong>
        <span className="physical-label__type">
          {labelTypeNames[record.kind]}
        </span>
        {record.context && (
          <span className="physical-label__context" title={record.context}>
            {record.context}
          </span>
        )}
        <span className="physical-label__brand">Florabase</span>
      </div>
      <svg
        className="physical-label__qr"
        role="img"
        aria-label={`QR to ${labelTypeNames[record.kind]} record`}
        viewBox={`0 0 ${String(geometry.size)} ${String(geometry.size)}`}
        shapeRendering="crispEdges"
      >
        <title>{url}</title>
        <rect width={geometry.size} height={geometry.size} fill="#fff" />
        <path d={geometry.path} fill="#000" />
      </svg>
    </article>
  );
}

export function LabelSheet({
  pages,
  canonicalOrigin,
}: {
  pages: LabelRecord[][];
  canonicalOrigin: string | null;
}) {
  return pages.map((records, page) => (
    <div className="label-page" key={page}>
      {records.map((record, index) => (
        <PrintedLabel
          key={`${record.kind}:${record.id}:${String(index)}`}
          record={record}
          canonicalOrigin={canonicalOrigin}
        />
      ))}
    </div>
  ));
}
