"use client";

import { useEffect, useId, useRef, type ReactNode, type FormEventHandler } from "react";
import { IncidentPriorityBadge, IncidentStatusBadge } from "@/components/incident-badges";
import type { IncidentResponse } from "@/types/incident";

export function IncidentEditDialog({ incident, title, pending, close, submit, children }: {
  incident: IncidentResponse; title: string; pending: boolean; close: () => void;
  submit: FormEventHandler<HTMLFormElement>; children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  return <dialog ref={dialog} className="assignment-dialog panel" aria-labelledby={titleId}
    onCancel={event => { event.preventDefault(); if (!pending) close(); }}>
    <div className="panel-heading"><div><p className="eyebrow">{incident.reference}</p><h2 id={titleId}>{title}</h2></div></div>
    <form className="incident-form incident-form-body" onSubmit={submit} aria-busy={pending}>
      <p><strong>{incident.title}</strong></p>
      <p className="my-3 flex gap-2"><IncidentStatusBadge status={incident.status} /><IncidentPriorityBadge priority={incident.priority} /></p>
      {children}
    </form>
  </dialog>;
}
