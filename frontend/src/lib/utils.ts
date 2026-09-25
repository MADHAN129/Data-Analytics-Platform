import * as React from "react"
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date))
}

export function formatDateShort(date: string | Date): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(date))
}

export function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)
}

/**
 * Robustly formats any error (FastAPI validation error, Axios/Fetch error, Error instance, or plain string/object)
 * into a clean, human-readable string.
 */
export function formatErrorMessage(error: unknown, fallback: string = "An unexpected error occurred"): string {
  if (!error) return fallback
  if (typeof error === "string") return error
  if (typeof error === "number" || typeof error === "boolean") return String(error)

  if (Array.isArray(error)) {
    const formatted = error
      .map((item) => formatErrorMessage(item, ""))
      .filter(Boolean)
      .join("; ")
    return formatted || fallback
  }

  if (typeof error === "object") {
    const obj = error as Record<string, any>

    // FastAPI / Pydantic validation object { loc: [...], msg: "...", type: "..." }
    if (typeof obj.msg === "string") {
      const locStr = Array.isArray(obj.loc)
        ? obj.loc.filter((part: unknown) => part !== "body").join(".")
        : ""
      return locStr ? `${locStr}: ${obj.msg}` : obj.msg
    }

    // FastAPI { detail: ... }
    if (obj.detail !== undefined) {
      return formatErrorMessage(obj.detail, fallback)
    }

    // Standard Error or response { message: ... }
    if (typeof obj.message === "string" && obj.message.trim()) {
      return obj.message
    }

    // Response { error: ... }
    if (typeof obj.error === "string" && obj.error.trim()) {
      return obj.error
    }

    try {
      const jsonStr = JSON.stringify(obj)
      return jsonStr === "{}" ? fallback : jsonStr
    } catch {
      return fallback
    }
  }

  return String(error) || fallback
}

/**
 * Sanitizes any React child input (especially toast descriptions and titles) so that
 * plain objects (e.g., FastAPI error objects {type, loc, msg, input, ctx}) or nested arrays
 * do not cause "Objects are not valid as a React child" runtime errors.
 */
export function sanitizeReactChild(content: unknown): React.ReactNode {
  if (content === null || content === undefined || typeof content === "boolean") {
    return null
  }
  if (typeof content === "string" || typeof content === "number") {
    return content
  }
  if (React.isValidElement(content)) {
    return content
  }
  if (Array.isArray(content)) {
    const isAllValidReactNodes = content.every(
      (item) =>
        item === null ||
        item === undefined ||
        typeof item === "string" ||
        typeof item === "number" ||
        React.isValidElement(item)
    )
    if (isAllValidReactNodes) {
      return content
    }
    return formatErrorMessage(content)
  }
  if (typeof content === "object") {
    return formatErrorMessage(content)
  }
  return String(content)
}
