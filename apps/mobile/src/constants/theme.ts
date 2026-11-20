/**
 * ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System
 * Mobile Design System Tokens (Soft Rouge & Cool Neutral)
 * Strictly enforces WCAG 2.2 AA (>=48px touch targets, >=4.5:1 text contrast)
 */

export const THEME = {
  colors: {
    // Brand Core
    brandMidnight: '#34141f',
    brandRouge: '#872e49',
    brandRose: '#f8ebf0',

    // Surfaces & Canvas
    canvas: '#f7f8fa',
    surface: '#ffffff',
    surfaceStrong: '#f0f1f4',
    line: '#e9e9ed',
    controlBorder: '#858997',

    // Typography & Ink
    ink: '#20242c',
    inkSoft: '#667085',
    textOnAction: '#ffffff',

    // Semantics
    success: '#059669',
    successBg: '#ecfdf5',
    warning: '#d97706',
    warningBg: '#fffbeb',
    error: '#dc2626',
    errorBg: '#fef2f2',
    accentBlue: '#2563eb',
    accentBlueBg: '#eff6ff',
  },

  // Dimensions & WCAG 2.2 Touch Targets
  layout: {
    minTouchTarget: 48, // strictly >= 48px
    bottomNavHeight: 72, // 72px thumb zone
    headerHeight: 64,
    cardRadius: 16,
    controlRadius: 10,
    buttonRadius: 10,
    scannerOverlayPadding: 24,
  },

  typography: {
    fontFamily: 'InterVariable, system-ui, -apple-system, sans-serif',
    hero: { fontSize: 28, lineHeight: 34, fontWeight: '800' as const },
    title: { fontSize: 20, lineHeight: 26, fontWeight: '700' as const },
    headline: { fontSize: 16, lineHeight: 22, fontWeight: '600' as const },
    body: { fontSize: 14, lineHeight: 20, fontWeight: '400' as const },
    caption: { fontSize: 12, lineHeight: 16, fontWeight: '500' as const },
    badge: { fontSize: 11, lineHeight: 14, fontWeight: '700' as const },
  },

  shadows: {
    sm: {
      shadowColor: '#34141f',
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.06,
      shadowRadius: 2,
      elevation: 2,
    },
    md: {
      shadowColor: '#34141f',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.08,
      shadowRadius: 6,
      elevation: 4,
    },
    scannerGlow: {
      shadowColor: '#872e49',
      shadowOffset: { width: 0, height: 0 },
      shadowOpacity: 0.35,
      shadowRadius: 12,
      elevation: 8,
    },
  },
} as const;

export default THEME;
