# ClassSync V2 — Brand Identity, Design Tokens & Typography System

This document specifies the authoritative visual identity, asset catalog, color token hierarchy, and typography guidelines for ClassSync V2 (Web SPA and Mobile applications).

---

## 1. Brand Logo Assets & Placement Directory

All official raster derivatives are located in `apps/web/public/branding/classsync-logo-assets/` and `apps/web/public/branding/`.

```
apps/web/public/
├── branding/
│   ├── cdm-seal.png                              # Official Colegio de Montalban Seal (400x400)
│   └── classsync-logo-assets/
│       ├── classsync-full-light.png              # Full Lockup with Tagline (1100x310)
│       ├── classsync-horizontal-light.png        # Horizontal Wordmark Lockup (1100x295)
│       ├── classsync-ribbon-mark.png             # Transparent Ribbon Symbol (1024x1024)
│       ├── classsync-icon-32.png                 # Browser Favicon (32x32)
│       ├── classsync-icon-48.png                 # Browser High-DPI Favicon (48x48)
│       ├── classsync-icon-192.png                # PWA / Mobile Touch Icon (192x192)
│       └── classsync-icon-512.png                # App Store / Splash Screen Icon (512x512)
└── fonts/
    ├── InterVariable.woff2                       # Self-hosted variable font (100–900 weight)
    └── Inter-LICENSE.txt                         # SIL Open Font License
```

### Visual Placement & Responsive Sizing Rules

| Component / Placement | Target Asset | Dimensions | Display Rules |
|---|---|---|---|
| **Desktop Welcome ($\ge 1280\text{px}$)** | `classsync-full-light.png` | `1100×310` | Render at `480px` max-width. Contains embedded tagline; do not add redundant subtitle text. |
| **Tablet & Compact Welcome ($< 1280\text{px}$)** | `classsync-horizontal-light.png` | `1100×295` | Render at `220px` to `320px` width. |
| **Desktop Navigation Sidebar** | `classsync-horizontal-light.png` | `1100×295` | Render at `200px` max-width inside the `256px` sidebar track. |
| **Mobile Workspace Header** | `classsync-horizontal-light.png` | `1100×295` | Render at `144px` max-width within the `64px` top header bar. |
| **Compact Symbol / Avatars** | `classsync-ribbon-mark.png` | `1024×1024` | Render at `32px`, `44px`, or `96px` with square aspect ratio. |
| **Institutional Trust / Footer** | `cdm-seal.png` | `400×400` | Render at `48px` to `64px` alongside official university accreditation text. |

### Visual Integrity Constraints
- **Dark Surface Rule:** There is no inverted dark-mode asset. On dark surfaces, place the unmodified light logo on a neutral light surface card (`background: #ffffff`, `border-radius: 8px`). Never apply CSS inversion filters (`filter: invert(1)` is strictly prohibited).
- **Accessible Fallback:** If network loading fails, replace image with semantic text `<span class="brand-text">ClassSync</span>` with `sr-only` descriptive labels.

---

## 2. Color Palette & Token Hierarchy (CSS Custom Properties)

ClassSync uses the **Soft Rouge & Cool Neutral** system, derived from Colegio de Montalban institutional colors:

```css
:root {
  /* =========================================================================
     1. Institutional Brand Core
     ========================================================================= */
  --brand-midnight:    #34141f;  /* Deep maroon for high-contrast navigation */
  --brand-rouge:       #872e49;  /* Primary brand action & active selection */
  --brand-rose:        #f8ebf0;  /* Soft rose tint for highlights and featured cards */

  /* =========================================================================
     2. Neutral Canvas & Surfaces
     ========================================================================= */
  --canvas:            #f7f8fa;  /* Clean app background canvas */
  --surface:           #ffffff;  /* Primary card and modal background */
  --surface-strong:    #f0f1f4;  /* Elevated panel & table header surface */
  --surface-subtle:    var(--canvas);
  --line:              #e9e9ed;  /* Structural divider borders */
  --control-border:    #858997;  /* Form inputs & interactive borders */

  /* =========================================================================
     3. Typography & Ink
     ========================================================================= */
  --ink:               #20242c;  /* High-contrast primary body text */
  --ink-soft:          #667085;  /* Secondary subtext & helper labels */
  --ink-on-tint:       #596273;  /* Text over tinted background badges */
  --text-on-action:    #ffffff;  /* High-contrast text on primary buttons */

  /* =========================================================================
     4. Interactive Actions & Focus
     ========================================================================= */
  --primary:           var(--brand-rouge);
  --primary-hover:     #6f2039;
  --primary-soft:      var(--brand-rose);
  --focus-ring:        #295c91;  /* High-visibility blue focus outline */
  --focus-on-dark:     #f0c9d5;

  /* =========================================================================
     5. Semantic Feedback & Status States
     ========================================================================= */
  /* Success: Confirmed, Available, Active */
  --success:           #16734b;
  --success-soft:      #eaf6ef;
  --success-border:    #9bc7ad;

  /* Warning: Drafts, Approaching Conflicts, Buffer Warnings */
  --warning:           #9a630a;
  --warning-soft:      #fff5df;
  --warning-border:    #d9bd83;

  /* Danger: Collisions, Capacity Overflows, Double Bookings */
  --danger:            #b42318;
  --danger-hover:      #8e1b12;
  --danger-soft:       #fff0ee;
  --danger-border:     #e8aba4;

  /* Info: System Notes, Academic Terms, Room Equipment */
  --info:              #295c91;
  --info-soft:         #edf4fc;
  --info-border:       #a7bfd9;
}
```

