import { Github, Database, ExternalLink } from "lucide-react";

const Footer = () => {
  return (
    <footer className="border-t border-border pt-20 pb-12">
      <div className="content-width text-center">
        <a
          href="mailto:jh.bae@kaist.ac.kr"
          className="font-sans text-sm academic-link"
        >
          jh.bae@kaist.ac.kr
        </a>
        <p className="font-sans text-sm text-muted-foreground mt-3">
          © 2025 Joonhyung Bae, KAIST
        </p>
        <div className="flex items-center justify-center gap-6 mt-6">
          <a href="https://github.com/joonhyungbae/BioArtlas" target="_blank" rel="noopener noreferrer" className="font-sans text-xs text-muted-foreground hover:text-accent transition-colors inline-flex items-center gap-1.5">
            <Github className="w-3.5 h-3.5" />
            GitHub
          </a>
          <a href="https://arxiv.org/abs/2511.19162" target="_blank" rel="noopener noreferrer" className="font-sans text-xs text-muted-foreground hover:text-accent transition-colors inline-flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5" />
            arXiv
          </a>
          <a href="https://bioartlas.com" target="_blank" rel="noopener noreferrer" className="font-sans text-xs text-muted-foreground hover:text-accent transition-colors inline-flex items-center gap-1.5">
            <ExternalLink className="w-3.5 h-3.5" />
            Interactive Demo
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
