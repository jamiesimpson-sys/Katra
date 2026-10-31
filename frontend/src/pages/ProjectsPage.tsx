import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Button, Card, ErrorText, Field, Input, RoleBadge } from "../components/ui";
import { api, type Project } from "../lib/api";
import { useMe } from "../lib/auth";

function CreateProject() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  // The module picker arrives with the module loader in M2.
  const [moduleId, setModuleId] = useState("diligence_ready");
  const create = useMutation({
    mutationFn: () => api<Project>("/api/projects", { method: "POST", body: { name, module_id: moduleId } }),
    onSuccess: () => {
      setName("");
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate();
  };

  return (
    <Card>
      <h2 className="mb-4 font-semibold">New project</h2>
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <Field label="Company / project name">
          <Input value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        <Field label="Module">
          <Input value={moduleId} onChange={(e) => setModuleId(e.target.value)} required />
        </Field>
        <Button type="submit" disabled={create.isPending}>
          Create
        </Button>
      </form>
      <ErrorText error={create.error} />
    </Card>
  );
}

export function ProjectsPage() {
  const { data: me } = useMe();
  const projects = useQuery({ queryKey: ["projects"], queryFn: () => api<Project[]>("/api/projects") });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Projects</h1>
      {me?.user.is_staff && <CreateProject />}
      <ErrorText error={projects.error} />
      {projects.data?.length === 0 && (
        <p className="text-slate-600">No projects yet. {me?.user.is_staff ? "Create one above." : "Ask your admin for an invite."}</p>
      )}
      <ul className="grid gap-3">
        {projects.data?.map((p) => (
          <li key={p.id}>
            <Link
              to={`/projects/${p.id}`}
              className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-5 py-4 hover:border-brand"
            >
              <div>
                <div className="font-medium">{p.name}</div>
                <div className="text-sm text-slate-500">{p.module_id}</div>
              </div>
              <RoleBadge role={p.role} />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
