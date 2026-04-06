import { z } from 'zod'

export const UserSchema = z.object({
  id: z.union([z.string(), z.number()]),
  email: z.string().email().or(z.literal('')).optional(),
  username: z.string().optional(),
  avatar_url: z.string().nullable().optional(),
  is_admin: z.boolean().optional(),
  created_at: z.string().optional(),
})
export type User = z.infer<typeof UserSchema>

export const LoginSchema = z.object({
  identifier: z.string().min(1, '请输入邮箱或用户名'),
  password: z.string().min(6, '密码至少6个字符'),
})

export const RegisterSchema = z.object({
  username: z
    .string()
    .min(3, '用户名至少3个字符')
    .max(30, '用户名最多30个字符')
    .regex(/^[a-zA-Z0-9_\u4e00-\u9fa5]+$/, '用户名只能包含字母、数字、下划线和中文'),
  email: z.string().email('请输入有效的邮箱地址').optional().or(z.literal('')),
  password: z.string().min(6, '密码至少6个字符'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: '两次输入的密码不一致',
  path: ['confirmPassword'],
})

export const ForgotPasswordEmailSchema = z.object({
  email: z.string().email('请输入有效的邮箱地址'),
})

export const ResetPasswordSchema = z.object({
  code: z.string().length(6, '请输入6位验证码'),
  password: z.string().min(6, '密码至少6个字符'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: '两次输入的密码不一致',
  path: ['confirmPassword'],
})

export const BindEmailSchema = z.object({
  email: z.string().email('请输入有效的邮箱地址'),
  code: z.string().length(6, '请输入6位验证码'),
})
