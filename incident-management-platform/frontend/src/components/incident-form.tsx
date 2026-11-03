"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Badge, Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { createIncident } from "@/services/incident.service";
import {
  incidentCategories, incidentPriorities,
  type IncidentCategory, type IncidentPriority, type IncidentResponse,
} from "@/types/incident";

type Field = "title" | "description" | "category" | "priority";
type Errors = Partial<Record<Field, string>>;
const length = (text: string) => Array.from(text.trim()).length;

function validationErrors(detail: unknown): Errors {
  const errors: Errors = {};
  if (!Array.isArray(detail)) return errors;
  for (const issue of detail) {
    if (!issue || !Array.isArray(issue.loc)) continue;
    const field = issue.loc[issue.loc.length - 1];
    if (field === "title") errors.title = "Le titre doit contenir entre 5 et 150 caractères.";
    if (field === "description") errors.description = "La description doit contenir entre 10 et 5 000 caractères.";
    if (field === "category") errors.category = "Sélectionnez une catégorie valide.";
    if (field === "priority") errors.priority = "Sélectionnez une priorité valide.";
  }
  return errors;
}

export function IncidentForm() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<IncidentCategory | "">("");
  const [priority, setPriority] = useState<IncidentPriority>("MEDIUM");
  const [errors, setErrors] = useState<Errors>({});
  const [message, setMessage] = useState("");
  const [expired, setExpired] = useState(false);
  const [pending, setPending] = useState(false);
  const [created, setCreated] = useState<IncidentResponse | null>(null);
  const locked = useRef(false);
  const feedback = useRef<HTMLDivElement>(null);
  const success = useRef<HTMLHeadingElement>(null);

  useEffect(() => { if (created) success.current?.focus(); }, [created]);
  useEffect(() => { if (message) feedback.current?.focus(); }, [message]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked.current) return;
    const next: Errors = {};
    if (length(title) < 5 || length(title) > 150) next.title = "Saisissez un titre de 5 à 150 caractères, hors espaces en début et fin.";
    if (length(description) < 10 || length(description) > 5000) next.description = "Décrivez l’incident en 10 à 5 000 caractères, hors espaces en début et fin.";
    if (!category || !(category in incidentCategories)) next.category = "Sélectionnez une catégorie.";
    if (!(priority in incidentPriorities)) next.priority = "Sélectionnez une priorité valide.";
    setErrors(next);
    setMessage("");
    setExpired(false);
    const first = Object.keys(next)[0];
    if (first) { document.getElementById(`incident-${first}`)?.focus(); return; }
    if (!category) return;
    locked.current = true;
    setPending(true);
    try {
      const result = await createIncident({ title, description, category, priority });
      setCreated(result);
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        setErrors(validationErrors(error.detail));
        setMessage("Certaines informations ont été refusées. Vérifiez les champs puis réessayez.");
      } else if (error instanceof ApiError && error.status === 401) {
        setExpired(true);
        setMessage("Votre session a expiré. Reconnectez-vous avant de créer cet incident.");
      } else if (error instanceof ApiError && error.status === 403) {
        setMessage("Votre compte n’est pas autorisé à créer un incident. Contactez votre administrateur.");
      } else {
        setMessage(error instanceof ApiError
          ? "La création n’a pas pu être confirmée. Vos informations sont conservées. Réessayez dans un instant."
          : "La réponse du service n’a pas été reçue. L’incident a peut-être été créé : vérifiez auprès de votre équipe avant de réessayer pour éviter un doublon.");
      }
    } finally { locked.current = false; setPending(false); }
  }

  if (created) return (
    <section className="panel incident-success">
      <Badge tone="success">Création confirmée</Badge>
      <h2 ref={success} tabIndex={-1}>L’incident {created.reference} a été créé.</h2>
      <p className="muted">Votre signalement est enregistré et prêt à être pris en charge.</p>
      <dl className="incident-receipt">
        <div><dt>Titre</dt><dd>{created.title}</dd></div>
        <div><dt>Statut</dt><dd><Badge>{created.status === "OPEN" ? "Ouvert" : created.status}</Badge></dd></div>
        <div><dt>Catégorie</dt><dd>{incidentCategories[created.category]}</dd></div>
        <div><dt>Priorité</dt><dd>{incidentPriorities[created.priority]}</dd></div>
        <div><dt>Créé le</dt><dd>{new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(created.created_at))}</dd></div>
      </dl>
      <div className="incident-actions">
        <Link className="button button-primary" href="/dashboard/incidents">Retour à l’espace incidents</Link>
        <Button variant="secondary" onClick={() => {
          setTitle(""); setDescription(""); setCategory(""); setPriority("MEDIUM");
          setCreated(null); setErrors({}); setMessage("");
        }}>Créer un autre incident</Button>
      </div>
    </section>
  );

  return (
    <div className="incident-create-grid">
      <form className="panel incident-form" method="post" noValidate onSubmit={submit} aria-busy={pending}>
        <div className="panel-heading"><h2>Décrire le problème</h2><span className="muted">Tous les champs sont obligatoires</span></div>
        <div className="incident-form-body">
          {message && <div className="form-error" role="alert" tabIndex={-1} ref={feedback}>
            {message}
            {expired && <p><Link href="/login?next=%2Fdashboard%2Fincidents%2Fnew" className="incident-text-link">Se reconnecter</Link></p>}
          </div>}
          <fieldset disabled={pending}>
            <div className="field">
              <label htmlFor="incident-title">Titre</label>
              <input id="incident-title" name="title" value={title} onChange={e => setTitle(e.target.value)} required aria-invalid={!!errors.title} aria-describedby="title-hint title-error" placeholder="Ex. Impossible d’accéder à la messagerie" />
              <div className="incident-field-meta" id="title-hint"><span>Résumez le problème en une phrase.</span><span>{length(title)} / 150</span></div>
              <p id="title-error" className="incident-field-error">{errors.title}</p>
            </div>
            <div className="field">
              <label htmlFor="incident-description">Description</label>
              <textarea id="incident-description" name="description" rows={7} value={description} onChange={e => setDescription(e.target.value)} required aria-invalid={!!errors.description} aria-describedby="description-hint description-error" placeholder="Que se passe-t-il ? Depuis quand ? Quels utilisateurs ou services sont concernés ?" />
              <div className="incident-field-meta" id="description-hint"><span>Précisez le contexte et les étapes pour reproduire le problème.</span><span>{length(description)} / 5 000</span></div>
              <p id="description-error" className="incident-field-error">{errors.description}</p>
            </div>
            <div className="incident-select-grid">
              <div className="field">
                <label htmlFor="incident-category">Catégorie</label>
                <select id="incident-category" name="category" value={category} onChange={e => setCategory(e.target.value as IncidentCategory)} required aria-invalid={!!errors.category} aria-describedby="category-error">
                  <option value="" disabled>Choisir une catégorie</option>
                  {Object.entries(incidentCategories).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                <p id="category-error" className="incident-field-error">{errors.category}</p>
              </div>
              <div className="field">
                <label htmlFor="incident-priority">Priorité</label>
                <select id="incident-priority" name="priority" value={priority} onChange={e => setPriority(e.target.value as IncidentPriority)} required aria-invalid={!!errors.priority} aria-describedby="priority-error">
                  {Object.entries(incidentPriorities).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                <p id="priority-error" className="incident-field-error">{errors.priority}</p>
              </div>
            </div>
          </fieldset>
          <div className="incident-actions">
            <Button type="submit" disabled={pending}>{pending ? "Création en cours…" : "Créer l’incident"}</Button>
            {!pending && <Link className="button button-secondary" href="/dashboard/incidents">Annuler</Link>}
            <span role="status" className="muted">{pending ? "Enregistrement de votre signalement…" : ""}</span>
          </div>
        </div>
      </form>
      <aside className="incident-guidance" aria-label="Conseils de signalement">
        <p className="eyebrow">UN SIGNALEMENT UTILE</p><h2>Aidez votre équipe à intervenir.</h2>
        <p>Décrivez les symptômes observés et leur impact. Ne partagez pas de mot de passe ni de clé d’accès.</p>
        <h3>Quelle priorité choisir ?</h3>
        <dl><dt>Faible</dt><dd>Gêne limitée, une solution de contournement existe.</dd><dt>Moyenne</dt><dd>Activité perturbée, sans blocage majeur.</dd><dt>Élevée</dt><dd>Activité fortement dégradée ou équipe bloquée.</dd><dt>Critique</dt><dd>Service essentiel indisponible ou incident de sécurité majeur.</dd></dl>
      </aside>
    </div>
  );
}
