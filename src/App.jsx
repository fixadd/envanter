import React from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet, Link } from "react-router-dom";

/**
 * Baylan Envanter — Layout 1 + Akış Ağacı (Tam İskelet)
 * -----------------------------------------------------
 * Bu dosya, seçtiğin "Klasik: Sol Menü + Üst Bar" tasarımını
 * verdiğin ağaç yapısıyla birebir eşleyen bir **yönlendirme (routing)**
 * ve **sayfa iskeleti** içerir.
 *
 * Kullanım:
 *  - React + Tailwind kurulu projeye ekleyin.
 *  - `react-router-dom` kurun:  npm i react-router-dom
 *  - <App /> bileşenini root'ta render edin.
 *
 * Notlar:
 *  - Login sonrasında ProtectedLayout altında tüm modüller çalışır.
 *  - Sol menüdeki linkler ağaçtaki path'lerle eşleşir.
 *  - Her sayfa şu an placeholder; gerçek tablo/formları kolayca doldurabilirsiniz.
 */

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Giriş (Anonim) */}
        <Route path="/login" element={<LoginPage />} />

        {/* Giriş Başarılı → Ana Kabuk (Protected) */}
        <Route element={<ProtectedLayout />}> 
          <Route index element={<Dashboard />} /> {/* Ana Sayfa ( / ) */}

          {/* ENVANTER */}
          <Route path="inventory">
            <Route index element={<InventoryList />} /> {/* Liste/Filtrele */}
            <Route path=":id" element={<InventoryDetail />} /> {/* Detay */}
            <Route path=":id/maintenance" element={<InventoryMaintenance />} /> {/* Bakım/Onarım */}
            <Route path=":id/status" element={<InventoryStatus />} /> {/* Durum Değişikliği */}
            <Route path=":id/edit" element={<InventoryEdit />} /> {/* Düzenle */}
            <Route path=":id/history" element={<InventoryHistory />} /> {/* Hareket Geçmişi */}
          </Route>

          <Route path="licenses">
            <Route index element={<LicenseList />} /> {/* Liste/Filtrele */}
            <Route path=":id/assign" element={<LicenseAssign />} /> {/* Atama/İptal */}
          </Route>

          <Route path="accessories" element={<Accessories />} />
          <Route path="printers" element={<Printers />} />

          {/* İŞLEMLER */}
          <Route path="requests">
            <Route index element={<Requests />} />
            <Route path="new" element={<RequestCreate />} /> {/* Talep Oluştur */}
            <Route path=":id/to-inventory" element={<RequestToInventory />} /> {/* Talebi Envantere Dönüştür */}
          </Route>

          <Route path="stock">
            <Route index element={<Stock />} />
            <Route path="in" element={<StockIn />} /> {/* Giriş Fişi */}
            <Route path="out" element={<StockOut />} /> {/* Çıkış Fişi */}
            <Route path="count" element={<StockCount />} /> {/* Sayım & Fark */}
          </Route>

          <Route path="trash" element={<Trash />} /> {/* Yumuşak silinenler */}

          {/* AYARLAR */}
          <Route path="profile" element={<Profile />} />
          <Route path="admin">
            <Route index element={<AdminHome />} />
            <Route path="users" element={<AdminUsers />} />
            <Route path="catalog" element={<AdminCatalogs />} /> {/* departman, lokasyon, tip, statü */}
            <Route path="integrations" element={<AdminIntegrations />} /> {/* LDAP/AD, e‑posta, SSO */}
            <Route path="system" element={<AdminSystem />} /> {/* yedekleme, log seviyesi */}
          </Route>

          <Route path="integrations" element={<Integrations />} />
          <Route path="logs" element={<Logs />} /> {/* [Yönetici] */}
          <Route path="inventory/add" element={<InventoryAdd />} /> {/* [Yetkili] */}

          {/* Çıkış */}
          <Route path="logout" element={<Logout />} />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

/* ------------------- Kimlik Doğrulama ------------------- */
function LoginPage() {
  return (
    <AuthShell title="Giriş Yap">
      <form className="space-y-3">
        <input className="w-full rounded-xl border px-3 py-2" placeholder="Kullanıcı adı" />
        <input className="w-full rounded-xl border px-3 py-2" placeholder="Şifre" type="password" />
        <button className="w-full rounded-xl border px-3 py-2 bg-slate-900 text-white">Giriş</button>
      </form>
      <div className="mt-3 text-center text-sm text-slate-500">
        <Link to="/">Demo: Doğrudan Ana Sayfaya Dön</Link>
      </div>
    </AuthShell>
  );
}

function AuthShell({ title, children }) {
  return (
    <div className="min-h-screen grid place-items-center bg-slate-100">
      <div className="w-full max-w-md rounded-2xl border bg-white p-6 shadow-sm">
        <div className="mb-4 text-center">
          <div className="mx-auto mb-2 h-12 w-12 rounded-2xl bg-sky-600 text-white grid place-items-center font-bold">B</div>
          <div className="text-lg font-semibold">{title}</div>
        </div>
        {children}
      </div>
    </div>
  );
}

