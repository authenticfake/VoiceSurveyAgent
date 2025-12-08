import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CampaignForm } from "@/components/CampaignForm";
import { apiClient } from "@/lib/api/client";
import { UserProvider } from "@/lib/auth/user-context";

vi.mock("@/lib/api/client", () => {
  const actual = vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      createCampaign: vi.fn().mockResolvedValue({ id: "1" }),
      updateCampaign: vi.fn().mockResolvedValue({ id: "1" }),
      activateCampaign: vi.fn().mockResolvedValue(undefined)
    }
  };
});

function wrapper(children: React.ReactNode) {
  return <UserProviderMock>{children}</UserProviderMock>;
}

function UserProviderMock({ children }: { children: React.ReactNode }) {
  return (
    <UserContextMock.Provider value={{ user: { id: "1", name: "Jane", email: "jane@example.com", role: "campaign_manager" }, loading: false, refresh: vi.fn() }}>
      {children}
    </UserContextMock.Provider>
  );
}

// Mock the context to avoid network call
import { createContext } from "react";
const UserContextMock = createContext({
  user: { id: "1", name: "Jane", email: "jane@example.com", role: "campaign_manager" as const },
  loading: false,
  refresh: async () => {}
});
vi.mock("@/lib/auth/user-context", () => ({
  useUserContext: () => ({
    user: { id: "1", name: "Jane", email: "jane@example.com", role: "campaign_manager" as const },
    loading: false,
    refresh: vi.fn()
  }),
  UserProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>
}));

describe("CampaignForm", () => {
  it("validates required fields before submission", async () => {
    render(<CampaignForm mode="create" />, { wrapper });

    fireEvent.click(screen.getByRole("button", { name: /create campaign/i }));

    expect(await screen.findAllByText(/required/i)).toHaveLength(4);
  });

  it("submits payload when valid", async () => {
    render(<CampaignForm mode="create" />, { wrapper });

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: "Test Campaign" } });
    fireEvent.change(screen.getByLabelText(/intro script/i), { target: { value: "Intro" } });
    fireEvent.change(screen.getAllByLabelText(/question 1/i)[0], { target: { value: "Q1" } });
    fireEvent.change(screen.getAllByLabelText(/question 2/i)[0], { target: { value: "Q2" } });
    fireEvent.change(screen.getAllByLabelText(/question 3/i)[0], { target: { value: "Q3" } });

    fireEvent.click(screen.getByRole("button", { name: /create campaign/i }));

    await waitFor(() => expect(apiClient.createCampaign).toHaveBeenCalled());
  });
});