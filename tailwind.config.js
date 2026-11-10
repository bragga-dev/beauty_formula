/**
 * Tailwind para e-mail — Fórmula da Beleza
 *
 * Ajustes pensados para clientes de e-mail:
 *  - preflight desligado (o reset está no email.css)
 *  - opacidades via variável CSS desligadas, para as cores saírem como #hex puro
 *  - espaçamentos, fontes e raios em px (nada de rem)
 *  - único breakpoint: "mobile" (max-width: 600px). Use com "!" para vencer o
 *    estilo inline:  mobile:!px-5
 */
const spacing = { 0: '0px', px: '1px' };
for (let i = 1; i <= 16; i++) spacing[i] = `${i * 4}px`;
spacing[20] = '80px';
spacing[24] = '96px';

module.exports = {
  content: ['./*.src.html'],
  corePlugins: {
    preflight: false,
    textOpacity: false,
    backgroundOpacity: false,
    borderOpacity: false,
    divideOpacity: false,
    placeholderOpacity: false,
    ringOpacity: false,
  },
  theme: {
    screens: { mobile: { max: '600px' } },
    spacing,
    fontSize: {
      '2xs': ['10px', '1.4'],
      xs: ['11px', '1.5'],
      sm: ['13px', '1.6'],
      base: ['15px', '1.7'],
      lg: ['18px', '1.4'],
      xl: ['22px', '1.2'],
      '2xl': ['28px', '1.15'],
    },
    borderRadius: {
      none: '0px',
      sm: '6px',
      DEFAULT: '8px',
      md: '10px',
      lg: '14px',
      full: '9999px',
    },
    maxWidth: { card: '600px' },
    letterSpacing: {
      normal: '0',
      brand: '0.02em',
      wide: '0.05em',
      widest: '0.12em',
      badge: '0.18em',
    },
    fontFamily: {
      display: ['Oswald', 'Arial Narrow', 'Arial', 'sans-serif'],
      serif: ["'Cormorant Garamond'", 'Georgia', "'Times New Roman'", 'serif'],
      sans: ['Inter', 'Arial', 'Helvetica', 'sans-serif'],
      mono: ["'Courier New'", 'monospace'],
    },
    colors: {
      transparent: 'transparent',
      ink: {
        950: '#0a0a0b',
        900: '#0f0f11',
        800: '#17171a',
        700: '#202023',
        600: '#2b2b2f',
      },
      bone: {
        50: '#faf9f7',
        100: '#f2f0ec',
        300: '#cfccc5',
        500: '#8f8c86',
        600: '#6b6862',
      },
      crimson: { 400: '#e23a52', 500: '#c6172e', 600: '#a10f24' },
      gold: { 300: '#e6c98a', 400: '#d4af6a', 500: '#b8923f' },
      line: {
        gold: 'rgba(212,175,106,0.38)',
        crimson: 'rgba(198,23,46,0.35)',
      },
    },
  },
};
