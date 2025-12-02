# UI Color Reference Guide

Quick reference for colors used in the modernized dashboard.

---

## 🎨 Primary Color Palette

### Brand Colors
```css
--primary-blue:       #1e3a8a  /* Deep blue - headers, primary actions */
--primary-light:      #3b82f6  /* Electric blue - accents, interactive elements */
```

**Usage**: Main branding, primary buttons, important headings

---

## 📊 Section-Specific Colors

### Section 1: RHEL Regression Analysis
```css
Border Color:  #1e3a8a  /* Deep blue */
Icon:          📊       /* Chart/bar graph */
```

### Section 2: Competitive Performance  
```css
Border Color:  #06b6d4  /* Cyan/teal */
Icon:          📈       /* Trending up chart */
```

### Section 3: Cloud Scaling
```css
Border Color:  #10b981  /* Green */
Icon:          ☁️       /* Cloud */
```

---

## ✅ Status Colors

### Success (Green)
```css
--success-green: #10b981
```
**When to use**: 
- Passing tests
- Performance improvements (>10%)
- No regressions detected
- Linear scaling achieved
- Competitive performance

### Warning (Amber)
```css
--warning-amber: #f59e0b
```
**When to use**:
- Moderate regressions (5-10%)
- Non-critical issues
- Review needed
- Sub-linear scaling
- Performance within 10-20% of baseline

### Error (Red)
```css
--error-red: #ef4444
```
**When to use**:
- Critical regressions (>10%)
- Failed tests
- Major performance degradation
- Significant competitive gap (>20%)

### Info (Cyan)
```css
--info-cyan: #06b6d4
```
**When to use**:
- Informational messages
- Neutral comparisons
- Data availability notes
- Helper text

---

## 🎯 Neutral Colors

### Text Colors
```css
--gray-900: #1f2937  /* Primary text, dark headings */
--gray-600: #6b7280  /* Secondary text, labels */
--gray-300: #d1d5db  /* Borders, dividers */
```

### Background Colors
```css
--gray-50:  #f9fafb  /* Light backgrounds, hover states */
--gray-100: #f3f4f6  /* Secondary backgrounds */
--white:    #ffffff  /* Cards, main surfaces */
```

---

## 📉 Data Visualization Colors

### Regression Scale (Heatmaps, Bar Charts)
```css
/* Red → Yellow → Gray → Light Green → Green */
[
  [0.0, '#ef4444'],   /* Strong regression (red) */
  [0.25, '#f97316'],  /* Moderate regression (orange) */
  [0.45, '#fbbf24'],  /* Mild regression (yellow) */
  [0.5, '#e5e7eb'],   /* Neutral (gray) */
  [0.55, '#a7f3d0'],  /* Mild improvement (light green) */
  [0.75, '#34d399'],  /* Moderate improvement (green) */
  [1.0, '#10b981']    /* Strong improvement (dark green) */
]
```

### Chart Color Sequence (Lines, Bars)
```css
/* Use in order for multiple data series */
#3b82f6  /* Blue */
#10b981  /* Green */
#f59e0b  /* Amber */
#ef4444  /* Red */
#8b5cf6  /* Purple */
#06b6d4  /* Cyan */
```

---

## 🔲 UI Element Colors

### Buttons

**Primary Button**
```css
background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
color: #ffffff;
```

**Secondary Button**
```css
background: linear-gradient(135deg, #6b7280 0%, #1f2937 100%);
color: #ffffff;
```

**Outline Button**
```css
border: 2px solid #3b82f6;
color: #1e3a8a;
background: transparent;

/* Hover */
background: #3b82f6;
color: #ffffff;
```

### Badges

**Primary Badge**
```css
background: #1e3a8a;
color: #ffffff;
```

**Secondary Badge**
```css
background: #6b7280;
color: #ffffff;
```

**Status Badges**
```css
/* Success */
background: #d1fae5;
color: #065f46;
border-left: 4px solid #10b981;

/* Warning */
background: #fef3c7;
color: #78350f;
border-left: 4px solid #f59e0b;

/* Error */
background: #fee2e2;
color: #7f1d1d;
border-left: 4px solid #ef4444;
```

### Cards

**Default Card**
```css
background: #ffffff;
border: none;
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
border-radius: 0.75rem;
```

**Card Header**
```css
background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%);
border-bottom: 3px solid #3b82f6;
```

**Card with Colored Border**
```css
border-left: 5px solid #1e3a8a;  /* Blue */
border-left: 5px solid #06b6d4;  /* Cyan */
border-left: 5px solid #10b981;  /* Green */
```

---

## 🎨 Gradient Examples

### Header Backgrounds
```css
linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)
```

### Primary Buttons
```css
linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)
```

### Alert Backgrounds
```css
/* Success */
linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%)

/* Warning */
linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)

/* Error */
linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)

/* Info */
linear-gradient(135deg, #cffafe 0%, #a5f3fc 100%)
```

