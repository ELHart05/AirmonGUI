interface StepCardProps {
  step: number;
  title: string;
  description: string;
  command?: string;
}

const StepCard = ({ step, title, description, command }: StepCardProps) => {
  return (
    <div className="relative flex gap-6">
      {/* Step number */}
      <div className="flex-shrink-0 w-12 h-12 flex items-center justify-center bg-primary/10 border border-primary/50 rounded-lg text-primary font-mono text-xl font-bold">
        {step.toString().padStart(2, '0')}
      </div>
      
      {/* Content */}
      <div className="flex-1 pb-8">
        <h3 className="font-mono text-lg text-foreground mb-2">{title}</h3>
        <p className="text-muted-foreground text-sm mb-3">{description}</p>
        
        {command && (
          <div className="bg-muted/50 border border-border rounded-md p-3 font-mono text-sm">
            <span className="text-primary">$</span>{' '}
            <span className="text-secondary">{command}</span>
          </div>
        )}
      </div>
      
      {/* Connecting line */}
      <div className="absolute left-6 top-12 bottom-0 w-px bg-gradient-to-b from-primary/50 to-transparent" />
    </div>
  );
};

export default StepCard;
