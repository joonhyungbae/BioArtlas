import { PROJECT_STATS, SITE_LINKS } from "@/lib/siteConfig";

const DatasetStats = () => {
  const stats = [
    { label: "Works", value: PROJECT_STATS.works },
    { label: "Artists", value: PROJECT_STATS.artists },
    { label: "Temporal Range", value: PROJECT_STATS.temporalRange },
    { label: "Unique Keywords", value: PROJECT_STATS.uniqueKeywords },
    { label: "Keywords per Work", value: PROJECT_STATS.keywordsPerWork },
    { label: "Total Assignments", value: PROJECT_STATS.totalAssignments },
    { label: "Analytical Axes", value: PROJECT_STATS.analyticalAxes },
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
          href={SITE_LINKS.dataFolder}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 font-sans text-sm academic-link mt-4"
        >
          Browse released dataset and metadata
          <span aria-hidden="true">→</span>
        </a>
      </div>
    </section>
  );
};

export default DatasetStats;
