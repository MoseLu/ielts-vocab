export const theme = {
  colors: {
    accent: '#FFD93D',
    accentDark: '#DDAA1E',
    accentSoft: '#FFFBEA',
    accentSubtle: '#FFFEF5',
    background: '#FFE8EE', // Pastel pink
    border: '#4A3B32', // Dark brown cartoon outline
    borderStrong: '#3A2B22',
    card: '#FFFFFF',
    danger: '#FF6B9D',
    dangerSoft: '#FFE8F0',
    emerald: '#6BCB77',
    emeraldSoft: '#E6F7EB',
    info: '#74C0FC',
    infoSoft: '#EBF6FF',
    muted: '#8A7A70',
    primary: '#6BCB77',
    primaryDark: '#4A9F54',
    primarySoft: '#E6F7EB',
    purple: '#C77DFF',
    purpleSoft: '#F6E8FF',
    rose: '#FF86A8',
    roseSoft: '#FFE7EF',
    shadow: '#4A3B32',
    success: '#6BCB77',
    surface: '#FFFDF0', // Cream white
    surfaceElevated: '#FFFFFF',
    surfaceInset: '#FFF9E6',
    text: '#4A3B32', // Dark brown text
    textInverse: '#ffffff',
    textTertiary: '#A49286',
  },
  radius: {
    card: 24, // Big radius for cards
    control: 999, // Pill shape for controls
    pill: 999,
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
  },
  typography: {
    body: 16,
    caption: 13,
    heading: 24,
    label: 14,
    title: 18,
  },
} as const
