import React, { useState, useEffect } from 'react';

interface TypewriterProps {
  text: string;
  speed?: number; // ms per character typing
  pauseDuration?: number; // ms to pause when complete
  className?: string;
  cursorClassName?: string;
}

export const TypewriterHeroSubtitle: React.FC<TypewriterProps> = ({
  text,
  speed = 36,
  pauseDuration = 7000, // hold for 7 seconds so users can read
  className = '',
  cursorClassName = '',
}) => {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    // Respect prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      setDisplayedText(text);
      return;
    }

    let currentIndex = 0;
    let timeoutId: ReturnType<typeof setTimeout>;

    const typeNextChar = () => {
      if (currentIndex < text.length) {
        currentIndex++;
        setDisplayedText(text.slice(0, currentIndex));
        timeoutId = setTimeout(typeNextChar, speed);
      } else {
        // Pause at completion, then loop gently
        timeoutId = setTimeout(() => {
          currentIndex = 0;
          setDisplayedText('');
          typeNextChar();
        }, pauseDuration);
      }
    };

    // Initial slight delay so it syncs with page load
    timeoutId = setTimeout(typeNextChar, 300);

    return () => clearTimeout(timeoutId);
  }, [text, speed, pauseDuration]);

  return (
    <span className={`inline-block font-medium tracking-wide ${className}`}>
      {displayedText}
      <span
        className={`inline-block w-[3px] h-[1.15em] ml-1 align-middle bg-yellow-400 rounded-sm animate-pulse ${cursorClassName}`}
        aria-hidden="true"
      />
    </span>
  );
};

export default TypewriterHeroSubtitle;
