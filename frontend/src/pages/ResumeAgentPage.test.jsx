import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/endpoints.js";
import ResumeAgentPage from "./ResumeAgentPage.jsx";

vi.mock("../api/endpoints.js", () => ({
  api: {
    agentStatus: vi.fn(),
    agentProfile: vi.fn(),
    listApplications: vi.fn(),
    listRuns: vi.fn(),
    tailorResume: vi.fn(),
    checkFit: vi.fn(),
    listEntries: vi.fn(),
    logEntry: vi.fn(),
  },
}));

const STATUS = {
  configured: true,
  has_profile: true,
  entry_count: 4,
  runs_today: 1,
  daily_run_limit: 25,
};

const renderPage = (url = "/agent") =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <ResumeAgentPage />
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  api.agentStatus.mockResolvedValue(STATUS);
  api.agentProfile.mockResolvedValue({ yaml: "", roles: [{ key: "acme", company: "Acme Corp", title: "Engineer" }] });
  api.listApplications.mockResolvedValue([{ id: 5, role_title: "Cloud Engineer", company: { name: "Globex" } }]);
  api.listRuns.mockResolvedValue([]);
  api.listEntries.mockResolvedValue([]);
});

describe("ResumeAgentPage", () => {
  it("shows today's usage against the cap", async () => {
    renderPage();
    expect(await screen.findByText(/1 of 25 AI runs used today/)).toBeInTheDocument();
  });

  it("builds a resume for a linked application and lists what the check removed", async () => {
    api.tailorResume.mockResolvedValue({
      id: 9,
      kind: "tailor",
      ok: true,
      job_title: "Cloud Engineer at Globex",
      result: {
        fit_score: 7,
        fit_explanation: "Good match.",
        summary: "Cloud engineer.",
        skills: [{ category: "Cloud", items: ["Azure"] }],
        experience: [{ role_key: "acme", bullets: [{ text: "Automated Azure deployments.", sources: [1] }] }],
        removed: ["Bullet removed (claims leadership): Led a team of 12."],
      },
    });
    renderPage("/agent?application=5");
    await screen.findByRole("option", { name: "Cloud Engineer at Globex" });
    expect(screen.getByLabelText(/For which application/)).toHaveValue("5");

    await userEvent.type(screen.getByLabelText("Job posting"), "We need a cloud engineer.");
    await userEvent.click(screen.getByRole("button", { name: "Build resume" }));

    expect(api.tailorResume).toHaveBeenCalledWith({
      job_text: "We need a cloud engineer.",
      job_title: "",
      application_id: 5,
    });
    expect(await screen.findByText("Automated Azure deployments.")).toBeInTheDocument();
    expect(screen.getByText(/Led a team of 12/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download Word file" })).toBeInTheDocument();
  });

  it("shows the server's message when the daily cap is reached", async () => {
    api.checkFit.mockRejectedValue(Object.assign(new Error("You've reached today's limit of 25 agent runs."), { fields: {} }));
    renderPage();
    await userEvent.type(screen.getByLabelText("Job posting"), "A posting.");
    await userEvent.click(screen.getByRole("button", { name: "Check fit" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("today's limit");
  });

  it("logs work under a job from the profile", async () => {
    api.logEntry.mockResolvedValue({ id: 12, open_questions: [] });
    renderPage("/agent?tab=log");
    await screen.findByRole("option", { name: "Engineer, Acme Corp" });
    await userEvent.type(screen.getByLabelText("What did you do?"), "Fixed the build.");
    await userEvent.click(screen.getByRole("button", { name: "Save entry" }));
    expect(api.logEntry).toHaveBeenCalledWith(expect.objectContaining({ role: "acme", raw_text: "Fixed the build." }));
    expect(await screen.findByText("Saved entry #12.")).toBeInTheDocument();
  });
});
