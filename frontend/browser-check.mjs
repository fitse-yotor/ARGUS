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
  executablePath:
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.goto("http://127.0.0.1:5173");
await page.getByLabel("Username").fill(config.ADMIN_USERNAME || "admin");
await page.getByLabel("Password", { exact: true }).fill(config.ADMIN_PASSWORD);
await page.getByRole("button", { name: "Sign in", exact: true }).click();
await page.getByRole("heading", { name: "Overview", exact: true }).waitFor();
await page.screenshot({ path: "../storage/overview.png", fullPage: true });
for (const name of [
  "Operations",
  "ARGUS Vision",
  "Traffic Analysis",
  "Convoy Analysis",
  "Events & Alerts",
  "Incidents",
  "Investigation",
  "Evidence",
  "Analytics",
  "Administration",
  "Demo Control",
]) {
  await page.locator("nav").getByRole("button", { name, exact: true }).click();
  await page.getByRole("heading", { name, exact: true }).waitFor();
}
await page
  .locator("nav")
  .getByRole("button", { name: "ARGUS Sense", exact: true })
  .click();
await page.getByRole("button", { name: "Enter Room", exact: true }).click();
await page.getByText("DETECTED", { exact: true }).waitFor();
await page.getByRole("button", { name: "Sit", exact: true }).click();
await page.getByText("SITTING", { exact: true }).waitFor();
await page.screenshot({ path: "../storage/rf-room.png", fullPage: true });
await page.getByRole("button", { name: "No Person", exact: true }).click();
console.log(
  JSON.stringify(
    {
      browser: "Chrome",
      checked: "login, 12 routes, RF controls and pose update",
      pageErrors: errors,
    },
    null,
    2,
  ),
);
await browser.close();
if (errors.length) process.exit(1);
