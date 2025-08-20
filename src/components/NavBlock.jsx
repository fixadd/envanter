import { Link, useLocation } from "react-router-dom";
import * as Icons from "lucide-react";

function NavBlock({ title, items }) {
  const { pathname } = useLocation();

  return (
    <div className="rounded-2xl border bg-white p-3 shadow-sm">
      {title && (
        <div className="mb-2 text-xs font-semibold tracking-wide text-slate-500">
          {title}
        </div>
      )}
      <ul className="space-y-1">
        {items.map((it) => {
          const active =
            it.to === "/" ? pathname === "/" : pathname.startsWith(it.to);

          const Icon = Icons[it.icon] || Icons.Circle;

          return (
            <li key={it.to}>
              <Link
                to={it.to}
                className={
                  "flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-slate-50 " +
                  (active ? "bg-slate-100 border border-slate-200" : "")
                }
              >
                <Icon size={16} className="text-slate-600" />
                <span>{it.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default NavBlock;
