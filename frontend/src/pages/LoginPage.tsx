import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Button, Card, ErrorText, Field, Input } from "../components/ui";
import { api, type Me } from "../lib/api";
import { useMe } from "../lib/auth";

export function LoginPage() {
  const { data: me } = useMe();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useMutation({
    mutationFn: () => api<Me>("/api/auth/login", { method: "POST", body: { email, password } }),
    onSuccess: (data) => {
      qc.setQueryData(["me"], data);
      navigate("/");
    },
  });

  if (me) return <Navigate to="/" replace />;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    login.mutate();
  };

  return (
    <div className="mx-auto mt-16 max-w-sm">
      <Card>
        <h1 className="mb-6 text-xl font-semibold">Sign in to Katra</h1>
        <form onSubmit={submit} className="space-y-4">
          <Field label="Email">
            <Input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field label="Password">
            <Input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </Field>
          <ErrorText error={login.error} />
          <Button type="submit" disabled={login.isPending} className="w-full">
            Sign in
          </Button>
        </form>
      </Card>
    </div>
  );
}