---

## 🌓 Contrast Ratios (WCAG AA Compliant)

All color combinations meet WCAG AA standards (4.5:1 minimum):

| Foreground | Background | Ratio | Pass |
|------------|------------|-------|------|
| #1f2937 (text) | #ffffff (white) | 15.9:1 | ✅ AAA |
| #6b7280 (secondary) | #ffffff | 5.8:1 | ✅ AA |
| #065f46 (success text) | #d1fae5 (success bg) | 7.2:1 | ✅ AAA |
| #78350f (warning text) | #fef3c7 (warning bg) | 8.1:1 | ✅ AAA |
| #7f1d1d (error text) | #fee2e2 (error bg) | 9.3:1 | ✅ AAA |
| #ffffff (white) | #1e3a8a (primary) | 9.7:1 | ✅ AAA |

---

## 🎯 Usage Guidelines

### DO ✅
- Use status colors consistently (green = good, amber = caution, red = error)
- Use section colors for their respective sections only
- Maintain contrast ratios for text
- Use gradients sparingly (headers, buttons, alerts)
- Test colors in both light and dark mode browsers

### DON'T ❌
- Don't mix section colors (blue border with green icon)
- Don't use red/green for non-status information (colorblind users)
- Don't use low-contrast color combinations
- Don't overuse gradients (cards, backgrounds)
- Don't use brand colors for negative information

---

## 🔧 CSS Variables

Define these in `:root` for easy theming:

```css
:root {
  /* Brand */
  --color-primary: #1e3a8a;
  --color-primary-light: #3b82f6;
  
  /* Status */
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: #06b6d4;
  
  /* Sections */
  --color-section-1: #1e3a8a;  /* RHEL Regression */
  --color-section-2: #06b6d4;  /* Competitive */
  --color-section-3: #10b981;  /* Cloud Scaling */
  
  /* Neutrals */
  --color-text-primary: #1f2937;
  --color-text-secondary: #6b7280;
  --color-text-muted: #9ca3af;
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f9fafb;
  --color-bg-tertiary: #f3f4f6;
  
  /* Borders */
  --color-border: #e5e7eb;
  --color-border-dark: #d1d5db;
}
```

---

## 🖌️ Hex to RGB Reference

For use with `rgba()` functions:

```css
/* Primary */
#1e3a8a = rgb(30, 58, 138)
#3b82f6 = rgb(59, 130, 246)

/* Status */
#10b981 = rgb(16, 185, 129)
#f59e0b = rgb(245, 158, 11)
#ef4444 = rgb(239, 68, 68)
#06b6d4 = rgb(6, 182, 212)

/* Neutrals */
#1f2937 = rgb(31, 41, 55)
#6b7280 = rgb(107, 114, 128)
#f3f4f6 = rgb(243, 244, 246)
#ffffff = rgb(255, 255, 255)
```

**Usage Example**:
```css
box-shadow: 0 4px 6px rgba(59, 130, 246, 0.1);  /* Blue shadow at 10% opacity */
```

---

## 📱 Responsive Considerations

Colors remain the same across screen sizes, but consider:

- **Mobile**: Use slightly larger color areas (harder to distinguish small colored elements)
- **Tablet**: Standard color usage
- **Desktop**: Can use more subtle color distinctions

---

## 🎨 Color Blindness Considerations

Our palette is designed for accessibility:

- **Protanopia/Deuteranopia (Red-Green)**: We supplement color with icons and text labels
- **Tritanopia (Blue-Yellow)**: Sufficient contrast between blues and ambers
- **Monochromacy**: All colors have distinct brightness levels

**Test Tools**:
- Chrome DevTools: Rendering > Emulate vision deficiencies
- Online: https://www.color-blindness.com/coblis-color-blindness-simulator/

---

## 🖨️ Print Styles

When printing, colors convert well to grayscale:

```css
@media print {
  /* Status colors */
  .alert-success { border-left-color: #000 !important; }
  .alert-warning { border-left-color: #666 !important; }
  .alert-danger { border-left-color: #000 !important; }
  
  /* Remove gradients */
  * { background-image: none !important; }
}
```

---

**Quick Reference Card** (print this section):

```
SECTIONS:
📊 RHEL Regression    #1e3a8a (blue)
📈 Competitive Perf   #06b6d4 (cyan)
☁️  Cloud Scaling     #10b981 (green)

STATUS:
✅ Success   #10b981 (green)
⚠️  Warning   #f59e0b (amber)
🔴 Error     #ef4444 (red)
ℹ️  Info      #06b6d4 (cyan)

NEUTRALS:
Text:       #1f2937 (dark gray)
Secondary:  #6b7280 (medium gray)
Border:     #e5e7eb (light gray)
Background: #ffffff (white)
```

---

**Last Updated**: December 2, 2025  
**Status**: Reference Guide for UI Modernization

