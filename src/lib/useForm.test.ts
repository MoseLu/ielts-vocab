// ── Tests for src/lib/useForm.ts ───────────────────────────────────────────────

import { renderHook, act } from '@testing-library/react'
import { z } from 'zod'
import { useForm } from './useForm'

const TestSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  age: z.number().min(18, 'Must be at least 18'),
})

describe('useForm', () => {
  describe('initialization', () => {
    it('initializes with empty values when no initialValues provided', () => {
      const { result } = renderHook(() => useForm({ schema: TestSchema }))
      expect(result.current.values).toEqual({})
      expect(result.current.errors).toEqual({})
      expect(result.current.touched).toEqual({})
    })

    it('initializes with provided initialValues', () => {
      const { result } = renderHook(() =>
        useForm({ schema: TestSchema, initialValues: { name: 'Alice', age: 25 } })
      )
      expect(result.current.values).toEqual({ name: 'Alice', age: 25 })
    })

    it('hasErrors is false on init', () => {
      const { result } = renderHook(() => useForm({ schema: TestSchema }))
      expect(result.current.hasErrors).toBe(false)
    })
  })

  describe('setFieldValue', () => {
    it('updates a single field value', () => {
      const { result } = renderHook(() => useForm({ schema: TestSchema }))
      act(() => {
        result.current.setFieldValue('name', 'Alice')
      })
      expect(result.current.values.name).toBe('Alice')
    })

    it('clears field error on valid input', () => {
      const { result } = renderHook(() => useForm({ schema: TestSchema }))
      // Trigger a validation error first by setting a too-short name
      act(() => {
        result.current.setFieldValue('name', 'A')
      })
      expect(result.current.errors.name).toBeTruthy()
      // Fix it
      act(() => {
        result.current.setFieldValue('name', 'Alice')
      })
      expect(result.current.errors.name).toBe('')
    })

    it('sets field error on invalid input', () => {
      const { result } = renderHook(() => useForm({ schema: TestSchema }))
      act(() => {
        result.current.setFieldValue('email', 'not-an-email')
      })
      expect(result.current.errors.email).toBeTruthy()
    })
  })

  describe('setFieldTouched', () => {
    it('marks a field as touched', () => {
      const { result } = renderHook(() => useForm({ schema: TestSchema }))
      act(() => {
        result.current.setFieldTouched('name')
      })
      expect(result.current.touched.name).toBe(true)
    })
  })

  describe('validate', () => {
    it('returns true for valid form', () => {
      const { result } = renderHook(() =>
        useForm({ schema: TestSchema, initialValues: { name: 'Alice', email: 'a@b.com', age: 25 } })
      )
      let isValid = false
      act(() => {
        isValid = result.current.validate()
      })
      expect(isValid).toBe(true)
      expect(result.current.errors).toEqual({})
    })

    it('returns false for invalid form', () => {
      const { result } = renderHook(() =>
        useForm({ schema: TestSchema, initialValues: { name: 'A', email: 'bad', age: 10 } })
      )
      let isValid = true
      act(() => {
        isValid = result.current.validate()
      })
      expect(isValid).toBe(false)
      expect(result.current.errors).not.toEqual({})
    })

    it('maps errors to field keys', () => {
      const { result } = renderHook(() =>
        useForm({ schema: TestSchema, initialValues: { name: 'A', email: 'bad', age: 10 } })
      )
      act(() => {
        result.current.validate()
      })
      expect(result.current.errors.name).toBeTruthy()
      expect(result.current.errors.email).toBeTruthy()
      expect(result.current.errors.age).toBeTruthy()
    })
  })

  describe('handleSubmit', () => {
    it('calls onValid with values when form is valid', async () => {
      const onValid = vi.fn()
      const { result } = renderHook(() =>
        useForm({
          schema: TestSchema,
          initialValues: { name: 'Alice', email: 'a@b.com', age: 25 },
        })
      )

      const handleSubmit = result.current.handleSubmit(onValid)
      const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent

      await act(async () => {
        await handleSubmit(fakeEvent)
      })

      expect(onValid).toHaveBeenCalledWith({ name: 'Alice', email: 'a@b.com', age: 25 })
    })

    it('does not call onValid when form is invalid', async () => {
      const onValid = vi.fn()
      const { result } = renderHook(() => useForm({ schema: TestSchema }))

      const handleSubmit = result.current.handleSubmit(onValid)
      const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent

      await act(async () => {
        await handleSubmit(fakeEvent)
      })

      expect(onValid).not.toHaveBeenCalled()
    })

    it('prevents default form behavior', async () => {
      const onValid = vi.fn()
      const { result } = renderHook(() =>
        useForm({
          schema: TestSchema,
          initialValues: { name: 'Alice', email: 'a@b.com', age: 25 },
        })
      )

      const handleSubmit = result.current.handleSubmit(onValid)
      const preventDefault = vi.fn()
      const fakeEvent = { preventDefault } as unknown as React.FormEvent

      await act(async () => {
        await handleSubmit(fakeEvent)
      })

      expect(preventDefault).toHaveBeenCalled()
    })

    it('sets __form error when onValid throws', async () => {
      const error = new Error('Server error')
      const { result } = renderHook(() =>
        useForm({
          schema: TestSchema,
          initialValues: { name: 'Alice', email: 'a@b.com', age: 25 },
        })
      )

      const handleSubmit = result.current.handleSubmit(async () => {
        throw error
      })
      const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent

      await act(async () => {
        await handleSubmit(fakeEvent)
      })

      expect(result.current.errors.__form).toBe('Server error')
    })
  })

  describe('reset', () => {
    it('resets values, errors, and touched', () => {
      const { result } = renderHook(() =>
        useForm({ schema: TestSchema, initialValues: { name: 'Alice', age: 25 } })
      )

      act(() => {
        result.current.setFieldValue('name', 'A')
        result.current.setFieldTouched('name')
      })
      expect(result.current.errors.name).toBeTruthy()
      expect(result.current.touched.name).toBe(true)

      act(() => {
        result.current.reset()
      })

      expect(result.current.values).toEqual({ name: 'Alice', age: 25 })
      expect(result.current.errors).toEqual({})
      expect(result.current.touched).toEqual({})
    })
  })

  describe('getFieldError', () => {
    it('returns undefined when field is not touched', () => {
      const { result } = renderHook(() => useForm({ schema: TestSchema }))
      act(() => {
        result.current.setFieldValue('email', 'bad')
      })
      expect(result.current.getFieldError('email')).toBeUndefined()
    })

    it('returns error when field is touched', () => {
      const { result } = renderHook(() => useForm({ schema: TestSchema }))
      act(() => {
        result.current.setFieldValue('email', 'bad')
        result.current.setFieldTouched('email')
      })
      expect(result.current.getFieldError('email')).toBeTruthy()
    })
  })

  describe('hasErrors', () => {
    it('is true when there are field errors', () => {
      const { result } = renderHook(() => useForm({ schema: TestSchema }))
      act(() => {
        result.current.setFieldValue('email', 'bad')
      })
      // getFieldError checks touched, but hasErrors checks errors object
      // Trigger validation to set error
      act(() => {
        result.current.validate()
      })
      expect(result.current.hasErrors).toBe(true)
    })

    it('is false when all errors are cleared', () => {
      const { result } = renderHook(() =>
        useForm({ schema: TestSchema, initialValues: { name: 'Alice', email: 'a@b.com', age: 25 } })
      )
      act(() => {
        result.current.validate()
      })
      expect(result.current.hasErrors).toBe(false)
    })
  })
})
