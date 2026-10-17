/**
 * Barabanki Connect — Leaflet OpenStreetMap Integration
 * Renders interactive maps for tourist spots, businesses, and event venues.
 */

window.initBarabankiMap = function (containerId, locations = [], center = [26.9288, 81.1895], zoom = 11) {
  const container = document.getElementById(containerId);
  if (!container || typeof L === "undefined") return;

  // Initialize map instance
  const map = L.map(containerId).setView(center, zoom);

  // Add OpenStreetMap raster tiles
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);

  // Custom SVG icon for Barabanki Connect markers
  const defaultIcon = L.divIcon({
    className: "bbk-custom-pin",
    html: `
      <div style="background-color:#1E3A8A; color:#FFFFFF; width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 6px rgba(0,0,0,0.3); border:2px solid #FFFFFF;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
      </div>
    `,
    iconSize: [30, 30],
    iconAnchor: [15, 30],
    popupAnchor: [0, -30],
  });

  const bounds = [];

  locations.forEach((item) => {
    if (item.latitude && item.longitude) {
      const marker = L.marker([item.latitude, item.longitude], { icon: defaultIcon }).addTo(map);

      let popupContent = `
        <div style="font-family: sans-serif; min-width: 200px; padding: 4px;">
          <h4 style="margin: 0 0 4px; font-size: 1rem; color: #1E3A8A;">${item.name || item.title}</h4>
          ${item.category ? `<span style="display:inline-block; font-size:0.75rem; background:#FEF3C7; color:#D97706; padding:2px 6px; border-radius:4px; font-weight:bold; margin-bottom:6px;">${item.category}</span>` : ""}
          <p style="margin: 0 0 8px; font-size: 0.85rem; color: #4B5563;">${item.address || ""}</p>
          ${item.url ? `<a href="${item.url}" style="display:inline-block; font-size:0.85rem; color:#1E3A8A; font-weight:bold; text-decoration:none;">View Details &rarr;</a>` : ""}
        </div>
      `;

      marker.bindPopup(popupContent);
      bounds.push([item.latitude, item.longitude]);
    }
  });

  // If multiple locations, fit bounds cleanly
  if (bounds.length > 1) {
    map.fitBounds(bounds, { padding: [50, 50] });
  } else if (bounds.length === 1) {
    map.setView(bounds[0], 14);
  }

  return map;
};