---

## 3. Typography System

ClassSync standardizes on **Inter Variable**, self-hosted directly within the bundle to eliminate external API calls and ensure zero latency in offline campus environments.

### Font-Face Declaration
```css
@font-face {
  font-family: 'Inter';
  src: url('/fonts/InterVariable.woff2') format('woff2');
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}

body {
  font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: var(--ink);
  background-color: var(--canvas);
  -webkit-font-smoothing: antialiased;
}
```

### Type Scale & Hierarchy

| Role | Font Size | Line Height | Weight | Letter Spacing | Context |
|---|---|---|---|---|---|
| **Display H1** | `28px` (1.75rem) | `34px` | Bold (`700`) | `-0.02em` | Portal Welcome, Dashboard Overview |
| **Section H2** | `20px` (1.25rem) | `26px` | Semibold (`600`) | `-0.01em` | Timetable Grid Headers, Room Cards |
| **Card H3** | `16px` (1.00rem) | `22px` | Medium (`500`) | `0em` | Course Code, Laboratory Name |
| **Body Regular** | `14px` (0.875rem)| `20px` | Regular (`400`) | `0em` | Standard text, Descriptions, Tables |
| **Caption / Meta**| `12px` (0.75rem) | `16px` | Medium (`500`) | `+0.01em` | Status Pills, Time Badges, Tags |

---

## 4. Dimensional Metrics & Layout Ergonomics

ClassSync strictly complies with **WCAG 2.2 AA** touch target criteria and responsive mobile navigation constraints:

```css
:root {
  /* Spacing Grid (8px baseline) */
  --space-1:           4px;
  --space-2:           8px;
  --space-3:           16px;
  --space-4:           24px;
  --space-5:           32px;
  --space-6:           48px;

  /* Corner Radii */
  --radius:            10px;     /* Standard inputs, buttons, badges */
  --radius-lg:         12px;     /* Content cards & dropdowns */
  --radius-featured:   16px;     /* Hero cards & modal dialogs */

  /* Viewport Layout Tracks */
  --sidebar-width:     256px;    /* Desktop navigation rail */
  --header-height:     64px;     /* Top utility & profile bar */
  --bottom-nav-height: 72px;     /* Student Android bottom bar */
  --control-height:    48px;     /* Mobile touch target minimum */
  --target-min:        44px;     /* Desktop click target minimum */

  /* Shadows */
  --shadow-card:       0 1px 3px rgb(32 36 44 / 5%);
  --shadow-overlay:    0 16px 48px rgb(28 36 48 / 18%);
}
```

---

## 5. UI Implementation Component Example

```tsx
import React from 'react';

export const BrandHeader: React.FC = () => {
  return (
    <header className="flex items-center justify-between h-[64px] px-4 bg-white border-b border-[var(--line)]">
      <div className="flex items-center gap-3">
        <img
          src="/branding/classsync-logo-assets/classsync-horizontal-light.png"
          alt="ClassSync Logo"
          className="h-[36px] w-auto max-w-[144px] md:max-w-[200px] object-contain"
        />
        <img
          src="/branding/cdm-seal.png"
          alt="CdM Institutional Seal"
          className="h-[32px] w-[32px] object-contain hidden sm:block opacity-90"
        />
      </div>

      <div className="flex items-center gap-2">
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--success-soft)] text-[var(--success)] border border-[var(--success-border)]">
          Live System
        </span>
      </div>
    </header>
  );
};
```
