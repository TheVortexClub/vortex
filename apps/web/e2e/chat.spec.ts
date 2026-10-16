import { expect, type Page, test } from "@playwright/test";

async function register(page: Page, name: string) {
  const email = `${name.toLowerCase()}-${Date.now()}@example.com`;
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByRole("button", { name: "Cadastre-se" }).click();
  await page.getByLabel("Nome").fill(name);
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha").fill("senha-forte-123");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await expect(page.getByRole("heading", { name: "VORTEX" })).toBeVisible();
  return email;
}

async function send(page: Page, text: string) {
  const box = page.getByLabel("Mensagem para o Vortex");
  await box.fill(text);
  await box.press("Enter");
}

test("home matches the layout: hero, action cards, chips, panels", async ({ page }) => {
  await register(page, "Ana");
  await expect(page.getByText("Muito mais que um chatbot. Um universo de possibilidades.")).toBeVisible();
  for (const card of ["Conversar", "Criar", "Analisar", "Programar", "Planejar", "Automatizar"]) {
    await expect(page.getByRole("button", { name: new RegExp(`^${card}`) })).toBeVisible();
  }
  await expect(page.getByRole("button", { name: "Me ajude a planejar um projeto" })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Painel" }).getByText("PRÓPRIO", { exact: true })).toBeVisible();
  await expect(page.getByText("Sem uso de créditos")).toBeVisible();
});

test("send, stream, persist, regenerate, like and search", async ({ page }) => {
  await register(page, "Bia");
  await send(page, "Olá Vortex");

  await expect(page).toHaveURL(/\/c\/[0-9a-f]{32}$/);
  await expect(page.getByText("Você disse: Olá Vortex")).toBeVisible();
  const sidebar = page.getByRole("complementary", { name: "Navegação principal" });
  await expect(sidebar.getByRole("link", { name: "Olá Vortex" })).toBeVisible();

  // history survives a reload
  await page.reload();
  await expect(page.getByText("Você disse: Olá Vortex")).toBeVisible();

  // Shift+Enter makes a new line instead of sending
  const box = page.getByLabel("Mensagem para o Vortex");
  await box.fill("linha 1");
  await box.press("Shift+Enter");
  await box.pressSequentially("linha 2");
  await expect(box).toHaveValue("linha 1\nlinha 2");
  await box.press("Enter");
  await expect(page.getByText(/Você disse: linha 1\s+linha 2/)).toBeVisible();

  await page.getByRole("button", { name: "Gerar novamente" }).click();
  await expect(page.getByText(/Você disse: linha 1/)).toHaveCount(1);

  const like = page.getByRole("button", { name: "Gostei" }).last();
  await like.click();
  await expect(like).toHaveAttribute("aria-pressed", "true");

  // Ctrl+K palette searches message text
  await page.getByRole("button", { name: /Pesquise conversas/ }).click();
  await page.getByPlaceholder("Pesquise conversas, ferramentas, seções...").fill("linha 2");
  await expect(page.getByRole("option", { name: "Olá Vortex" })).toBeVisible();
});

test("action card sets the mode and accounts are isolated", async ({ page, browser }) => {
  await register(page, "Caio");
  await page.getByRole("button", { name: /^Programar/ }).click();
  await expect(page.getByText("Modo Programar")).toBeVisible();
  await send(page, "uma função");
  await expect(page.getByText("Você disse: uma função")).toBeVisible();

  const other = await browser.newPage();
  await register(other, "Duda");
  const sidebar = other.getByRole("complementary", { name: "Navegação principal" });
  await expect(sidebar.getByText("Suas conversas aparecem aqui.")).toBeVisible();
  await other.close();
});
