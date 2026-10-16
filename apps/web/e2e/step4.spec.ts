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

test("project: create, chat inside it, see it in the panel", async ({ page }) => {
  await register(page, "Proj");
  await page.getByRole("link", { name: "Projetos" }).first().click();
  await page.getByRole("button", { name: "Criar o primeiro projeto" }).click();
  await page.getByLabel("Nome").fill("Estratégia de Marketing");
  await page.getByLabel("Instruções para o Vortex").fill("Tom informal.");
  await page.getByRole("button", { name: "Criar projeto" }).click();

  await page.getByRole("link", { name: /Estratégia de Marketing/ }).click();
  await expect(page.getByText("Tom informal.")).toBeVisible();
  await page.getByRole("link", { name: "Nova conversa no projeto" }).click();
  await expect(page.getByText("Nova conversa no projeto: Estratégia de Marketing")).toBeVisible();

  const box = page.getByLabel("Mensagem para o Vortex");
  await box.fill("ideias de post");
  await box.press("Enter");
  await expect(page.getByText("Você disse: ideias de post")).toBeVisible();
  await expect(page.getByText("Projeto: Estratégia de Marketing")).toBeVisible();

  const panel = page.getByRole("complementary", { name: "Painel" });
  await expect(panel.getByText("1 conversa")).toBeVisible();
});

test("settings: model parameters and tools persist; server tab is admin-only", async ({ page }) => {
  await register(page, "Conf");
  await page.goto("/configuracoes");
  // "Proj" signed up first in this file, so "Conf" is never the admin
  await expect(page.getByRole("tab", { name: "Perfil" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Servidor" })).toHaveCount(0);

  await page.getByRole("tab", { name: "Modelo" }).click();
  await page.getByLabel("Instruções personalizadas").fill("Responda curto.");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByText("Salvo")).toBeVisible();
  await page.reload();
  await page.getByRole("tab", { name: "Modelo" }).click();
  await expect(page.getByLabel("Instruções personalizadas")).toHaveValue("Responda curto.");

  await page.getByRole("tab", { name: "Ferramentas" }).click();
  await expect(page.getByRole("switch", { name: "Navegação Web" })).toBeVisible();

  await page.getByRole("tab", { name: "Acesso à API" }).click();
  await expect(page.getByText("/v1", { exact: false }).first()).toBeVisible();

});

test("usage dashboard shows totals and server stats", async ({ page }) => {
  await register(page, "Uso");
  const box = page.getByLabel("Mensagem para o Vortex");
  await box.fill("oi");
  await box.press("Enter");
  await expect(page.getByText("Você disse: oi")).toBeVisible();

  await page.goto("/uso");
  await expect(page.getByRole("heading", { name: "Uso e Desempenho" })).toBeVisible();
  await expect(page.getByRole("img", { name: /Respostas por dia, total 1/ })).toBeVisible();
  await expect(page.getByRole("meter", { name: /CPU/ })).toBeVisible();
});
