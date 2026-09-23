"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/components/ui/use-toast"
import { api } from "@/lib/api-client"
import { Loader2, ArrowLeft, CheckCircle } from "lucide-react"

const forgotSchema = z.object({
  email: z.string().email("Invalid email address"),
})

type ForgotFormData = z.infer<typeof forgotSchema>

export function ForgotPasswordForm() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSent, setIsSent] = useState(false)
  const { toast } = useToast()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotFormData>({
    resolver: zodResolver(forgotSchema),
    defaultValues: { email: "" },
  })

  const onSubmit = async (data: ForgotFormData) => {
    setIsSubmitting(true)
    try {
      await api.forgotPassword(data)
      setIsSent(true)
    } catch {
      toast({
        title: "Error",
        description: "Something went wrong. Please try again.",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isSent) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex justify-center">
            <CheckCircle className="h-12 w-12 text-emerald-500" />
          </div>
          <CardTitle className="text-center text-2xl font-bold">Check your email</CardTitle>
          <CardDescription className="text-center">
            If an account exists with that email, we&apos;ve sent password reset instructions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 text-center">
            <p className="text-sm font-medium text-foreground mb-2">
              Development Mailbox (MailHog)
            </p>
            <p className="text-xs text-muted-foreground mb-3">
              In this environment, outgoing emails are captured locally by MailHog.
            </p>
            <a
              href="http://localhost:8025"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
            >
              Open Mailbox (localhost:8025) ↗
            </a>
          </div>
        </CardContent>
        <CardFooter className="flex justify-center">
          <a
            href="/login"
            className="inline-flex items-center text-sm text-primary hover:underline"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to sign in
          </a>
        </CardFooter>
      </Card>
    )
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold">Forgot password?</CardTitle>
        <CardDescription>
          Enter your email and we&apos;ll send you a reset link
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="john@company.com"
              {...register("email")}
            />
            {errors.email && (
              <p className="text-sm text-destructive">{errors.email.message}</p>
            )}
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-4">
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending...
              </>
            ) : (
              "Send reset link"
            )}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            <a href="/login" className="text-primary hover:underline">
              <ArrowLeft className="mr-1 inline h-4 w-4" />
              Back to sign in
            </a>
          </p>
        </CardFooter>
      </form>
    </Card>
  )
}
