import { Github, Terminal, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useState } from 'react';

const installSteps = [
  {
    label: 'Clone',
    command: 'git clone https://github.com/ELHart05/AirmonGUI.git\ncd AirmonGUI',
  },
  {
    label: 'Backend (FastAPI)',
    command:
      'cd backend\npython3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt\nsudo .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --reload',
  },
  {
    label: 'Frontend (Vue 3 + Vite)',
    command: 'cd frontend\nnpm install\nnpm run dev',
  },
];

const DownloadSection = () => {
  const [copied, setCopied] = useState<string | null>(null);

  const copy = (label: string, command: string) => {
    navigator.clipboard.writeText(command);
    setCopied(label);
    setTimeout(() => setCopied(null), 1500);
  };

  return (
    <section id="download" className="py-24 relative">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-secondary/5 to-transparent" />

      <div className="container mx-auto px-4 relative z-10">
        <div className="max-w-3xl mx-auto text-center">
          <span className="font-mono text-sm text-accent mb-4 block">// GET STARTED</span>
          <h2 className="text-3xl md:text-4xl font-mono font-bold mb-4">
            <span className="text-foreground">Clone, Install,</span>{' '}
            <span className="text-accent">Run.</span>
          </h2>
          <p className="text-muted-foreground mb-12">
            AirmonGUI is open source. Spin up the FastAPI backend and the Vue frontend
            locally — everything stays on your machine.
          </p>

          {/* Install command blocks */}
          <div className="space-y-4 mb-12 text-left">
            {installSteps.map((step) => (
              <div
                key={step.label}
                className="bg-card border border-border rounded-xl overflow-hidden"
              >
                <div className="flex items-center justify-between px-4 py-2 bg-muted/40 border-b border-border">
                  <span className="font-mono text-xs text-primary">▸ {step.label}</span>
                  <button
                    onClick={() => copy(step.label, step.command)}
                    className="flex items-center gap-1 font-mono text-xs text-muted-foreground hover:text-primary transition-colors"
                  >
                    <Copy className="w-3 h-3" />
                    {copied === step.label ? 'copied' : 'copy'}
                  </button>
                </div>
                <pre className="p-4 font-mono text-xs text-foreground whitespace-pre overflow-x-auto">
                  {step.command}
                </pre>
              </div>
            ))}
          </div>

          {/* CTAs */}
          <div className="flex items-center justify-center">
            <a
              href="https://github.com/ELHart05/AirmonGUI"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="hero" size="xl" className="group">
                <Github className="w-5 h-5" />
                View on GitHub
              </Button>
            </a>
          </div>

          {/* Requirements */}
          <div className="mt-12 grid md:grid-cols-2 gap-4 text-left">
            <div className="p-6 bg-muted/30 border border-border rounded-xl">
              <h4 className="font-mono text-sm text-foreground mb-4 flex items-center gap-2">
                <Terminal className="w-4 h-4 text-primary" /> System
              </h4>
              <ul className="space-y-2 font-mono text-xs text-muted-foreground">
                <li><span className="text-primary">▸</span> Linux (kernel 4.x+, tested on Kali & Ubuntu 22.04)</li>
                <li><span className="text-primary">▸</span> Wireless adapter with monitor-mode support</li>
                <li><span className="text-primary">▸</span> aircrack-ng suite + wireless-tools on $PATH</li>
                <li><span className="text-primary">▸</span> Root privileges (raw socket access)</li>
              </ul>
            </div>
            <div className="p-6 bg-muted/30 border border-border rounded-xl">
              <h4 className="font-mono text-sm text-foreground mb-4 flex items-center gap-2">
                <Terminal className="w-4 h-4 text-secondary" /> Toolchain
              </h4>
              <ul className="space-y-2 font-mono text-xs text-muted-foreground">
                <li><span className="text-secondary">▸</span> Python 3.11+ and pip</li>
                <li><span className="text-secondary">▸</span> Node.js 18+ and npm 9+</li>
                <li><span className="text-secondary">▸</span> FastAPI 0.111 / Uvicorn / Pydantic v2</li>
                <li><span className="text-secondary">▸</span> Vue 3.4 / Vite 5 / Tailwind CSS 3</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default DownloadSection;
