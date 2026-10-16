# Vortex 24 horas no ar (Windows)

Guia para deixar o notebook servindo o Vortex o tempo todo. São três peças:
**Ollama** (o modelo), **servidor do Vortex** (site + API) e **o Windows não dormir**.

## 1. Ollama

O instalador do Ollama já coloca um atalho na pasta Inicializar, então ele abre sozinho quando
você entra no Windows.

**Como saber se está rodando:**

- Ícone da lhama 🦙 perto do relógio (às vezes escondido na setinha `^`).
- No navegador, abra http://localhost:11434: deve aparecer `Ollama is running`.
- No terminal: `ollama ps` mostra os modelos carregados na memória.

**Se não estiver rodando:** menu Iniciar → digite `Ollama` → abrir.

**Opcional: manter o modelo sempre na memória.** Por padrão o Ollama descarrega o modelo depois
de alguns minutos sem uso, e a próxima pergunta demora alguns segundos a mais para começar. Para
deixar sempre carregado (usa ~2,5 GB de RAM com o modelo 3B):

```powershell
setx OLLAMA_KEEP_ALIVE -1
```

Depois feche o Ollama (botão direito no ícone da lhama → **Quit Ollama**) e abra de novo.

## 2. Servidor do Vortex

Para ligar agora:

```powershell
cd C:\Users\BernardoAlmeida\Videos\Vortex
.\scripts\serve.ps1
```

Para ligar **sozinho** toda vez que você entrar no Windows:

```powershell
.\scripts\install-autostart.ps1
```

Isso cria o atalho **Vortex Servidor** na sua pasta Inicializar (abre minimizado). Para desfazer:
`.\scripts\install-autostart.ps1 -Remove`.

Para desligar o servidor: clique na janela dele e aperte `Ctrl+C` (ou feche a janela).

## 3. O Windows não pode dormir

Se o notebook suspender, o Vortex sai do ar. Confira em **Configurações → Sistema → Energia e
bateria → Tela, suspensão e hibernação**:

- **Ao conectar, colocar meu dispositivo em suspensão após:** `Nunca`.
- A tela pode desligar à vontade; isso não afeta o servidor.

Se for um notebook e você quiser fechar a tampa: **Painel de Controle → Opções de Energia →
Escolher a função de fechamento da tampa → Ao fechar a tampa (conectado): Nada a fazer.**

Deixe o notebook **ligado na tomada**.

## 4. Reinícios do Windows Update

O Windows Update às vezes reinicia o computador. Para evitar no meio do dia:
**Configurações → Windows Update → Opções avançadas → Horário ativo** (ex.: 07:00–01:00).

Depois de um reinício, o Ollama e o Vortex voltam sozinhos **assim que alguém entrar no Windows**.
Se você quiser que voltem sem ninguém digitar a senha, existe o login automático do Windows
(`netplwiz`), mas ele deixa o notebook aberto para quem tiver acesso físico a ele: só use se o
notebook fica num lugar seguro.

## 5. Acesso pelos outros aparelhos

- Endereço: `http://<IP-do-notebook>:3000`. O `serve.ps1` mostra o IP ao iniciar.
- **Firewall:** na primeira vez o Windows pergunta sobre o **Node.js**; marque **Redes privadas**.
  Se você negou sem querer: **Painel de Controle → Firewall do Windows Defender → Permitir um
  aplicativo pelo firewall → Node.js → marcar Privada**.
- **O IP pode mudar** quando o roteador reinicia. Para fixar, faça uma *reserva de DHCP* para o
  notebook nas configurações do roteador (geralmente em http://192.168.0.1 ou http://192.168.1.1;
  procure "DHCP", "Reserva de endereço" ou "IP fixo").
- **Fora de casa** (4G, outra rede): use um túnel como **Tailscale** (mais simples: instale no
  notebook e no celular, entre na mesma conta e acesse pelo nome do notebook) ou **Cloudflare
  Tunnel**. Não abra a porta 3000 direto no roteador.

## Checklist rápido

| Item | Como conferir |
|---|---|
| Ollama rodando | http://localhost:11434 mostra `Ollama is running` |
| Modelo do Vortex instalado | `ollama list` mostra `vortex:0.2.1` |
| Servidor no ar | http://localhost:3000 abre o login |
| Outros aparelhos | celular no mesmo Wi-Fi abre `http://<IP>:3000` |
| Não dorme | Energia → suspensão `Nunca` (na tomada) |
| Volta sozinho | atalho **Vortex Servidor** na pasta Inicializar (`Win+R` → `shell:startup`) |
