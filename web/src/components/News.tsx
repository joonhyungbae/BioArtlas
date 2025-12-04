import { Database, Users, Presentation } from "lucide-react";

const News = () => {
  const newsItems = [
    {
      date: "December 4, 2025",
      icon: Presentation,
      title: "NeurIPS 2025 Presentation",
      description: "Successfully presented BioArtlas at NeurIPS 2025 Creative AI Track.",
    },
    {
      date: "August 31, 2025",
      icon: Users,
      title: "Expanded Research Collaboration",
      description: "Initiated interdisciplinary expansion with 2 curators, 1 artist, and 1 biotechnologist.",
    },
    {
      date: "August 12, 2025",
      icon: Database,
      title: "Dataset Release",
      description: "Released the complete BioArtlas dataset on GitHub with 81 works across 13 dimensions.",
    },
  ];

  return (
    <section className="py-section">
      <div className="content-width max-w-[800px]">
        <p className="section-label">News</p>
        
        <div className="space-y-3 md:space-y-4">
          {newsItems.map((item, index) => (
            <div 
              key={index}
              className="flex items-start gap-3 md:gap-4 p-4 md:p-6 bg-card border border-border rounded-lg"
            >
              <div className="flex-shrink-0 w-8 h-8 md:w-9 md:h-9 rounded-full bg-accent/10 flex items-center justify-center">
                <item.icon className="w-3.5 h-3.5 md:w-4 md:h-4 text-accent" />
              </div>
              <div className="flex-1 min-w-0">
                <span className="font-mono text-[10px] md:text-xs text-muted-foreground">
                  {item.date}
                </span>
                <h3 className="font-sans text-sm md:text-base font-medium text-foreground mt-0.5 md:mt-1">
                  {item.title}
                </h3>
                <p className="font-serif text-xs md:text-sm text-muted-foreground mt-1 leading-relaxed">
                  {item.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default News;
