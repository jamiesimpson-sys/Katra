import { describe, expect, it } from "vitest";
import { navForRole } from "./nav";

const labels = (role: Parameters<typeof navForRole>[0]) => navForRole(role).map((i) => i.label);

describe("navForRole", () => {
  it("gives viewers only the read-only pages, without the question bank", () => {
    expect(labels("viewer")).toEqual(["Overview", "Report", "Q&A"]);
  });

  it("keeps admin-only pages away from owners", () => {
    expect(labels("owner")).not.toContain("Members");
    expect(labels("owner")).not.toContain("Audit log");
    expect(labels("owner")).toContain("Interview");
    expect(labels("owner")).toContain("Question bank");
  });

  it("does not offer the interview to admins", () => {
    expect(labels("admin")).not.toContain("Interview");
    expect(labels("admin")).toContain("Members");
  });
});
