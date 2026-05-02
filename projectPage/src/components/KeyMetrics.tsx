interface MetricCardProps {
  metric: string;
  label: string;
  description: string;
}

const MetricCard = ({ metric, label, description }: MetricCardProps) => (
  <div className="bg-card border border-border rounded-lg p-6 md:p-10 text-center flex flex-col h-full">
    <div className="flex-1 flex items-center justify-center min-h-[56px] md:min-h-[72px]">
      <span className="font-serif text-3xl sm:text-4xl md:text-5xl font-medium text-foreground tracking-tight tabular-nums">
        {metric}
      </span>
    </div>
    <div className="mt-3 md:mt-4">
      <div className="font-sans text-[10px] md:text-xs uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </div>
      <p className="font-sans text-xs md:text-sm text-muted-foreground mt-1.5 md:mt-2 min-h-[32px] md:min-h-[40px] flex items-center justify-center">
        {description}
      </p>
    </div>
  </div>
);

const KeyMetrics = () => {
  const metrics = [
    { metric: "81", label: "Bioart Works", description: "33 artists and collectives, 1976–2022" },
    { metric: "13", label: "Analytical Dimensions", description: "From materiality to power dynamics" },
    { metric: "0.664", label: "Silhouette Coefficient", description: "±0.008, 800+ configurations evaluated" },
    { metric: "0.81", label: "Trust. / Continuity", description: "Neighborhood preservation metrics" },
  ];

  return (
    <section className="py-section">
      <div className="content-width">
        <p className="section-label">Key Metrics</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {metrics.map((m) => (
            <MetricCard key={m.label} {...m} />
          ))}
        </div>
      </div>
    </section>
  );
};

export default KeyMetrics;
