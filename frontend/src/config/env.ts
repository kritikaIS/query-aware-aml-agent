/**
 * Environment configuration
 * Implementation Assumption: reads from VITE_ prefixed env vars
 */

export const env = {
  apiBaseUrl:   import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  appTitle:     import.meta.env.VITE_APP_TITLE ?? 'AML Agent',
  isDev:        import.meta.env.DEV,
  isProd:       import.meta.env.PROD,
  mode:         import.meta.env.MODE,
} as const
