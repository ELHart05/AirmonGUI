import { Wifi, Github, Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useState } from 'react';

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <a href="#" className="flex items-center gap-2 group">
            <div className="p-2 bg-primary/10 rounded-lg group-hover:bg-primary/20 transition-colors">
              <Wifi className="w-5 h-5 text-primary" />
            </div>
            <span className="font-mono text-lg font-semibold text-foreground">
              AirMon<span className="text-primary">GUI</span>
            </span>
          </a>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-muted-foreground hover:text-primary transition-colors font-mono text-sm">
              Features
            </a>
            <a href="#how-it-works" className="text-muted-foreground hover:text-primary transition-colors font-mono text-sm">
              How it Works
            </a>
            <a href="#download" className="text-muted-foreground hover:text-primary transition-colors font-mono text-sm">
              Download
            </a>
            <a href="https://github.com/ELHart05/AirmonGUI" target="_blank" rel="noopener noreferrer">
              <Button variant="outline" size="sm" className="gap-2">
                <Github className="w-4 h-4" />
                GitHub
              </Button>
            </a>
          </div>

          {/* Mobile Menu Button */}
          <button 
            className="md:hidden p-2 text-muted-foreground hover:text-primary"
            onClick={() => setIsOpen(!isOpen)}
          >
            {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isOpen && (
          <div className="md:hidden py-4 border-t border-border">
            <div className="flex flex-col gap-4">
              <a href="#features" className="text-muted-foreground hover:text-primary transition-colors font-mono text-sm">
                Features
              </a>
              <a href="#how-it-works" className="text-muted-foreground hover:text-primary transition-colors font-mono text-sm">
                How it Works
              </a>
              <a href="#download" className="text-muted-foreground hover:text-primary transition-colors font-mono text-sm">
                Download
              </a>
              <a href="https://github.com/ELHart05/AirmonGUI" target="_blank" rel="noopener noreferrer">
                <Button variant="outline" size="sm" className="gap-2 w-fit">
                  <Github className="w-4 h-4" />
                  GitHub
                </Button>
              </a>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
