import {
  Wifi,
  Radar,
  Radio,
  KeyRound,
  Cpu,
  FolderArchive,
  Save,
  ShieldCheck,
} from 'lucide-react';
import FeatureCard from './FeatureCard';

const features = [
  {
    icon: Wifi,
    title: 'Monitor Mode Control',
    description: 'Enable or disable monitor mode on a selected interface. Interfering processes are killed only for that adapter, leaving your other connections intact.',
  },
  {
    icon: Radar,
    title: 'Live Network Scanning',
    description: 'Launch airodump-ng capture jobs and watch discovered access points and clients populate a live-updating table in real time.',
  },
  {
    icon: Radio,
    title: 'Targeted Deauth',
    description: 'Send targeted or broadcast deauthentication frames against a specific BSSID, with automatic channel tuning so frames reach the target.',
  },
  {
    icon: KeyRound,
    title: 'Handshake Capture',
    description: 'Guided workflow combining airodump-ng and aireplay-ng. Auto-deauth triggers and handshake detection are built right in.',
  },
  {
    icon: Cpu,
    title: 'Password Cracking',
    description: 'Submit captured handshakes to aircrack-ng with a wordlist, stream live progress logs, and stop jobs whenever you want.',
  },
  {
    icon: FolderArchive,
    title: 'Capture Management',
    description: 'Browse, download, and delete .cap and .csv files stored in the server-side capture directory — no shell required.',
  },
  {
    icon: Save,
    title: 'Session Persistence',
    description: 'Interface selection and target context (BSSID, channel) are saved to localStorage and restored on every reload.',
  },
  {
    icon: ShieldCheck,
    title: 'Localhost Only',
    description: 'Backend and frontend bind to loopback by default. Your auditing workflow stays on your machine — no external calls.',
  },
];

const FeaturesSection = () => {
  return (
    <section id="features" className="py-24 relative">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/5 to-transparent" />

      <div className="container mx-auto px-4 relative z-10">
        <div className="text-center mb-16">
          <span className="font-mono text-sm text-primary mb-4 block">// FEATURES</span>
          <h2 className="text-3xl md:text-4xl font-mono font-bold mb-4">
            <span className="text-foreground">The Full</span>{' '}
            <span className="text-primary text-glow">Aircrack-ng Suite</span>
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Every workflow you'd run from the terminal — wrapped in a clean local web UI.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, index) => (
            <FeatureCard
              key={feature.title}
              icon={feature.icon}
              title={feature.title}
              description={feature.description}
              delay={index * 100}
            />
          ))}
        </div>
      </div>
    </section>
  );
};

export default FeaturesSection;
