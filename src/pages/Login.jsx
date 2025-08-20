import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import AuthShell from "../components/AuthShell";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (username && password) {
      localStorage.setItem("isAuth", "true");
      navigate("/");
    }
  }

  return (
    <AuthShell title="Giriş Yap">
      <form className="space-y-3" onSubmit={handleSubmit}>
        <input
          className="w-full rounded-xl border px-3 py-2"
          placeholder="Kullanıcı adı"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          className="w-full rounded-xl border px-3 py-2"
          placeholder="Şifre"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button className="w-full rounded-xl border px-3 py-2 bg-slate-900 text-white">Giriş</button>
      </form>
      <div className="mt-3 text-center text-sm text-slate-500">
        <Link to="/">Demo: Doğrudan Ana Sayfaya Dön</Link>
      </div>
    </AuthShell>
  );
}
