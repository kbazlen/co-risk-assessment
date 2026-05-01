/**
 * hillshade-cities-addon.js  (v8)
 * ─────────────────────────────────────────────────────────────────────────────
 * Features:
 *   - Hillshade terrain layer (ESRI World Hillshade, multiply blend)
 *   - City markers + labels
 *   - River network clipped to Colorado border with bleed margin
 *   - Top-5 industries panel in the left sidebar (collapsible section)
 *   - Map layers toggles in the left sidebar (collapsible section)
 *   - PNG export (hillshade re-composited with multiply after html2canvas)
 *   - Choropleth legend auto-hides when the processed-data overlay is active
 *
 * v8 changes vs v7:
 *   - Floating industry panel + fixed layer toggles removed.
 *   - Both now render as collapsible sections inside #left-addon-sections
 *     (the div injected at the bottom of #left in index.html).
 *   - Sections built once; sector rows update in-place on click.
 */

(function () {
  "use strict";

  /* ══════════════════════════════════════════════════════════════════════════
   * CONFIG
   * ══════════════════════════════════════════════════════════════════════════ */

  const BBOX = { lonMin: -109.05, latMin: 36.99, lonMax: -102.04, latMax: 41.01 };

  const HILLSHADE_REST =
    "https://services.arcgisonline.com/arcgis/rest/services/Elevation/World_Hillshade/MapServer/export";
  const HILLSHADE_PX      = 1200;
  const HILLSHADE_OPACITY = 0.5;

  const CITY_DOT_RADIUS   = 5;
  const CITY_DOT_COLOR    = "#dc143c";
  const CITY_LABEL_SIZE   = 11;
  const CITY_LABEL_OFFSET = [8, 4];

  const CO_STATE_URL       = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";
  const CO_FIPS            = 8;
  const RIVER_COLOR        = "#0000ff9e";
  const RIVER_OPACITY      = 0.65;
  const RIVER_WIDTH        = 1;
  const RIVERS_URL =
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_rivers_lake_centerlines.geojson";

  const SECTOR_TOP_N       = 5;
  const COUNTY_HIGHLIGHT_N = 5;

  const MAP_CONTAINER_ID = "center";

  const EXCLUDE_SELECTORS = [
    "#png-dl-btn",
    "#overlay-controls",
    "#legend",
    "#tiff-legend",
  ];

  const HAZARD_SEL   = ["#hazard-select", "[data-hazard]", "select:first-of-type"];
  const SCENARIO_SEL = ["#gwl-select",    "[data-scenario]","select:nth-of-type(2)"];

  /* ══════════════════════════════════════════════════════════════════════════
   * CITY DATA
   * ══════════════════════════════════════════════════════════════════════════ */

  const CITIES = [
    { name: "Aurora",           lon: -104.7275, lat: 39.7084 },
    { name: "Boulder",          lon: -105.2515, lat: 40.0273 },
    { name: "Colorado Springs", lon: -104.7606, lat: 38.8674 },
    { name: "Craig",            lon: -107.5557, lat: 40.5170 },
    { name: "Denver",           lon: -104.9893, lat: 39.7627 },
    { name: "Durango",          lon: -107.8703, lat: 37.2750 },
    { name: "Fort Collins",     lon: -105.0657, lat: 40.5478 },
    { name: "Glenwood Springs", lon: -107.3344, lat: 39.5454 },
    { name: "Grand Junction",   lon: -108.5675, lat: 39.0878 },
    { name: "Greeley",          lon: -104.7707, lat: 40.4149 },
    { name: "Gunnison",         lon: -106.9246, lat: 38.5490 },
    { name: "Lamar",            lon: -102.6152, lat: 38.0737 },
    { name: "Montrose",         lon: -107.8594, lat: 38.4688 },
    { name: "Pueblo",           lon: -104.6131, lat: 38.2706 },
    { name: "Trinidad",         lon: -104.4908, lat: 37.1749 },
  ];

  /* ══════════════════════════════════════════════════════════════════════════
   * UTILITIES
   * ══════════════════════════════════════════════════════════════════════════ */

  function findFirst(sels) {
    for (const s of sels) { const el = document.querySelector(s); if (el) return el; }
    return null;
  }

  function readLabel(el) {
    if (!el) return null;
    if (el.tagName === "SELECT" && el.selectedOptions.length)
      return el.selectedOptions[0].text.trim();
    return (el.innerText || el.textContent || "").trim().split(/\s+/).slice(0, 5).join(" ");
  }

  function slug(s) {
    return (s || "unknown")
      .replace(/[°+]/g, "")
      .replace(/[^a-zA-Z0-9._-]/g, "_")
      .replace(/_+/g, "_")
      .replace(/^_|_$/g, "");
  }

  function buildFilename() {
    const hazard   = slug(readLabel(findFirst(HAZARD_SEL)))   || "hazard";
    const scenario = slug(readLabel(findFirst(SCENARIO_SEL))) || "scenario";
    const date     = new Date().toISOString().slice(0, 10);
    return `Colorado_ClimateHazard_${hazard}_${scenario}_${date}.png`;
  }

  function getViewBox() {
    const svg = document.getElementById("choro-svg");
    if (!svg) return null;
    const vb = svg.viewBox.baseVal;
    return (vb && vb.width) ? { w: vb.width, h: vb.height } : null;
  }

  function projectedBBoxRect(proj) {
    const pts = [
      [BBOX.lonMin, BBOX.latMin], [BBOX.lonMin, BBOX.latMax],
      [BBOX.lonMax, BBOX.latMin], [BBOX.lonMax, BBOX.latMax],
    ].map(p => proj(p)).filter(Boolean);
    if (pts.length < 2) return null;
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    return { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
  }

  function isExcluded(el) {
    return EXCLUDE_SELECTORS.some(s => { try { return el.matches(s); } catch { return false; } });
  }

  /* ══════════════════════════════════════════════════════════════════════════
   * 1.  HILLSHADE
   * ══════════════════════════════════════════════════════════════════════════ */

  let hillshadeCanvasEl = null;  // displayed on screen (clipped to CO border)
  let hillshadeImgSrc   = null;  // raw <img> used for drawing onto canvas + PNG export

  function buildHillshadeUrl() {
    const aspect = (BBOX.lonMax - BBOX.lonMin) / (BBOX.latMax - BBOX.latMin);
    return HILLSHADE_REST + "?" + new URLSearchParams({
      bbox: `${BBOX.lonMin},${BBOX.latMin},${BBOX.lonMax},${BBOX.latMax}`,
      bboxSR: "4326", imageSR: "4326",
      size: `${Math.round(HILLSHADE_PX)},${Math.round(HILLSHADE_PX / aspect)}`,
      format: "png32", transparent: "true", f: "image",
    });
  }

  function drawHillshadeToCanvas(proj) {
    if (!hillshadeCanvasEl || !hillshadeImgSrc) return;
    if (!hillshadeImgSrc.complete || !hillshadeImgSrc.naturalWidth) return;
    const vb = getViewBox(); if (!vb) return;
    const r  = projectedBBoxRect(proj); if (!r) return;

    hillshadeCanvasEl.width  = Math.round(vb.w);
    hillshadeCanvasEl.height = Math.round(vb.h);
    const ctx = hillshadeCanvasEl.getContext("2d");
    ctx.clearRect(0, 0, hillshadeCanvasEl.width, hillshadeCanvasEl.height);

    ctx.save();
    if (coOutlineCache) {
      const path2d = new Path2D(d3.geoPath().projection(proj)(coOutlineCache));
      ctx.clip(path2d);
    }
    ctx.drawImage(hillshadeImgSrc, r.x, r.y, r.w, r.h);
    ctx.restore();
  }

  function initHillshade(proj, vb, container) {
    if (!hillshadeCanvasEl) {
      // Display canvas — clipped to Colorado border
      hillshadeCanvasEl = document.createElement("canvas");
      hillshadeCanvasEl.id = "hs-layer";
      Object.assign(hillshadeCanvasEl.style, {
        position: "absolute", top: "0", left: "0",
        width: "100%", height: "100%",
        pointerEvents: "none",
        opacity: HILLSHADE_OPACITY,
        mixBlendMode: "multiply",
      });
      container.appendChild(hillshadeCanvasEl);

      // Hidden img — loads the tile once; reused for canvas draw + PNG export
      hillshadeImgSrc = new Image();
      hillshadeImgSrc.crossOrigin = "anonymous";
      hillshadeImgSrc.src = buildHillshadeUrl();
      hillshadeImgSrc.addEventListener("load", () => {
        console.log("[addon] Hillshade loaded ✓");
        drawHillshadeToCanvas(proj);
      });
      hillshadeImgSrc.addEventListener("error", () => console.warn("[addon] Hillshade failed."));
    }

    // Resize canvas to current viewport and redraw if image already loaded
    hillshadeCanvasEl.width  = Math.round(vb.w);
    hillshadeCanvasEl.height = Math.round(vb.h);
    drawHillshadeToCanvas(proj);
  }

  /* ══════════════════════════════════════════════════════════════════════════
   * 2.  CITIES
   * ══════════════════════════════════════════════════════════════════════════ */

  let citySvgEl = null;

  function drawCities(proj, vb) {
    const NS = "http://www.w3.org/2000/svg";
    if (!citySvgEl) {
      citySvgEl = document.createElementNS(NS, "svg");
      citySvgEl.id = "cities-layer";
      Object.assign(citySvgEl.style, {
        position: "absolute", top: "0", left: "0",
        width: "100%", height: "100%", pointerEvents: "none", overflow: "visible",
      });
      document.getElementById(MAP_CONTAINER_ID).appendChild(citySvgEl);
    }
    citySvgEl.setAttribute("viewBox", `0 0 ${vb.w} ${vb.h}`);
    citySvgEl.innerHTML = `
      <defs>
        <filter id="city-shadow" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#000" flood-opacity="0.35"/>
        </filter>
      </defs>`;
    const g = document.createElementNS(NS, "g");
    CITIES.forEach(city => {
      const pt = proj([city.lon, city.lat]);
      if (!pt || isNaN(pt[0])) return;
      const [cx, cy] = pt, [dx, dy] = CITY_LABEL_OFFSET;
      const halo = document.createElementNS(NS, "circle");
      halo.setAttribute("cx", cx); halo.setAttribute("cy", cy);
      halo.setAttribute("r", CITY_DOT_RADIUS + 2.5); halo.setAttribute("fill", "rgba(255,255,255,0.72)");
      g.appendChild(halo);
      const dot = document.createElementNS(NS, "circle");
      dot.setAttribute("cx", cx); dot.setAttribute("cy", cy);
      dot.setAttribute("r", CITY_DOT_RADIUS); dot.setAttribute("fill", CITY_DOT_COLOR);
      dot.setAttribute("stroke", "#fff"); dot.setAttribute("stroke-width", "1.6");
      dot.setAttribute("filter", "url(#city-shadow)");
      g.appendChild(dot);
      const lbl = document.createElementNS(NS, "text");
      lbl.setAttribute("x", cx + dx); lbl.setAttribute("y", cy + dy);
      lbl.setAttribute("font-family", "system-ui,-apple-system,sans-serif");
      lbl.setAttribute("font-size", CITY_LABEL_SIZE); lbl.setAttribute("font-weight", "700");
      lbl.setAttribute("fill", "#111"); lbl.setAttribute("stroke", "rgba(255,255,255,0.93)");
      lbl.setAttribute("stroke-width", "3"); lbl.setAttribute("paint-order", "stroke");
      lbl.setAttribute("stroke-linejoin", "round"); lbl.textContent = city.name;
      g.appendChild(lbl);
    });
    citySvgEl.appendChild(g);
  }

  /* ══════════════════════════════════════════════════════════════════════════
   * 3.  RIVERS
   * ══════════════════════════════════════════════════════════════════════════ */

  let riverSvgEl   = null;
  let riverGeoJSON = null;
  let coOutlineCache = null;

  async function fetchColoradoOutline() {
    if (coOutlineCache) return coOutlineCache;
    try {
      const topo   = await fetch(CO_STATE_URL).then(r => r.json());
      const states = topojson.feature(topo, topo.objects.states);
      coOutlineCache = states.features.find(f => +f.id === CO_FIPS);
    } catch (e) { console.warn("[addon] CO outline fetch failed:", e); }
    return coOutlineCache;
  }

  async function fetchRivers() {
    if (riverGeoJSON) return riverGeoJSON;
    try {
      const data = await fetch(RIVERS_URL).then(r => r.json());
      data.features = data.features.filter(f => {
        const coords = f.geometry?.coordinates; if (!coords) return false;
        const pts = f.geometry.type === "MultiLineString" ? coords.flat() : coords;
        return pts.some(([lon, lat]) =>
          lon >= BBOX.lonMin && lon <= BBOX.lonMax && lat >= BBOX.latMin && lat <= BBOX.latMax
        );
      });
      riverGeoJSON = data;
      console.log(`[addon] Rivers loaded ✓  (${data.features.length} features)`);
    } catch (e) { console.warn("[addon] Rivers fetch failed:", e); }
    return riverGeoJSON;
  }

  async function drawRivers(proj, vb) {
    const container = document.getElementById(MAP_CONTAINER_ID);
    if (!container) return;
    if (!riverSvgEl) {
      riverSvgEl = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      riverSvgEl.id = "rivers-svg";
      Object.assign(riverSvgEl.style, {
        position: "absolute", top: "0", left: "0",
        width: "100%", height: "100%", pointerEvents: "none", overflow: "visible",
      });
      container.insertBefore(riverSvgEl, document.getElementById("cities-layer") || null);
    }
    riverSvgEl.setAttribute("viewBox", `0 0 ${vb.w} ${vb.h}`);
    riverSvgEl.innerHTML = "";

    const [geojson, coFeature] = await Promise.all([fetchRivers(), fetchColoradoOutline()]);
    if (!geojson) return;

    const pathGen = d3.geoPath().projection(proj);
    const clipId  = "co-rivers-clip";
    const defs    = document.createElementNS("http://www.w3.org/2000/svg", "defs");

    if (coFeature) {
      const coPath = pathGen(coFeature) || "";
      defs.innerHTML = `<clipPath id="${clipId}"><path d="${coPath}"/></clipPath>`;
    } else {
      defs.innerHTML = `<clipPath id="${clipId}"><rect width="${vb.w}" height="${vb.h}"/></clipPath>`;
    }
    riverSvgEl.appendChild(defs);

    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("clip-path", `url(#${clipId})`);

    geojson.features
      .filter(f => {
        const coords = f.geometry?.coordinates; if (!coords) return false;
        const pts = f.geometry.type === "MultiLineString" ? coords.flat() : coords;
        return pts.some(([lon, lat]) =>
          lon >= BBOX.lonMin - 1 && lon <= BBOX.lonMax + 1 &&
          lat >= BBOX.latMin - 1 && lat <= BBOX.latMax + 1
        );
      })
      .forEach(f => {
        const d = pathGen(f); if (!d) return;
        const name    = (f.properties?.name || "").toLowerCase();
        const isMajor = /colorado|arkansas|platte|rio grande|gunnison/.test(name);
        const path    = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", d); path.setAttribute("fill", "none");
        path.setAttribute("stroke", RIVER_COLOR);
        path.setAttribute("stroke-width",   isMajor ? RIVER_WIDTH * 1.8 : RIVER_WIDTH);
        path.setAttribute("stroke-opacity",  RIVER_OPACITY);
        path.setAttribute("stroke-linecap",  "round");
        path.setAttribute("stroke-linejoin", "round");
        g.appendChild(path);
      });

    riverSvgEl.appendChild(g);
  }

  /* ══════════════════════════════════════════════════════════════════════════
   * 4.  SECTOR HIGHLIGHT — red county outlines on the map
   * ══════════════════════════════════════════════════════════════════════════ */

  let highlightSvgEl  = null;
  let activeSectorKey = null;

  function initHighlightSvg(container) {
    if (highlightSvgEl) return;
    highlightSvgEl = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    highlightSvgEl.id = "sector-highlight-svg";
    Object.assign(highlightSvgEl.style, {
      position: "absolute", top: "0", left: "0",
      width: "100%", height: "100%", pointerEvents: "none", overflow: "visible",
    });
    container.insertBefore(highlightSvgEl, document.getElementById("cities-layer") || null);
  }

  function drawHighlights(proj, vb) {
    if (!highlightSvgEl) return;
    highlightSvgEl.setAttribute("viewBox", `0 0 ${vb.w} ${vb.h}`);
    highlightSvgEl.innerHTML = "";
    if (!activeSectorKey || !STATE.countyGeo) return;

    const topCounties = getTopCountiesForSector(activeSectorKey);
    const topFips     = new Set(topCounties.map(c => c.fips));
    const pathGen     = d3.geoPath().projection(proj);

    STATE.countyGeo.features.forEach(f => {
      const fips = f.id.toString().padStart(5, "0");
      if (!topFips.has(fips)) return;
      const d = pathGen(f); if (!d) return;
      const rank = topCounties.findIndex(c => c.fips === fips) + 1;

      const glow = document.createElementNS("http://www.w3.org/2000/svg", "path");
      glow.setAttribute("d", d); glow.setAttribute("fill", "rgba(220,20,60,0.10)");
      glow.setAttribute("stroke", "rgba(220,20,60,0.30)"); glow.setAttribute("stroke-width", "7");
      glow.setAttribute("stroke-linejoin", "round");
      highlightSvgEl.appendChild(glow);

      const outline = document.createElementNS("http://www.w3.org/2000/svg", "path");
      outline.setAttribute("d", d); outline.setAttribute("fill", "none");
      outline.setAttribute("stroke", "#dc143c"); outline.setAttribute("stroke-width", "2.2");
      outline.setAttribute("stroke-linejoin", "round");
      highlightSvgEl.appendChild(outline);

      const c = pathGen.centroid(f);
      if (c && !isNaN(c[0])) {
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", c[0]); circle.setAttribute("cy", c[1]);
        circle.setAttribute("r", "10"); circle.setAttribute("fill", "#dc143c");
        circle.setAttribute("stroke", "#fff"); circle.setAttribute("stroke-width", "1.5");
        highlightSvgEl.appendChild(circle);

        const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
        txt.setAttribute("x", c[0]); txt.setAttribute("y", c[1]);
        txt.setAttribute("text-anchor", "middle"); txt.setAttribute("dominant-baseline", "central");
        txt.setAttribute("fill", "#fff"); txt.setAttribute("font-size", "9");
        txt.setAttribute("font-family", "system-ui, sans-serif"); txt.setAttribute("font-weight", "700");
        txt.textContent = rank;
        highlightSvgEl.appendChild(txt);
      }
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
   * 5.  INDUSTRIES & LAYERS — left panel sections
   * ══════════════════════════════════════════════════════════════════════════ */

  let _addonBuilt = false;

  // ── Data helpers ──────────────────────────────────────────────────────────

  function getLoadedCounties() {
    const hid = Object.keys(STATE.hazardData || {})[0];
    return hid ? (STATE.hazardData[hid].counties || []) : [];
  }

  function computeTopSectors() {
    if (!STATE.sectors?.length) return [];
    const counties = getLoadedCounties();
    if (!counties.length) return [];
    const totals = {};
    STATE.sectors.forEach(s => { totals[s.key] = 0; });
    counties.forEach(county => {
      STATE.sectors.forEach(s => {
        const sd = county.sectors?.[s.key];
        if (sd?.exposed > 0) totals[s.key] += sd.exposed;
      });
    });
    return STATE.sectors
      .map(s => ({ ...s, stateTotal: totals[s.key] || 0 }))
      .filter(s => s.stateTotal > 0)
      .sort((a, b) => b.stateTotal - a.stateTotal)
      .slice(0, SECTOR_TOP_N);
  }

  function getTopCountiesForSector(sectorKey) {
    return getLoadedCounties()
      .map(c => ({ fips: c.fips, name: c.name, exposed: c.sectors?.[sectorKey]?.exposed || 0 }))
      .filter(c => c.exposed > 0)
      .sort((a, b) => b.exposed - a.exposed)
      .slice(0, COUNTY_HIGHLIGHT_N);
  }

  // ── Section builder helper ────────────────────────────────────────────────

  function makeSection(title, startOpen = true) {
    const sec = document.createElement("div");
    sec.className = "ls-section";

    const hdr = document.createElement("div");
    hdr.className = "ls-hdr" + (startOpen ? " open" : "");
    hdr.innerHTML = `${title} <span class="ls-chev">▾</span>`;
    hdr.addEventListener("click", () => {
      const body = hdr.nextElementSibling;
      const chev = hdr.querySelector(".ls-chev");
      const isClosed = body.classList.toggle("closed");
      hdr.classList.toggle("open", !isClosed);
      if (chev) chev.style.transform = isClosed ? "rotate(-90deg)" : "";
    });

    const body = document.createElement("div");
    body.className = "ls-body" + (startOpen ? "" : " closed");

    sec.appendChild(hdr);
    sec.appendChild(body);
    return sec;
  }

  // ── Industries section ────────────────────────────────────────────────────

  function buildIndustriesSection(container) {
    const topSectors = computeTopSectors();
    if (!topSectors.length) return false; // not ready

    const sec  = makeSection("🏭 Top Industries");
    const body = sec.querySelector(".ls-body");
    body.id    = "industries-sec-body";

    const sub = document.createElement("p");
    sub.style.cssText = "font-size:10px;color:var(--muted);margin-bottom:8px;line-height:1.5;";
    sub.textContent   = "Outdoor-exposed workers · click to highlight top counties";
    body.appendChild(sub);

    _renderSectorRows(body, topSectors);
    container.appendChild(sec);
    return true;
  }

  function _renderSectorRows(body, topSectors) {
    // Remove existing rows + clear btn before re-rendering
    body.querySelectorAll(".sector-pick-row, .sector-clear-btn").forEach(el => el.remove());

    const maxTotal = topSectors[0].stateTotal;

    topSectors.forEach(s => {
      const pct      = (s.stateTotal / maxTotal * 100).toFixed(0);
      const isActive = s.key === activeSectorKey;
      const expLabel = s.stateTotal >= 1000
        ? (s.stateTotal / 1000).toFixed(1) + "k"
        : Math.round(s.stateTotal).toString();

      const row = document.createElement("div");
      row.className           = "sector-pick-row" + (isActive ? " active" : "");
      row.dataset.sectorKey   = s.key;
      row.innerHTML = `
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="width:7px;height:7px;border-radius:50%;background:${s.color};
                       flex-shrink:0;display:inline-block;"></span>
          <span style="flex:1;font-size:11px;color:var(--text);white-space:nowrap;
                       overflow:hidden;text-overflow:ellipsis;" title="${s.label}">
            ${s.short || s.label}
          </span>
          <span style="font-size:10px;color:var(--muted);flex-shrink:0;">${expLabel}</span>
        </div>
        <div style="height:3px;border-radius:2px;background:var(--bg3);overflow:hidden;">
          <div style="width:${pct}%;height:100%;border-radius:2px;
                      background:${isActive ? "#dc143c" : s.color};"></div>
        </div>
        ${isActive
          ? `<div style="font-size:9px;color:#dc143c;">
               ▲ top ${COUNTY_HIGHLIGHT_N} counties outlined on map
             </div>`
          : ""}
      `;

      row.addEventListener("click", () => {
        activeSectorKey = (activeSectorKey === s.key) ? null : s.key;
        const proj = window.__coProjection, vb = getViewBox();
        if (proj && vb) drawHighlights(proj, vb);
        const sBody = document.getElementById("industries-sec-body");
        if (sBody) _renderSectorRows(sBody, topSectors);
      });

      body.appendChild(row);
    });

    // Clear button
    if (activeSectorKey) {
      const clearBtn = document.createElement("div");
      clearBtn.className  = "sector-clear-btn";
      clearBtn.style.cssText = `
        margin-top:6px;padding:5px 8px;text-align:center;
        font-size:10px;color:var(--muted);cursor:pointer;border-radius:var(--r);
        border:1px solid var(--border);transition:color 0.15s,background 0.15s;
      `;
      clearBtn.textContent = "✕  clear selection";
      clearBtn.addEventListener("mouseenter", () => { clearBtn.style.color="#1a2756"; clearBtn.style.background="rgba(26,39,86,0.05)"; });
      clearBtn.addEventListener("mouseleave", () => { clearBtn.style.color="var(--muted)"; clearBtn.style.background="transparent"; });
      clearBtn.addEventListener("click", () => {
        activeSectorKey = null;
        const proj = window.__coProjection, vb = getViewBox();
        if (proj && vb) drawHighlights(proj, vb);
        const sBody = document.getElementById("industries-sec-body");
        if (sBody) _renderSectorRows(sBody, topSectors);
      });
      body.appendChild(clearBtn);
    }
  }

  // ── Layers section ────────────────────────────────────────────────────────

  function buildLayersSection(container) {
    const sec  = makeSection("🗺 Map Layers", true);
    const body = sec.querySelector(".ls-body");

    const layers = [
      { emoji: "🏔", label: "Hillshade",  id: "hs-layer" },
      { emoji: "📍", label: "Cities",     id: "cities-layer" },
      { emoji: "🌊", label: "Rivers",     id: "rivers-svg" },
    ];

    layers.forEach(({ emoji, label, id }) => {
      const lbl = document.createElement("label");
      lbl.className = "layer-row";

      const cb = document.createElement("input");
      cb.type    = "checkbox";
      cb.checked = true;
      cb.addEventListener("change", () => {
        const target = document.getElementById(id);
        if (target) target.style.display = cb.checked ? "" : "none";
      });

      lbl.append(cb, document.createTextNode(` ${emoji} ${label}`));
      body.appendChild(lbl);
    });

    container.appendChild(sec);
  }

  // ── Master build (called once, retries until data ready) ──────────────────

  function buildAddonSections() {
    const container = document.getElementById("left-addon-sections");
    if (!container) { setTimeout(buildAddonSections, 300); return; }

    const topSectors = computeTopSectors();
    if (!topSectors.length) {
      // Hazard data not yet fetched — retry
      setTimeout(buildAddonSections, 600);
      return;
    }

    container.innerHTML = "";
    buildIndustriesSection(container);
    buildLayersSection(container);
    _addonBuilt = true;
  }

  /* ══════════════════════════════════════════════════════════════════════════
   * 6.  LEGEND SYNC — hide choropleth legend when overlay is active
   * ══════════════════════════════════════════════════════════════════════════ */

  function patchToggleOverlay() {
    const original = window.toggleOverlay;
    if (typeof original !== "function") { setTimeout(patchToggleOverlay, 200); return; }
    window.toggleOverlay = function (...args) {
      original.apply(this, args);
      const leg = document.getElementById("legend");
      if (leg) {
        leg.style.transition    = "opacity 0.25s";
        leg.style.opacity       = STATE.overlayOn ? "0" : "1";
        leg.style.pointerEvents = STATE.overlayOn ? "none" : "";
      }
    };
    console.log("[addon] toggleOverlay() patched for legend sync ✓");
  }

  /* ══════════════════════════════════════════════════════════════════════════
   * 7.  PNG EXPORT
   *
   * Clicking the button produces a ZIP containing two files:
   *   • <name>.png        — the map (legend excluded from this canvas)
   *   • <name>_legend.png — the active legend captured separately at 3× scale
   *
   * JSZip is loaded on demand from cdnjs so no extra <script> tag is needed.
   * ══════════════════════════════════════════════════════════════════════════ */

  async function captureMapCanvas(container) {
    if (hillshadeCanvasEl) hillshadeCanvasEl.style.visibility = "hidden";
    let baseCanvas;
    try {
      baseCanvas = await html2canvas(container, {
        useCORS: true, allowTaint: false, scale: 2, logging: false, ignoreElements: isExcluded,
      });
    } finally {
      if (hillshadeCanvasEl) hillshadeCanvasEl.style.visibility = "";
    }

    // ── Full canvas (same size as container) ─────────────────────────────
    const full = document.createElement("canvas");
    full.width = baseCanvas.width; full.height = baseCanvas.height;
    const fctx = full.getContext("2d");
    fctx.drawImage(baseCanvas, 0, 0);

    // Re-composite hillshade with Colorado clip, matching screen appearance
    const proj    = window.__coProjection, vb = getViewBox();
    const r       = (proj && vb) ? projectedBBoxRect(proj) : null;
    const hsReady = hillshadeImgSrc && hillshadeImgSrc.complete && hillshadeImgSrc.naturalWidth > 0;
    if (r && hsReady) {
      const scaleX = full.width / vb.w, scaleY = full.height / vb.h;
      fctx.save();
      fctx.globalAlpha              = HILLSHADE_OPACITY;
      fctx.globalCompositeOperation = "multiply";
      if (coOutlineCache) {
        fctx.setTransform(scaleX, 0, 0, scaleY, 0, 0);
        fctx.clip(new Path2D(d3.geoPath().projection(proj)(coOutlineCache)));
        fctx.setTransform(1, 0, 0, 1, 0, 0);
      }
      fctx.drawImage(hillshadeImgSrc, r.x * scaleX, r.y * scaleY, r.w * scaleX, r.h * scaleY);
      fctx.restore();
    }

    // ── Crop to Colorado projected bounding box + padding ────────────────
    // r is in SVG user-units; scale to output canvas pixels.
    if (r && vb) {
      const PAD_PX  = 24;          // padding around the state in output pixels
      const SCALE   = 2;           // html2canvas scale factor used above
      const scaleX  = full.width  / vb.w;
      const scaleY  = full.height / vb.h;

      const cropX = Math.max(0, Math.floor(r.x * scaleX) - PAD_PX);
      const cropY = Math.max(0, Math.floor(r.y * scaleY) - PAD_PX);
      const cropW = Math.min(full.width  - cropX, Math.ceil(r.w * scaleX) + PAD_PX * 2);
      const cropH = Math.min(full.height - cropY, Math.ceil(r.h * scaleY) + PAD_PX * 2);

      const cropped = document.createElement("canvas");
      cropped.width  = cropW;
      cropped.height = cropH;
      const cctx = cropped.getContext("2d");
      cctx.drawImage(full, cropX, cropY, cropW, cropH, 0, 0, cropW, cropH);
      return cropped;
    }

    return full;
  }

  async function captureLegendCanvas() {
    // Capture only the colour-bar element — no background, no labels, transparent PNG
    const barId = STATE.overlayOn ? "tiff-legend-bar" : "legend-bar";
    const bar   = document.getElementById(barId);
    if (!bar) return null;

    // Force the parent legend visible temporarily so html2canvas can reach the bar
    const parentId = STATE.overlayOn ? "tiff-legend" : "legend";
    const parent   = document.getElementById(parentId);
    const prevParentOpacity = parent ? parent.style.opacity  : "";
    const prevParentDisplay = parent ? parent.style.display  : "";
    if (parent) { parent.style.opacity = "1"; parent.style.display = "block"; }

    let canvas;
    try {
      canvas = await html2canvas(bar, {
        useCORS:         true,
        scale:           4,          // crisp gradient at high resolution
        logging:         false,
        backgroundColor: null,       // transparent — no box, no background
      });
    } finally {
      if (parent) {
        parent.style.opacity = prevParentOpacity;
        parent.style.display = prevParentDisplay;
      }
    }
    return canvas;
  }

  function buildLegendText() {
    const h       = STATE.activeHazard || {};
    const gwl     = STATE.activeGwl    || "";
    const title   = document.getElementById(STATE.overlayOn ? "tiff-legend-title" : "legend-title")?.textContent?.trim() || "";
    const minVal  = document.getElementById(STATE.overlayOn ? "tleg-min"          : "leg-min")?.textContent?.trim()      || "—";
    const maxVal  = document.getElementById(STATE.overlayOn ? "tleg-max"          : "leg-max")?.textContent?.trim()      || "—";
    const date    = new Date().toISOString().slice(0, 10);

    return [
      `Colorado Climate Hazard × Jobs — Legend Metadata`,
      `Exported:    ${date}`,
      ``,
      `Layer:       ${title}`,
      `Hazard:      ${h.label || ""}`,
      `Unit:        ${h.unit  || ""}`,
      `Scenario:    ${gwl}`,
      `Description: ${h.description || ""}`,
      ``,
      `Colour ramp`,
      `  Min: ${minVal}`,
      `  Max: ${maxVal}`,
      ``,
      `Bounding box (WGS-84)`,
      `  lonMin: ${BBOX.lonMin}   latMin: ${BBOX.latMin}`,
      `  lonMax: ${BBOX.lonMax}   latMax: ${BBOX.latMax}`,
    ].join("\n");
  }

  function buildLegendFilename() {
    const minX  = BBOX.lonMin;
    const maxY  = BBOX.latMax;
    const label = slug(STATE.activeHazard?.label  || "legend");
    const n     = slug(STATE.activeGwl            || "");
    return `LEGEND_${label}_${n}_${minX}_${maxY}.png`;
  }

  // Convert a canvas to a Uint8Array PNG blob synchronously via toBlob
  function canvasToBlob(canvas) {
    return new Promise(resolve => canvas.toBlob(resolve, "image/png"));
  }

  function addPngButton() {
    if (document.getElementById("png-dl-btn")) return;
    const style = document.createElement("style");
    style.textContent = `
      #png-dl-btn {
        position:fixed;bottom:24px;right:24px;z-index:9000;
        display:flex;align-items:center;gap:8px;padding:10px 18px;
        background:#1a2756;
        color:#fff;border:none;border-radius:4px;font-size:13px;font-weight:600;
        font-family:'Source Sans 3',sans-serif;cursor:pointer;letter-spacing:.02em;
        box-shadow:0 2px 10px rgba(26,39,86,0.35);transition:opacity .15s,transform .15s;
        border-bottom:3px solid #b8860b;
      }
      #png-dl-btn:hover{opacity:.9;transform:translateY(-1px);}
      #png-dl-btn:active{transform:translateY(0);}
      #png-dl-btn:disabled{opacity:.5;cursor:wait;transform:none;}
    `;
    document.head.appendChild(style);
    const btn = document.createElement("button");
    btn.id        = "png-dl-btn";
    btn.innerHTML = `<span>🗜</span><span class="btn-txt"> Download Map + Legend</span>`;
    btn.addEventListener("click", async () => {
      const container = document.getElementById(MAP_CONTAINER_ID);
      if (!container) { alert("Map container not found."); return; }
      btn.disabled = true; btn.querySelector(".btn-txt").textContent = " Generating…";
      try {
        // Load JSZip on demand
        if (typeof JSZip === "undefined") {
          await loadScript("https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js");
        }

        const baseName = buildFilename().replace(".png", "");

        // Capture both canvases in parallel
        const [mapCanvas, legendCanvas] = await Promise.all([
          captureMapCanvas(container),
          captureLegendCanvas(),
        ]);

        // Convert to blobs
        const mapBlob    = await canvasToBlob(mapCanvas);
        const legendBlob = legendCanvas ? await canvasToBlob(legendCanvas) : null;

        // Pack into ZIP
        const zip = new JSZip();
        zip.file(`${baseName}.png`,        mapBlob);
        if (legendBlob) zip.file(buildLegendFilename(), legendBlob);
        zip.file(buildLegendFilename().replace(".png", ".txt"), buildLegendText());

        const zipBlob = await zip.generateAsync({ type: "blob", compression: "DEFLATE" });
        const a = document.createElement("a");
        a.href     = URL.createObjectURL(zipBlob);
        a.download = `${baseName}.zip`;
        a.click();
        setTimeout(() => URL.revokeObjectURL(a.href), 10000);

        console.log("[addon] ZIP saved:", a.download);
      } catch (err) {
        console.error("[addon] Export failed:", err);
        alert("Export failed — see console.\n\n" + err.message);
      } finally {
        btn.disabled = false; btn.querySelector(".btn-txt").textContent = " Download Map + Legend";
      }
    });
    document.body.appendChild(btn);
  }

  /* ══════════════════════════════════════════════════════════════════════════
   * 8.  MASTER UPDATE
   * ══════════════════════════════════════════════════════════════════════════ */

  async function update() {
    const proj = window.__coProjection;
    if (typeof proj !== "function") {
      console.warn("[addon] window.__coProjection not set yet — skipping update.");
      return;
    }
    const vb = getViewBox(); if (!vb) return;
    const container = document.getElementById(MAP_CONTAINER_ID); if (!container) return;

    if (getComputedStyle(container).position === "static")
      container.style.position = "relative";

    initHillshade(proj, vb, container);
    initHighlightSvg(container);
    await drawRivers(proj, vb);
    drawHighlights(proj, vb);
    drawCities(proj, vb);

    // Build left-panel sections only once
    if (!_addonBuilt) buildAddonSections();
  }

  window.__addonUpdate = update;

  /* ══════════════════════════════════════════════════════════════════════════
   * 9.  BOOTSTRAP
   * ══════════════════════════════════════════════════════════════════════════ */

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
      const s = document.createElement("script");
      s.src = src; s.onload = resolve; s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  function waitForMap(intervalMs = 250, timeoutMs = 30000) {
    return new Promise((resolve, reject) => {
      const deadline = Date.now() + timeoutMs;
      const t = setInterval(() => {
        if (getViewBox() && typeof window.__coProjection === "function") {
          clearInterval(t); resolve();
        } else if (Date.now() > deadline) {
          clearInterval(t);
          reject(new Error("[addon] Timed out waiting for map. Make sure window.__coProjection = STATE.projection is set in initMap()."));
        }
      }, intervalMs);
    });
  }

  async function bootstrap() {
    if (typeof html2canvas === "undefined") {
      await loadScript("https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js");
    }

    addPngButton();
    patchToggleOverlay();

    try { await waitForMap(); } catch (e) { console.error(e.message); return; }

    update();

    const container = document.getElementById(MAP_CONTAINER_ID);
    if (container && typeof ResizeObserver !== "undefined") {
      let debounce;
      new ResizeObserver(() => {
        clearTimeout(debounce);
        debounce = setTimeout(update, 80);
      }).observe(container);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }

})();