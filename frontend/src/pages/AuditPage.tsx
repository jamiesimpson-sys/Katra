import { useQuery } from "@tanstack/react-query";
import { Card, ErrorText } from "../components/ui";
import { api, type AuditEntry } from "../lib/api";
import { useProject } from "./ProjectPage";

export function AuditPage() {
  const project = useProject();
  const entries = useQuery({
    queryKey: ["audit", project.id],
    queryFn: () => api<AuditEntry[]>(`/api/projects/${project.id}/audit`),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Audit log</h1>
      <ErrorText error={entries.error} />
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-2">When</th>
              <th className="px-4 py-2">Action</th>
              <th className="px-4 py-2">User</th>
              <th className="px-4 py-2">Target</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {entries.data?.map((e) => (
              <tr key={e.id}>
                <td className="px-4 py-2 whitespace-nowrap">{new Date(e.created_at).toLocaleString()}</td>
                <td className="px-4 py-2 font-mono">{e.action}</td>
                <td className="px-4 py-2 font-mono text-xs">{e.user_id?.slice(0, 8) ?? "—"}</td>
                <td className="px-4 py-2 text-xs">{e.target_type ? `${e.target_type} ${e.target_id?.slice(0, 8)}` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
