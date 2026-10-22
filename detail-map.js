const el=document.getElementById("detailMap");
if(el && window.L) {
  const lat=Number(el.dataset.lat), lon=Number(el.dataset.lon);
  const map=L.map("detailMap",{scrollWheelZoom:false}).setView([lat,lon],15);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
  L.marker([lat,lon]).addTo(map);
}
