import StepCard from './StepCard';

const steps = [
  {
    step: 1,
    title: 'Clone the Repository',
    description: 'Grab the source from GitHub. AirmonGUI is fully open source — no accounts, no telemetry.',
    command: 'git clone https://github.com/ELHart05/AirmonGUI.git',
  },
  {
    step: 2,
    title: 'Set Up the Backend',
    description: 'Create a Python venv and install the FastAPI backend dependencies. Requires Python 3.11+.',
    command: 'cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt',
  },
  {
    step: 3,
    title: 'Set Up the Frontend',
    description: 'Install the Vue 3 + Vite frontend dependencies. Requires Node.js 18+ and npm 9+.',
    command: 'cd frontend && npm install',
  },
  {
    step: 4,
    title: 'Run Both Services',
    description: 'Start the FastAPI backend as root (raw sockets) and the Vite dev server, then open http://localhost:5173.',
    command: 'sudo .venv/bin/uvicorn main:app --port 8000  &  npm run dev',
  },
];

const HowItWorksSection = () => {
  return (
    <section id="how-it-works" className="py-24 relative">
      <div className="container mx-auto px-4">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left side - Steps */}
          <div>
            <span className="font-mono text-sm text-secondary mb-4 block">// HOW IT WORKS</span>
            <h2 className="text-3xl md:text-4xl font-mono font-bold mb-8">
              <span className="text-foreground">Get Started in</span>{' '}
              <span className="text-secondary text-glow-secondary">Minutes</span>
            </h2>
            
            <div className="space-y-2">
              {steps.map((step) => (
                <StepCard
                  key={step.step}
                  step={step.step}
                  title={step.title}
                  description={step.description}
                  command={step.command}
                />
              ))}
            </div>
          </div>

          {/* Right side - Preview */}
          <div className="relative">
            {/* Glow effect */}
            <div className="absolute inset-0 bg-primary/20 rounded-2xl blur-3xl -z-10" />
            
            {/* Mock window */}
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              {/* Window header */}
              <div className="flex items-center gap-2 px-4 py-3 bg-muted/50 border-b border-border">
                <div className="w-3 h-3 rounded-full bg-destructive/80" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <div className="w-3 h-3 rounded-full bg-primary/80" />
                <span className="ml-4 font-mono text-xs text-muted-foreground">AirMonGUI v2.4</span>
              </div>
              
              {/* Window content */}
              <div className="p-6 space-y-4">
                {/* Adapter status */}
                <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-primary animate-pulse" />
                    <span className="font-mono text-sm">wlan0mon</span>
                  </div>
                  <span className="font-mono text-xs text-primary">MONITOR MODE</span>
                </div>
                
                {/* Network list */}
                <div className="space-y-2">
                  {[
                    { ssid: 'CoffeeShop_5G', signal: 85, channel: 36 },
                    { ssid: 'HomeNetwork', signal: 72, channel: 6 },
                    { ssid: 'Guest_WiFi', signal: 45, channel: 11 },
                  ].map((network) => (
                    <div key={network.ssid} className="flex items-center justify-between p-3 bg-muted/20 rounded-lg border border-border/50 hover:border-primary/30 transition-colors cursor-pointer">
                      <div>
                        <div className="font-mono text-sm text-foreground">{network.ssid}</div>
                        <div className="font-mono text-xs text-muted-foreground">CH {network.channel}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-primary to-secondary rounded-full"
                            style={{ width: `${network.signal}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs text-muted-foreground w-8">{network.signal}%</span>
                      </div>
                    </div>
                  ))}
                </div>
                
                {/* Stats bar */}
                <div className="flex justify-between pt-4 border-t border-border">
                  <div className="font-mono text-xs text-muted-foreground">
                    Networks: <span className="text-primary">47</span>
                  </div>
                  <div className="font-mono text-xs text-muted-foreground">
                    Clients: <span className="text-secondary">128</span>
                  </div>
                  <div className="font-mono text-xs text-muted-foreground">
                    Packets: <span className="text-accent">12.4k</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HowItWorksSection;
