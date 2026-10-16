import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SECTIONS, sectionBySlug } from "@/lib/sections";

export function generateStaticParams() {
  return SECTIONS.filter((s) => s.step).map((s) => ({ section: s.slug }));
}

export default async function SectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section: slug } = await params;
  const section = sectionBySlug(slug);
  if (!section?.step) notFound();
  const Icon = section.icon;
  return (
    <div className="grid h-full place-items-center p-6">
      <div className="vx-panel max-w-lg p-8 text-center">
        <span className="mx-auto grid size-16 place-items-center rounded-2xl border border-line-strong bg-elev">
          <Icon className="size-8 text-accent" />
        </span>
        <h1 className="mt-5 text-2xl font-semibold">{section.label}</h1>
        <p className="mt-2 text-muted">{section.description}</p>
        <p className="mt-4 inline-block rounded-lg bg-accent/15 px-3 py-1 text-sm text-accent">
          Chega na etapa {section.step} do roadmap
        </p>
        <div className="mt-6">
          <Link href="/" className="inline-flex items-center gap-2 rounded-xl border border-line px-4 py-2 text-sm hover:border-accent">
            <ArrowLeft className="size-4" /> Voltar ao chat
          </Link>
        </div>
      </div>
    </div>
  );
}
