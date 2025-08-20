import { Navigate, Outlet, Link } from "react-router-dom";

export default function ProtectedLayout() {
  const isAuthenticated = true; // demo
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <ClassicShell />;
}

function ClassicShell() {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <div className="mx-auto max-w-6xl px-4 py-6">
        <div className="grid grid-cols-12 gap-6">
          <aside className="col-span-3 lg:col-span-2">
            <div className="sticky top-20 space-y-2">
              <NavBlock title="ENVANTER" items={[
                { label: "Envanter Takip", to: "/inventory" },
                { label: "Lisans Takip", to: "/licenses" },
                { label: "Aksesuar Takip", to: "/accessories" },
                { label: "Yazıcı Takip", to: "/printers" },
              ]} />
              <NavBlock title="İŞLEMLER" items={[
                { label: "Talep Takip", to: "/requests" },
                { label: "Stok Takip", to: "/stock" },
                { label: "Çöp Kutusu", to: "/trash" },
              ]} />
              <NavBlock title="AYARLAR" items={[
                { label: "Profil", to: "/profile" },
                { label: "Admin Paneli", to: "/admin" },
                { label: "Bağlantılar", to: "/integrations" },
                { label: "Kayıtlar", to: "/logs" },
                { label: "Envanter Ekleme", to: "/inventory/add" },
              ]} />
              <NavBlock title="" items={[{ label: "Çıkış", to: "/logout" }]} />
            </div>
          </aside>
          <main className="col-span-9 lg:col-span-10 space-y-6">
            <div className="rounded-2xl border bg-white p-4 shadow-sm flex flex-wrap items-center justify-between gap-3">
              <div className="font-semibold">Baylan Envanter</div>
              <div className="flex items-center gap-2">
                <input className="w-64 rounded-xl border px-3 py-1.5 text-sm" placeholder="Ara: cihaz, kullanıcı, seri no" />
                <button className="rounded-xl border px-3 py-1.5 text-sm bg-slate-900 text-white">Ara</button>
              </div>
            </div>
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

function NavBlock({ title, items }) {
  return (
    <div className="rounded-2xl border bg-white p-3 shadow-sm">
      {title && <div className="mb-2 text-xs font-semibold tracking-wide text-slate-500">{title}</div>}
      <ul className="space-y-1">
        {items.map((it) => (
          <li key={it.to}>
            <Link className="block rounded-xl px-3 py-2 text-sm hover:bg-slate-50" to={it.to}>{it.label}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
