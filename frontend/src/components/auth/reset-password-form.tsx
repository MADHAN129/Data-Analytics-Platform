"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useRouter, useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/components/ui/use-toast"
import { api } from "@/lib/api-client"
import { Loader2, CheckCircle, KeyRound, ArrowLeft } from "lucide-react"

const resetSchema = z
  .object({
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  })

type ResetFormData = z.infer<typeof resetSchema>

export function ResetPasswordForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get("token")
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isDone, setIsDone] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetFormData>({
    resolver: zodResolver(resetSchema),
    defaultValues: { password: "", confirmPassword: "" },
  })

  const onSubmit = async (data: ResetFormData) => {
    if (!token) {
      toast({
        title: "Error",
        description: "Missing or invalid reset token. Please request a new link.",
        variant: "destructive",
      })
      return
    }

    setIsSubmitting(true)
    try {
      await api.resetPassword({ token: token.trim(), new_password: data.password })
      setIsDone(true)
      toast({
        title: "Success",
        description: "Password reset successful! You can now sign in with your new password.",
      })
    } catch {
      toast({
        title: "Error",
        description: "Invalid or expired reset link. Please request a new one.",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!token) {
    return (
      <Card className="w-full max-w-md shadow-lg border-muted">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-2xl font-bold text-destructive">Invalid or Missing Link</CardTitle>
          <CardDescription>
            This reset link is missing a valid token. Please request a new password reset link.
          </CardDescription>
        </CardHeader>
        <CardFooter className="flex flex-col gap-3 pt-2">
          <Button className="w-full" onClick={() => router.push("/forgot-password")}>
            Request New Reset Link
          </Button>
          <button
            type="button"
            onClick={() => router.push("/login")}
            className="text-xs text-muted-foreground hover:underline inline-flex items-center justify-center"
          >
            <ArrowLeft className="mr-1 h-3 w-3" />
            Back to sign in
          </button>
        </CardFooter>
      </Card>
    )
  }

  if (isDone) {
    return (
      <Card className="w-full max-w-md shadow-lg border-muted">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-2">
            <CheckCircle className="h-12 w-12 text-emerald-500" />
          </div>
          <CardTitle className="text-2xl font-bold">Password reset</CardTitle>
          <CardDescription>
            Your password has been reset successfully.
          </CardDescription>
        </CardHeader>
        <CardFooter className="flex justify-center pt-2">
          <Button className="w-full" onClick={() => router.push("/login")}>
            Sign in with new password
          </Button>
        </CardFooter>
      </Card>
    )
  }

  return (
    <Card className="w-full max-w-md shadow-lg border-muted">
      <CardHeader className="space-y-1">
        <div className="flex items-center gap-2">
          <KeyRound className="h-5 w-5 text-primary" />
          <CardTitle className="text-2xl font-bold">Set new password</CardTitle>
        </div>
        <CardDescription>Enter your new password below.</CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="password">New password</Label>
            <Input
              id="password"
              type="password"
              placeholder="Min. 8 characters"
              {...register("password")}
            />
            {errors.password && (
              <p className="text-sm text-destructive">{errors.password.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirm password</Label>
            <Input
              id="confirmPassword"
              type="password"
              placeholder="Repeat your new password"
              {...register("confirmPassword")}
            />
            {errors.confirmPassword && (
              <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>
            )}
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-4">
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Resetting password...
              </>
            ) : (
              "Reset password"
            )}
          </Button>
          <div className="flex items-center justify-between w-full text-xs text-muted-foreground">
            <button
              type="button"
              onClick={() => router.push("/forgot-password")}
              className="text-primary hover:underline inline-flex items-center"
            >
              Request new link
            </button>
            <button
              type="button"
              onClick={() => router.push("/login")}
              className="text-muted-foreground hover:underline inline-flex items-center"
            >
              <ArrowLeft className="mr-1 h-3 w-3" />
              Back to sign in
            </button>
          </div>
        </CardFooter>
      </form>
    </Card>
  )
}


