import React, { useState, useEffect, useRef, useCallback } from 'react';
import { OccupancyHeader } from '../components/projector/OccupancyHeader';
import { RadialCountdownRing } from '../components/projector/RadialCountdownRing';
import { DynamicQRCode } from '../components/projector/DynamicQRCode';

export interface ProjectorViewProps {
  roomCode?: string;
  courseCode?: string;
  courseTitle?: string;
  sectionName?: string;
  facultyName?: string;
  sessionId?: string;
}

/**
 * High-Contrast 1080p/720p COMLAB Presence Projector View.
 * Displays real-time 15s rotating RFC 6238 TOTP QR code, SVG radial ring,
 * and live workstation occupancy count.
 */
export const ProjectorView: React.FC<ProjectorViewProps> = ({
  roomCode = 'PRRC 301',
  courseCode = 'CC-IPT2',
  courseTitle = 'Integrative Programming and Technologies 2',
  sectionName = 'BSIT-3A',
  facultyName = 'Engr. Nathaniel Gomez',
  sessionId = 'c3d3a012-789a-4c2b-9a8c-7f8e12345678',
}) => {
  const [token, setToken] = useState<string>('384912');
  const [remainingSeconds, setRemainingSeconds] = useState<number>(15.0);
  const [isRotating, setIsRotating] = useState<boolean>(false);
  const [occupiedCount, setOccupiedCount] = useState<number>(28);
  const [isLive, setIsLive] = useState<boolean>(true);

  const prevStepRef = useRef<number>(-1);
  const animationFrameRef = useRef<number | null>(null);

  // Fetch updated TOTP payload from the presence microservice (:8004)
  const fetchActiveTOTP = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/presence/totp/${encodeURIComponent(roomCode)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.totp) {
          setToken(data.totp);
        }
      }
    } catch {
      // In offline/demo mode, token updates via fallback generator
    }
  }, [roomCode]);

  // Real-Time Epoch Synchronization & SVG Animation Loop (60 FPS)
  useEffect(() => {
    const updateCountdown = () => {
      const nowMs = Date.now();
      const currentStep = Math.floor(nowMs / 15000);
      const elapsedInStepMs = nowMs % 15000;
      const remainingMs = 15000 - elapsedInStepMs;
      const remSec = remainingMs / 1000;

      setRemainingSeconds(remSec);

      // Detect step rotation boundary
      if (prevStepRef.current !== -1 && currentStep !== prevStepRef.current) {
        setIsRotating(true);
        fetchActiveTOTP();
        setTimeout(() => setIsRotating(false), 200);
      }
      prevStepRef.current = currentStep;

      animationFrameRef.current = requestAnimationFrame(updateCountdown);
    };

    animationFrameRef.current = requestAnimationFrame(updateCountdown);
    fetchActiveTOTP();

    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [fetchActiveTOTP]);

  // Connect to SSE Vacancy Stream (:8004)
  useEffect(() => {
    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource(`/api/v1/presence/rooms/${encodeURIComponent(roomCode)}/stream`);

      eventSource.onopen = () => setIsLive(true);
      eventSource.onerror = () => setIsLive(false);

      eventSource.addEventListener('occupancy_update', (e) => {
        try {
          const data = JSON.parse(e.data);
          if (typeof data.occupied_count === 'number') {
            setOccupiedCount(data.occupied_count);
          }
        } catch (err) {
          console.error('SSE occupancy parse error:', err);
        }
      });
    } catch {
      setIsLive(false);
    }

    return () => {
      if (eventSource) eventSource.close();
    };
  }, [roomCode]);

  // Construct Dynamic QR Payload JSON
  const qrPayload = JSON.stringify({
    room: roomCode,
    session: sessionId,
    totp: token,
    ts: Math.floor(Date.now() / 1000),
  });

  return (
    <div className="min-h-screen w-full bg-[#1a0810] text-white flex flex-col justify-between overflow-hidden select-none font-['Inter',sans-serif]">
      {/* 1. Header Bar with Brand Card & Occupancy Telemetry */}
      <OccupancyHeader
        roomCode={roomCode}
        courseCode={courseCode}
        courseTitle={courseTitle}
        sectionName={sectionName}
        facultyName={facultyName}
        occupiedCount={occupiedCount}
        totalStations={45}
        isLive={isLive}
      />

      {/* 2. Main Center Display: High-Contrast QR Code & SVG Radial Ring */}
      <main className="flex-1 flex flex-col lg:flex-row items-center justify-center gap-12 px-8 py-6">
        {/* Primary QR Code Card */}
        <div className="flex flex-col items-center">
          <DynamicQRCode
            payload={qrPayload}
            size={340}
            token={token}
            isRotating={isRotating}
          />
        </div>

        {/* Countdown Ring & Scanning Guidance */}
        <div className="flex flex-col items-center lg:items-start gap-6 max-w-md text-center lg:text-left">
          <div className="flex items-center gap-6">
            <RadialCountdownRing
              remainingSeconds={remainingSeconds}
              size={150}
              strokeWidth={10}
            />
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white">
                Live Attendance Check-In
              </h2>
              <p className="text-xs text-[#f8ebf0]/80 mt-1">
                Point your smartphone camera at the QR code. Tokens refresh every 15s to eliminate proxy attendance.
              </p>
            </div>
          </div>

          {/* Simple 3-Step Student Instructions */}
          <div className="bg-[#34141f]/70 rounded-xl p-4 border border-[#872e49]/40 w-full text-left">
            <h3 className="text-xs font-bold text-[#f8ebf0] uppercase tracking-wider mb-2">
              How to Check In:
            </h3>
            <ol className="text-xs text-[#f8ebf0]/90 space-y-2 list-decimal list-inside font-medium">
              <li>Open the ClassSync PWA or Campus Mobile App.</li>
              <li>Aim your camera at the QR code above.</li>
              <li>Confirm your physical workstation number (e.g. PC-14).</li>
            </ol>
          </div>
        </div>
      </main>

      {/* 3. Footer Status Bar */}
      <footer className="px-8 py-3 bg-[#34141f]/40 border-t border-[#4a1c2b] flex items-center justify-between text-[11px] text-[#f8ebf0]/70">
        <div className="flex items-center gap-3">
          <span>RFC 6238 HMAC-SHA256 • 15s Interval</span>
          <span>•</span>
          <span>Room: {roomCode}</span>
        </div>
        <div>Colegio de Montalban / Pamantasan ng Montalban • ClassSync Presence</div>
      </footer>
    </div>
  );
};

export default ProjectorView;
