import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import Layout from "./Layout.jsx";

let user;
vi.mock("../auth.jsx", () => ({ useAuth: () => ({ user, logout: vi.fn() }) }));

const renderLayout = () =>
  render(
    <MemoryRouter>
      <Layout />
    </MemoryRouter>,
  );

// The resume agent link is only for the account the server allows.
describe("Layout", () => {
  it("shows the resume agent to its owner", () => {
    user = { email: "owner@example.com", agent_enabled: true };
    renderLayout();
    expect(screen.getByRole("link", { name: "Resume agent" })).toHaveAttribute("href", "/agent");
  });

  it("hides it from everyone else", () => {
    user = { email: "someone@example.com", agent_enabled: false };
    renderLayout();
    expect(screen.queryByRole("link", { name: "Resume agent" })).not.toBeInTheDocument();
  });
});
