import { Github, BookOpen, ExternalLink } from "lucide-react";
import { SITE_LINKS } from "@/lib/siteConfig";

const Footer = () => {
  return (
    <footer className="border-t border-border pt-20 pb-12">
      <div className="content-width text-center">
        <a
          href={SITE_LINKS.contact}
          className="font-sans text-sm academic-link"
        >
          jh.bae@kaist.ac.kr
        </a>
        <p className="font-sans text-sm text-muted-foreground mt-3">
          © 2025–2026 Joonhyung Bae, KAIST
        </p>
        <div className="flex items-center justify-center gap-6 mt-6">
          <a href={SITE_LINKS.repository} target="_blank" rel="noopener noreferrer" className="font-sans text-xs text-muted-foreground hover:text-accent transition-colors inline-flex items-center gap-1.5">
            <Github className="w-3.5 h-3.5" />
            Repository
          </a>
          <a href={SITE_LINKS.arxiv} target="_blank" rel="noopener noreferrer" className="font-sans text-xs text-muted-foreground hover:text-accent transition-colors inline-flex items-center gap-1.5">
            <BookOpen className="w-3.5 h-3.5" />
            arXiv
          </a>
          <a href={SITE_LINKS.interactiveAtlas} target="_blank" rel="noopener noreferrer" className="font-sans text-xs text-muted-foreground hover:text-accent transition-colors inline-flex items-center gap-1.5">
            <ExternalLink className="w-3.5 h-3.5" />
            Interactive Demo
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
