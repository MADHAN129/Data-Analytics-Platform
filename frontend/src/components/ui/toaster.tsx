"use client"

import { useToast } from "@/components/ui/use-toast"
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from "@/components/ui/toast"

import { sanitizeReactChild } from "@/lib/utils"

export function Toaster() {
  const { toasts } = useToast()

  return (
    <ToastProvider>
      {toasts.map(function ({ id, title, description, action, ...props }) {
        const safeTitle = sanitizeReactChild(title)
        const safeDescription = sanitizeReactChild(description)

        return (
          <Toast key={id} {...props}>
            <div className="grid gap-1">
              {safeTitle ? <ToastTitle>{safeTitle}</ToastTitle> : null}
              {safeDescription ? <ToastDescription>{safeDescription}</ToastDescription> : null}
            </div>
            {action}
            <ToastClose />
          </Toast>
        )
      })}
      <ToastViewport />
    </ToastProvider>
  )
}
