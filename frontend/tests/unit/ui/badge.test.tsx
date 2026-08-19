import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Badge } from "@/shared/ui/badge";

describe("Badge", () => {
  it.each([
    ["neutral", "Thông tin", "i"],
    ["ready", "Sẵn sàng", "✓"],
    ["warning", "Cần chú ý", "!"],
    ["critical", "Lỗi", "×"],
  ] as const)("pairs %s color with text and a decorative cue", (tone, label, icon) => {
    render(
      <Badge tone={tone} icon={icon}>
        {label}
      </Badge>,
    );
    expect(screen.getByText(label)).toHaveTextContent(label);
    expect(screen.getByText(icon)).toHaveAttribute("aria-hidden", "true");
  });
});
