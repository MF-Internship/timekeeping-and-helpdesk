import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MobiFoneLogo } from "@/shared/ui/brand";

describe("MobiFoneLogo", () => {
  it("uses approved local responsive assets with meaningful alt text", () => {
    const { container } = render(<MobiFoneLogo />);
    const image = screen.getByRole("img", { name: "MobiFone" });
    expect(image).toHaveAttribute("src", "/brand/logo-phone.jpg");
    expect(image).toHaveAttribute("width", "1436");
    expect(image).toHaveAttribute("height", "1026");
    const source = container.querySelector("source");
    expect(source).toHaveAttribute("srcset", "/brand/logo-desktop.png");
    expect(source).toHaveAttribute("media", "(min-width: 48rem)");
    expect(source).toHaveAttribute("width", "659");
    expect(source).toHaveAttribute("height", "400");
  });

  it("preserves aspect ratio with contain behavior and a clear-space wrapper", async () => {
    const css = await import("@/shared/ui/brand/MobiFoneLogo.module.css");
    render(<MobiFoneLogo />);
    expect(screen.getByRole("img", { name: "MobiFone" })).toHaveClass(css.default.logo);
    expect(screen.getByRole("img", { name: "MobiFone" }).closest("picture")).toHaveClass(
      css.default.picture,
    );
  });
});
