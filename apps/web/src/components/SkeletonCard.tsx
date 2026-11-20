import React from 'react';

/**
 * Skeleton Loading Components (Decision Log D-11).
 * Mirrors exact card geometries with animate-pulse to prevent Cumulative Layout Shift (CLS).
 */

export const NextClassHeroSkeleton: React.FC = () => (
  <div className="w-full h-[184px] bg-white rounded-[16px] border border-[var(--line)] p-6 animate-pulse flex flex-col justify-between shadow-sm">
    <div className="flex items-center justify-between">
      <div className="h-6 w-48 bg-[var(--surface-strong)] rounded-md" />
      <div className="h-6 w-24 bg-[var(--surface-strong)] rounded-full" />
    </div>
    <div className="space-y-2.5">
      <div className="h-4 w-32 bg-[var(--surface-strong)] rounded-md" />
      <div className="h-4 w-72 bg-[var(--surface-strong)] rounded-md" />
    </div>
    <div className="flex items-center justify-between pt-2">
      <div className="h-4 w-28 bg-[var(--surface-strong)] rounded-md" />
      <div className="h-10 w-36 bg-[var(--surface-strong)] rounded-lg" />
    </div>
  </div>
);

export const TimetableSlotSkeleton: React.FC = () => (
  <div className="w-full h-[88px] bg-white rounded-[10px] border border-[var(--line)] p-4 animate-pulse flex items-center justify-between shadow-sm">
    <div className="space-y-2">
      <div className="h-5 w-32 bg-[var(--surface-strong)] rounded-md" />
      <div className="h-3.5 w-44 bg-[var(--surface-strong)] rounded-md" />
    </div>
    <div className="h-7 w-20 bg-[var(--surface-strong)] rounded-full" />
  </div>
);

export const WorkstationGridSkeleton: React.FC = () => (
  <div className="space-y-4">
    <div className="h-6 w-48 bg-[var(--surface-strong)] rounded-md animate-pulse" />
    <div className="grid grid-cols-5 sm:grid-cols-9 gap-2.5 p-5 bg-white rounded-[16px] border border-[var(--line)] animate-pulse shadow-sm">
      {Array.from({ length: 45 }).map((_, i) => (
        <div key={i} className="h-12 w-full bg-[var(--surface-strong)] rounded-[8px]" />
      ))}
    </div>
  </div>
);

export const FacultyScheduleSkeleton: React.FC = () => (
  <div className="w-full bg-white rounded-[16px] border border-[var(--line)] p-6 animate-pulse space-y-4 shadow-sm">
    <div className="h-7 w-56 bg-[var(--surface-strong)] rounded-md" />
    <div className="grid grid-cols-6 gap-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-48 bg-[var(--surface-strong)] rounded-[10px]" />
      ))}
    </div>
  </div>
);

export const RoomDirectorySkeleton: React.FC = () => (
  <div className="w-full bg-white rounded-[16px] border border-[var(--line)] p-6 animate-pulse space-y-4 shadow-sm">
    <div className="flex justify-between items-center">
      <div className="h-7 w-60 bg-[var(--surface-strong)] rounded-md" />
      <div className="h-8 w-40 bg-[var(--surface-strong)] rounded-md" />
    </div>
    <div className="space-y-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-12 w-full bg-[var(--surface-strong)] rounded-[8px]" />
      ))}
    </div>
  </div>
);
