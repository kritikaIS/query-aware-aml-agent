/** @type {import('tailwindcss').Config} */
// Documented Requirement: Tailwind CSS + CSS variables for design tokens (§11)
// All colors reference CSS variables defined in src/styles/tokens.css
// so that the Compliance Dark theme is the single source of truth (§4.1)
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      // ── Colors (§4.1 Compliance Dark palette) ──────────────────────────
      // Values are CSS variable references so they auto-update with theme
      colors: {
        bg: {
          void:         'var(--bg-void)',
          panel:        'var(--bg-panel)',
          'panel-raised': 'var(--bg-panel-raised)',
        },
        border: {
          hairline: 'var(--border-hairline)',
        },
        text: {
          primary:   'var(--text-primary)',
          secondary: 'var(--text-secondary)',
        },
        accent: {
          cyan:   'var(--accent-cyan)',
          violet: 'var(--accent-violet)',
        },
        risk: {
          low:    'var(--risk-low)',
          medium: 'var(--risk-medium)',
          high:   'var(--risk-high)',
        },
        skipped: 'var(--skipped-grey)',
      },

      // ── Typography (§4.2) ───────────────────────────────────────────────
      fontFamily: {
        sans:  ['Inter', 'system-ui', 'sans-serif'],
        mono:  ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'xs':   ['12px', { lineHeight: '16px' }],
        'sm':   ['13px', { lineHeight: '20px' }],
        'base': ['14px', { lineHeight: '22px' }],
        'md':   ['15px', { lineHeight: '24px' }],
        'lg':   ['20px', { lineHeight: '28px' }],
        'xl':   ['24px', { lineHeight: '32px' }],
        '2xl':  ['28px', { lineHeight: '36px' }],
        '3xl':  ['32px', { lineHeight: '40px' }],
      },
      fontWeight: {
        normal:   '400',
        medium:   '500',
        semibold: '600',
        bold:     '700',
      },

      // ── Spacing (§4.3 – 8px base unit) ─────────────────────────────────
      spacing: {
        '0':  '0px',
        '1':  '4px',
        '2':  '8px',     // base unit
        '3':  '12px',
        '4':  '16px',
        '5':  '20px',
        '6':  '24px',    // gutter
        '7':  '28px',
        '8':  '32px',
        '9':  '36px',
        '10': '40px',
        '12': '48px',
        '14': '56px',
        '16': '64px',
        '20': '80px',
        '24': '96px',
        '32': '128px',
      },

      // ── Border radius ───────────────────────────────────────────────────
      borderRadius: {
        'none': '0',
        'sm':   '4px',
        'md':   '6px',
        'lg':   '8px',
        'xl':   '12px',
        '2xl':  '16px',
        'full': '9999px',
      },

      // ── Shadows ─────────────────────────────────────────────────────────
      // Glassmorphism minimal: hint of blur on overlays only (§4.3)
      boxShadow: {
        'panel':   '0 1px 3px 0 rgba(0,0,0,0.4), 0 1px 2px -1px rgba(0,0,0,0.4)',
        'raised':  '0 4px 12px 0 rgba(0,0,0,0.5)',
        'overlay': '0 8px 32px 0 rgba(0,0,0,0.6)',
        'inset':   'inset 0 1px 0 0 rgba(255,255,255,0.04)',
        'cyan-glow': '0 0 12px 2px rgba(62,214,196,0.25)',
        'none': 'none',
      },

      // ── Z-index ─────────────────────────────────────────────────────────
      zIndex: {
        'base':    '0',
        'raised':  '10',
        'overlay': '20',
        'drawer':  '30',
        'modal':   '40',
        'tooltip': '50',
        'topbar':  '60',
      },

      // ── Motion tokens (§7.1) ────────────────────────────────────────────
      transitionDuration: {
        'instant': '100ms',
        'fast':    '180ms',
        'base':    '300ms',
        'slow':    '500ms',
      },
      transitionTimingFunction: {
        'motion-out':  'cubic-bezier(0.2, 0, 0, 1)',
        'motion-ease': 'ease-in-out',
      },

      // ── Breakpoints (§9) ────────────────────────────────────────────────
      screens: {
        'mobile': '0px',
        'tablet': '768px',
        'desktop': '1280px',
      },
    },
  },
  plugins: [],
}
