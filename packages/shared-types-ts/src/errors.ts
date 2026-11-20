/**
 * Human-Centered Plain-Language Error Definitions & Translations
 * Official Project: ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System
 *
 * Strictly enforces Decision Log D-12:
 * Absolute ban on internal technical system jargon (e.g. "409 Conflict", "CP-SAT Infeasibility", "TOTP Desync").
 * Translates errors to empathetic, contextual recovery copy.
 */

export interface ClassSyncAppError {
  code: string;
  user_message: string;
  action_label?: string;
  technical_details?: string;
  suggested_alternative?: string;
}

export const ERROR_MESSAGES = {
  // Workstation Claiming & Presence
  WORKSTATION_ALREADY_CLAIMED: (claimedStation: number, suggestedStation?: number): string =>
    suggestedStation
      ? `Seat PC-${claimedStation} was just claimed by a classmate! PC-${suggestedStation} is open right next to it.`
      : `Seat PC-${claimedStation} was just claimed by a classmate! Please select another open seat.`,

  TOTP_EXPIRED:
    'The QR code just refreshed! Point your camera at the screen to scan the new code.',

  INVALID_STUDENT_ID:
    'Student IDs must look like 24-00123 (numbers only, no emails).',

  STUDENT_NOT_ENROLLED:
    'You are not enrolled in this scheduled section. Please check your assigned class schedule.',

  // Authentication & Zero-Trust Ingress
  INVALID_GOOGLE_DOMAIN_STUDENT:
    'Please select your official school Google account (@student.pnm.edu.ph) to sign in.',

  INVALID_GOOGLE_DOMAIN_FACULTY:
    'Please select your official school Google account (@pnm.edu.ph) to sign in.',

  TURNSTILE_CHALLENGE_FAILED:
    'Human verification check could not be completed. Please tap the verification checkbox and try again.',

  PASSWORD_WEAK_ASVS:
    'Your password needs to be at least 8 characters long and avoid common words like campus names or years.',

  PASSWORD_MISMATCH:
    'The passwords you entered do not match. Please re-enter them carefully.',

  INVALID_CREDENTIALS:
    'The email/ID or password you entered does not match our records. Please double-check and try again.',

  // Scheduling & Facility Quarantine
  ROOM_QUARANTINED: (roomCode: string): string =>
    `Room ${roomCode} is an administrative facility and cannot be booked for student classes.`,

  ROOM_PROGRAM_LOCKED: (roomCode: string, requiredProgram: string): string =>
    `Room ${roomCode} is reserved exclusively for ${requiredProgram} laboratory courses.`,

  EMERGENCY_ROOM_MOVED: (newRoomCode: string, reason = 'maintenance'): string =>
    `⚠️ Room Update: Your class moved to ${newRoomCode} due to ${reason}.`,

  // Offline & Network
  OFFLINE_MODE:
    '🟢 Offline Mode • Showing your saved schedule. Reconnecting to campus Wi-Fi...',

  NETWORK_TIMEOUT:
    'We could not reach the campus server. Please check your connection or wait a moment while we retry.',
} as const;

/**
 * Maps standard HTTP error statuses or backend exception strings
 * to empathetic user-facing plain language messages.
 */
export function translateErrorToPlainLanguage(
  statusOrCode: number | string,
  context?: {
    stationNumber?: number;
    suggestedStation?: number;
    roomCode?: string;
    program?: string;
  }
): ClassSyncAppError {
  if (statusOrCode === 409 || statusOrCode === 'WORKSTATION_CONFLICT') {
    const station = context?.stationNumber ?? 1;
    const suggested = context?.suggestedStation;
    return {
      code: 'WORKSTATION_CONFLICT',
      user_message: ERROR_MESSAGES.WORKSTATION_ALREADY_CLAIMED(station, suggested),
      action_label: suggested ? `Select PC-${suggested}` : 'Choose Another Seat',
    };
  }

  if (statusOrCode === 'TOTP_EXPIRED' || statusOrCode === 410) {
    return {
      code: 'TOTP_EXPIRED',
      user_message: ERROR_MESSAGES.TOTP_EXPIRED,
      action_label: 'Scan Again',
    };
  }

  if (statusOrCode === 'INVALID_STUDENT_ID' || statusOrCode === 422) {
    return {
      code: 'INVALID_STUDENT_ID',
      user_message: ERROR_MESSAGES.INVALID_STUDENT_ID,
      action_label: 'Correct ID',
    };
  }

  if (statusOrCode === 'INVALID_DOMAIN' || statusOrCode === 403) {
    return {
      code: 'INVALID_DOMAIN',
      user_message: ERROR_MESSAGES.INVALID_GOOGLE_DOMAIN_STUDENT,
      action_label: 'Switch Google Account',
    };
  }

  if (statusOrCode === 'TURNSTILE_FAILED' || statusOrCode === 400) {
    return {
      code: 'TURNSTILE_FAILED',
      user_message: ERROR_MESSAGES.TURNSTILE_CHALLENGE_FAILED,
      action_label: 'Retry Verification',
    };
  }

  return {
    code: 'GENERAL_ERROR',
    user_message: 'Something did not load as expected. Please refresh or try again in a moment.',
    action_label: 'Refresh',
  };
}
