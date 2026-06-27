import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { Icon } from "./ui";

function Tab({ to, children, end }: { to: string; children: ReactNode; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
          isActive ? "bg-primary text-white" : "text-slate-600 hover:bg-slate-100"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh flex flex-col">
      <header className="sticky top-0 z-20 bg-surface/90 backdrop-blur border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-4">
          <NavLink to="/" className="flex items-center gap-2 font-bold text-primary">
            <span className="text-accent">{Icon.pulse()}</span>
            MedArchive
          </NavLink>
          <nav className="flex items-center gap-1 ml-2">
            <Tab to="/" end>Поиск</Tab>
            <span className="mx-1 text-slate-300">|</span>
            <Tab to="/admin">Дашборд</Tab>
            <Tab to="/admin/queue">Очередь</Tab>
            <Tab to="/admin/upload">Загрузка</Tab>
          </nav>
          <div className="ml-auto text-xs text-muted-fg hidden sm:block">
            Каталог медицинских услуг · RU/KK
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">{children}</main>
      <footer className="border-t border-slate-200 text-center text-xs text-muted-fg py-4">
        MedArchive — нормализация архива прайс-листов клиник
      </footer>
    </div>
  );
}
