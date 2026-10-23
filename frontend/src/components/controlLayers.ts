interface DismissLayer {
  element: HTMLElement;
  priority: number;
  dismiss: () => void;
}
const layers: DismissLayer[] = [];
function topLayer(dialog?: HTMLElement) {
  const activeDialog =
    dialog ?? Array.from(document.querySelectorAll("dialog[open]")).at(-1);
  return layers
    .filter(
      (layer) =>
        layer.element.isConnected &&
        (!activeDialog || activeDialog.contains(layer.element)),
    )
    .sort((a, b) => a.priority - b.priority)
    .at(-1);
}
function escape(event: KeyboardEvent) {
  if (event.key !== "Escape" || event.defaultPrevented) return;
  const layer = topLayer();
  if (!layer) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  layer.dismiss();
}
export function registerControlLayer(layer: DismissLayer) {
  if (!layers.length) document.addEventListener("keydown", escape, true);
  layers.push(layer);
  return () => {
    const index = layers.indexOf(layer);
    if (index >= 0) layers.splice(index, 1);
    if (!layers.length) document.removeEventListener("keydown", escape, true);
  };
}
export function dismissDialogControlLayer(dialog: HTMLElement) {
  const layer = topLayer(dialog);
  layer?.dismiss();
  return Boolean(layer);
}
export function controlOverlayHost(trigger: HTMLElement) {
  const parent = trigger.closest("dialog[open]") ?? document.body;
  let host = parent.querySelector<HTMLElement>(
    ":scope > [data-controls-overlay-host]",
  );
  if (!host) {
    host = document.createElement("div");
    host.dataset.controlsOverlayHost = "";
    host.className = "controls-overlay-host";
    parent.append(host);
  }
  return host;
}
