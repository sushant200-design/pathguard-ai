const map = L.map("hazardMap").setView([19.9975, 73.7898], 12);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);
let allReports = [], markers = [], userMarker = null, userCircle = null, userLocation = null;
const list = document.getElementById("nearbyList");
const count = document.getElementById("mapResultCount");
const radiusSelect = document.getElementById("radiusSelect");
const search = document.getElementById("mapSearch");
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function colorFor(score) { return score >= 70 ? "#e15a58" : score >= 50 ? "#e7a63d" : "#27a77b"; }
function haversine(lat1,lon1,lat2,lon2) {
  const rad = x => x*Math.PI/180, dLat=rad(lat2-lat1), dLon=rad(lon2-lon1);
  const a=Math.sin(dLat/2)**2+Math.cos(rad(lat1))*Math.cos(rad(lat2))*Math.sin(dLon/2)**2;
  return 6371*2*Math.asin(Math.sqrt(Math.min(1,a)));
}
function visibleReports() {
  const radius = Number(radiusSelect.value);
  return allReports.map(r => ({...r, distance_km: userLocation ? haversine(userLocation[0],userLocation[1],r.latitude,r.longitude) : null}))
    .filter(r => (!userLocation || r.distance_km <= radius) &&
      (`${r.category} ${r.location_name} ${r.description}`.toLowerCase().includes((search.value||"").toLowerCase())))
    .sort((a,b) => b.risk_score-a.risk_score || (a.distance_km??0)-(b.distance_km??0));
}
function render() {
  markers.forEach(m => map.removeLayer(m)); markers=[];
  const rows=visibleReports();
  rows.forEach(r => {
    const marker=L.circleMarker([r.latitude,r.longitude],{radius:8,color:colorFor(r.risk_score),fillColor:colorFor(r.risk_score),fillOpacity:.85,weight:2}).addTo(map);
    marker.bindPopup(`<b>PG-${String(r.id).padStart(4,"0")} · ${esc(r.category)}</b><br>${esc(r.location_name||"Road location")}<br>Risk score: ${r.risk_score}<br>Status: ${esc(r.status)}<br><a href="/report/${r.id}">View report</a>`);
    markers.push(marker);
  });
  count.textContent = `${rows.length} report${rows.length===1?"":"s"}${userLocation ? ` within ${radiusSelect.value} km` : " · all locations"}`;
  if (!rows.length) list.innerHTML = `<div class="empty-map"><span>⌖</span><b>No matching reports</b><small>${userLocation?"Try a wider radius or change your location.":"No reports have been submitted yet."}</small></div>`;
  else list.innerHTML=rows.map(r=>`<a class="nearby-item" href="/report/${r.id}"><span class="nearby-marker" style="--pin:${colorFor(r.risk_score)}">!</span><span class="nearby-item-body"><b>${esc(r.category)} · PG-${String(r.id).padStart(4,"0")}</b><small>${esc(r.location_name||r.description.slice(0,55))}</small><span class="nearby-item-meta"><span class="status status-${esc(r.status.toLowerCase().replaceAll(" ","-"))}">${esc(r.status)}</span>${r.distance_km!==null?`<span>${r.distance_km.toFixed(1)} km away</span>`:""}<span>Risk ${r.risk_score}</span></span></span></a>`).join("");
}
async function loadReports() {
  try { const response=await fetch("/api/reports"); if(!response.ok) throw new Error(); allReports=await response.json(); render(); }
  catch { list.innerHTML="<div class='empty-map'>Could not load reports. Refresh to try again.</div>"; }
}
function setUserLocation(lat,lon) {
  userLocation=[lat,lon]; map.setView(userLocation,13);
  if(userMarker) map.removeLayer(userMarker);
  if(userCircle) map.removeLayer(userCircle);
  userMarker=L.marker(userLocation).addTo(map).bindPopup("Your selected location");
  userCircle=L.circle(userLocation,{radius:Number(radiusSelect.value)*1000,color:"#4e8df5",fillOpacity:.05,weight:1}).addTo(map);
  render();
}
document.getElementById("mapLocate")?.addEventListener("click",()=>{
  if(!navigator.geolocation) return alert("Geolocation is not supported. Map markers can still be explored.");
  navigator.geolocation.getCurrentPosition(p=>setUserLocation(p.coords.latitude,p.coords.longitude),
    ()=>alert("Location permission was denied. Showing all reports; you can still explore the map."));
});
radiusSelect.addEventListener("change",()=>{if(userLocation){if(userCircle) userCircle.setRadius(Number(radiusSelect.value)*1000);}render();});
search.addEventListener("input",render);
loadReports();
