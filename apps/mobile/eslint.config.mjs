import { readFileSync } from 'node:fs';
import tsEslintPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import reactHooksPlugin from 'eslint-plugin-react-hooks';

const lineLimitConfig = JSON.parse(
  readFileSync(new URL('../../scripts/file-line-limit.config.json', import.meta.url), 'utf8'),
);

export default [
  {
    ignores: ['android/**', 'ios/**', 'node_modules/**'],
  },
  {
    linterOptions: {
      reportUnusedDisableDirectives: 'off',
    },
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    plugins: {
      '@typescript-eslint': tsEslintPlugin,
      'react-hooks': reactHooksPlugin,
    },
    rules: {
      'max-lines': [
        'error',
        {
          max: lineLimitConfig.maxLines,
          skipBlankLines: false,
          skipComments: false,
        },
      ],
    },
  },
];
