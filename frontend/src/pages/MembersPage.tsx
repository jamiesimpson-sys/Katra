import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Button, Card, ErrorText, Field, Input, RoleBadge, SecondaryButton, Select } from "../components/ui";
import { api, type Invite, type Member, type Role } from "../lib/api";
import { useMe } from "../lib/auth";
import { useProject } from "./ProjectPage";

export function MembersPage() {
  const project = useProject();
  const base = `/api/projects/${project.id}`;
  const qc = useQueryClient();
  const { data: me } = useMe();
  const members = useQuery({ queryKey: ["members", project.id], queryFn: () => api<Member[]>(`${base}/members`) });
  const invites = useQuery({ queryKey: ["invites", project.id], queryFn: () => api<Invite[]>(`${base}/invites`) });

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("owner");
  const [lastLink, setLastLink] = useState<string | null>(null);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["members", project.id] });
    qc.invalidateQueries({ queryKey: ["invites", project.id] });
  };
  const invite = useMutation({
    mutationFn: () => api<Invite>(`${base}/invites`, { method: "POST", body: { email, role } }),
    onSuccess: (inv) => {
      setLastLink(inv.invite_url ?? null);
      setEmail("");
      refresh();
    },
  });
  const revoke = useMutation({
    mutationFn: (id: string) => api(`${base}/invites/${id}`, { method: "DELETE" }),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (userId: string) => api(`${base}/members/${userId}`, { method: "DELETE" }),
    onSuccess: refresh,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    invite.mutate();
  };
  const pending = invites.data?.filter((i) => !i.accepted_at && !i.revoked_at && new Date(i.expires_at) > new Date());

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Members</h1>

      <Card>
        <h2 className="mb-4 font-semibold">Invite someone</h2>
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-[1fr_160px_auto] sm:items-end">
          <Field label="Email">
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field label="Role">
            <Select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              <option value="owner">Owner</option>
              <option value="viewer">Viewer (buyer)</option>
              <option value="admin">Admin</option>
            </Select>
          </Field>
          <Button type="submit" disabled={invite.isPending}>
            Create invite
          </Button>
        </form>
        <ErrorText error={invite.error} />
        {lastLink && (
          <div className="mt-4 rounded-md bg-amber-50 p-3 text-sm">
            <p className="mb-1 font-medium">Send this link to the invitee. It is shown only once.</p>
            <code className="block break-all">{lastLink}</code>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="mb-4 font-semibold">People</h2>
        <ul className="divide-y divide-slate-100">
          {members.data?.map((m) => (
            <li key={m.user.id} className="flex items-center justify-between py-2 text-sm">
              <span>
                {m.user.display_name || m.user.email} <span className="text-slate-500">{m.user.email}</span>
              </span>
              <span className="flex items-center gap-3">
                <RoleBadge role={m.role} />
                {m.user.id !== me?.user.id && (
                  <SecondaryButton onClick={() => remove.mutate(m.user.id)}>Remove</SecondaryButton>
                )}
              </span>
            </li>
          ))}
        </ul>
        <ErrorText error={remove.error} />
      </Card>

      {pending && pending.length > 0 && (
        <Card>
          <h2 className="mb-4 font-semibold">Pending invites</h2>
          <ul className="divide-y divide-slate-100">
            {pending.map((i) => (
              <li key={i.id} className="flex items-center justify-between py-2 text-sm">
                <span>
                  {i.email} <span className="text-slate-500">expires {new Date(i.expires_at).toLocaleString()}</span>
                </span>
                <span className="flex items-center gap-3">
                  <RoleBadge role={i.role} />
                  <SecondaryButton onClick={() => revoke.mutate(i.id)}>Revoke</SecondaryButton>
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
