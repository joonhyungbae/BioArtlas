import ActionButtons from "@/components/ActionButtons";
import KeyMetrics from "@/components/KeyMetrics";
import Methodology from "@/components/Methodology";
import Findings from "@/components/Findings";
import DatasetStats from "@/components/DatasetStats";
import News from "@/components/News";
import Citation from "@/components/Citation";
import Footer from "@/components/Footer";
import heroVisualization from "@/assets/bioartlas-visualization.png";

const Index = () => {
  return (
    <main className="min-h-screen bg-background">
      {/* Header Section */}
      <header className="pt-12 pb-10 md:pt-20 md:pb-16">
        <div className="content-width text-center">
          <h1 className="font-serif text-4xl sm:text-5xl md:text-display text-navy-900 mb-3 md:mb-4 animate-fade-in">
            BioArtlas
          </h1>
          <p 
            className="font-sans text-lg sm:text-xl md:text-2xl text-slate-600 max-w-3xl mx-auto tracking-[-0.02em] animate-fade-in px-2"
            style={{ animationDelay: "0.1s" }}
          >
            Computational Clustering of Multi-Dimensional Complexity in Bioart
          </p>
          
          {/* Conference Badge */}
          <div 
            className="mt-5 md:mt-6 animate-fade-in"
            style={{ animationDelay: "0.2s" }}
          >
            <span className="inline-block px-3 py-1 md:px-4 md:py-1.5 border border-border rounded-full font-sans text-xs md:text-sm text-muted-foreground">
              NeurIPS 2025 • Creative AI Track
            </span>
          </div>

          {/* Author Info */}
          <div 
            className="mt-6 md:mt-8 animate-fade-in"
            style={{ animationDelay: "0.3s" }}
          >
            <p className="font-sans text-sm md:text-base text-foreground">Joonhyung Bae</p>
            <p className="font-sans text-xs md:text-sm text-muted-foreground mt-1">
              Graduate School of Culture Technology, KAIST
            </p>
          </div>

          {/* Action Buttons */}
          <div className="animate-fade-in" style={{ animationDelay: "0.4s" }}>
            <ActionButtons />
          </div>
        </div>
      </header>

      {/* Hero Visualization */}
      <section className="pb-section">
        <div className="content-width max-w-[1400px]">
          <figure className="bg-card border border-border rounded-lg overflow-hidden shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
            <img
              src={heroVisualization}
              alt="Interactive UMAP visualization showing 81 bioart works clustered across 13 analytical dimensions, with nodes representing individual artworks connected by semantic similarity"
              className="w-full h-auto aspect-[16/9] object-cover"
            />
          </figure>
          <figcaption className="text-center mt-4 font-serif text-sm italic text-muted-foreground">
            Figure 1: BioArtlas interactive visualization interface.{" "}
            <a 
              href="https://www.bioartlas.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="academic-link not-italic"
            >
              https://www.bioartlas.com
            </a>
          </figcaption>
        </div>
      </section>

      {/* Abstract */}
      <section className="py-section">
        <div className="content-width max-w-[800px]">
          <p className="section-label">Abstract</p>
          <div className="space-y-6 font-serif text-body-large text-foreground leading-[1.75]">
            <p>
              Bioart represents a convergence of artistic practice, biological science, and technological 
              innovation—encompassing transgenic organisms, tissue engineering, and biosemiotic inquiry. 
              Traditional taxonomic frameworks prove insufficient for capturing this multidimensional 
              complexity, as works simultaneously function as aesthetic objects, scientific instruments, 
              ethical provocations, and political statements.
            </p>
            <p>
              We present BioArtlas, a computational framework analyzing 81 significant bioart works across 
              thirteen curated analytical dimensions—materiality, methodology, actor relations, ethical 
              approaches, aesthetic strategies, epistemic functions, philosophical stances, social contexts, 
              audience engagement, temporal and spatial scales, power dynamics, and documentation practices. 
              Our axis-aware representation preserves semantic distinctions while enabling cross-dimensional 
              comparison through systematic evaluation of over 800 representation–space–algorithm combinations.
            </p>
            <p>
              The optimal configuration—Agglomerative clustering (k=15) on 4D UMAP—achieves a silhouette 
              coefficient of 0.664±0.008 with high neighborhood preservation (trustworthiness/continuity ≈0.81). 
              Analysis reveals four organizational patterns: artist-specific methodological cohesion, 
              technique-based segmentation, temporal artistic evolution, and trans-temporal conceptual 
              affinities. We provide both rigorous computational analysis and accessible exploration through 
              an interactive web interface.
            </p>
          </div>
        </div>
      </section>

      {/* News */}
      <News />

      {/* Key Metrics */}
      <KeyMetrics />

      {/* Methodology */}
      <Methodology />

      {/* Findings */}
      <Findings />

      {/* Dataset Stats */}
      <DatasetStats />

      {/* Citation */}
      <Citation />

      {/* Footer */}
      <Footer />
    </main>
  );
};

export default Index;
