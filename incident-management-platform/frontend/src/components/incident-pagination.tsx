"use client";

import { useId } from "react";
import { Button } from "@/components/ui";
import type { PaginatedIncidentsResponse } from "@/types/incident";

type PaginationData = Omit<PaginatedIncidentsResponse, "items"> & {
  items: readonly unknown[];
};

export function IncidentPagination({
  data,
  pageSize,
  onPageChange,
  onPageSizeChange,
  noun = "incidents",
  sizeLabel = "Incidents par page",
}: {
  noun?: string;
  sizeLabel?: string;
  data?: PaginationData;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}) {
  const id = useId();
  const hasPages = !!data && data.total_pages > 0;
  const first =
    data && data.items.length ? (data.page - 1) * data.page_size + 1 : 0;
  const last =
    data && data.items.length
      ? Math.min(data.total, first + data.items.length - 1)
      : 0;
  return (
    <nav
      aria-label={`Pagination des ${noun}`}
      className="incident-pagination incident-form"
    >
      <div className="field">
        <label htmlFor={id}>{sizeLabel}</label>
        <select
          id={id}
          value={pageSize}
          onChange={(event) => onPageSizeChange(Number(event.target.value))}
        >
          {[10, 20, 50, 100].map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
      </div>
      <div className="incident-pagination-summary" role="status">
        {data
          ? `Affichage de ${first} à ${last} sur ${data.total} ${noun}`
          : "Pagination indisponible pendant le chargement ou en cas d’erreur."}
      </div>
      <div className="incident-pagination-actions">
        <Button
          variant="secondary"
          disabled={!hasPages || !data.has_previous || data.page <= 1}
          onClick={() => data && onPageChange(data.page - 1)}
        >
          Précédent
        </Button>
        <span>
          {hasPages
            ? `Page ${data.page} sur ${data.total_pages}`
            : data
              ? "Aucune page"
              : "—"}
        </span>
        <Button
          variant="secondary"
          disabled={
            !hasPages || !data.has_next || data.page >= data.total_pages
          }
          onClick={() => data && onPageChange(data.page + 1)}
        >
          Suivant
        </Button>
      </div>
    </nav>
  );
}
