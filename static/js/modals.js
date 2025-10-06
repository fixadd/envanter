// basit sekme davranışı: .tab-lite içindeki .btn'lere data-target="#id"
document.addEventListener('click', (e)=>{
  const btn = e.target.closest('.tab-lite .btn[data-target]');
  if(!btn) return;
  const wrap = btn.closest('.tabbed');
  if(!wrap) return;
  wrap.querySelectorAll('.tab-lite .btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  const target = btn.dataset.target;
  wrap.querySelectorAll('.tab-pane').forEach(p=>p.classList.add('d-none'));
  wrap.querySelector(target)?.classList.remove('d-none');
});
