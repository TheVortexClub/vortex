import {
  Bot,
  Brain,
  Compass,
  FolderOpen,
  LayoutGrid,
  LibraryBig,
  type LucideIcon,
  MessageSquareText,
  Settings,
  SquarePlus,
  Workflow,
} from "lucide-react";

export type Section = {
  slug: string;
  label: string;
  href: string;
  icon: LucideIcon;
  /** Roadmap step that delivers this section (absent = available now). */
  step?: number;
  description?: string;
};

export const SECTIONS: Section[] = [
  { slug: "chat", label: "Chat", href: "/", icon: MessageSquareText },
  {
    slug: "explorar",
    label: "Explorar",
    href: "/explorar",
    icon: Compass,
    step: 8,
    description: "Galeria de prompts, modelos de agentes e presets da comunidade.",
  },
  {
    slug: "agentes",
    label: "Agentes",
    href: "/agentes",
    icon: Bot,
    step: 7,
    description: "Crie agentes com nome, instruções, ferramentas e arquivos de conhecimento.",
  },
  {
    slug: "ferramentas",
    label: "Ferramentas",
    href: "/ferramentas",
    icon: LayoutGrid,
    description: "Navegação web, geração de imagens, OCR, planilhas e execução de código.",
  },
  {
    slug: "criar",
    label: "Criar",
    href: "/criar",
    icon: SquarePlus,
    description: "Gere imagens e vídeos localmente, sem enviar nada para fora.",
  },
  {
    slug: "biblioteca",
    label: "Biblioteca",
    href: "/biblioteca",
    icon: LibraryBig,
    step: 8,
    description: "Todas as imagens, vídeos, documentos e códigos gerados, num só lugar.",
  },
  {
    slug: "projetos",
    label: "Projetos",
    href: "/projetos",
    icon: FolderOpen,
    description: "Espaços que reúnem conversas, arquivos, agentes e instruções.",
  },
  {
    slug: "automatizacoes",
    label: "Automatizações",
    href: "/automatizacoes",
    icon: Workflow,
    step: 7,
    description: "Fluxos com gatilhos (agenda, webhook, arquivo) e ações automáticas.",
  },
  {
    slug: "memoria",
    label: "Memória",
    href: "/memoria",
    icon: Brain,
    description: "Memória de longo prazo que você pode ver, editar, apagar e desligar.",
  },
  {
    slug: "configuracoes",
    label: "Configurações",
    href: "/configuracoes",
    icon: Settings,
    description: "Perfil, idioma, tema, parâmetros do modelo e acesso à API.",
  },
];

export const sectionBySlug = (slug: string) => SECTIONS.find((s) => s.slug === slug);
