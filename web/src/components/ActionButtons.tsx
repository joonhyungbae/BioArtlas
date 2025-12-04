import { FileText, Database, ExternalLink, BookOpen } from "lucide-react";

const ActionButtons = () => {
  const buttons = [
    { label: "Paper", icon: FileText, href: "https://drive.google.com/file/d/1cOFNX9_fSElhr82nEqz4eceoduLoBPeF/view?usp=drive_link" },
    { label: "arXiv", icon: BookOpen, href: "https://arxiv.org/abs/2511.19162" },
    { label: "Dataset", icon: Database, href: "https://github.com/joonhyungbae/BioArtlas" },
    { label: "Interactive Atlas", icon: ExternalLink, href: "https://bioartlas.com", emphasis: true },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3 mt-8 sm:mt-10 max-w-2xl mx-auto">
      {buttons.map((button) => (
        <a
          key={button.label}
          href={button.href}
          target="_blank"
          rel="noopener noreferrer"
          className={`
            inline-flex items-center justify-center gap-2 px-4 py-3 sm:px-6 sm:py-4 rounded-lg
            border border-border bg-card
            font-sans text-sm sm:text-[15px] font-medium text-foreground
            transition-all duration-300 ease-out
            hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)] hover:border-muted-foreground/30 hover:-translate-y-0.5
            ${button.emphasis ? "bg-secondary border-muted-foreground/20" : ""}
          `}
        >
          <button.icon className="w-4 h-4 sm:w-[18px] sm:h-[18px]" strokeWidth={1.5} />
          <span className="whitespace-nowrap">{button.label}</span>
        </a>
      ))}
    </div>
  );
};

export default ActionButtons;
