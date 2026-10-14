import { useMemo } from "react";
import { CategoryGlyph } from "./CategoryGlyph";
import {
  recordUrl,
  labelTypeNames,
  type LabelPreset,
  type LabelRecord,
} from "./labelData";
import { qrGeometry } from "./qrCode";
export function LabelQr({
  record,
  baseUrl,
  preset,
}: {
  record: LabelRecord;
  baseUrl: string;
  preset: LabelPreset;
}) {
  const url = recordUrl(record.kind, record.id, baseUrl, record.harvestId);
  const geometry = useMemo(
    () => qrGeometry(url, preset.id !== "small"),
    [url, preset.id],
  );
  return (
    <div
      className="label-qr"
      data-destination={url}
      data-glyph-placement={geometry.icon ? "inset" : "adjacent"}
    >
      <svg
        role="img"
        aria-label={`QR to ${labelTypeNames[record.kind]} source record`}
        viewBox={`0 0 ${String(geometry.size)} ${String(geometry.size)}`}
        className="label-qr__code"
        shapeRendering="crispEdges"
      >
        <rect width={geometry.size} height={geometry.size} fill="white" />
        <path d={geometry.path} fill="black" />
        {geometry.icon && (
          <g>
            <rect
              {...{
                x: geometry.icon.x,
                y: geometry.icon.y,
                width: geometry.icon.size,
                height: geometry.icon.size,
              }}
              fill="white"
            />
            <svg
              x={geometry.icon.x + 0.6}
              y={geometry.icon.y + 0.6}
              width={geometry.icon.size - 1.2}
              height={geometry.icon.size - 1.2}
              viewBox="0 0 24 24"
              color="black"
              shapeRendering="geometricPrecision"
            >
              <CategoryGlyph kind={record.kind} />
            </svg>
          </g>
        )}
      </svg>
      {!geometry.icon && (
        <CategoryGlyph kind={record.kind} className="label-qr__adjacent" />
      )}
    </div>
  );
}
