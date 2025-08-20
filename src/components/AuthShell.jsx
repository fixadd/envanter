export default function AuthShell({ title, children }) {
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
