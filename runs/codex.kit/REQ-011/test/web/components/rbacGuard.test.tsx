import { render, screen } from "@testing-library/react";
import { RbacGuard } from "@/components/RbacGuard";

vi.mock("@/lib/auth/user-context", () => ({
  useUserContext: () => ({
    user: { id: "1", email: "viewer@example.com", name: "Viewer", role: "viewer" as const },
    loading: false,
    refresh: vi.fn()
  })
}));

describe("RbacGuard", () => {
  it("renders fallback when role not allowed", () => {
    render(
      <RbacGuard allowed={["admin"]} fallback={<span>No access</span>}>
        <div>Secret</div>
      </RbacGuard>
    );

    expect(screen.getByText("No access")).toBeInTheDocument();
  });

  it("renders children when allowed", () => {
    vi.mocked(require("@/lib/auth/user-context")).useUserContext = () => ({
      user: { id: "1", email: "admin@example.com", name: "Admin", role: "admin" as const },
      loading: false,
      refresh: vi.fn()
    });

    render(
      <RbacGuard allowed={["admin"]}>
        <div>Secret</div>
      </RbacGuard>
    );

    expect(screen.getByText("Secret")).toBeInTheDocument();
  });
});