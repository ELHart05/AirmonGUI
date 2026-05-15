import { LucideIcon } from 'lucide-react';

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  delay?: number;
}

const FeatureCard = ({ icon: Icon, title, description, delay = 0 }: FeatureCardProps) => {
  return (
    <div 
      className="group relative p-6 bg-card border border-border rounded-lg hover:border-primary/50 transition-all duration-500 hover:box-glow"
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Corner decorations */}
      <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-primary/50 rounded-tl" />
      <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-primary/50 rounded-tr" />
      <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-primary/50 rounded-bl" />
      <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-primary/50 rounded-br" />
      
      <div className="flex items-center gap-4 mb-4">
        <div className="p-3 bg-primary/10 rounded-lg group-hover:bg-primary/20 transition-colors">
          <Icon className="w-6 h-6 text-primary" />
        </div>
        <h3 className="font-mono text-lg text-foreground group-hover:text-primary transition-colors">
          {title}
        </h3>
      </div>
      
      <p className="text-muted-foreground text-sm leading-relaxed">
        {description}
      </p>
    </div>
  );
};

export default FeatureCard;
