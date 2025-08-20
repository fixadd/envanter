import { Navigate, Outlet } from "react-router-dom";
import NavBlock from "./NavBlock";

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
              <NavBlock title="" items={[{ label: "Ana Sayfa", to: "/", icon: "Home" }]} />
              <NavBlock title="ENVANTER" items={[
                { label: "Envanter Takip", to: "/inventory", icon: "Box" },
                { label: "Lisans Takip", to: "/licenses", icon: "Key" },
                { label: "Aksesuar Takip", to: "/accessories", icon: "Package" },
                { label: "Yazıcı Takip", to: "/printers", icon: "Printer" },
              ]} />
              <NavBlock title="İŞLEMLER" items={[
                { label: "Talep Takip", to: "/requests", icon: "FileText" },
                { label: "Stok Takip", to: "/stock", icon: "Layers" },
                { label: "Çöp Kutusu", to: "/trash", icon: "Trash2" },
              ]} />
              <NavBlock title="AYARLAR" items={[
                { label: "Profil", to: "/profile", icon: "User" },
                { label: "Admin Paneli", to: "/admin", icon: "Settings" },
                { label: "Bağlantılar", to: "/integrations", icon: "Link" },
                { label: "Kayıtlar", to: "/logs", icon: "ClipboardList" },
                { label: "Envanter Ekleme", to: "/inventory/add", icon: "PlusCircle" },
              ]} />
              <NavBlock title="" items={[{ label: "Çıkış", to: "/logout", icon: "LogOut" }]} />
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

