import js from '@eslint/js'
import globals from 'globals'

export default [
  js.configs.recommended,
  {
    languageOptions: {
      // Browser APIs (FormData, fetch, etc.) for Vite/React sources.
      globals: {
        ...globals.browser,
      },
    },
  },
]
