# Briefly - Design & Brand Guide

## 🎨 1. Brand Identity: "Signal from Noise"

**Concept:** The logo represents the core mission of Briefly: finding the signal (valuable content) amidst the noise (information overload).

**Implementation:**
- **Format:** SVG (Vector) for infinite scalability and perfect transparency.
- **Visual:** Scattered lines ("Noise") entering from the left, converging into a solid triangular pointer ("Signal") on the right.
- **Responsiveness:** The SVG contains embedded CSS media queries to automatically adjust colors and effects (glow) based on the user's system theme (Light vs. Dark mode).
- **File:** `public/briefly_logo.svg`

**Color Logic:**
- **Light Mode:** Uses standard Electric Indigo (`#6366f1` to `#4f46e5` gradient).
- **Dark Mode:** Switches to a lighter Indigo (`#a5b4fc`) with a subtle `#6366f1` glow for better contrast against deep backgrounds.

## 🎨 2. UI/UX Color System

We are moving towards a **"Premium Productivity"** aesthetic. The goal is clarity and reduced eye strain for reading long articles, while maintaining a modern, tech-forward feel.

### Primary Brand Color
Used for primary actions (buttons), key highlights, and active states.
- **Electric Indigo**: `#6366f1` (Indigo 500) - *Vibrant but readable.*
- **Hover State**: `#4f46e5` (Indigo 600)

### 🌓 Dark Mode Palette (Cyber-Professional)
Avoid pure black (`#000000`) to reduce contrast harshness. Use deep, rich greys/blues.

| Token | Hex Code | Description |
| :--- | :--- | :--- |
| **Background (Main)** | `#0B0C15` | A very deep, almost black, navy-grey. Feels infinite. |
| **Surface (Card/Nav)** | `#151725` | Slightly lighter for separation. |
| **Surface Hover** | `#1E2136` | Interactive elements. |
| **Border/Divider** | `#2D2F45` | Subtle separation lines. |
| **Text Primary** | `#E2E8F0` | Off-white (Slate 200). Never pure white. |
| **Text Secondary** | `#94A3B8` | Muted grey (Slate 400). |
| **Accent Glow** | `rgba(99, 102, 241, 0.15)` | For glassmorphism effects on cards. |

### ☀️ Light Mode Palette (Clean Editorial)
Focus on readability and paper-like qualities.

| Token | Hex Code | Description |
| :--- | :--- | :--- |
| **Background (Main)** | `#FAFAFA` | Neutral 50. Warm, paper-like off-white. |
| **Surface (Card/Nav)** | `#FFFFFF` | Pure white. High crispness. |
| **Surface Hover** | `#F1F5F9` | Slate 100. |
| **Border/Divider** | `#E2E8F0` | Slate 200. Very subtle. |
| **Text Primary** | `#1E293B` | Slate 800. Deep blue-grey. Never pure black. |
| **Text Secondary** | `#64748B` | Slate 500. Balanced contrast. |
| **Accent/Link** | `#6366f1` | Using the brand Indigo for consistency. |

### Status Colors (Semantic)
Unified across both modes, adjusting opacity/shade slightly if needed.

- **Success**: `#10B981` (Emerald 500) - Connected, Active.
- **Warning**: `#F59E0B` (Amber 500) - Processing, Low Relevance.
- **Error**: `#EF4444` (Red 500) - Failed, Disconnected.
- **Info**: `#3B82F6` (Blue 500) - New, Updates.

### Typography
Recommended font stack for this look:
- **Headings**: `Inter` or `Plus Jakarta Sans` (Geometric, modern).
- **Body/Reading**: `Inter` or `Geist` (Highly legible for UI).
- **Monospace**: `JetBrains Mono` or `Geist Mono` (For data/code).
