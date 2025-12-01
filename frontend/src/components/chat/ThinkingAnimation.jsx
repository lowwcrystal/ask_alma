import React, { useState, useEffect } from 'react';

// Thinking animation frames (constant)
const THINKING_FRAMES = [
  '/thinking_frame_1.png',
  '/thinking_frame_2.png',
  '/thinking_frame_3.png'
];

/**
 * Animated thinking indicator component
 * Displays a rotating animation while the AI is processing
 */
const ThinkingAnimation = React.memo(function ThinkingAnimation() {
  const [currentFrame, setCurrentFrame] = useState(0);

  // Preload all frames for smooth animation
  useEffect(() => {
    THINKING_FRAMES.forEach(frame => {
      const img = new Image();
      img.src = frame;
    });
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentFrame((prev) => (prev + 1) % THINKING_FRAMES.length);
    }, 500); // Change frame every 500ms

    return () => clearInterval(interval);
  }, []);

  return (
    <img 
      src={THINKING_FRAMES[currentFrame]} 
      alt="Thinking" 
      className="w-12 h-12 object-contain"
      loading="eager"
      decoding="async"
    />
  );
});

export default ThinkingAnimation;

