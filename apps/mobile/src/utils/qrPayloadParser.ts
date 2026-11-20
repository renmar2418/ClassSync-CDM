/**
 * ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System
 * Dynamic 15s Rotating TOTP QR Payload Decoder
 *
 * Decodes and validates the presence QR payload projected on the classroom screen.
 * Payload contract: { room: string, session: string, totp: string, ts: number }
 */

export interface QRPresencePayload {
  room: string;
  session: string;
  totp: string;
  ts: number;
  workstation_id?: number;
}

export interface QRPayloadParseResult {
  success: boolean;
  payload?: QRPresencePayload;
  error?: string;
  isExpired?: boolean;
}

/**
 * Parses raw QR scan string and verifies structure and freshness.
 * Standard rotation window is 15 seconds, with a ±1-step (30s total) clock drift allowance.
 */
export function parseQRPresencePayload(
  rawScanData: string,
  currentTimeMs: number = Date.now(),
  maxClockDriftSeconds: number = 30
): QRPayloadParseResult {
  if (!rawScanData || typeof rawScanData !== 'string') {
    return {
      success: false,
      error: 'Empty or invalid QR scan data received.',
    };
  }

  let parsed: any;
  try {
    // 1. Attempt JSON decoding
    parsed = JSON.parse(rawScanData.trim());
  } catch {
    // 2. Fallback: URI query format (classync://presence?room=...&session=...&totp=...&ts=...)
    try {
      const url = new URL(rawScanData);
      const params = url.searchParams;
      parsed = {
        room: params.get('room') || '',
        session: params.get('session') || '',
        totp: params.get('totp') || '',
        ts: Number(params.get('ts') || 0),
        workstation_id: params.has('workstation_id')
          ? Number(params.get('workstation_id'))
          : undefined,
      };
    } catch {
      return {
        success: false,
        error: 'This QR code is not recognized by ClassSync. Please scan the official classroom projector.',
      };
    }
  }

  // Validate required fields
  if (!parsed || typeof parsed !== 'object') {
    return {
      success: false,
      error: 'Invalid QR payload format.',
    };
  }

  const room = typeof parsed.room === 'string' ? parsed.room.trim() : '';
  const session = typeof parsed.session === 'string' ? parsed.session.trim() : '';
  const totp = typeof parsed.totp === 'string' || typeof parsed.totp === 'number'
    ? String(parsed.totp).trim()
    : '';
  const ts = typeof parsed.ts === 'number' ? parsed.ts : Number(parsed.ts);

  if (!room) {
    return {
      success: false,
      error: 'Classroom code missing from QR payload.',
    };
  }

  if (!session) {
    return {
      success: false,
      error: 'Academic session token missing from QR payload.',
    };
  }

  // TOTP must be 6 digits
  if (totp.length !== 6 || isNaN(Number(totp))) {
    return {
      success: false,
      error: 'Invalid attendance token code in QR payload.',
    };
  }

  // Check freshness (ts in milliseconds or seconds)
  const normalizedTsMs = ts < 10000000000 ? ts * 1000 : ts;
  const ageSeconds = Math.abs(currentTimeMs - normalizedTsMs) / 1000;

  if (ageSeconds > maxClockDriftSeconds) {
    return {
      success: false,
      isExpired: true,
      error: 'The QR code just refreshed! Point your camera at the screen to scan the new code.',
      payload: {
        room,
        session,
        totp,
        ts,
        workstation_id: parsed.workstation_id,
      },
    };
  }

  return {
    success: true,
    payload: {
      room,
      session,
      totp,
      ts,
      workstation_id: parsed.workstation_id,
    },
  };
}

export default parseQRPresencePayload;