/* ------------------- Korunan Kabuk (Layout) ------------------- */
function ProtectedLayout() {
  // TODO: gerçek auth kontrolünü burada yapın. Not logged-in ise /login'e atın.
  const isAuthenticated = true; // demo
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <ClassicShell />;
}

function ClassicShell() {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <div className="mx-auto max-w-6xl px-4 py-6">
        <div className="grid grid-cols-12 gap-6">
          {/* Sidebar */}
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

          {/* Content */}
          <main className="col-span-9 lg:col-span-10 space-y-6">
            {/* Üst Bar */}
            <div className="rounded-2xl border bg-white p-4 shadow-sm flex flex-wrap items-center justify-between gap-3">
              <div className="font-semibold">Baylan Envanter</div>
              <div className="flex items-center gap-2">
                <input className="w-64 rounded-xl border px-3 py-1.5 text-sm" placeholder="Ara: cihaz, kullanıcı, seri no" />
                <button className="rounded-xl border px-3 py-1.5 text-sm bg-slate-900 text-white">Ara</button>
              </div>
            </div>

            {/* Sayfa İçeriği */}
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

/* ------------------- Ana Sayfa ------------------- */
function Dashboard() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard title="Toplam Cihaz" value="1.284" hint="Aktif: 1.102 / Arızalı: 44" />
        <KPICard title="Lisans (aktif)" value="362" hint="30 gün içinde bitecek: 12" />
        <KPICard title="Aksesuar Stok" value="3.412" hint="Eşik altı: 5" />
        <KPICard title="Açık Talep" value="19" hint="Ortalama SLA: 2.1 gün" />
      </div>
      <TableSkeleton />
    </div>
  );
}

