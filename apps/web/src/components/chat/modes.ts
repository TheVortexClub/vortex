import {
  CalendarCheck,
  Code,
  FileSearch,
  type LucideIcon,
  MessageSquareMore,
  PenTool,
  Workflow,
} from "lucide-react";
import type { Mode } from "@/lib/api";

export const MODES: {
  id: Mode;
  title: string;
  description: string;
  icon: LucideIcon;
  color: string;
  placeholder: string;
}[] = [
  {
    id: "conversar",
    title: "Conversar",
    description: "Tire dúvidas e converse sobre qualquer assunto",
    icon: MessageSquareMore,
    color: "text-blue-400",
    placeholder: "Digite sua mensagem para o Vortex...",
  },
  {
    id: "criar",
    title: "Criar",
    description: "Gere textos, imagens, vídeos e ideias",
    icon: PenTool,
    color: "text-teal-300",
    placeholder: "O que vamos criar hoje?",
  },
  {
    id: "analisar",
    title: "Analisar",
    description: "Analise arquivos, imagens e dados",
    icon: FileSearch,
    color: "text-indigo-400",
    placeholder: "Cole o texto ou descreva o que quer analisar...",
  },
  {
    id: "programar",
    title: "Programar",
    description: "Escreva, revise e execute códigos",
    icon: Code,
    color: "text-sky-400",
    placeholder: "Descreva o código que você precisa...",
  },
  {
    id: "planejar",
    title: "Planejar",
    description: "Organize tarefas e crie projetos",
    icon: CalendarCheck,
    color: "text-emerald-400",
    placeholder: "O que você quer planejar?",
  },
  {
    id: "automatizar",
    title: "Automatizar",
    description: "Crie agentes e automatize fluxos",
    icon: Workflow,
    color: "text-violet-400",
    placeholder: "Qual tarefa você quer automatizar?",
  },
];
