import { Link } from "react-router-dom";
import AuthShell from "../components/AuthShell";
export default function Login() {
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
