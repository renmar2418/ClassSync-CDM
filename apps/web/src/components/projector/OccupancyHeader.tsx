import React from 'react';

export interface OccupancyHeaderProps {
  roomCode: string;
  courseCode: string;
  courseTitle: string;
  sectionName: string;
  facultyName: string;
  occupiedCount: number;
  totalStations?: number;
  isLive?: boolean;
}

/**
 * Projector View Header.
 * Displays CdM brand assets inside a neutral white card (strictly no CSS invert),
 * course/section information, and real-time workstation occupancy telemetry.
 */
export const OccupancyHeader: React.FC<OccupancyHeaderProps> = ({
  roomCode,
  courseCode,
  courseTitle,
  sectionName,
  facultyName,
  occupiedCount,
  totalStations = 45,
  isLive = true,
}) => {
  const percentage = Math.min(100, Math.round((occupiedCount / totalStations) * 100));

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 px-8 py-5 border-b border-[#34141f] bg-[#1a0810]/95 backdrop-blur-md">
      {/* Brand & Section Metadata */}
      <div className="flex items-center gap-5">
        {/* Neutral white card container — STRICT PROHIBITION of CSS filter: invert(1) */}
        <div className="bg-white rounded-[8px] p-2 flex items-center justify-center shadow-md">
          <img
            src="/branding/classsync-logo-assets/classsync-horizontal-light.png"
            alt="ClassSync Logo"
            className="h-7 w-auto max-w-[150px] object-contain"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
              const fb = e.currentTarget.parentElement?.querySelector('.brand-fallback');
              if (fb) (fb as HTMLElement).style.display = 'block';
            }}
          />
          <span className="brand-fallback hidden text-base font-bold text-[#872e49]">
            ClassSync
          </span>
        </div>

        <div>
          <div className="flex items-center gap-2.5">
            <span className="px-3 py-0.5 rounded-full text-xs font-bold bg-[#872e49] text-white tracking-wide shadow-sm">
              {sectionName}
            </span>
            <span className="text-lg font-bold text-white tracking-tight">
              {courseCode}: {courseTitle}
            </span>
          </div>
          <p className="text-xs text-[#f8ebf0]/80 mt-1 font-medium">
            Faculty: <span className="text-white font-semibold">{facultyName}</span> • Room:{' '}
            <span className="text-white font-semibold">{roomCode}</span>
          </p>
        </div>
      </div>

      {/* Real-Time Telemetry Counter */}
      <div className="flex items-center gap-6">
        <div className="text-right">
          <div className="text-[11px] text-[#f8ebf0]/70 uppercase tracking-widest font-bold">
            Workstation Occupancy
          </div>
          <div className="text-2xl font-black text-white tabular-nums flex items-center justify-end gap-2">
            <span className="text-emerald-400">{occupiedCount}</span>
            <span className="text-[#858997] text-lg font-normal">/ {totalStations}</span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#34141f] text-[#f8ebf0] border border-[#872e49]">
              {percentage}%
            </span>
          </div>
        </div>

        {/* Live SSE Status Pill */}
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#34141f] border border-[#872e49]/60 text-xs text-[#f8ebf0]">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              isLive ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
            }`}
          />
          <span className="font-semibold tracking-wide">
            {isLive ? 'Live SSE Stream' : 'Connecting...'}
          </span>
        </div>
      </div>
    </header>
  );
};

export default OccupancyHeader;
