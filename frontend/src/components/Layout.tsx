import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useMe } from "../lib/auth";

export function Layout() {
  const { data: me } = useMe();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<{ status: string; commit: string }>("/api/health"),
    staleTime: Infinity,
  });
  const logout = useMutation({
    mutationFn: () => api("/api/auth/logout", { method: "POST" }),
    onSettled: () => {
      qc.clear();
      navigate("/login");
    },
  });

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-semibold text-brand">
            Katra
          </Link>
          {me && (
            <div className="flex items-center gap-4 text-sm text-slate-600">
              <span>{me.user.email}</span>
              <button className="hover:text-slate-900" onClick={() => logout.mutate()}>
                Sign out
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-6xl px-4 pb-6 text-xs text-slate-400">
        Katra prototype · build {health.data?.commit ?? "…"}
      </footer>
    </div>
  );
}
