import { useNavigate } from "react-router-dom";
import { useState } from "react";
import AuthShell from "../components/AuthShell";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (username === "admin" && password === "admin") {
      localStorage.setItem("isAuth", "true");
      navigate("/");
    } else {
      setError("Kullanıcı adı veya şifre hatalı");
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
        {error && <div className="text-sm text-red-500">{error}</div>}
        <button className="w-full rounded-xl border px-3 py-2 bg-slate-900 text-white">Giriş</button>
      </form>
    </AuthShell>
  );
}
