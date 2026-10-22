const mapEl = document.getElementById("reportMap");
if (mapEl && window.L) {
  const defaultCenter = [19.9975, 73.7898]; // Nashik default view; user can choose any location.
  const map = L.map("reportMap").setView(defaultCenter, 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(map);
  let marker = null;
  const latInput = document.getElementById("latitude");
  const lonInput = document.getElementById("longitude");
  const label = document.getElementById("coordsLabel");
  function setPoint(lat, lon) {
    latInput.value = lat.toFixed(6);
    lonInput.value = lon.toFixed(6);
    label.textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
    if (marker) marker.setLatLng([lat, lon]);
    else marker = L.marker([lat, lon], {draggable: true}).addTo(map);
    marker.on("dragend", () => { const p = marker.getLatLng(); setPoint(p.lat, p.lng); });
  }
  map.on("click", e => setPoint(e.latlng.lat, e.latlng.lng));
  document.getElementById("useMyLocation")?.addEventListener("click", () => {
    if (!navigator.geolocation) return alert("Geolocation is not supported by this browser.");
    navigator.geolocation.getCurrentPosition(pos => {
      const {latitude, longitude} = pos.coords;
      map.setView([latitude, longitude], 16);
      setPoint(latitude, longitude);
    }, () => alert("Could not access your location. Click the map to choose a location."));
  });
  const fileInput = document.getElementById("reportImage");
  fileInput?.addEventListener("change", () => {
    const file = fileInput.files[0], preview = document.getElementById("imagePreview");
    preview.innerHTML = "";
    if (file) {
      const img = document.createElement("img");
      img.alt = "Selected image preview"; img.src = URL.createObjectURL(file);
      preview.appendChild(img);
    }
  });
}
