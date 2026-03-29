# Design Guidelines - RAG Business Document Wiki

**Last Updated:** 2026-03-26
**Style:** Clean & Minimal
**Accent:** Blue (Professional)

## Design System

### Color Palette

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--primary` | #2563eb | #3b82f6 | Buttons, links, focus |
| `--primary-light` | #dbeafe | #1e3a5f | Primary backgrounds |
| `--secondary` | #64748b | #94a3b8 | Secondary text |
| `--background` | #ffffff | #0f172a | Page background |
| `--surface` | #f8fafc | #1e293b | Cards, panels |
| `--border` | #e2e8f0 | #334155 | Borders, dividers |
| `--text-primary` | #0f172a | #f1f5f9 | Headings, body |
| `--text-secondary` | #64748b | #94a3b8 | Muted text |
| `--success` | #10b981 | #34d399 | Success states |
| `--warning` | #f59e0b | #fbbf24 | Warnings |
| `--error` | #ef4444 | #f87171 | Errors |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| H1 | Inter | 32px | 700 |
| H2 | Inter | 24px | 600 |
| H3 | Inter | 18px | 600 |
| Body | Inter | 14px | 400 |
| Small | Inter | 12px | 400 |
| Code | JetBrains Mono | 13px | 400 |

### Spacing Scale

| Token | Value |
|-------|-------|
| xs | 4px |
| sm | 8px |
| md | 16px |
| lg | 24px |
| xl | 32px |
| 2xl | 48px |

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| sm | 4px | Buttons, inputs |
| md | 8px | Cards, modals |
| lg | 12px | Large containers |
| full | 9999px | Pills, avatars |

### Shadows

```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.07);
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
```

---

## Layout Structure

### Main Layout

```
┌─────────────────────────────────────────────────────────┐
│  HEADER: Logo | Search | User Menu                      │ 64px
├─────────┬───────────────────────────────────────────────┤
│         │                                               │
│  SIDE   │              MAIN CONTENT                     │
│  BAR    │                                               │
│         │    [Depends on current view]                  │
│  240px  │                                               │
│         │                                               │
│  Nav    │                                               │
│  Items  │                                               │
│         │                                               │
├─────────┴───────────────────────────────────────────────┤
│  FOOTER (optional): Status | Version                    │ 32px
└─────────────────────────────────────────────────────────┘
```

### Sidebar Navigation

```
┌─────────────────┐
│ 📁 Documents    │
│ 💬 Chat         │
│ 🔍 Search       │
│ ─────────────── │
│ ⚙️ Settings     │
│ 👤 Admin        │ (role-based)
└─────────────────┘
```

---

## Component Specifications

### 1. Document Card

```
┌─────────────────────────────────────────┐
│ 📄 [Filename]                    [···]  │
├─────────────────────────────────────────┤
│ Type: PDF  |  Size: 2.4 MB              │
│ Uploaded: 2 hours ago                   │
│ Status: ● Ready                         │
└─────────────────────────────────────────┘
```

- Hover: Subtle lift (shadow-lg)
- Actions: Download, Delete, View Details
- Status indicators: Processing (spinner), Ready (green), Error (red)

### 2. Upload Zone

```
┌─────────────────────────────────────────┐
│                                         │
│     📤 Drag & drop files here          │
│        or click to browse               │
│                                         │
│     Supported: PDF, DOCX, XLSX         │
│     Max size: 50 MB                     │
│                                         │
└─────────────────────────────────────────┘
```

- Active drag: Dashed border turns primary color
- Progress: Linear progress bar below
- Multi-file: Stack cards vertically

### 3. Chat Interface

```
┌─────────────────────────────────────────┐
│ 💬 Chat with your documents             │
├─────────────────────────────────────────┤
│                                         │
│  [User message right-aligned]           │
│                                         │
│  [AI response left-aligned]             │
│  📎 Sources: doc1.pdf (p.3)            │
│                                         │
├─────────────────────────────────────────┤
│ [Type message...]              [Send]   │
└─────────────────────────────────────────┘
```

- Typing indicator: Animated dots
- Source citations: Clickable, opens document
- Code blocks: Syntax highlighted

### 4. Search Results

```
┌─────────────────────────────────────────┐
│ 🔍 [Search query....................]   │
│ Filters: [All] [PDF] [DOCX] [XLSX]      │
├─────────────────────────────────────────┤
│ Result 1                                │
│ Document: quarterly_report.pdf          │
│ ...highlighted <mark>context</mark>...  │
│ Relevance: 92% | Page 3                 │
├─────────────────────────────────────────┤
│ Result 2 ...                            │
└─────────────────────────────────────────┘
```

### 5. Admin Dashboard

```
┌──────────────┬──────────────┬──────────────┐
│   📊 1,234   │   👥 56      │   📄 892     │
│   Documents  │   Users      │   Chunks     │
└──────────────┴──────────────┴──────────────┘

┌─────────────────────────────────────────┐
│ Recent Activity                          │
│ • User X uploaded report.pdf (2m ago)   │
│ • User Y deleted old_doc.docx (15m ago) │
└─────────────────────────────────────────┘
```

---

## Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | < 640px | Single column, bottom nav |
| Tablet | 640-1024px | Collapsible sidebar |
| Desktop | > 1024px | Full sidebar |

---

## Interaction Patterns

### Loading States
- Skeleton screens for content areas
- Spinner for async operations
- Progress bars for uploads

### Error Handling
- Inline validation for forms
- Toast notifications for API errors
- Retry buttons for failed operations

### Animations
- Transitions: 150ms ease-out
- Hover effects: Instant feedback
- Page transitions: Fade 200ms

---

## Accessibility

- WCAG 2.1 AA compliance
- Focus indicators visible
- Keyboard navigation
- ARIA labels for interactive elements
- Color contrast ratio ≥ 4.5:1

---

## Tailwind Config

```javascript
// tailwind.config.js
module.exports = {
  content: ['./src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
```
