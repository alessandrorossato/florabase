import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import {
  labelPreset,
  labelTypeNames,
  sourceHref,
  type LabelRecord,
  type LabelPreset,
} from "./labelData";

import { LabelQr } from "./LabelQr";

function ScientificName({ name }: { name: string }) {
  return (
    <span className="label-scientific-name">
      {name
        .split(/(\b(?:subsp\.|var\.|f\.|sp\.|spp\.|cf\.|aff\.)(?=\s|$))/)
        .map((part, index) =>
          index % 2 ? (
            <span key={index} className="label-name-rank">
              {part}
            </span>
          ) : (
            <i key={index} className="scientific-name">
              {part}
            </i>
          ),
        )}
    </span>
  );
}
export function LabelIdentity({ record }: { record: LabelRecord }) {
  return (
    <>
      <ScientificName name={record.botanicalName} />
      {record.cultivar && (
        <>
          {" "}
          <span className="label-cultivar">‘{record.cultivar}’</span>
        </>
      )}
    </>
  );
}
function Sheet({
  records,
  preset,
  baseUrl,
}: {
  records: LabelRecord[];
  preset: LabelPreset;
  baseUrl: string | null;
}) {
  const labelsPerPage = preset.columns * preset.rows;
  return (
    <div
      className={`label-page label-page--${preset.id}`}
      style={
        {
          "--label-width": `${String(preset.widthMm)}mm`,
          "--label-height": `${String(preset.heightMm)}mm`,
          "--label-columns": preset.columns,
          "--label-rows": preset.rows,
          "--label-margin-x": `${String(preset.marginX)}mm`,
          "--label-margin-y": `${String(preset.marginY)}mm`,
          "--label-qr-size": `${String(preset.qrMm)}mm`,
        } as CSSProperties
      }
    >
      {Array.from({ length: labelsPerPage }, (_, index) => {
        const record = records.at(index);
        const position = {
          "--label-column": index % preset.columns,
          "--label-row": Math.floor(index / preset.columns),
        } as CSSProperties;
        return record ? (
          <article
            key={index}
            className="physical-label"
            style={position}
            data-source={sourceHref(record)}
            aria-label={`${labelTypeNames[record.kind]}: ${record.botanicalName}`}
          >
            <div className="physical-label__content">
              <strong className="physical-label__name">
                <ScientificName name={record.botanicalName} />
              </strong>
              {record.cultivar && (
                <span className="label-cultivar physical-label__cultivar">
                  ‘{record.cultivar}’
                </span>
              )}
              {record.commonName && (
                <span className="physical-label__common-name">
                  {record.commonName}
                </span>
              )}
            </div>
            {baseUrl ? (
              <LabelQr record={record} baseUrl={baseUrl} preset={preset} />
            ) : (
              <div className="label-qr-unconfigured">QR not configured</div>
            )}
          </article>
        ) : (
          <div
            key={index}
            className="physical-label physical-label--empty"
            style={position}
            aria-hidden="true"
          />
        );
      })}
    </div>
  );
}
function PaperPreview({
  records,
  page,
  preset,
  baseUrl,
}: {
  records: LabelRecord[];
  page: number;
  preset: LabelPreset;
  baseUrl: string | null;
}) {
  const labelsPerPage = preset.columns * preset.rows;
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.5);
  const [clipped, setClipped] = useState(0);
  useLayoutEffect(() => {
    const wrapper = ref.current;
    if (!wrapper) return;
    let active = true;
    const update = () => {
      if (!active) return;
      setScale(wrapper.clientWidth / ((210 * 96) / 25.4));
      const clippedSources = new Set<string>();
      wrapper
        .querySelectorAll<HTMLElement>(
          ".physical-label__content, .physical-label__content > *",
        )
        .forEach((element) => {
          if (
            element.scrollHeight > element.clientHeight + 1 ||
            element.scrollWidth > element.clientWidth + 1
          ) {
            const source = element
              .closest("[data-source]")
              ?.getAttribute("data-source");
            if (source) clippedSources.add(source);
          }
        });
      setClipped(clippedSources.size);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(wrapper);
    void document.fonts.ready.then(update);
    return () => {
      active = false;
      observer.disconnect();
    };
  }, [records, preset]);
  return (
    <figure className="label-sheet-preview">
      <figcaption>
        Sheet {page + 1} · {records.length}{" "}
        {records.length === 1 ? "label" : "labels"} ·{" "}
        {labelsPerPage - records.length} empty cells
      </figcaption>
      {clipped > 0 && (
        <p className="label-overflow-warning" role="status">
          Text exceeds the label area for {clipped}{" "}
          {clipped === 1 ? "source" : "sources"}. Check the preview and full
          Label content before printing.
        </p>
      )}
      <div
        ref={ref}
        className="label-paper-preview"
        style={{ "--preview-scale": scale } as CSSProperties}
      >
        <Sheet records={records} preset={preset} baseUrl={baseUrl} />
      </div>
    </figure>
  );
}
export function LabelSheet({
  pages,
  preview = false,
  preset = labelPreset,
  baseUrl = null,
}: {
  pages: LabelRecord[][];
  preview?: boolean;
  preset?: LabelPreset;
  baseUrl?: string | null;
}) {
  return pages.map((records, page) =>
    preview ? (
      <PaperPreview
        key={page}
        records={records}
        page={page}
        preset={preset}
        baseUrl={baseUrl}
      />
    ) : (
      <Sheet key={page} records={records} preset={preset} baseUrl={baseUrl} />
    ),
  );
}
