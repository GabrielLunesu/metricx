import { z } from "zod";

/**
 * Centralized form validation schemas.
 * WHY: Keeps validation consistent across screens and easy to tune in one place.
 */
export const profileSchema = z.object({
  name: z.string().trim().min(2, "Name must be at least 2 characters"),
  email: z.string().trim().email("Enter a valid email"),

});

export const passwordSchema = z
  .object({
    old_password: z.string().min(8, "Current password is required"),
    new_password: z
      .string()
      .min(8, "New password must be at least 8 characters")
      .regex(/[0-9]/, "Include at least one number")
      .regex(/[A-Za-z]/, "Include at least one letter"),
    confirm_password: z.string().min(8, "Confirm your new password"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords must match",
  });

export const manualCostSchema = z.object({
  label: z.string().trim().min(2, "Add a short label"),
  category: z.string().trim().min(1, "Pick a category"),
  amount_dollar: z
    .coerce.number({ invalid_type_error: "Amount must be a number" })
    .positive("Amount must be greater than zero"),
  date: z.string().trim().min(1, "Date is required"),
  notes: z.preprocess(
    (val) => (typeof val === "string" ? val.trim() : ""),
    z.string().max(280, "Keep notes under 280 characters"),
  ),
});

/**
 * Business Profile Schema
 * WHY: Validates workspace business information collected during onboarding
 * NOTE: All fields optional except they're validated when provided
 */
export const businessProfileSchema = z.object({
  domain: z.string().trim().optional().or(z.literal('')),
  domain_description: z.string().trim().max(500, "Description too long").optional().or(z.literal('')),
  niche: z.string().trim().max(100, "Niche too long").optional().or(z.literal('')),
  target_markets: z.array(z.string()).optional().default([]),
  brand_voice: z.string().trim().optional().or(z.literal('')),
});
