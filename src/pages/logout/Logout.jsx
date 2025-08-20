import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Page from "../../components/Page";

export default function Logout() {
  const navigate = useNavigate();

  useEffect(() => {
    localStorage.removeItem("token");
    navigate("/login", { replace: true });
  }, [navigate]);

  return <Page title="Çıkış" />;
}
