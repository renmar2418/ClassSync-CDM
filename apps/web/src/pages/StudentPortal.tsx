import React, { useState } from 'react';
import { NextClassHero, NextClassItem } from '../components/NextClassHero';
import {
  Calendar,
  Clock,
  MapPin,
  Monitor,
  CheckCircle,
  AlertTriangle,
  X,
  Sparkles,
} from 'lucide-react';

export interface TimetableEntryItem {
  id: string;
  courseCode: string;
  courseTitle: string;
  roomCode: string;
  roomType: 'LECTURE' | 'COMPUTER_LAB' | 'SCIENCE_LAB' | 'FUNCTION_HALL';
  dayOfWeek: number; // 0=Mon ... 5=Sat
  startSlot: number; // 0..23 (07:00 = slot 0, 19:00 = slot 23)
  durationSlots: number;
  facultyName: string;
  sectionCode: string;
}

/**
 * Format slot 0..23 into 12-hour continuous time string (e.g., slot 0 -> 07:00 AM)
 */
export function formatSlotTime(slot: number): string {
  const totalMinutes = 7 * 60 + slot * 30;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours > 12 ? hours - 12 : hours === 0 ? 12 : hours;
  const displayMinutes = minutes < 10 ? `0${minutes}` : minutes;
  return `${displayHours}:${displayMinutes} ${period}`;
}

