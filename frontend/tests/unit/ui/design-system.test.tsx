import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ActionGroup } from "@/shared/ui/action-group";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Field, Input } from "@/shared/ui/form";
import { PageIntro } from "@/shared/ui/typography";

describe("shared design system", () => {
  it("exposes semantic typography, fields, badges and named actions", () => {
    render(<>
      <PageIntro eyebrow="Quản trị" title="Người dùng" description="Quản lý tài khoản theo vai trò." />
      <Field label="Tên đăng nhập" htmlFor="username" description="Dùng để đăng nhập.">
        <Input id="username" />
      </Field>
      <Badge tone="ready">Đang hoạt động</Badge>
      <ActionGroup><Button aria-label="Lưu người dùng">Lưu</Button></ActionGroup>
    </>);
    expect(screen.getByRole("heading", { name: "Người dùng" })).toBeInTheDocument();
    expect(screen.getByLabelText("Tên đăng nhập")).toBeInTheDocument();
    expect(screen.getByText("Dùng để đăng nhập.")).toBeInTheDocument();
    expect(screen.getByText("Đang hoạt động")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lưu người dùng" })).toBeInTheDocument();
  });

  it("keeps visible keyboard focus, touch targets and wrapping in global tokens", () => {
    const css = readFileSync(resolve("src/app/globals.css"), "utf8");
    expect(css).toMatch(/:focus-visible/);
    expect(css).toContain("--touch-target");
    expect(css).toMatch(/overflow-wrap:\s*anywhere/);
  });
});
