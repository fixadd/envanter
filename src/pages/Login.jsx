import { useNavigate } from "react-router-dom";
import { useState } from "react";
import AuthShell from "../components/AuthShell";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    try {
      const response = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();
      if (!response.ok) {
        setError(data.message || "Kullanıcı adı veya şifre hatalı");
        return;
      }

      // Token'ı güvenli bir şekilde sakla
      localStorage.setItem("token", data.token);
      navigate("/");
    } catch (err) {
      setError("Sunucuya bağlanılamadı");
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
