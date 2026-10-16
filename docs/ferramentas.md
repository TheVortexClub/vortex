# Ferramentas do Vortex (pesquisa, código, imagens)

Tudo roda no seu servidor. Cada ferramenta fica **indisponível** até o serviço dela estar ligado;
a página **Ferramentas** do Vortex mostra o estado de cada uma e o motivo.

## 1. Pesquisa na web e ambiente de código (Docker)

Com o **Docker Desktop** aberto, na pasta do Vortex:

```powershell
.\scripts\setup-tools.ps1
```

Isso faz duas coisas (baixa ~600 MB na primeira vez):

| O quê | Como fica |
|---|---|
| **SearXNG** (pesquisa) | container `vortex-searxng` em `http://127.0.0.1:8888`, reinicia sozinho com o Docker |
| **vortex-sandbox** (código) | imagem com Python, pandas, numpy, matplotlib, scipy e openpyxl |

Depois, no Vortex: **Ferramentas → Verificar de novo**.

**Como usar**

- **Pesquisar:** ligue o botão **Pesquisar** antes de enviar. O Vortex pesquisa, lê até 3 páginas e
  cita as fontes como [1], [2]. A pesquisa só acontece quando você liga o botão (é a única coisa
  que sai para a internet). Páginas da sua rede local e do próprio servidor são bloqueadas.
- **Código e planilhas:** ligue **Ferramentas** e peça uma conta, análise ou gráfico. Blocos de
  Python na resposta ganham o botão **Executar**. Os arquivos da conversa ficam em `/data/<nome>`.

**Segurança do ambiente de código:** cada execução roda num container novo, **sem internet**,
com sistema de arquivos só-leitura, usuário sem privilégios, sem capacidades do Linux, limite
de memória (`VORTEX_SANDBOX_MEMORY`, 768 MB), 1 CPU, 128 processos e tempo
(`VORTEX_SANDBOX_TIMEOUT`, 60 s). O código **nunca** roda direto no Windows. Sem o Docker, o botão
Executar não aparece.

Para desligar e remover: `.\scripts\setup-tools.ps1 -Remove`.

## 2. Geração de imagens (ComfyUI)

O Vortex usa o **ComfyUI** (Stable Diffusion) pela API dele. Instalação no Windows:

1. Baixe o **ComfyUI portable** na página de releases do projeto ComfyUI no GitHub e extraia
   (ex.: `C:\ComfyUI`).
2. Baixe um modelo e coloque em `ComfyUI\models\checkpoints\`:
   - **Sem GPU NVIDIA (como este notebook): SD-Turbo** (`sd_turbo.safetensors`, 2,5–5 GB conforme a versão → gera em
     1–4 passos). Configure `VORTEX_IMAGE_CHECKPOINT=sd_turbo.safetensors` e use 4 passos na
     página Criar.
   - Com GPU NVIDIA: Stable Diffusion 1.5 (`v1-5-pruned-emaonly.safetensors`) ou SDXL.
3. Inicie: sem GPU, `run_cpu.bat`; com NVIDIA, `run_nvidia_gpu.bat`. Ele abre em
   `http://127.0.0.1:8188`.
4. Se o arquivo do modelo tiver outro nome, ajuste `VORTEX_IMAGE_CHECKPOINT` no `.env` e reinicie
   o Vortex.

**Tempo esperado:** com CPU, uma imagem 512×512 leva de ~1 minuto (SD-Turbo, 4 passos) a vários
minutos (SD 1.5, 20 passos). As imagens são geradas uma de cada vez; as outras esperam na fila.

**Como usar:** página **Criar**, ou no chat com **Ferramentas** ligado: "crie uma imagem de…".

## 3. Vídeos

Geração de vídeo local (CogVideoX, LTX-Video, Wan) chega na etapa 8 e **precisa de GPU NVIDIA
com bastante memória** (12 GB+). Em CPU não é viável.
