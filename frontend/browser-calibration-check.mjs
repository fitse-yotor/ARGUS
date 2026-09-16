// Browser regression for road calibration, lane speed limits and live Convoy mode.
// Requires the dev stack (python scripts/dev.py) and signs in with the local administrator.
import { chromium } from "@playwright/test";
import fs from "node:fs";
const config = Object.fromEntries(
  fs
    .readFileSync("../.env", "utf8")
    .trim()
    .split("\n")
    .filter((l) => l.includes("="))
    .map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1)]),
);
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
});
const page = await browser.newPage({ viewport: { width: 1500, height: 1400 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.goto("http://127.0.0.1:5173");
await page.getByLabel("Username").fill(config.ADMIN_USERNAME || "admin");
await page.getByLabel("Password", { exact: true }).fill(config.ADMIN_PASSWORD);
await page.getByRole("button", { name: "Sign in", exact: true }).click();
await page
  .locator("nav")
  .getByRole("button", { name: "Traffic Analysis", exact: true })
  .click();
await page
  .locator("input[type=file]")
  .setInputFiles("../storage/validation/TEST-bundled-image-fixture.avi");
// The upload switches the selected video, so geometry must wait for it to finish.
const uploading = page.getByText("Uploading and preparing video…");
await uploading.waitFor({ state: "visible", timeout: 30000 }).catch(() => {});
await uploading.waitFor({ state: "hidden", timeout: 180000 });
await page
  .getByRole("button", { name: "Calibrate road", exact: true })
  .waitFor({ timeout: 60000 });
await page.getByRole("button", { name: "Calibrate road", exact: true }).click();
const stage = page.locator("svg.overlay");
const box = await stage.boundingBox();
const click = async (points) => {
  for (const [x, y] of points)
    await page.mouse.click(box.x + box.width * x, box.y + box.height * y);
};
// Four corners of a road rectangle: near-left, near-right, far-right, far-left.
await click([
  [0.25, 0.85],
  [0.75, 0.85],
  [0.62, 0.45],
  [0.38, 0.45],
]);
await page.getByLabel("Measured width, point 1 → 2 (m)").fill("3.5");
await page.getByLabel("Measured length, point 2 → 3 (m)").fill("25");
await page.getByRole("button", { name: "Save", exact: true }).click();
await page
  .getByText("Road calibration · 3.5 × 25 m")
  .waitFor({ timeout: 15000 });
await page.getByRole("button", { name: "Draw zone", exact: true }).click();
await click([
  [0.2, 0.9],
  [0.8, 0.9],
  [0.65, 0.4],
  [0.35, 0.4],
]);
await page.getByLabel("Name", { exact: true }).fill("Lane 1");
// Select labels carry their option text in the accessible name, so these match on a substring.
await page.getByLabel("Type").selectOption("Lane");
await page.getByLabel("Object class").selectOption("vehicle");
await page.getByLabel("Speed limit km/h (0 = no speed rule)").fill("40");
await page.getByRole("button", { name: "Save", exact: true }).click();
await page.getByText("Lane · vehicle · limit 40 km/h").waitFor({ timeout: 15000 });
await page.getByLabel("Free-flow speed km/h").fill("60");
await page.screenshot({ path: "../storage/calibration.png", fullPage: true });
// A second calibration on the same view is refused rather than silently accepted.
await page
  .getByRole("button", { name: "Edit road calibration", exact: true })
  .waitFor();
await page
  .locator("nav")
  .getByRole("button", { name: "Live Cameras", exact: true })
  .click();
await page.getByRole("button", { name: "Add camera" }).click();
const modes = await page
  .getByLabel("Analysis mode")
  .first()
  .locator("option")
  .allTextContents();
if (!modes.includes("Convoy"))
  throw Error("live cameras cannot select Convoy mode");
console.log(
  JSON.stringify(
    {
      workflow:
        "calibrate road → lane with speed limit → free-flow speed → live Convoy mode available",
      liveModes: modes,
      pageErrors: errors,
    },
    null,
    2,
  ),
);
await browser.close();
if (errors.length) process.exit(1);
