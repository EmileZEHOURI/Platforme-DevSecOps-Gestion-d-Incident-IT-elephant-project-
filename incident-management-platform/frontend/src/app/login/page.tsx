"use client";
import { useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { Brand, Button } from "@/components/ui";
import { getMe, login } from "@/services/auth.service";
import { ApiError } from "@/lib/api";
const subscribe = () => () => {};
export default function LoginPage() {
  const ready = useSyncExternalStore(subscribe, () => true, () => false);
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [show, setShow] = useState(false);
  function destination() { const next = new URLSearchParams(window.location.search).get("next"); return next && /^\/dashboard(?:\/[a-zA-Z0-9_-]+)*$/.test(next) ? next : "/dashboard"; }
  useEffect(() => { let active = true; void getMe().then(user => { if (active && user.is_active) router.replace(destination()); }).catch(() => {}); return () => { active = false; }; }, [router]);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const data = new FormData(event.currentTarget); setBusy(true); setError("");
    let authenticated = false;
    try {
      await login(String(data.get("email")).trim(), String(data.get("password")));
      authenticated = true;
      const user = await getMe();
      if (!user.is_active) throw new Error("Ce compte ne peut pas accéder à la plateforme.");
      router.replace(destination());
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401
        ? authenticated
          ? "Identifiants acceptés, mais la session n’a pas pu être conservée. Autorisez les cookies pour ce site et réessayez."
          : "Adresse électronique ou mot de passe incorrect."
        : err instanceof Error ? err.message : "Connexion impossible.");
      setBusy(false);
    }
  }
  return <main className="login-layout"><section className="login-story"><Brand /><div className="story-content"><p className="eyebrow">OPÉRATIONS IT · DEVSECOPS</p><h1>Gardez le contrôle.<br /><span>Ensemble.</span></h1><p>Un point de repère pour vos incidents,<br /> vos équipes et la continuité de vos services.</p><div className="signal-graphic" aria-hidden="true"><span>01 — DÉTECTER</span><span>02 — COORDONNER</span><span>03 — RÉSOUDRE</span></div></div><p className="story-footer">Incident Management Platform · ESPACE INTERNE</p></section><section className="login-form-panel"><div className="login-form-wrap"><p className="eyebrow">VOTRE ESPACE DE TRAVAIL</p><h2>Bon retour.</h2><p className="muted">Connectez-vous pour accéder à votre plateforme.</p><form method="post" onSubmit={submit} className="login-form" aria-busy={busy}><div className="field"><label htmlFor="email">Adresse électronique</label><input id="email" name="email" type="email" autoComplete="username" placeholder="prenom.nom@entreprise.fr" required disabled={busy} /></div><div className="field"><label htmlFor="password">Mot de passe</label><div className="password-field"><input id="password" name="password" type={show ? "text" : "password"} autoComplete="current-password" placeholder="Votre mot de passe" required disabled={busy} /><button type="button" onClick={() => setShow(!show)} aria-pressed={show} aria-label={show ? "Masquer le mot de passe" : "Afficher le mot de passe"}>{show ? "Masquer" : "Afficher"}</button></div></div>{error && <p className="form-error" role="alert">{error}</p>}<Button disabled={busy || !ready} type="submit" className="login-submit">{!ready ? "Chargement…" : busy ? "Connexion en cours…" : "Se connecter"}<span aria-hidden="true">→</span></Button></form><noscript><p className="form-error">JavaScript doit être activé pour vous connecter.</p></noscript><div className="login-help"><strong>Besoin d’un accès ?</strong><p>Contactez votre administrateur pour obtenir un compte ou réinitialiser votre mot de passe.</p></div><p className="login-security">Accès réservé aux membres autorisés.</p></div></section></main>;
}