export const StudentPortal: React.FC = () => {
  const [selectedDay, setSelectedDay] = useState<number>(0); // 0=Mon, 1=Tue, ..., 5=Sat
  const [comlabOccupancy, setComlabOccupancy] = useState<number>(28);
  const [claimModalOpen, setClaimModalOpen] = useState<boolean>(false);
  const [targetRoom, setTargetRoom] = useState<string>('PRRC 301');
  const [selectedWorkstation, setSelectedWorkstation] = useState<number>(14);
  const [totpCode, setTotpCode] = useState<string>('');
  const [claimStatus, setClaimStatus] = useState<'idle' | 'success' | 'conflict' | 'submitting'>('idle');
  const [conflictMessage, setConflictMessage] = useState<string>('');
  const [recommendedStation, setRecommendedStation] = useState<number>(15);

  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  // Sample verified student timetable entries (Mon-Sat 07:00-19:00, 30-min continuous slots 0-23)
  const sampleEntries: TimetableEntryItem[] = [
    {
      id: 'entry-1',
      courseCode: 'CC-IPT2',
      courseTitle: 'Integrative Programming & Technologies 2',
      roomCode: 'PRRC 301',
      roomType: 'COMPUTER_LAB',
      dayOfWeek: 0, // Monday
      startSlot: 2, // 08:00 AM
      durationSlots: 6, // 3 hours (08:00 AM - 11:00 AM)
      facultyName: 'Engr. Nathaniel Gomez',
      sectionCode: 'BSIT-3A',
    },
    {
      id: 'entry-2',
      courseCode: 'IT-NET2',
      courseTitle: 'Advanced Networking & Routing',
      roomCode: 'PRRC 201',
      roomType: 'LECTURE',
      dayOfWeek: 0, // Monday
      startSlot: 10, // 12:00 PM
      durationSlots: 6, // 3 hours (12:00 PM - 03:00 PM)
      facultyName: 'Prof. Maria Santos',
      sectionCode: 'BSIT-3A',
    },
    {
      id: 'entry-3',
      courseCode: 'IT-SEC1',
      courseTitle: 'Information Assurance & Security',
      roomCode: 'PRRC 302',
      roomType: 'COMPUTER_LAB',
      dayOfWeek: 2, // Wednesday
      startSlot: 6, // 10:00 AM
      durationSlots: 6, // 3 hours (10:00 AM - 01:00 PM)
      facultyName: 'Engr. Nathaniel Gomez',
      sectionCode: 'BSIT-3A',
    },
    {
      id: 'entry-4',
      courseCode: 'GE-ETHICS',
      courseTitle: 'Ethics & Professionalism',
      roomCode: 'PRRC 104',
      roomType: 'LECTURE',
      dayOfWeek: 4, // Friday
      startSlot: 2, // 08:00 AM
      durationSlots: 6, // 3 hours (08:00 AM - 11:00 AM)
      facultyName: 'Prof. Ronald Diaz',
      sectionCode: 'BSIT-3A',
    },
  ];

  // Up Next / Hero item definition
  const heroItem: NextClassItem = {
    courseCode: 'CC-IPT2',
    courseTitle: 'Integrative Programming and Technologies 2',
    roomCode: 'PRRC 301',
    buildingName: 'PRRC Building',
    floor: 3,
    roomType: 'COMPUTER_LAB',
    startSlot: 2,
    durationSlots: 6,
    timeDisplay: `${formatSlotTime(2)} – ${formatSlotTime(8)}`,
    countdownText: 'Starts in 18 minutes',
    isInSession: false,
  };

  const dayEntries = sampleEntries.filter((e) => e.dayOfWeek === selectedDay);

  // Trigger claim modal
  const handleOpenClaim = (roomCode: string) => {
    setTargetRoom(roomCode);
    setClaimStatus('idle');
    setClaimModalOpen(true);
  };

  // Submit seat claim
  const handleClaimSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setClaimStatus('submitting');

    setTimeout(() => {
      // Simulate D-12 conflict for PC-14 if chosen to verify empathetic resolution
      if (selectedWorkstation === 14) {
        setClaimStatus('conflict');
        setConflictMessage('Seat PC-14 was just claimed by a classmate! PC-15 is open right next to it.');
        setRecommendedStation(15);
      } else {
        setClaimStatus('success');
        setComlabOccupancy((prev) => Math.min(45, prev + 1));
      }
    }, 600);
  };

  return (
    <div className="space-y-6">
      {/* 1. Next Class Hero Card (Hick's Law: single glance answer) */}
      <section aria-label="Next Class Overview">
        <NextClassHero
          classItem={heroItem}
          onClaimSeat={(room) => handleOpenClaim(room)}
          onViewDetails={() => setSelectedDay(0)}
        />
      </section>

      {/* 2. COMLAB Telemetry Bar (45 Stations) */}
      <section className="bg-white rounded-[16px] border border-[var(--line)] p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[var(--brand-rose)] text-[var(--brand-rouge)] flex items-center justify-center">
            <Monitor size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-[var(--ink)]">COMLAB 1 (PRRC 301)</span>
              <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
                LIVE
              </span>
            </div>
            <div className="text-xs text-[var(--ink-soft)] mt-0.5">
              Workstation occupancy: {comlabOccupancy} of 45 stations claimed ({45 - comlabOccupancy} vacant)
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => handleOpenClaim('PRRC 301')}
            className="tactile-button min-h-[48px] px-5 py-2.5 rounded-[10px] bg-[var(--brand-rouge)] hover:bg-[var(--primary-hover)] text-white text-sm font-semibold flex items-center gap-2"
          >
            <Sparkles size={16} />
            <span>Claim Workstation</span>
          </button>
        </div>
      </section>

      {/* 3. Day-Chunked Timetable (Miller's Law Mon-Sat 07:00-19:00 continuous 30-min slots 0-23) */}
      <section className="bg-white rounded-[16px] border border-[var(--line)] p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h3 className="text-lg font-bold text-[var(--ink)]">Weekly Class Schedule</h3>
            <p className="text-xs text-[var(--ink-soft)]">
              Continuous 30-minute intervals (Slots 0–23 • Mon–Sat 07:00–19:00)
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-semibold text-[var(--ink-soft)]">
            <Calendar size={15} />
            <span>BSIT-3A Cohort Schedule</span>
          </div>
        </div>

        {/* Day Tabs (Miller's Law: chunking into 6 distinct days) */}
        <div className="flex overflow-x-auto pb-2 gap-2 border-b border-[var(--line)]">
          {days.map((dayName, idx) => {
            const isSelected = selectedDay === idx;
            return (
              <button
                key={dayName}
                onClick={() => setSelectedDay(idx)}
                className={`tactile-button min-h-[48px] px-4 py-2 rounded-[10px] text-xs sm:text-sm font-bold whitespace-nowrap transition-colors ${
                  isSelected
                    ? 'bg-[var(--brand-rouge)] text-white shadow-sm'
                    : 'bg-[var(--surface-strong)] text-[var(--ink-soft)] hover:text-[var(--ink)]'
                }`}
              >
                {dayName}
              </button>
            );
          })}
        </div>

        {/* Timetable Entries List */}
        <div className="mt-6 space-y-3">
          {dayEntries.length === 0 ? (
            <div className="py-12 text-center text-sm text-[var(--ink-soft)]">
              No classes scheduled for {days[selectedDay]}. Enjoy your study time!
            </div>
          ) : (
            dayEntries.map((entry) => {
              const startStr = formatSlotTime(entry.startSlot);
              const endStr = formatSlotTime(entry.startSlot + entry.durationSlots);
              const isLab = entry.roomType === 'COMPUTER_LAB';

              return (
                <div
                  key={entry.id}
                  className={`p-4 rounded-[12px] border transition-all flex flex-wrap items-center justify-between gap-4 ${
                    isLab
                      ? 'bg-[var(--brand-rose)]/25 border-[var(--brand-rouge)]/30 hover:border-[var(--brand-rouge)]'
                      : 'bg-white border-[var(--line)] hover:border-[var(--control-border)]'
                  }`}
                >
                  <div className="space-y-1">
                    {/* Miller's Law 3 chunked items: [Subject Code], [Room Code], [Time Window] */}
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-bold px-2 py-0.5 rounded bg-[var(--brand-rose)] text-[var(--brand-rouge)]">
                        {entry.courseCode}
                      </span>
                      <span className="text-xs font-bold px-2 py-0.5 rounded bg-[var(--surface-strong)] text-[var(--ink)] flex items-center gap-1">
                        <MapPin size={12} />
                        {entry.roomCode}
                      </span>
                      <span className="text-xs text-[var(--ink-soft)] flex items-center gap-1">
                        <Clock size={12} />
                        {startStr} – {endStr} ({entry.durationSlots * 30} mins)
                      </span>
                    </div>

                    <h4 className="text-base font-bold text-[var(--ink)] mt-1">
                      {entry.courseTitle}
                    </h4>

                    <div className="text-xs text-[var(--ink-soft)]">
                      Faculty: {entry.facultyName} • Section: {entry.sectionCode}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {isLab && (
                      <button
                        onClick={() => handleOpenClaim(entry.roomCode)}
                        className="tactile-button min-h-[48px] px-4 py-2 rounded-[8px] bg-[var(--brand-rouge)] text-white text-xs font-bold flex items-center gap-1.5"
                      >
                        <Monitor size={14} />
                        <span>Seat Claim</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* 4. COMLAB Seat Claim Modal with Decision Log D-12 Empathetic Conflict Handling */}
      {claimModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white w-full max-w-md rounded-[16px] shadow-2xl border border-[var(--line)] p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[var(--line)] pb-3">
              <div className="flex items-center gap-2">
                <Monitor className="text-[var(--brand-rouge)]" size={20} />
                <h3 className="text-base font-bold text-[var(--ink)]">Claim Seat in {targetRoom}</h3>
              </div>
              <button
                onClick={() => setClaimModalOpen(false)}
                className="min-h-[48px] min-w-[48px] flex items-center justify-center text-[var(--ink-soft)]"
                aria-label="Close Dialog"
              >
                <X size={20} />
              </button>
            </div>

            {claimStatus === 'success' ? (
              <div className="py-6 text-center space-y-3">
                <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-700 mx-auto flex items-center justify-center">
                  <CheckCircle size={32} />
                </div>
                <h4 className="text-lg font-bold text-[var(--ink)]">Seat PC-{selectedWorkstation} Confirmed!</h4>
                <p className="text-xs text-[var(--ink-soft)] max-w-xs mx-auto">
                  Your seat check-in for {targetRoom} is recorded in the presence ledger. Have a great session!
                </p>
                <button
                  onClick={() => setClaimModalOpen(false)}
                  className="tactile-button min-h-[48px] w-full mt-4 rounded-[10px] bg-[var(--brand-rouge)] text-white font-bold text-sm"
                >
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleClaimSubmit} className="space-y-4">
                {/* Decision Log D-12 Empathetic Error Card on Conflict */}
                {claimStatus === 'conflict' && (
                  <div className="p-3.5 rounded-[10px] bg-[var(--warning-soft)] border border-[var(--warning-border)] space-y-2">
                    <div className="flex items-start gap-2 text-xs font-medium text-[var(--warning)]">
                      <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
                      <span>{conflictMessage}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedWorkstation(recommendedStation);
                        setClaimStatus('idle');
                      }}
                      className="tactile-button min-h-[48px] w-full rounded-[8px] bg-[var(--warning)] text-white text-xs font-bold flex items-center justify-center gap-1.5"
                    >
                      <span>Select PC-{recommendedStation}</span>
                    </button>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-bold text-[var(--ink)] mb-1">
                    Select Workstation (1–45)
                  </label>
                  <select
                    value={selectedWorkstation}
                    onChange={(e) => {
                      setSelectedWorkstation(parseInt(e.target.value, 10));
                      setClaimStatus('idle');
                    }}
                    className="w-full min-h-[48px] px-3.5 rounded-[10px] border border-[var(--control-border)] bg-white text-sm text-[var(--ink)]"
                  >
                    {Array.from({ length: 45 }).map((_, i) => (
                      <option key={i + 1} value={i + 1}>
                        Workstation PC-{i + 1}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[var(--ink)] mb-1">
                    Enter 6-Digit Screen Code
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={6}
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value)}
                    placeholder="e.g. 384912"
                    className="w-full min-h-[48px] px-3.5 rounded-[10px] border border-[var(--control-border)] bg-white text-center font-mono text-lg tracking-widest text-[var(--ink)]"
                  />
                  <p className="text-[11px] text-[var(--ink-soft)] mt-1">
                    Enter the code projected on the classroom screen. Refreshes every 15s.
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={claimStatus === 'submitting'}
                  className="tactile-button min-h-[48px] w-full rounded-[10px] bg-[var(--brand-rouge)] hover:bg-[var(--primary-hover)] text-white font-bold text-sm shadow-sm flex items-center justify-center"
                >
                  {claimStatus === 'submitting' ? 'Verifying with Classroom Server...' : 'Confirm Seat Check-In'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
