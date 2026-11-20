import React, { useMemo } from 'react';

export interface RadialCountdownRingProps {
  /** Seconds remaining in the current 15s window (0.0 to 15.0). */
  remainingSeconds: number;
  /** Full interval duration in seconds (default 15). */
  interval?: number;
  /** Diameter of the SVG ring in pixels (default 140). */
  size?: number;
  /** Stroke width in pixels (default 8). */
  strokeWidth?: number;
  /** Custom CSS classes for container. */
  className?: string;
}

/**
 * SVG Radial Countdown Ring.
 * Smoothly animates a depleting circular stroke over 15 seconds.
 * Color shifts dynamically from Brand Rouge (#872e49) -> Amber Rose -> Danger Alert Rose.
 * Complies with D-10 motion standards and dark surface aesthetics.
 */
export const RadialCountdownRing: React.FC<RadialCountdownRingProps> = ({
  remainingSeconds,
  interval = 15,
  size = 140,
  strokeWidth = 8,
  className = '',
}) => {
  const center = size / 2;
  const radius = center - strokeWidth;
  const circumference = 2 * Math.PI * radius;

  // Clamped fraction remaining: 1.0 (full) down to 0.0 (empty)
  const fraction = Math.max(0, Math.min(1, remainingSeconds / interval));
  const strokeDashoffset = circumference * (1 - fraction);

  // Discrete numerical label: 15s, 14s, ..., 1s
  const displaySeconds = Math.max(1, Math.ceil(remainingSeconds));

  // Dynamic color transition based on urgency:
  // >5s: Brand Rouge (#872e49)
  // 2s-5s: Warm Rose / Amber Alert (#e11d48)
  // <2s: High-Alert Red Rose (#ef4444)
  const strokeColor = useMemo(() => {
    if (remainingSeconds > 5) return '#872e49';
    if (remainingSeconds > 2) return '#e11d48';
    return '#ef4444';
  }, [remainingSeconds]);

  return (
    <div
      className={`relative inline-flex items-center justify-center select-none ${className}`}
      style={{ width: size, height: size }}
      aria-label={`TOTP timer: ${displaySeconds} seconds remaining until refresh`}
      role="timer"
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="transform -rotate-90"
      >
        {/* Background track circle */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="#34141f"
          strokeWidth={strokeWidth}
          className="opacity-50"
        />

        {/* Foreground animated countdown ring */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          style={{
            transition: 'stroke-dashoffset 100ms linear, stroke 250ms ease',
          }}
        />
      </svg>

      {/* Numerical countdown label & descriptor */}
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span
          className="text-3xl font-extrabold tracking-tight text-white tabular-nums drop-shadow-sm"
          style={{ color: strokeColor }}
        >
          {displaySeconds}s
        </span>
        <span className="text-[10px] uppercase font-bold tracking-widest text-[#f8ebf0]/70">
          Refresh
        </span>
      </div>
    </div>
  );
};

export default RadialCountdownRing;
