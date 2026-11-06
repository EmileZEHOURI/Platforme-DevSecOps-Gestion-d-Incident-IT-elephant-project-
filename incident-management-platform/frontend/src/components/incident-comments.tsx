"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Badge, Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { createComment } from "@/services/comment.service";
import type { CommentResponse } from "@/types/comment";
import type { IncidentResponse } from "@/types/incident";

const dates = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });

export function IncidentComments({ incident }: { incident: IncidentResponse }) {
  const { user } = useAuth();
  const [content, setContent] = useState("");
  const [comments, setComments] = useState<CommentResponse[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [code, setCode] = useState<number>();
  const [fieldError, setFieldError] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const locked = useRef(false);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const feedback = useRef<HTMLDivElement>(null);
  const active = useRef(true);
  const closed = incident.status === "CLOSED" || code === 409;
  const unavailable = code === 404 || code === 401 || code === 403;
  const count = Array.from(content.trim()).length;

  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  useEffect(() => { if (error) feedback.current?.focus(); }, [error]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked.current || closed || unavailable) return;
    setError(""); setFieldError(""); setConfirmation(""); setCode(undefined);
    if (count === 0 || count > 5000) {
      setFieldError("Saisissez un commentaire de 1 à 5 000 caractères, hors espaces en début et fin.");
      textarea.current?.focus();
      return;
    }
    locked.current = true; setPending(true);
    try {
      const comment = await createComment(incident.id, { content });
      if (!active.current) return;
      setComments(previous => [...previous, comment]);
      setContent("");
      setConfirmation("Commentaire ajouté avec succès.");
    } catch (cause) {
      if (!active.current) return;
      const status = cause instanceof ApiError ? cause.status : undefined;
      setCode(status);
      if (status === 404) setError("Incident introuvable ou inaccessible. Le commentaire n’a pas été ajouté.");
      else if (status === 409) setError("Cet incident est fermé et ne peut plus recevoir de commentaire.");
      else if (status === 401) setError("Votre session a expiré. Reconnectez-vous pour ajouter un commentaire.");
      else if (status === 403) setError("Vous n’êtes pas autorisé à commenter cet incident.");
      else if (status === 422) {
        setFieldError("Le contenu a été refusé. Il doit contenir de 1 à 5 000 caractères après suppression des espaces périphériques.");
        setError("Vérifiez votre commentaire avant de le renvoyer.");
      } else if (status) setError("Le commentaire n’a pas pu être confirmé. Votre saisie est conservée ; réessayez dans un instant.");
      else setError("La réponse du service n’a pas été reçue. Le commentaire a peut-être été enregistré : vérifiez auprès de votre équipe avant de réessayer pour éviter un doublon.");
    } finally { locked.current = false; if (active.current) setPending(false); }
  }

  return <section className="panel" aria-labelledby="comments-heading">
    <div className="panel-heading"><h2 id="comments-heading">Commentaires</h2>{closed && <Badge>Incident fermé</Badge>}</div>
    <div className="incident-comments-body">
      <p className="muted comment-scope">Les commentaires ajoutés pendant cette consultation sont affichés ici. L’historique des commentaires n’est pas encore disponible.</p>
      <div role="status" className="comment-confirmation">{confirmation}</div>
      {comments.length > 0 && <ol className="comment-list" aria-label="Commentaires ajoutés pendant cette consultation">
        {comments.map(comment => <li key={comment.id}>
          <article>
            <header className="comment-meta"><strong>{user && comment.author_id === user.id ? `${user.full_name} (vous)` : `Utilisateur n° ${comment.author_id}`}</strong><time dateTime={comment.created_at}>{dates.format(new Date(comment.created_at))}</time></header>
            <p className="comment-content">{comment.content}</p>
          </article>
        </li>)}
      </ol>}
      {closed && <p className="comment-closed" id="comment-closed">Cet incident est fermé. L’ajout de commentaires est désactivé.</p>}
      {error && <div className="form-error" role="alert" tabIndex={-1} ref={feedback}>
        {error}
        {code === 401 && <p><Link className="incident-text-link" href={`/login?next=${encodeURIComponent(`/dashboard/incidents/${incident.id}`)}`}>Se reconnecter</Link></p>}
        {code === 404 && <p><Link className="incident-text-link" href="/dashboard/incidents">Retour à mes incidents</Link></p>}
      </div>}
      <form className="incident-form comment-form" method="post" noValidate onSubmit={submit} aria-busy={pending}>
        <div className="field">
          <label htmlFor="comment-content">Ajouter un commentaire</label>
          <textarea id="comment-content" name="content" ref={textarea} rows={5} value={content} onChange={event => setContent(event.target.value)} required disabled={pending || closed || unavailable} aria-invalid={!!fieldError} aria-describedby={`comment-hint comment-error${closed ? " comment-closed" : ""}`} placeholder="Apportez une précision ou partagez une évolution de la situation…" />
          <div className="incident-field-meta" id="comment-hint"><span>Évitez les mots de passe et les informations sensibles.</span><span>{count} / 5 000</span></div>
          <p className="incident-field-error" id="comment-error">{fieldError}</p>
        </div>
        <div className="incident-actions"><Button type="submit" disabled={pending || closed || unavailable}>{pending ? "Envoi en cours…" : "Ajouter le commentaire"}</Button><span className="muted" role="status">{pending ? "Enregistrement du commentaire…" : ""}</span></div>
      </form>
    </div>
  </section>;
}
