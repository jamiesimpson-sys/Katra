import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button, Card, ErrorText, Field, Input } from "../components/ui";
import { api, type InvitePreview, type Me } from "../lib/api";

export function AcceptInvitePage() {
  const { token = "" } = useParams();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const preview = useQuery({
    queryKey: ["invite", token],
    queryFn: () => api<InvitePreview>(`/api/invites/${token}`),
    retry: false,
  });
  const accept = useMutation({
    mutationFn: () =>
      api<Me>(`/api/invites/${token}/accept`, { method: "POST", body: { password, display_name: name } }),
    onSuccess: (data) => {
      qc.setQueryData(["me"], data);
      navigate("/");
    },
  });

  if (preview.isLoading) return null;
  if (preview.error || !preview.data)
    return (
      <Card className="mx-auto mt-16 max-w-md">
        <ErrorText error={preview.error} />
      </Card>
    );

  const invite = preview.data;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    accept.mutate();
  };

  return (
    <div className="mx-auto mt-16 max-w-md">
      <Card>
        <h1 className="mb-2 text-xl font-semibold">Join {invite.project_name}</h1>
        <p className="mb-6 text-sm text-slate-600">
          You've been invited as <strong>{invite.role}</strong> ({invite.email}).
          {invite.user_exists ? " Enter your existing password to accept." : " Choose a password to create your account."}
        </p>
        <form onSubmit={submit} className="space-y-4">
          {!invite.user_exists && (
            <Field label="Your name">
              <Input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
            </Field>
          )}
          <Field label={invite.user_exists ? "Password" : "Choose a password (10+ characters)"}>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={invite.user_exists ? 1 : 10}
              autoComplete={invite.user_exists ? "current-password" : "new-password"}
              required
            />
          </Field>
          <ErrorText error={accept.error} />
          <Button type="submit" disabled={accept.isPending} className="w-full">
            Accept invite
          </Button>
        </form>
      </Card>
    </div>
  );
}
