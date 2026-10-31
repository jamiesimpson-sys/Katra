import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ErrorText } from "../components/ui";
import { api, type ModuleDef, type Priority } from "../lib/api";
import { useProject } from "./ProjectPage";

const PRIORITY_STYLE: Record<Priority, string> = {
  high: "bg-red-50 text-red-700",
  medium: "bg-amber-50 text-amber-800",
  low: "bg-slate-100 text-slate-600",
};

export function QuestionBankPage() {
  const project = useProject();
  const module = useQuery({
    queryKey: ["project-module", project.id],
    queryFn: () => api<ModuleDef>(`/api/projects/${project.id}/module`),
  });
  const [open, setOpen] = useState<string | null>(null);

  if (module.error) return <ErrorText error={module.error} />;
  if (!module.data) return null;
  const m = module.data;
  const docName = Object.fromEntries(m.document_types.map((d) => [d.id, d.name]));
  const total = m.sections.reduce((n, s) => n + s.questions.length, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Question bank</h1>
        <p className="mt-1 text-sm text-slate-600">
          {m.name} v{m.version} · {m.sections.length} sections · {total} questions · about {m.target_sessions} sessions of{" "}
          {m.session_length_minutes} minutes
        </p>
        <p className="mt-2 text-sm text-slate-600">{m.description}</p>
      </div>

      {m.sections.map((section) => {
        const isOpen = open === section.id;
        return (
          <div key={section.id} className="rounded-lg border border-slate-200 bg-white">
            <button
              className="flex w-full items-center justify-between px-5 py-4 text-left"
              onClick={() => setOpen(isOpen ? null : section.id)}
              aria-expanded={isOpen}
            >
              <span>
                <span className="font-semibold">{section.name}</span>
                {section.description && <span className="block text-sm text-slate-500">{section.description}</span>}
              </span>
              <span className="ml-4 shrink-0 text-sm text-slate-500">
                {section.questions.length} questions {isOpen ? "▴" : "▾"}
              </span>
            </button>
            {isOpen && (
              <ol className="divide-y divide-slate-100 border-t border-slate-100">
                {section.questions.map((q) => (
                  <li key={q.id} className="px-5 py-3 text-sm">
                    <div className="flex items-start justify-between gap-3">
                      <span>{q.text}</span>
                      <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs capitalize ${PRIORITY_STYLE[q.priority]}`}>
                        {q.priority}
                      </span>
                    </div>
                    {q.related_document_types.length > 0 && (
                      <div className="mt-1 text-xs text-slate-500">
                        Related documents: {q.related_document_types.map((d) => docName[d] ?? d).join(", ")}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>
        );
      })}
    </div>
  );
}
