import { useEffect, useRef } from 'react';
import SimpleParallax from 'simple-parallax-js';

/**
 * ParallaxImage - Wrapper component for applying parallax effect to images
 * 
 * @param {string} src - Image source URL
 * @param {string} alt - Alt text for accessibility
 * @param {string} className - Additional CSS classes
 * @param {number} scale - Scale factor (1.1 - 1.5 recommended)
 * @param {string} orientation - 'up', 'down', 'left', 'right'
 * @param {boolean} overflow - Allow overflow of image
 * @param {number} delay - Delay for the parallax effect
 * @param {string} transition - CSS transition value
 */
const ParallaxImage = ({
  src,
  alt = '',
  className = '',
  scale = 1.2,
  orientation = 'up',
  overflow = false,
  delay = 0.4,
  transition = 'cubic-bezier(0,0,0,1)',
  ...props
}) => {
  const imageRef = useRef(null);
  const parallaxInstance = useRef(null);

  useEffect(() => {
    if (imageRef.current && !parallaxInstance.current) {
      parallaxInstance.current = new SimpleParallax(imageRef.current, {
        scale,
        orientation,
        overflow,
        delay,
        transition
      });
    }

    return () => {
      if (parallaxInstance.current) {
        parallaxInstance.current.destroy();
        parallaxInstance.current = null;
      }
    };
  }, [scale, orientation, overflow, delay, transition]);

  return (
    <img
      ref={imageRef}
      src={src}
      alt={alt}
      className={className}
      loading="lazy"
      {...props}
    />
  );
};

/**
 * ParallaxContainer - Apply parallax effect to any element
 * 
 * @param {ReactNode} children - Child elements to apply parallax to
 * @param {number} scale - Scale factor
 * @param {string} orientation - Direction of parallax
 */
const ParallaxContainer = ({
  children,
  scale = 1.15,
  orientation = 'up',
  overflow = true,
  delay = 0.3,
  className = ''
}) => {
  const containerRef = useRef(null);
  const parallaxInstance = useRef(null);

  useEffect(() => {
    // Find the first image child to apply parallax
    if (containerRef.current) {
      const images = containerRef.current.querySelectorAll('img');
      if (images.length > 0 && !parallaxInstance.current) {
        parallaxInstance.current = new SimpleParallax(images, {
          scale,
          orientation,
          overflow,
          delay,
          transition: 'cubic-bezier(0,0,0,1)'
        });
      }
    }

    return () => {
      if (parallaxInstance.current) {
        parallaxInstance.current.destroy();
        parallaxInstance.current = null;
      }
    };
  }, [scale, orientation, overflow, delay]);

  return (
    <div ref={containerRef} className={className}>
      {children}
    </div>
  );
};

export { ParallaxImage, ParallaxContainer };
export default ParallaxImage;
