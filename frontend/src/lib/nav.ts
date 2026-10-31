import type { Role } from "./api";

export interface NavItem {
  path: string;
  label: string;
  roles: Role[];
  // Milestone that delivers the page; undefined = available now.
  milestone?: string;
}

// The single source of truth for what each role can see. The API enforces the same rules.
export const NAV: NavItem[] = [
  { path: "", label: "Overview", roles: ["admin", "owner", "viewer"] },
  { path: "documents", label: "Documents", roles: ["admin", "owner"], milestone: "M3" },
  { path: "interview", label: "Interview", roles: ["owner"], milestone: "M4" },
  { path: "verify", label: "Verify answers", roles: ["owner"], milestone: "M5" },
  { path: "coverage", label: "Coverage", roles: ["admin", "owner"], milestone: "M6" },
  { path: "report", label: "Report", roles: ["admin", "viewer"], milestone: "M7" },
  { path: "qa", label: "Q&A", roles: ["admin", "viewer"], milestone: "M8" },
  { path: "members", label: "Members", roles: ["admin"] },
  { path: "audit", label: "Audit log", roles: ["admin"] },
];

export function navForRole(role: Role): NavItem[] {
  return NAV.filter((item) => item.roles.includes(role));
}
