import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ExportButton } from "@/components/ExportButton";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => {
  const actual = vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      exportContacts: vi.fn().mockResolvedValue(new Blob(["id"], { type: "text/csv" }))
    }
  };
});

vi.mock("@/lib/auth/user-context", () => ({
  useUserContext: () => ({
    user: { id: "1", email: "cm@example.com", name: "CM", role: "campaign_manager" as const },
    loading: false,
    refresh: vi.fn()
  })
}));

describe("ExportButton", () => {
  it("invokes export and downloads file", async () => {
    const createSpy = vi.spyOn(document, "createElement");
    const appendSpy = vi.spyOn(document.body, "appendChild");
    const removeSpy = vi.spyOn(document.body, "removeChild");
    render(<ExportButton campaignId="123" />);

    fireEvent.click(screen.getByRole("button", { name: /download csv export/i }));

    await waitFor(() => expect(apiClient.exportContacts).toHaveBeenCalledWith("123"));
    expect(createSpy).toHaveBeenCalledWith("a");
    expect(appendSpy).toHaveBeenCalled();
    expect(removeSpy).toHaveBeenCalled();
  });
});