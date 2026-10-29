(async () => {
  const [baseline, captures] = await Promise.all([
    fetch("baseline.json").then((response) => response.json()),
    fetch("captures.json").then((response) => response.json()),
  ]);
  const controls = Object.fromEntries(
    ["page", "view", "width", "theme"].map((id) => [
      id,
      document.getElementById(id),
    ]),
  );
  const update = () => {
    const page = controls.page.value;
    const width = Number(controls.width.value);
    const theme = controls.theme.value;
    controls.view.disabled = page === "dashboard";
    document.getElementById("view-label").hidden = page === "dashboard";
    const prefix =
      page === "dashboard" ? page : `${page}-${controls.view.value}`;
    const after = captures.find(
      (entry) => entry.id === `${prefix}-${width}-${theme}`,
    );
    const before = baseline.find(
      (entry) =>
        entry.page === page && entry.width === width && entry.theme === theme,
    );
    const beforeImage = document.getElementById("before");
    const beforeLink = document.getElementById("before-link");
    beforeImage.hidden = !before;
    beforeLink.removeAttribute("href");
    if (before) {
      beforeImage.src = `/baseline/${before.id}.jpg`;
      beforeLink.href = beforeImage.src;
    }
    document.getElementById("before-note").textContent = before
      ? `${before.capturedAt} · ${page === "dashboard" ? "retained real Dashboard" : "retained single-directory representation; Gallery was unavailable"}.`
      : "No retained baseline at this exact width. The after capture remains measured at the selected viewport.";
    const afterImage = document.getElementById("after");
    afterImage.src = `/renders/wave1/${after.id}.jpg`;
    afterImage.alt = `${page} ${page === "dashboard" ? "" : controls.view.value} — actual production Review, ${width}×844, ${theme}`;
    document.getElementById("after-link").href = afterImage.src;
    document.getElementById("after-note").textContent =
      `${after.capturedAt} · CSS ${after.viewport.join("×")} · JPEG ${after.raster.join("×")} · document ${after.document.join("×")}.`;
    document.getElementById("comparison-note").textContent =
      page === "dashboard"
        ? "Same retained synthetic collection; operational date advances by one day. The new photographs are Media assets, not inferred specimen links."
        : "Same retained API-backed records. Search, lifecycle, quantities and group distinctions remain owned by the existing capability.";
  };
  controls.page.addEventListener("change", () => {
    controls.view.value = controls.page.value === "plants" ? "gallery" : "list";
    update();
  });
  for (const control of Object.values(controls))
    control.addEventListener("change", update);
  const card = (entry, target) => {
    const article = document.createElement("article");
    const title = document.createElement("h3");
    title.textContent = entry.id;
    const link = document.createElement("a");
    link.href = `/renders/wave1/${entry.id}.jpg`;
    const image = document.createElement("img");
    image.src = link.href;
    image.alt = entry.note;
    image.loading = "lazy";
    const note = document.createElement("p");
    note.textContent = entry.note;
    link.append(image);
    article.append(title, link, note);
    target.append(article);
    if (entry.fullPageSupplement) {
      const full = document.createElement("a");
      full.href = `/renders/wave1/${entry.fullPageSupplement}`;
      full.textContent = "Full-page long-record capture";
      article.append(full);
    }
  };
  for (const id of [
    "dashboard-two-images-1440",
    "dashboard-two-images-attribution-1440",
  ])
    card(
      captures.find((entry) => entry.id === id),
      document.getElementById("special"),
    );
  const matrix =
    /^(dashboard|seeds-list|seeds-gallery|plants-list|plants-gallery)-(1440|1024|880|390)-(light|dark)$/;
  for (const entry of captures.filter(
    (entry) =>
      !matrix.test(entry.id) && !entry.id.startsWith("dashboard-two-images"),
  ))
    card(entry, document.getElementById("contexts"));
  update();
})().catch((error) => {
  document.getElementById("comparison-note").textContent =
    `Evidence could not load: ${error.message}`;
});
