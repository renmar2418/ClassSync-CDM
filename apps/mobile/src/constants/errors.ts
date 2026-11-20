/**
 * ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System
 * Mobile Human-Centered Plain-Language Error Definitions & Translations
 * Strictly enforces Decision Log D-12:
 * Absolute ban on internal technical system jargon (e.g. "409 Conflict", "CP-SAT Infeasibility", "TOTP Desync").
 */

export interface MobileAppError {
  code: string;
  user_message: string;
  action_label?: string;
  suggested_alternative?: string;
}

export const ERROR_MESSAGES = {
  // Presence & Scanner
  WORKSTATION_ALREADY_CLAIMED: (claimedStation: number, suggestedStation?: number): string =>
    suggestedStation
      ? `Seat PC-${claimedStation} was just claimed by a classmate! PC-${suggestedStation} is open right next to it.`
      : `Seat PC-${claimedStation} was just claimed by a classmate! Please select another open seat.`,

  TOTP_EXPIRED:
    'The QR code just refreshed! Point your camera at the screen to scan the new code.',

  INVALID_QR_FORMAT:
    'This QR code is not recognized by ClassSync. Please point your camera at the active classroom projector.',

  INVALID_STUDENT_ID:
    'Student IDs must look like 24-00123 (numbers only, no emails).',

  STUDENT_NOT_ENROLLED:
    'You are not enrolled in this scheduled section. Please check your assigned class schedule.',

  // Authentication & Ingress
  INVALID_GOOGLE_DOMAIN_STUDENT:
    'Please select your official school Google account (@student.pnm.edu.ph) to sign in.',

  INVALID_CREDENTIALS:
    'The student ID or password you entered does not match our records. Please double-check and try again.',

  CAMERA_PERMISSION_DENIED:
    'Camera access is needed to scan classroom attendance QR codes. Please enable camera permissions in settings.',

  // Scheduling & Spatial Constraints
  ROOM_QUARANTINED: (roomCode: string): string =>
    `Room ${roomCode} is an administrative facility and cannot be booked for student classes.`,

  EMERGENCY_ROOM_MOVED: (newRoomCode: string, reason = 'maintenance'): string =>
    `⚠️ Room Update: Your class moved to ${newRoomCode} due to ${reason}.`,

  // Network & Offline Mode
  OFFLINE_MODE:
    '🟢 Offline Mode • Showing your saved schedule. Reconnecting to campus Wi-Fi...',

  NETWORK_TIMEOUT:
    'We could not reach the campus server. Please check your connection or wait a moment while we retry.',
} as const;

/**
 * Translates raw backend status codes or error messages into empathetic Decision Log D-12 copy.
 */
export function translateErrorMessage(rawError: string | number, context?: { claimedStation?: number; suggestedStation?: number; roomCode?: string }): string {
  if (typeof rawError === 'number') {
    if (rawError === 409) {
      return ERROR_MESSAGES.WORKSTATION_ALREADY_CLAIMED(
        context?.claimedStation ?? 1,
        context?.suggestedStation ?? (context?.claimedStation ? context.claimedStation + 1 : 2)
      );
    }
    if (rawError === 401 || rawError === 403) {
      return ERROR_MESSAGES.STUDENT_NOT_ENROLLED;
    }
    if (rawError === 410) {
      return ERROR_MESSAGES.TOTP_EXPIRED;
    }
    if (rawError >= 500) {
      return ERROR_MESSAGES.NETWORK_TIMEOUT;
    }
  }

  const str = String(rawError).toLowerCase();
  if (str.includes('409') || str.includes('conflict') || str.includes('claimed')) {
    return ERROR_MESSAGES.WORKSTATION_ALREADY_CLAIMED(
      context?.claimedStation ?? 1,
      context?.suggestedStation ?? 2
    );
  }
  if (str.includes('totp') || str.includes('expired') || str.includes('refresh') || str.includes('410')) {
    return ERROR_MESSAGES.TOTP_EXPIRED;
  }
  if (str.includes('not enrolled') || str.includes('unauthorized') || str.includes('forbidden')) {
    return ERROR_MESSAGES.STUDENT_NOT_ENROLLED;
  }
  if (str.includes('quarantine')) {
    return ERROR_MESSAGES.ROOM_QUARANTINED(context?.roomCode || 'this room');
  }
  if (str.includes('network') || str.includes('failed to fetch') || str.includes('timeout')) {
    return ERROR_MESSAGES.NETWORK_TIMEOUT;
  }

  return rawError.toString();
}

export default ERROR_MESSAGES;
