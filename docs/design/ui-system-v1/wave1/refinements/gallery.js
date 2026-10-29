(async () => {
  const captures = await fetch("captures.json").then((r) => r.json());
  const controls = Object.fromEntries(
    ["page", "view", "width", "theme"].map((id) => [
      id,
      document.getElementById(id),
    ]),
  );
  const matrix = new Set();
  for (const page of [
    "dashboard",
    "seeds-list",
    "seeds-gallery",
    "plants-list",
    "plants-gallery",
  ])
    for (const width of [1440, 1024, 880, 390])
      for (const theme of ["light", "dark"])
        matrix.add(`${page}-${width}-${theme}`);
  function update() {
    const page = controls.page.value;
    controls.view.disabled = page === "dashboard";
    const id = `${page}${page === "dashboard" ? "" : `-${controls.view.value}`}-${controls.width.value}-${controls.theme.value}`;
    const capture = captures.find((c) => c.id === id);
    for (const [side, root] of [
      ["before", "wave1"],
      ["after", "wave1-final"],
    ]) {
      const url = `/renders/${root}/${id}.jpg`;
      document.getElementById(side).src = url;
      document.getElementById(`${side}-link`).href = url;
    }
    document.getElementById("measurement").textContent = capture
      ? `${capture.capturedAt} · CSS ${capture.viewport.join("×")} · document ${capture.document.join("×")} · ${capture.theme}.`
      : "Capture unavailable.";
  }
  for (const control of Object.values(controls))
    control.addEventListener("change", update);
  for (const capture of captures.filter((c) => !matrix.has(c.id))) {
    const figure = document.createElement("figure");
    const link = document.createElement("a");
    link.href = `/renders/wave1-final/${capture.id}.jpg`;
    const image = document.createElement("img");
    image.src = link.href;
    image.alt = capture.note;
    image.loading = "lazy";
    link.append(image);
    const caption = document.createElement("figcaption");
    caption.textContent = `${capture.id} · ${capture.note}`;
    figure.append(caption, link);
    document.getElementById("contexts").append(figure);
  }
  update();
})();
