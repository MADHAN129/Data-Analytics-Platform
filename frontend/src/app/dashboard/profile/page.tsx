"use client"
<<<<<<< HEAD

import { PlaceholderPage } from "@/components/shared/placeholder-page"
=======
// Test Git Commit
import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api-client"
import { useProfileStore } from "@/store/profile-store"
import { useToast } from "@/components/ui/use-toast"
import { ProfilePhotoSection } from "@/components/profile/profile-photo-section"
import { PersonalInfoSection } from "@/components/profile/personal-info-section"
import { ContactInfoSection } from "@/components/profile/contact-info-section"
import { OrganizationSection } from "@/components/profile/organization-section"
import { PreferencesSection } from "@/components/profile/preferences-section"
import { SecuritySection } from "@/components/profile/security-section"
import { ActivitySection } from "@/components/profile/activity-section"
import type { ProfileResponse } from "@/types/api"
>>>>>>> 6f9fde1 (Updated profile page)

export default function ProfilePage() {
  return <PlaceholderPage title="Profile" description="Manage your account settings" />
}
