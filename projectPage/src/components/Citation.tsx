import { useState } from "react";
import { Copy, Check } from "lucide-react";

const Citation = () => {
  const [copied, setCopied] = useState(false);

  const bibtex = `@inproceedings{bae2025bioartlas,
  title     = {BioArtlas: Computational Clustering of 
               Multi-Dimensional Complexity in Bioart},
  author    = {Bae, Joonhyung},
  booktitle = {Proceedings of the 39th Conference on Neural
               Information Processing Systems},
  year      = {2025},
  note      = {Creative AI Track}
}`;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(bibtex);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="py-section">
      <div className="content-width max-w-[800px]">
        <p className="section-label">Citation</p>
        <div className="relative group">
          <pre className="code-block whitespace-pre-wrap text-xs md:text-sm pr-12">{bibtex}</pre>
          <button
            onClick={handleCopy}
            className="absolute top-3 right-3 md:top-4 md:right-4 p-2 rounded-md bg-card border border-border
                       opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity duration-200
                       hover:bg-secondary"
            aria-label="Copy citation"
          >
            {copied ? (
              <Check className="w-4 h-4 text-accent" />
            ) : (
              <Copy className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
        </div>
      </div>
    </section>
  );
};

export default Citation;
