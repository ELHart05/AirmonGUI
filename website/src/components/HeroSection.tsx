import { ArrowRight, Terminal, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import AnimatedTerminal from './AnimatedTerminal';

const HeroSection = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center pb-16 pt-20 overflow-hidden scanlines">
      {/* Background effects */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/5 rounded-full blur-3xl" />
      
      {/* Grid pattern */}
      <div 
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage: `linear-gradient(hsl(var(--primary) / 0.1) 1px, transparent 1px),
                           linear-gradient(90deg, hsl(var(--primary) / 0.1) 1px, transparent 1px)`,
          backgroundSize: '50px 50px'
        }}
      />

      <div className="container mx-auto px-4 relative z-10">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 border border-primary/30 rounded-full mb-8">
            <Shield className="w-4 h-4 text-primary" />
            <span className="font-mono text-sm text-primary">Open Source Security Tool</span>
          </div>

          {/* Main heading */}
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-mono font-bold mb-6 leading-tight">
            <span className="text-foreground">Wireless</span>{' '}
            <span className="text-primary text-glow">Security</span>
            <br />
            <span className="text-foreground">Made</span>{' '}
            <span className="text-secondary text-glow-secondary">Visual</span>
          </h1>

          {/* Animated terminal session */}
          <div className="mb-8">
            <AnimatedTerminal />
          </div>

          {/* Description */}
          <p className="text-lg md:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
            A modern graphical interface for airmon-ng. Monitor mode, packet capture,
            and network analysis — all without touching the command line.
          </p>

          {/* CTA Buttons */}
          <div className="flex items-center justify-center">
            <a
              href="https://github.com/ELHart05/AirmonGUI"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="hero" size="xl" className="group">
                <Terminal className="w-5 h-5" />
                View on GitHub
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Button>
            </a>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 mt-16 max-w-lg mx-auto">
            <div className="text-center">
              <div className="font-mono text-3xl font-bold text-primary text-glow">100%</div>
              <div className="text-sm text-muted-foreground mt-1">Open Source</div>
            </div>
            <div className="text-center">
              <div className="font-mono text-3xl font-bold text-secondary text-glow-secondary">Local</div>
              <div className="text-sm text-muted-foreground mt-1">Runs Offline</div>
            </div>
            <div className="text-center">
              <div className="font-mono text-3xl font-bold text-accent">0</div>
              <div className="text-sm text-muted-foreground mt-1">Telemetry</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