function KPICard({ title, value, hint }) {
  return (
    <div className="rounded-2xl border bg-white p-4 shadow-sm">
      <div className="text-sm text-slate-500">{title}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {hint && <div className="mt-2 text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="rounded-2xl border bg-white overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b font-medium">Son İşlemler</div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              {["Tarih", "Kullanıcı", "İşlem", "Nesne", "Durum"].map((h) => (
                <th key={h} className="px-4 py-2 text-left whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 6 }).map((_, i) => (
              <tr key={i} className="border-t hover:bg-slate-50">
                <td className="px-4 py-2">2025-08-20 10:{20 + i}</td>
                <td className="px-4 py-2">kadir.can</td>
                <td className="px-4 py-2">Atama</td>
                <td className="px-4 py-2">Cihaz #{1200 + i}</td>
                <td className="px-4 py-2">
                  <span className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs bg-emerald-50 border-emerald-200 text-emerald-600">Başarılı</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ------------------- ENVANTER ------------------- */
function InventoryList(){
  return (
    <Card title="Envanter — Liste/Filtrele">
      <div className="mb-3 flex flex-wrap gap-2">
        <input className="rounded-xl border px-3 py-1.5 text-sm" placeholder="Ara" />
        <select className="rounded-xl border px-3 py-1.5 text-sm"><option>Lokasyon</option></select>
        <select className="rounded-xl border px-3 py-1.5 text-sm"><option>Durum</option></select>
      </div>
      <PlaceholderTable rows={8} />
    </Card>
  );
}
function InventoryDetail(){ return <Card title="Envanter — Detay Görüntüle"><Placeholder /></Card>; }
function InventoryMaintenance(){ return <Card title="Envanter — Bakım/Onarım Kaydı"><Placeholder /></Card>; }
function InventoryStatus(){ return <Card title="Envanter — Durum Değişikliği (aktif/hurda)"><Placeholder /></Card>; }
function InventoryEdit(){ return <Card title="Envanter — Düzenle"><PlaceholderForm /></Card>; }
function InventoryHistory(){ return <Card title="Envanter — Hareket Geçmişi (audit)"><PlaceholderTimeline /></Card>; }

/* ------------------- LİSANS ------------------- */
function LicenseList(){ return <Card title="Lisans — Liste/Filtrele"><PlaceholderTable rows={6} /></Card>; }
function LicenseAssign(){ return <Card title="Lisans — Atama / İptal"><PlaceholderForm /></Card>; }

/* ------------------- AKSESUAR & YAZICI ------------------- */
function Accessories(){ return <Card title="Aksesuar Takip"><PlaceholderTable rows={6} /></Card>; }
function Printers(){ return <Card title="Yazıcı Takip"><PlaceholderTable rows={6} /></Card>; }

/* ------------------- İŞLEMLER ------------------- */
function Requests(){ return <Card title="Talep Takip"><PlaceholderKanban /></Card>; }
function RequestCreate(){ return <Card title="Talep Oluştur"><PlaceholderForm /></Card>; }
function RequestToInventory(){ return <Card title="Talebi Envantere Dönüştür"><Placeholder /></Card>; }

function Stock(){ return <Card title="Stok Takip"><PlaceholderTable rows={6} /></Card>; }
function StockIn(){ return <Card title="Stok — Giriş Fişi"><PlaceholderForm /></Card>; }
function StockOut(){ return <Card title="Stok — Çıkış Fişi"><PlaceholderForm /></Card>; }
function StockCount(){ return <Card title="Stok — Sayım & Fark İşleme"><Placeholder /></Card>; }

function Trash(){ return <Card title="Çöp Kutusu (Soft Delete)"><PlaceholderTable rows={5} /></Card>; }

/* ------------------- AYARLAR ------------------- */
function Profile(){ return <Card title="Profil"><PlaceholderForm /></Card>; }
function AdminHome(){ return <Card title="Admin Paneli"><Placeholder /></Card>; }
function AdminUsers(){ return <Card title="Admin • Kullanıcı & Rol Yönetimi"><PlaceholderTable rows={5} /></Card>; }
function AdminCatalogs(){ return <Card title="Admin • Tanımlar (departman, lokasyon, tip, statü)"><PlaceholderTable rows={5} /></Card>; }
function AdminIntegrations(){ return <Card title="Admin • Entegrasyonlar (LDAP/AD, e‑posta, SSO)"><PlaceholderForm /></Card>; }
function AdminSystem(){ return <Card title="Admin • Sistem Ayarları (yedekleme, log seviyesi)"><PlaceholderForm /></Card>; }

function Integrations(){ return <Card title="Bağlantılar"><Placeholder /></Card>; }
function Logs(){ return <Card title="Kayıtlar (Audit/Log)"><PlaceholderTable rows={10} /></Card>; }
function InventoryAdd(){ return <Card title="Envanter Ekleme"><PlaceholderForm /></Card>; }

/* ------------------- ÇIKIŞ ------------------- */
function Logout(){ return <Card title="Çıkış"><div className="text-sm text-slate-500">Oturum kapatma işlemi…</div></Card>; }

/* ------------------- Basit UI Yardımcıları ------------------- */
function Card({ title, children }){
  return (
    <div className="rounded-2xl border bg-white p-4 shadow-sm">
      {title && <div className="mb-3 font-medium">{title}</div>}
      {children}
    </div>
  );
}

function Placeholder(){
  return <div className="text-sm text-slate-500">Bu bölüm için tablo/form bileşenlerini ekleyin.</div>;
}
function PlaceholderForm(){
  return (
    <form className="grid gap-3 max-w-2xl">
      <input className="rounded-xl border px-3 py-1.5 text-sm" placeholder="Metin alanı" />
      <div className="grid grid-cols-2 gap-3">
        <select className="rounded-xl border px-3 py-1.5 text-sm"><option>Seçim 1</option></select>
        <select className="rounded-xl border px-3 py-1.5 text-sm"><option>Seçim 2</option></select>
      </div>
      <textarea className="rounded-xl border px-3 py-1.5 text-sm" rows={3} placeholder="Açıklama" />
      <div className="flex gap-2">
        <button className="rounded-xl border px-3 py-1.5 text-sm bg-slate-900 text-white">Kaydet</button>
        <button className="rounded-xl border px-3 py-1.5 text-sm">Vazgeç</button>
      </div>
    </form>
  );
}
function PlaceholderTable({ rows=6 }){
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-slate-600">
          <tr>
            {Array.from({ length: 6 }).map((_,i)=> (
              <th key={i} className="px-4 py-2 text-left whitespace-nowrap">Başlık {i+1}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, r) => (
            <tr key={r} className="border-t hover:bg-slate-50">
              {Array.from({ length: 6 }).map((_,c)=> (
                <td key={c} className="px-4 py-2">—</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function PlaceholderKanban(){
  const cols = ["Açık", "Onay Bekliyor", "Atandı", "Tamamlandı"];
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cols.map((c)=> (
        <div key={c} className="rounded-2xl border bg-white p-3 shadow-sm">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-sm font-medium">{c}</div>
            <span className="text-xs rounded-full border px-2 py-0.5">4</span>
          </div>
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_,i)=> (
              <div key={i} className="rounded-xl border p-3 hover:bg-slate-50">
                <div className="text-sm font-medium">TLP-{120+i} • Laptop Talebi</div>
                <div className="mt-1 text-xs text-slate-500">İsteyen: ahmet.y — Öncelik: Orta</div>
              </div>
            ))}
            <button className="w-full rounded-xl border px-3 py-2 text-sm">+ Kart Ekle</button>
          </div>
        </div>
      ))}
    </div>
  );
}
function PlaceholderTimeline(){
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_,i)=> (
        <div key={i} className="relative pl-6">
          <div className="absolute left-0 top-1 h-3 w-3 rounded-full bg-sky-500"></div>
          <div className="text-sm font-medium">Olay Başlığı {i+1}</div>
          <div className="text-xs text-slate-500">2025-08-20 10:{10+i}</div>
        </div>
      ))}
    </div>
  );
}
