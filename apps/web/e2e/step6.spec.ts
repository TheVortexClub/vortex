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

// The e2e server has no SearXNG/ComfyUI/sandbox: tools must say so instead of pretending.
test("tools page shows what's ready and why the rest isn't", async ({ page }) => {
  await register(page, "Tools");
  await page.goto("/ferramentas");
  await expect(page.getByRole("heading", { name: "Ferramentas" })).toBeVisible();
  await expect(page.getByText("SearXNG (pesquisa local) não está rodando")).toBeVisible();
  await expect(page.getByText("Chega na etapa 7 do roadmap.").first()).toBeVisible();
  await expect(page.getByText("setup-tools.ps1")).toBeVisible();
});

test("search toggle is disabled with a reason when search isn't set up", async ({ page }) => {
  await register(page, "Busca");
  const search = page.getByRole("button", { name: "Pesquisar" });
  await expect(search).toBeDisabled();
  await expect(search).toHaveAttribute("title", /SearXNG/);
});

test("create page explains image generation isn't active", async ({ page }) => {
  await register(page, "Arte");
  await page.goto("/criar");
  await expect(page.getByText("A geração de imagens ainda não está ativa neste servidor.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Gerar imagem" })).toBeDisabled();
});
