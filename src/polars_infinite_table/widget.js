export function render({ model, el }) {
  el.classList.add("polars-infinite-table");

  const container = document.createElement("div");
  container.style.display = "inline-block";
  container.style.width = "max-content";
  container.style.maxWidth = "100%";
  container.style.maxHeight = model.get("max_height") || "500px";
  container.style.overflow = "auto";
  container.style.border = "1px solid #ccc";

  const table = document.createElement("table");
  table.className = "dataframe";
  const tbody = document.createElement("tbody");

  const setHeaderOffset = () => {
    const firstHeaderRow = table.querySelector("thead tr:nth-child(1)");
    if (!firstHeaderRow) return;
    const rowHeight = Math.ceil(firstHeaderRow.getBoundingClientRect().height);
    table.style.setProperty("--header-row-1-height", `${rowHeight}px`);
  };
  const updateHeader = () => {
    table.innerHTML = model.get("header_html") || "";
    table.appendChild(tbody);
    requestAnimationFrame(setHeaderOffset);
  };
  container.appendChild(table);

  const status = document.createElement("div");
  status.className = "polars-row-status";
  const statusText = document.createElement("span");
  const reverseLink = document.createElement("button");
  reverseLink.type = "button";
  reverseLink.className = "polars-reverse-link";
  reverseLink.addEventListener("click", (event) => {
    event.preventDefault();
    model.set("reverse_order", !model.get("reverse_order"));
    model.save_changes();
  });
  status.appendChild(statusText);
  status.appendChild(document.createTextNode(" "));
  status.appendChild(reverseLink);

  const updateStatus = () => {
    if (!model.get("is_initialized")) {
      statusText.textContent = "Loading rows...";
      return;
    }
    const loadedRows = model.get("loaded_rows") || 0;
    const totalRows = model.get("total_rows") || 0;
    statusText.textContent = `Loaded ${loadedRows} of ${totalRows} rows`;
  };
  const updateReverseLink = () => {
    const totalRows = model.get("total_rows") || 0;
    reverseLink.style.display = totalRows < 2 ? "none" : "inline";
    reverseLink.textContent = model.get("reverse_order")
      ? "Reverse (on)"
      : "Reverse";
  };

  const sentinel = document.createElement("div");
  sentinel.style.height = "5px";
  sentinel.style.width = "100%";
  sentinel.style.display = "block";
  container.appendChild(sentinel);

  let requestInFlight = false;
  let loadWatchdogId = null;
  const clearLoadWatchdog = () => {
    if (loadWatchdogId !== null) {
      clearTimeout(loadWatchdogId);
      loadWatchdogId = null;
    }
  };
  const updateSentinel = () => {
    sentinel.style.display = model.get("has_more_rows") ? "block" : "none";
  };

  const loadMore = () => {
    if (requestInFlight) return;
    if (!model.get("has_more_rows")) return;
    requestInFlight = true;
    model.set("load_token", model.get("load_token") + 1);
    model.save_changes();
    clearLoadWatchdog();
    // Recover if the kernel never answers.
    loadWatchdogId = setTimeout(() => {
      requestInFlight = false;
      loadWatchdogId = null;
    }, 2000);
  };
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries[0] && entries[0].isIntersecting) loadMore();
    },
    { root: container, rootMargin: "150px" },
  );

  // Table width can settle after initial layout (fonts, column widths); keep the
  // sentinel spanning the full scroll width.
  const sentinelWidthSync = () => {
    const targetWidth = Math.max(table.scrollWidth, container.clientWidth || 0);
    sentinel.style.width = `${targetWidth}px`;
  };
  const tableResizeObserver = new ResizeObserver(sentinelWidthSync);
  tableResizeObserver.observe(table);
  const onWindowResize = () => {
    setHeaderOffset();
    sentinelWidthSync();
  };
  window.addEventListener("resize", onWindowResize);

  const maybeLoadInitialChunk = () => {
    const loadedRows = model.get("loaded_rows") || 0;
    if (loadedRows > 0 || !model.get("has_more_rows")) return;
    loadMore();
  };

  const appendRows = (html) => {
    if (!html) return;
    const temp = document.createElement("tbody");
    temp.innerHTML = html;
    while (temp.firstChild) tbody.appendChild(temp.firstChild);
  };
  let resetScrollOnNextStaticRows = false;
  const replaceRowsPreservingScroll = (html) => {
    const previousTop = resetScrollOnNextStaticRows ? 0 : container.scrollTop;
    const previousLeft = resetScrollOnNextStaticRows ? 0 : container.scrollLeft;
    resetScrollOnNextStaticRows = false;
    tbody.innerHTML = "";
    appendRows(html);
    requestAnimationFrame(() => {
      container.scrollTop = previousTop;
      container.scrollLeft = previousLeft;
    });
  };

  const settleRequest = () => {
    requestInFlight = false;
    clearLoadWatchdog();
  };
  const onNewRowsHtml = () => {
    appendRows(model.get("new_rows_html"));
    settleRequest();
    sentinelWidthSync();
    updateStatus();
  };
  const onStaticRowsHtml = () => {
    replaceRowsPreservingScroll(model.get("static_rows_html"));
    settleRequest();
    sentinelWidthSync();
    updateStatus();
    maybeLoadInitialChunk();
  };
  const onReverseOrderChange = () => {
    resetScrollOnNextStaticRows = true;
    updateReverseLink();
  };
  const onLoadedRows = () => {
    settleRequest();
    updateStatus();
  };
  const applyStateFromModel = () => {
    updateHeader();
    replaceRowsPreservingScroll(model.get("static_rows_html"));
    settleRequest();
    sentinelWidthSync();
    updateSentinel();
    updateStatus();
    updateReverseLink();
    maybeLoadInitialChunk();
  };

  model.on("change:new_rows_token", onNewRowsHtml);
  model.on("change:header_html", updateHeader);
  model.on("change:static_rows_html", onStaticRowsHtml);
  model.on("change:has_more_rows", updateSentinel);
  model.on("change:loaded_rows", onLoadedRows);
  model.on("change:total_rows", applyStateFromModel);
  model.on("change:reverse_order", onReverseOrderChange);

  // Apply state after listeners are attached to avoid hydration races.
  applyStateFromModel();

  observer.observe(sentinel);
  el.appendChild(container);
  el.appendChild(status);

  return () => {
    observer.disconnect();
    tableResizeObserver.disconnect();
    window.removeEventListener("resize", onWindowResize);
    clearLoadWatchdog();
    model.off("change:new_rows_token", onNewRowsHtml);
    model.off("change:header_html", updateHeader);
    model.off("change:static_rows_html", onStaticRowsHtml);
    model.off("change:has_more_rows", updateSentinel);
    model.off("change:loaded_rows", onLoadedRows);
    model.off("change:total_rows", applyStateFromModel);
    model.off("change:reverse_order", onReverseOrderChange);
  };
}
