"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Badge, Brand, Button, LoadingState, StatePanel } from "@/components/ui";
import { logout } from "@/services/auth.service";
import { ApiError } from "@/lib/api";

const navigation = [ { href: "/dashboard", title: "Vue d’ensemble", icon: "▦" }, { href: "/dashboard/incidents", title: "Incidents", icon: "◈" }, { href: "/dashboard/services", title: "État des services", icon: "◉" }, { href: "/dashboard/account", title: "Mon compte", icon: "◷" } ];
export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, error, refresh } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  useEffect(() => { if (!loading && !user && !error) router.replace(`/login?next=${encodeURIComponent(pathname)}`); }, [loading, user, error, router, pathname]);
  useEffect(() => { void refresh(); }, [pathname, refresh]);
  async function signOut() {
    setLeaving(true); setLogoutError("");
    try { await logout(); window.location.assign("/login"); }
    catch (err) { if (err instanceof ApiError && err.status === 401) { window.location.assign("/login"); return; } setLogoutError(err instanceof Error ? err.message : "Déconnexion impossible."); setLeaving(false); }
  }
  if (loading) return <LoadingState />;
  if (error) return <main className="session-error"><StatePanel title="Connexion interrompue" description={error} error><Button onClick={() => void refresh()}>Réessayer</Button></StatePanel></main>;
  if (!user) return <LoadingState />;
  return <div className="app-shell"><a href="#main-content" className="skip-link">Aller au contenu</a><aside className={`sidebar ${open ? "is-open" : ""}`}><Link href="/dashboard" aria-label="Incident — accueil"><Brand /></Link><div className="workspace-label"><span className="workspace-icon">IT</span><div>Espace de travail<small>Opérations & sécurité</small></div></div><p className="nav-label">PILOTAGE</p><nav aria-label="Navigation principale" id="main-navigation">{navigation.map(item => <Link key={item.href} href={item.href} onClick={() => setOpen(false)} className={pathname === item.href ? "nav-item active" : "nav-item"} aria-current={pathname === item.href ? "page" : undefined}><span aria-hidden="true">{item.icon}</span>{item.title}</Link>)}</nav><div className="sidebar-footer"><span className="avatar">{user.full_name.slice(0, 2).toUpperCase()}</span><div className="user-summary"><strong>{user.full_name}</strong><small>{user.role}</small></div></div></aside><div className="app-body"><header className="topbar"><Button variant="ghost" className="menu-toggle" aria-expanded={open} aria-controls="main-navigation" onClick={() => setOpen(!open)}>{open ? "Fermer" : "Menu"}</Button><span className="breadcrumb">Espace de travail <span>/</span> <strong>{navigation.find(n => n.href === pathname)?.title ?? "Dashboard"}</strong></span><div className="topbar-actions"><Badge tone="success">Session active</Badge><Button variant="ghost" disabled={leaving} onClick={() => void signOut()}>{leaving ? "Déconnexion…" : "Se déconnecter"}</Button></div></header><main id="main-content" className="main-content" tabIndex={-1}>{logoutError && <p role="alert" className="form-error">{logoutError}</p>}{children}</main><footer className="app-footer">Incident Management Platform<span>Un espace commun pour vos opérations.</span></footer></div></div>;
}
