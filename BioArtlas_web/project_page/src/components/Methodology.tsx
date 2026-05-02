const Methodology = () => {
  const stages = [
    {
      number: "01",
      title: "Data Collection & Annotation",
      details: [
        "81 works from major bioart institutions",
        "770 unique keywords across 13 axes",
        "Domain-informed codebook construction",
      ],
    },
    {
      number: "02",
      title: "Representation Learning",
      details: [
        "Dual embeddings: BGE-large + GTE-large (2048-dim)",
        "Per-axis aggregation with semantic preservation",
        "Automated codebook optimization (K=47)",
      ],
    },
    {
      number: "03",
      title: "Systematic Evaluation",
      details: [
        "800+ representation–space–algorithm combinations",
        "Multi-metric validation framework",
        "Optimal: Agglomerative k=15 on 4D UMAP",
      ],
    },
  ];

  return (
    <section className="py-section bg-secondary/50">
      <div className="content-width">
        <p className="section-label">Methodology</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-8">
          {stages.map((stage, index) => (
            <div key={stage.number} className="relative">
              <div className="bg-card border border-border rounded-lg p-5 md:p-8">
                <span className="font-mono text-[10px] md:text-xs text-muted-foreground">{stage.number}</span>
                <h3 className="font-sans font-medium text-base md:text-lg text-foreground mt-1.5 md:mt-2 mb-3 md:mb-4">
                  {stage.title}
                </h3>
                <ul className="space-y-1.5 md:space-y-2">
                  {stage.details.map((detail, i) => (
                    <li key={i} className="font-mono text-xs md:text-sm text-muted-foreground leading-relaxed">
                      {detail}
                    </li>
                  ))}
                </ul>
              </div>
              {index < stages.length - 1 && (
                <div className="hidden md:block absolute top-1/2 -right-4 w-8 h-px bg-border" />
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Methodology;
