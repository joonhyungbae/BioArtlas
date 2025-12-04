const DatasetStats = () => {
  const stats = [
    { label: "Works", value: "81" },
    { label: "Artists", value: "33" },
    { label: "Temporal Range", value: "1976–2022" },
    { label: "Unique Keywords", value: "770" },
    { label: "Keywords per Work", value: "28.2 (mean)" },
    { label: "Total Assignments", value: "2,285" },
    { label: "Analytical Axes", value: "13" },
  ];

  return (
    <section className="py-section bg-secondary/50">
      <div className="content-width max-w-[700px]">
        <p className="section-label">Dataset Composition</p>
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <tbody>
              {stats.map((stat, index) => (
                <tr
                  key={stat.label}
                  className={index % 2 === 1 ? "bg-secondary/50" : ""}
                >
                  <td className="px-4 md:px-6 py-3 md:py-4 font-sans text-xs md:text-sm text-muted-foreground">
                    {stat.label}
                  </td>
                  <td className="px-4 md:px-6 py-3 md:py-4 font-mono text-xs md:text-sm text-foreground text-right">
                    {stat.value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <a
          href="https://github.com/joonhyungbae/BioArtlas"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 font-sans text-sm academic-link mt-4"
        >
          Access full dataset on GitHub
          <span aria-hidden="true">→</span>
        </a>
      </div>
    </section>
  );
};

export default DatasetStats;
