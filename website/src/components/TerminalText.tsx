import { useEffect, useState } from 'react';

interface TerminalTextProps {
  text: string;
  speed?: number;
  className?: string;
}

const TerminalText = ({ text, speed = 50, className = '' }: TerminalTextProps) => {
  const [displayText, setDisplayText] = useState('');
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    let index = 0;
    const interval = setInterval(() => {
      if (index < text.length) {
        setDisplayText(text.slice(0, index + 1));
        index++;
      } else {
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed]);

  useEffect(() => {
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);

    return () => clearInterval(cursorInterval);
  }, []);

  return (
    <span className={className}>
      {displayText}
      <span className={`${showCursor ? 'opacity-100' : 'opacity-0'} text-primary`}>█</span>
    </span>
  );
};

export default TerminalText;
