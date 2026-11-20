import React from 'react';
import { NextClassHeroSkeleton } from './SkeletonCard';
import { Clock, MapPin, Monitor, ArrowRight, CheckCircle2 } from 'lucide-react';

export interface NextClassItem {
  courseCode: string;
  courseTitle: string;
  roomCode: string;
  buildingName: string;
  floor: number;
  roomType: 'LECTURE' | 'COMPUTER_LAB' | 'SCIENCE_LAB' | 'FUNCTION_HALL';
  startSlot: number;
  durationSlots: number;
  timeDisplay: string;
  countdownText: string;
  isInSession?: boolean;
}

export interface NextClassHeroProps {
  classItem?: NextClassItem | null;
  isLoading?: boolean;
  onClaimSeat?: (roomCode: string) => void;
  onViewDetails?: () => void;
}

/**
 * Hick's Law Next Class Hero Card.
 * Answers "Where is my next class right now?" at a single glance without menu digging.
 */
export const NextClassHero: React.FC<NextClassHeroProps> = ({
  classItem,
  isLoading = false,
  onClaimSeat,
  onViewDetails,
}) => {
  if (isLoading) {
    return <NextClassHeroSkeleton />;
  }

  if (!classItem) {
    return (
      <div className="w-full bg-white rounded-[16px] border border-[var(--line)] p-6 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-[var(--success-soft)] flex items-center justify-center text-[var(--success)]">
            <CheckCircle2 size={24} />
          </div>
          <div>
            <h3 className="text-lg font-bold text-[var(--ink)]">All Done for Today!</h3>
            <p className="text-sm text-[var(--ink-soft)]">
              No more scheduled classes today. Check your schedule tab for tomorrow's classes.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const isComlab = classItem.roomType === 'COMPUTER_LAB';

  return (
    <div className="relative overflow-hidden w-full bg-gradient-to-br from-white via-white to-[var(--brand-rose)]/40 rounded-[16px] border border-[var(--line)] p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-[var(--brand-rose)] text-[var(--brand-rouge)] uppercase tracking-wide">
            {classItem.isInSession ? 'Class In Session' : 'Up Next'}
          </span>
          <span className="text-xs text-[var(--ink-soft)] flex items-center gap-1">
            <Clock size={13} />
            {classItem.countdownText}
          </span>
        </div>

        {/* Room Code Badge */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[var(--brand-rouge)] text-white text-sm font-bold shadow-sm">
          <MapPin size={14} />
          <span>{classItem.roomCode}</span>
        </div>
      </div>

      {/* Subject and Details */}
      <div className="mb-4">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-[var(--brand-rouge)]">{classItem.courseCode}</span>
          <span className="text-xs text-[var(--ink-soft)]">
            {classItem.buildingName} • Floor {classItem.floor}
          </span>
        </div>
        <h2 className="text-xl sm:text-2xl font-bold text-[var(--ink)] tracking-tight line-clamp-1 mt-0.5">
          {classItem.courseTitle}
        </h2>
        <p className="text-sm text-[var(--ink-soft)] mt-1 flex items-center gap-1.5">
          <Clock size={14} className="text-[var(--ink-soft)]" />
          <span>{classItem.timeDisplay}</span>
          <span className="text-xs text-[var(--ink-soft)]">({classItem.durationSlots * 30} mins)</span>
        </p>
      </div>

      {/* Action Footer */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[var(--line)]/60">
        <div className="text-xs text-[var(--ink-soft)] flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Room verified & schedulable</span>
        </div>

        <div className="flex items-center gap-2">
          {isComlab && onClaimSeat && (
            <button
              onClick={() => onClaimSeat(classItem.roomCode)}
              className="tactile-button min-h-[48px] px-5 py-2.5 rounded-[10px] bg-[var(--brand-rouge)] hover:bg-[var(--primary-hover)] text-white font-semibold text-sm flex items-center gap-2 shadow-sm"
            >
              <Monitor size={16} />
              <span>Claim Seat in COMLAB</span>
            </button>
          )}

          {onViewDetails && (
            <button
              onClick={onViewDetails}
              className="tactile-button min-h-[48px] px-4 py-2.5 rounded-[10px] border border-[var(--control-border)] hover:bg-[var(--surface-strong)] text-[var(--ink)] font-medium text-sm flex items-center gap-1.5"
            >
              <span>Details</span>
              <ArrowRight size={15} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
