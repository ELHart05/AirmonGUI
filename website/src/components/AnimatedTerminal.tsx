import { useEffect, useState } from 'react';

type Line =
  | { type: 'cmd'; text: string }
  | { type: 'out'; text: string; tone?: 'muted' | 'primary' | 'secondary' | 'accent' | 'destructive' };

const script: Line[] = [
  { type: 'cmd', text: 'git clone https://github.com/ELHart05/AirmonGUI.git' },
  { type: 'out', text: '✓ Cloned into AirmonGUI/', tone: 'primary' },
  { type: 'cmd', text: 'cd backend && pip install -r requirements.txt' },
  { type: 'out', text: '✓ FastAPI backend ready', tone: 'primary' },
  { type: 'cmd', text: 'cd ../frontend && npm install' },
  { type: 'out', text: '✓ Vue 3 frontend ready', tone: 'secondary' },
  { type: 'cmd', text: 'sudo uvicorn main:app & npm run dev' },
  { type: 'out', text: '→ http://localhost:5173  ·  AirmonGUI is live', tone: 'accent' },
];

const toneClass: Record<string, string> = {
  muted: 'text-muted-foreground',
  primary: 'text-primary',
  secondary: 'text-secondary',
  accent: 'text-accent',
  destructive: 'text-destructive',
};

const AnimatedTerminal = () => {
  const [step, setStep] = useState(0);
  const [showOutput, setShowOutput] = useState(false);
  const [typed, setTyped] = useState('');

  useEffect(() => {
    const command = script[step * 2];
    const output = script[step * 2 + 1];

    if (!command || command.type !== 'cmd') {
      return undefined;
    }

    let i = 0;
    setTyped('');
    setShowOutput(false);

    let reveal: ReturnType<typeof setTimeout> | undefined;
    let advance: ReturnType<typeof setTimeout> | undefined;

    const typing = setInterval(() => {
      i++;
      setTyped(command.text.slice(0, i));

      if (i >= command.text.length) {
        clearInterval(typing);
        reveal = setTimeout(() => {
          setShowOutput(true);
        }, 350);
        advance = setTimeout(() => {
          setStep((current) => (current + 1) % (script.length / 2));
        }, output ? 2450 : 1200);
      }
    }, 45);

    return () => {
      clearInterval(typing);
      if (reveal) clearTimeout(reveal);
      if (advance) clearTimeout(advance);
    };
  }, [step]);

  const command = script[step * 2];
  const output = script[step * 2 + 1];

  return (
    <div className="max-w-2xl mx-auto bg-card border border-border rounded-lg overflow-hidden shadow-2xl">
      {/* Title bar */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-muted/40 border-b border-border">
        <div className="w-3 h-3 rounded-full bg-destructive/80" />
        <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
        <div className="w-3 h-3 rounded-full bg-primary/80" />
        <span className="ml-3 font-mono text-xs text-muted-foreground">
          root@kali — airmon-gui
        </span>
      </div>

      {/* Body */}
      <div className="p-4 font-mono text-sm text-left space-y-1 min-h-[82px]">
        {command?.type === 'cmd' && (
          <div className="whitespace-nowrap overflow-hidden text-ellipsis">
            <span className="text-primary">root@kali:~#</span>{' '}
            <span className="text-foreground">{typed}</span>
            {!showOutput && (
              <span className="inline-block w-2 h-4 bg-primary align-middle ml-0.5 animate-pulse" />
            )}
          </div>
        )}

        {showOutput && output?.type === 'out' && (
          <div className="whitespace-nowrap overflow-hidden text-ellipsis">
            <span className={toneClass[output.tone ?? 'muted']}>{output.text}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnimatedTerminal;
