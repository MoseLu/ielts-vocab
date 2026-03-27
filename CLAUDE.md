# IELTS Vocabulary App

An IELTS vocabulary learning web application.

## Superpowers Skills (Auto-Trigger)

**Superpowers TDD and skills are the primary workflow for this project.**

### TDD Priority
- **Use `/superpowers:test-driven-development`** for all new features, bug fixes, refactoring
- **Iron Law**: NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
- RED-GREEN-REFACTOR cycle strictly followed

### Skill Triggers
| Trigger | Skill | When |
|---------|-------|------|
| Building something new | `superpowers:brainstorming` | Before any creative work |
| Bug/issue | `superpowers:systematic-debugging` | Before proposing fixes |
| Feature implementation | `superpowers:test-driven-development` | Before writing code |
| Code review ready | `superpowers:requesting-code-review` | After completing tasks |
| Verify completion | `superpowers:verification-before-completion` | Before claiming done |

### Auto-Activation Rule
**BEFORE any response or action, check if any Superpowers skill applies.**

## Technology Stack

- **Frontend**: React 19 + TypeScript + Vite
- **Styling**: Tailwind CSS + CSS variables
- **Validation**: Zod (runtime type validation)
- **Backend**: Python Flask + SQLite
- **Auth**: JWT Token + localStorage

## Project Structure

```
src/
├── app/                    # App router entry
├── components/
│   ├── ui/                 # Base UI components (Button, Card, Input, Modal, Loading)
│   ├── layout/             # Layout components (MainLayout, AuthLayout, PracticeLayout)
│   └── practice/           # Practice feature components
├── contexts/               # React context providers (Auth, Settings, Toast, AIChat)
├── features/
│   ├── vocabulary/hooks/   # useVocabBooks, useBookWords, useBookProgress, useAllBookProgress
│   ├── ai-chat/            # AI chat feature
│   └── speech/             # Speech recognition feature
├── hooks/                  # Shared hooks (useSpeechRecognition, useAIChat)
├── lib/                    # Utilities
│   ├── index.ts            # Helpers (storage, API fetch, formatting)
│   ├── schemas.ts           # Zod schemas for all data shapes
│   ├── validation.ts       # safeParse, ValidationResult utilities
│   └── useForm.ts          # Zod-powered form validation hook
├── types/                  # Global TypeScript interfaces
├── constants/              # App constants (practice modes, storage keys, defaults)
└── styles/                # CSS entry point
```

## Zod Validation

All data shapes are validated at runtime with [Zod](https://zod.dev).

**Schema location**: `src/lib/schemas.ts`

Schemas cover:
- Auth forms (`LoginSchema`, `RegisterSchema`)
- API responses (`AuthResponseSchema`, `BooksListResponseSchema`, etc.)
- Domain types (`UserSchema`, `BookSchema`, `ChapterSchema`, `WordSchema`, etc.)
- App settings (`AppSettingsSchema`)
- Practice types (`PracticeModeSchema`, `WordSchema`, etc.)

**Validation utilities** (`src/lib/validation.ts`):
- `safeParse(schema, data)` → `ValidationResult<T>` — never throws
- `parseOrThrow(schema, data)` → throws on failure
- `formatErrors(result)` / `firstError(result)` — human-readable error formatting

**Form hook** (`src/lib/useForm.ts`):
- `useForm({ schema })` — field-level validation, touch tracking, form-level submit

All contexts use Zod validation:
- `AuthContext` — validates login/register input + API responses
- `SettingsContext` — validates persisted settings on load
- `ToastContext` — validates toast payloads
- `useAIChat` — validates AI API responses
- `useVocabBooks` / `useBookWords` / `useBookProgress` — validates all API responses

## Key Features

1. **Authentication**: Login/Register with Zod validation
2. **Vocabulary Books**: Browse, filter, and study from vocabulary books
3. **Practice Modes**: Smart, Listening, Meaning, Dictation, Radio
4. **Progress Tracking**: Book/chapter-level progress with Zod-validated persistence
5. **AI Chat Assistant**: Contextual learning help powered by AI
6. **Responsive Design**: Mobile-friendly UI

## Backend API

The backend is built with Flask and provides RESTful APIs:

- **Auth API** (`/api/auth`): Register, login, logout, avatar
- **Books API** (`/api/books`): List books, fetch words, chapter progress
- **Progress API** (`/api/books/progress`): Save and retrieve learning progress
- **AI API** (`/api/ai/ask`): AI chat assistant

## Development

```bash
# Frontend
cd E:/app/ielts-vocab
npm run dev        # Dev server
npm run build      # Production build

# Backend
cd backend
pip install flask flask-cors flask-sqlalchemy flask-jwt-extended
python app.py      # Runs at http://localhost:5000
```

## Browser APIs

- `speechSynthesis`: Pronunciation in listening mode
- `localStorage`: Auth token, user data, settings, progress
- `WebSocket`: Real-time speech recognition (via Socket.IO)
