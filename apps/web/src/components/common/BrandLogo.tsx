import React, { useState } from 'react';

export interface BrandLogoProps {
  variant?: 'full' | 'horizontal' | 'ribbon';
  surface?: 'light' | 'dark';
  className?: string;
}

/**
 * Authoritative ClassSync Brand Logo Component.
 * Enforces Decision Log D-11 & DESIGN_SYSTEM.md:
 * On dark surfaces, wraps unmodified light logo in a neutral white card (bg-white rounded-[8px] p-2).
 * STRICT PROHIBITION of CSS filter: invert(1).
 */
export const BrandLogo: React.FC<BrandLogoProps> = ({
  variant = 'horizontal',
  surface = 'light',
  className = '',
}) => {
  const [hasError, setHasError] = useState(false);

  let assetPath = '/branding/classsync-logo-assets/classsync-horizontal-light.png';
  let defaultWidth = 'w-[180px]';

  if (variant === 'full') {
    assetPath = '/branding/classsync-logo-assets/classsync-full-light.png';
    defaultWidth = 'w-[240px]';
  } else if (variant === 'ribbon') {
    assetPath = '/branding/classsync-logo-assets/classsync-ribbon-mark.png';
    defaultWidth = 'w-[44px] h-[44px]';
  }

  const imageElement = !hasError ? (
    <img
      src={assetPath}
      alt="ClassSync Logo"
      className={`h-auto object-contain ${defaultWidth} ${className}`}
      onError={() => setHasError(true)}
    />
  ) : (
    <span className="brand-fallback font-bold text-[#872e49] text-base tracking-tight">
      ClassSync
    </span>
  );

  // If on a dark surface, wrap in neutral white surface card (STRICT NO INVERT)
  if (surface === 'dark') {
    return (
      <div className="bg-white rounded-[8px] p-2 flex items-center justify-center shadow-sm inline-flex">
        {imageElement}
      </div>
    );
  }

  return <div className="inline-flex items-center">{imageElement}</div>;
};
