import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, useOutletContext, useParams } from "react-router-dom";
import { ErrorText, RoleBadge } from "../components/ui";
import { api, type Project } from "../lib/api";
import { navForRole } from "../lib/nav";

export function useProject() {
  return useOutletContext<Project>();
}

export function ProjectPage() {
  const { projectId = "" } = useParams();
  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api<Project>(`/api/projects/${projectId}`),
    retry: false,
  });

  if (project.error) return <ErrorText error={project.error} />;
  if (!project.data) return null;
  const p = project.data;

  return (
    <div className="grid gap-8 md:grid-cols-[200px_1fr]">
      <aside>
        <div className="mb-4">
          <div className="font-semibold">{p.name}</div>
          <div className="mt-1 flex items-center gap-2 text-sm text-slate-500">
            {p.module_id} <RoleBadge role={p.role} />
          </div>
        </div>
        <nav className="flex flex-col gap-1">
          {navForRole(p.role).map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm ${isActive ? "bg-brand-light font-medium text-brand" : "text-slate-700 hover:bg-slate-100"}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <section>
        <Outlet context={p} />
      </section>
    </div>
  );
}

export function OverviewPage() {
  const p = useProject();
  const next: Record<string, string> = {
    admin: "Invite the owner from Members. Documents, coverage and the report follow in later milestones.",
    owner: "Upload documents and start your first interview session once those features are live.",
    viewer: "The verified report and Q&A assistant will appear here once the owner has verified answers.",
  };
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Overview</h1>
      <p className="text-slate-600">{next[p.role]}</p>
    </div>
  );
}

export function ComingSoon({ title, milestone }: { title: string; milestone: string }) {
  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold">{title}</h1>
      <p className="text-slate-600">Arrives in milestone {milestone}.</p>
    </div>
  );
}
