import { readFileSync } from 'node:fs';
import tsEslintPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import reactHooksPlugin from 'eslint-plugin-react-hooks';

const lineLimitConfig = JSON.parse(
  readFileSync(new URL('../scripts/file-line-limit.config.json', import.meta.url), 'utf8'),
);

const oversizeJsTsBaseline = Object.keys(lineLimitConfig.baseline).filter((filePath) =>
  /\.(?:[cm]?[jt]sx?)$/u.test(filePath),
);

export default [
  {
    ignores: [
      'dist/**',
      '**/dist/**',
      'coverage/**',
      '**/coverage/**',
      'node_modules/**',
      '**/node_modules/**',
      ...lineLimitConfig.exemptions,
    ],
  },
  {
    linterOptions: {
      reportUnusedDisableDirectives: 'off',
    },
  },
  {
    files: ['**/*.{js,mjs,cjs,jsx,ts,mts,cts,tsx}'],
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
  ...(oversizeJsTsBaseline.length > 0
    ? [
        {
          files: oversizeJsTsBaseline,
          rules: {
            'max-lines': 'off',
          },
        },
      ]
    : []),
];
