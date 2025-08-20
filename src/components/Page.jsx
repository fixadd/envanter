export default function Page({ title, children }) {
  return (
    <div className="rounded-2xl border bg-white p-4 shadow-sm">
      {title && <div className="mb-3 font-medium">{title}</div>}
      {children || <div className="text-sm text-slate-500">Bu bölüm için içerik eklenecek.</div>}
    </div>
  );
}
