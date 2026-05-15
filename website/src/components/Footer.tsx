import { Wifi, Github } from 'lucide-react';

const Footer = () => {
  return (
    <footer className="py-12 border-t border-border">
      <div className="container mx-auto px-4">
        <div className="grid md:grid-cols-4 gap-8 mb-8">
          {/* Brand */}
          <div className="md:col-span-2">
            <a href="#" className="flex items-center gap-2 mb-4">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Wifi className="w-5 h-5 text-primary" />
              </div>
              <span className="font-mono text-lg font-semibold text-foreground">
                AirMon<span className="text-primary">GUI</span>
              </span>
            </a>
            <p className="text-sm text-muted-foreground max-w-sm">
              Open source graphical interface for airmon-ng. 
              Built by security researchers, for security researchers.
            </p>
          </div>

          {/* Links */}
          <div>
            <h4 className="font-mono text-sm text-foreground mb-4">Resources</h4>
            <ul className="space-y-2">
              <li>
                <a href="#" className="text-sm text-muted-foreground hover:text-primary transition-colors">
                  Contributing
                </a>
              </li>
              <li>
                <a href="#" className="text-sm text-muted-foreground hover:text-primary transition-colors">
                  License
                </a>
              </li>
            </ul>
          </div>

          {/* Community */}
          <div>
            <h4 className="font-mono text-sm text-foreground mb-4">Community</h4>
            <div className="flex gap-4">
              <a
                href="https://github.com/ELHart05/AirmonGUI"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 bg-muted rounded-lg hover:bg-primary/10 hover:text-primary transition-colors"
              >
                <Github className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>

        {/* Bottom */}
        <div className="pt-8 border-t border-border flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="font-mono text-xs text-muted-foreground">
            © 2024 AirMonGUI. Released under GPL-3.0 License.
          </p>
          <p className="font-mono text-xs text-muted-foreground">
            For educational and authorized testing only.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
