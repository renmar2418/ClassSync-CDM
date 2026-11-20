/**
 * ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System
 * Deterministic Zero-Regex Student ID Validator
 *
 * Requirements:
 * 1. Exact 8 characters in length.
 * 2. Prefix '24-'.
 * 3. 5 ASCII digit characters '0' through '9' following the hyphen.
 * 4. STRICTLY ZERO regex imports, zero RegExp construction, and zero regex methods (test/match/search/replace)
 *    to prevent ReDoS vulnerabilities under Zero-Trust Institutional Ingress.
 */

export interface StudentIdValidationResult {
  isValid: boolean;
  error?: string;
  normalizedId?: string;
}

/**
 * Validates student ID format deterministically without using any regular expressions.
 * Acceptable format: "24-XXXXX" where X is a digit '0'-'9'.
 */
export function validateStudentIDDeterministic(rawId: unknown): StudentIdValidationResult {
  if (typeof rawId !== 'string') {
    return {
      isValid: false,
      error: 'Student ID must be a text string.',
    };
  }

  const trimmed = rawId.trim();

  // Rule 1: Exact length must be 8
  if (trimmed.length !== 8) {
    return {
      isValid: false,
      error: 'Student ID must be exactly 8 characters long (format: 24-XXXXX).',
    };
  }

  // Rule 2: Prefix must be '24-'
  if (trimmed.charAt(0) !== '2' || trimmed.charAt(1) !== '4' || trimmed.charAt(2) !== '-') {
    return {
      isValid: false,
      error: "Student ID must begin with the university cohort prefix '24-'.",
    };
  }

  // Rule 3: Remaining 5 characters must each be ASCII digits '0'..'9'
  for (let i = 3; i < 8; i++) {
    const ch = trimmed.charAt(i);
    if (ch < '0' || ch > '9') {
      return {
        isValid: false,
        error: `Character '${ch}' at position ${i + 1} is not a valid digit. Must be 0-9.`,
      };
    }
  }

  return {
    isValid: true,
    normalizedId: trimmed,
  };
}

/**
 * Boolean helper for quick gating.
 */
export function isStudentIDValid(rawId: unknown): boolean {
  return validateStudentIDDeterministic(rawId).isValid;
}

export default validateStudentIDDeterministic;
