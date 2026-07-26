/**
 * Class name utility — merges Tailwind classes safely.
 * Uses clsx for conditional logic + tailwind-merge to resolve conflicts.
 */

import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
