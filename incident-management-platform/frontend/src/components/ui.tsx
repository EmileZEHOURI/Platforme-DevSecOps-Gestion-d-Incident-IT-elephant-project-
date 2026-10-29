import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Button({
  className = "",
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
}) {
  return (
    <button className={`button button-${variant} ${className}`} {...props} />
  );
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning";
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
export function PageHeader({
  eyebrow = "ESPACE OPÉRATIONNEL",
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="muted">{description}</p>
      </div>
      {action}
    </header>
  );
}
export function StatePanel({
  title,
  description,
  error = false,
  children,
}: {
  title: string;
  description: string;
  error?: boolean;
  children?: ReactNode;
}) {
  return (
    <div
      className={`state-panel ${error ? "state-error" : ""}`}
      role={error ? "alert" : "status"}
    >
      <span className="state-symbol" aria-hidden="true">
        {error ? "!" : "◎"}
      </span>
      <h2>{title}</h2>
      <p className="muted">{description}</p>
      {children}
    </div>
  );
}
export function LoadingState() {
  return (
    <div className="loading-state" role="status">
      <span className="spinner" />
      Vérification de votre session…
    </div>
  );
}
export function Brand() {
  return (
    <span className="brand">
      <span className="brand-mark" aria-hidden="true">
        i<span>m</span>
      </span>
      <span>
        Incident<span className="brand-sub">MANAGEMENT PLATFORM</span>
      </span>
    </span>
  );
}
