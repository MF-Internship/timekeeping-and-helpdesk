import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Card } from "@/shared/ui/card";
import { SectionHeading } from "@/shared/ui/section-heading";

describe("Card and SectionHeading", () => {
  it("creates a labelled region without feature logic", () => {
    render(
      <Card aria-labelledby="card-title">
        <SectionHeading title="Vị trí" id="card-title" />
        <p>Nội dung</p>
      </Card>,
    );
    expect(screen.getByRole("region", { name: "Vị trí" })).toHaveTextContent("Nội dung");
  });

  it.each([2, 3, 4] as const)("lets the caller choose heading level %s", (level) => {
    render(<SectionHeading title={`Mức ${level}`} level={level} />);
    expect(screen.getByRole("heading", { name: `Mức ${level}`, level })).toBeVisible();
  });
});
