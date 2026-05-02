const Findings = () => {
  const findings = [
    {
      numeral: "I",
      title: "Artist-Specific Methodological Cohesion",
      description:
        "Stelarc's four works (1976–2006) demonstrate persistent focus on cyborg embodiment and posthuman performance, clustering together despite three-decade span.",
    },
    {
      numeral: "II",
      title: "Technique-Based Segmentation",
      description:
        "Tissue culture artworks distribute across two proximate regions with substantial neighborhood overlap, indicating related but distinguishable technical foci.",
    },
    {
      numeral: "III",
      title: "Temporal Artistic Evolution",
      description:
        "Individual artists' works occupy distinct neighborhoods across clusters, revealing methodological diversification over time (e.g., Joe Davis, Eduardo Kac).",
    },
    {
      numeral: "IV",
      title: "Trans-Temporal Conceptual Affinities",
      description:
        "Conceptual similarity transcends chronology: Joe Davis's Poetica Vaginal (1986) and Jenna Sutela's nimiia cétiï (2018) show high mutual k-NN membership despite 32-year gap.",
    },
  ];

  return (
    <section className="py-section">
      <div className="content-width max-w-[900px]">
        <p className="section-label">Principal Findings</p>
        <div className="space-y-8 md:space-y-10">
          {findings.map((finding) => (
            <div key={finding.numeral} className="flex gap-3 md:gap-6">
              <span className="font-serif text-xl md:text-2xl text-muted-foreground shrink-0 w-6 md:w-8">
                {finding.numeral}.
              </span>
              <div>
                <h3 className="font-sans font-medium text-lg md:text-xl text-foreground mb-2">
                  {finding.title}
                </h3>
                <p className="font-serif text-sm md:text-body text-foreground leading-[1.7]">
                  {finding.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Findings;
