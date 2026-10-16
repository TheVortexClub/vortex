import { expect, type Page, test } from "@playwright/test";

async function register(page: Page, name: string) {
  await page.goto("/login");
  await page.getByRole("button", { name: "Cadastre-se" }).click();
  await page.getByLabel("Nome").fill(name);
  await page.getByLabel("E-mail").fill(`${name.toLowerCase()}-${Date.now()}@example.com`);
  await page.getByLabel("Senha").fill("senha-forte-123");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await expect(page.getByRole("heading", { name: "VORTEX" })).toBeVisible();
}

test("attach a file, ask about it, see the source", async ({ page }) => {
  await register(page, "Arq");
  await page.locator('input[type="file"]').first().setInputFiles({
    name: "receita.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Pão de queijo: 500g de polvilho azedo."),
  });
  const chip = page.getByRole("list", { name: "Anexos" }).getByText("receita.txt");
  await expect(chip).toBeVisible();
  await expect(page.getByRole("button", { name: "Enviar" })).toBeDisabled(); // no text yet
  await expect(page.getByText(/\d+ B$/)).toBeVisible({ timeout: 20_000 }); // ready (size shown)

  const box = page.getByLabel("Mensagem para o Vortex");
  await box.fill("Quanto polvilho vai?");
  await box.press("Enter");
  await expect(page.getByText("Você disse: Quanto polvilho vai?")).toBeVisible();
  await expect(page.getByRole("link", { name: "receita.txt" }).first()).toBeVisible(); // attachment on the message
  await expect(page.getByLabel("Fontes").getByText("receita.txt")).toBeVisible();
});

test("remember something in chat, then manage it on the memory page", async ({ page }) => {
  await register(page, "Mem");
  const box = page.getByLabel("Mensagem para o Vortex");
  await box.fill("Lembre que eu moro em Niterói");
  await box.press("Enter");
  await expect(page.getByText("Guardei na memória:")).toBeVisible();

  await page.getByRole("link", { name: "ver memória" }).click();
  await expect(page.getByText("eu moro em Niterói", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Esquecer" }).click();
  await expect(page.getByText("Nada guardado ainda")).toBeVisible();
});
