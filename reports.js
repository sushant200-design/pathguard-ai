const searchInput = document.getElementById("reportSearch");
const statusFilter = document.getElementById("statusFilter");
const sortFilter = document.getElementById("sortFilter");
const grid = document.getElementById("reportGrid");
function updateReports() {
  if (!grid) return;
  const q = (searchInput?.value || "").toLowerCase();
  const status = statusFilter?.value || "";
  const cards = [...grid.querySelectorAll(".searchable-report")];
  cards.forEach(card => {
    card.hidden = !(card.dataset.search.includes(q) && (!status || card.dataset.status === status));
  });
  const visible = cards.filter(c => !c.hidden);
  visible.sort((a,b) => sortFilter?.value === "risk"
    ? Number(b.dataset.risk)-Number(a.dataset.risk)
    : b.dataset.date.localeCompare(a.dataset.date));
  visible.forEach(card => grid.appendChild(card));
  const empty = document.getElementById("noReports");
  if (empty) empty.hidden = visible.length !== 0;
}
[searchInput,statusFilter,sortFilter].forEach(el => el?.addEventListener("input", updateReports));
