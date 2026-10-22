const search=document.getElementById("adminSearch"), status=document.getElementById("adminStatus");
function filterAdmin() {
  const q=(search?.value||"").toLowerCase(), s=status?.value||"";
  document.querySelectorAll("#adminTable tbody tr").forEach(row=>{
    row.hidden=!(row.dataset.search.includes(q)&&(!s||row.dataset.status===s));
  });
}
search?.addEventListener("input",filterAdmin); status?.addEventListener("change",filterAdmin);
