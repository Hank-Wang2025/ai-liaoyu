import assert from "node:assert/strict";
import test from "node:test";

import { getImprovementText } from "../src/utils/reportPresentation.ts";

test("translates backend none rating instead of showing raw code", () => {
  const translate = (key: string) => {
    if (key === "report.improvementRatings.none") {
      return "translated-none";
    }
    return key;
  };

  assert.equal(
    getImprovementText(
      {
        rating: "none",
        emotion_improvement: 0,
      },
      0,
      translate,
    ),
    "translated-none",
  );
});
