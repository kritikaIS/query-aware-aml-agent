/**
 * Framer Motion animation variants
 * Documented Requirement: §7 Motion & Animation System
 * Every variant has fixed duration, easing, and trigger — no decorative animations.
 * All motion operates on transform/opacity only — never width/top (§13 frame budget)
 */

import type { Variants } from 'framer-motion'
import { MOTION } from '@/constants'

// ── Easing curves (§7.1) ──────────────────────────────────────────────
export const EASING = {
  motionOut:   [0.2, 0, 0, 1] as [number, number, number, number],
  easeOut:     'easeOut',
  easeInOut:   'easeInOut',
  linear:      'linear',
} as const

// ── Fade (generic) ────────────────────────────────────────────────────
export const fadeVariants: Variants = {
  hidden:  { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: MOTION.BASE, ease: EASING.motionOut },
  },
  exit: {
    opacity: 0,
    transition: { duration: MOTION.FAST, ease: EASING.easeOut },
  },
}

// ── Slide up (cards entering from below) ─────────────────────────────
export const slideUpVariants: Variants = {
  hidden:  { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: MOTION.SLOW, ease: EASING.motionOut },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: { duration: MOTION.FAST, ease: EASING.easeOut },
  },
}

// ── Slide in from right (drawer, §7.1 motion-base) ────────────────────
export const drawerVariants: Variants = {
  hidden:  { opacity: 0, x: '100%' },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: MOTION.BASE, ease: EASING.motionOut },
  },
  exit: {
    opacity: 0,
    x: '100%',
    transition: { duration: MOTION.BASE, ease: EASING.easeInOut },
  },
}

// ── Modal (slide up + fade, §7.1 motion-base) ─────────────────────────
export const modalVariants: Variants = {
  hidden:  { opacity: 0, scale: 0.97, y: 8 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: MOTION.BASE, ease: EASING.motionOut },
  },
  exit: {
    opacity: 0,
    scale: 0.97,
    y: 8,
    transition: { duration: MOTION.FAST, ease: EASING.easeOut },
  },
}

// ── Overlay backdrop (dims behind drawer/modal) ───────────────────────
export const backdropVariants: Variants = {
  hidden:  { opacity: 0 },
  visible: { opacity: 1, transition: { duration: MOTION.BASE } },
  exit:    { opacity: 0, transition: { duration: MOTION.BASE } },
}

// ── Stagger container for pipeline card assembly (§7.2 seq 1) ────────
// Cards fade+slide up left-to-right with 60ms stagger; order = execution order
export const staggerContainerVariants: Variants = {
  hidden:  {},
  visible: {
    transition: {
      staggerChildren: MOTION.STAGGER_DELAY,
      delayChildren: 0,
    },
  },
}

// ── Individual pipeline card (child of stagger container) ────────────
export const pipelineCardVariants: Variants = {
  hidden:  { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: MOTION.SLOW, ease: EASING.motionOut },
  },
}

// ── Skip reveal (§7.2 seq 2) ─────────────────────────────────────────
// Card briefly appears in full color, then desaturates + strikes through
// Implemented as a keyframe animation via CSS class, triggered by state
export const skipRevealVariants: Variants = {
  initial:   { opacity: 1, filter: 'saturate(1)' },
  skipping:  {
    opacity: [1, 1, 0.5],
    filter:  ['saturate(1)', 'saturate(0.8)', 'saturate(0)'],
    transition: { duration: 0.25, ease: EASING.easeInOut, times: [0, 0.4, 1] },
  },
  skipped: {
    opacity: 0.6,
    filter: 'saturate(0)',
    transition: { duration: 0 },
  },
}

// ── Score resolution (§7.2 seq 3) ────────────────────────────────────
// Risk badges resolve via 400ms sweep — "this number was computed"
export const scoreResolveVariants: Variants = {
  hidden:  { opacity: 0, scale: 0.8 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.4, ease: EASING.motionOut },
  },
}

// ── Accordion row expand/collapse (§5.3 entity rows) ─────────────────
export const accordionVariants: Variants = {
  collapsed: {
    opacity: 0,
    height: 0,
    transition: { duration: MOTION.FAST, ease: EASING.motionOut },
  },
  expanded: {
    opacity: 1,
    height: 'auto',
    transition: { duration: MOTION.BASE, ease: EASING.motionOut },
  },
}

// ── Page transition (SPA view switches) ──────────────────────────────
export const pageVariants: Variants = {
  enter:  { opacity: 0, y: 12 },
  center: {
    opacity: 1,
    y: 0,
    transition: { duration: MOTION.BASE, ease: EASING.motionOut },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: { duration: MOTION.FAST, ease: EASING.easeOut },
  },
}

// ── Breathing pulse for "agent is planning" indicator (§7.3) ─────────
// The ONE animation that loops — slow 2.4s breathing pulse only
export const breathingPulseVariants: Variants = {
  pulse: {
    opacity: [0.6, 1, 0.6],
    scale:   [1, 1.03, 1],
    transition: {
      duration: MOTION.BREATHING_DURATION,
      repeat: Infinity,
      ease: EASING.easeInOut,
    },
  },
}
