# 09_responsive_and_accessibility.md

## Responsive and Accessibility Specification

### Responsive Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Mobile | < 640px | Stack composer vertically, full-width bubbles, 2-col preview grid |
| Tablet | 640-1024px | Side-by-side sender info + bubble, 3-col preview grid |
| Desktop | > 1024px | Max-width container (7xl), 4-col preview grid |

### Mobile Layout (< 640px)

#### Message List
- Full-width message bubbles
- Sender info stacked above bubble
- Status badge inline with sender name
- Public code below message
- Recall button full-width on own messages

#### Composer
- Vertical stack: sender name → textarea → image previews → send button
- Send button full-width
- Image previews: 2 columns
- Touch targets: minimum 44x44px

#### MessageItem
- Receipt card: full-width, image aspect ratio maintained
- Status badge: small size
- Actions stacked vertically

### Tablet Layout (640-1024px)

#### Message List
- Sender info + bubble side by side
- Max-width: 600px for bubbles
- Status badge in sender row

#### Composer
- Horizontal layout: attachment button | textarea | emoji | send
- Image previews: 3 columns
- Sender name inline with textarea

### Desktop Layout (> 1024px)

#### Message List
- Max-width: 4xl (896px) for comfortable reading
- Generous whitespace
- Smooth scroll animations

#### Composer
- Comfortable spacing
- Image previews: 4 columns
- All controls inline

### Accessibility Requirements

#### 1. Keyboard Navigation
- All interactive elements focusable (tabindex="0" or native)
- Visible focus rings (focus-visible)
- Logical tab order
- Escape key closes modals
- Enter/Space activates buttons

#### 2. Focus Management
- Modal opens → focus moves to first focusable element
- Modal closes → focus returns to trigger
- New messages → announce via aria-live
- Error messages → focus moves to error

#### 3. Screen Reader Support
- ARIA roles: dialog, status, log, button, listitem
- aria-live="polite" for message list
- aria-live="assertive" for errors
- aria-label on icon-only buttons
- aria-describedby for form hints

#### 4. Color Independence
- Status conveyed by: icon + text + color
- Never color alone for status
- High contrast ratios (WCAG AA minimum)
- Focus indicators visible in all themes

#### 5. Text Alternatives
- Images: alt="Biên lai {transaction_code} from {sender_name}"
- Icons: aria-hidden="true" with text labels
- Status icons: described by adjacent text

#### 6. Form Accessibility
- Labels associated with inputs (label for=id)
- Required fields marked (aria-required="true")
- Error messages linked (aria-describedby)
- Placeholder not used as label

#### 7. Motion Reduction
- Respect prefers-reduced-motion
- Disable animations when reduced
- No auto-playing animations

### Implementation Details

#### Focus Styles
```css
/* Global focus visible */
*:focus-visible {
  outline: 2px solid #38bdf8; /* sky-400 */
  outline-offset: 2px;
}

/* Custom focus for buttons */
.btn:focus-visible {
  ring: 2px solid #38bdf8;
  ring-offset: 2px;
  ring-offset-slate-950;
}
```

#### ARIA Live Regions
```tsx
// Message list
<div role="log" aria-live="polite" aria-label="Danh sách tin nhắn">

// Error toast
<div role="alert" aria-live="assertive">

// Status updates
<span role="status" aria-live="polite">
```

#### Keyboard Handlers
```tsx
// Modal close on Escape
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  };
  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}, [onClose]);

// Send on Enter, newline on Shift+Enter
const handleKeyDown = (e: React.KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (canSend) handleSubmit(e);
  }
};
```

#### Reduced Motion
```tsx
const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');

{!prefersReducedMotion && <AnimatePresence>...</AnimatePresence>}
```

### Testing Checklist

#### Keyboard Navigation
- [ ] Tab through all elements in order
- [ ] Shift+Tab reverse order
- [ ] Enter activates buttons
- [ ] Space activates buttons
- [ ] Escape closes modals
- [ ] Arrow keys in menus (if any)
- [ ] Focus visible at all times

#### Screen Reader (NVDA/JAWS/VoiceOver)
- [ ] Message list announces new messages
- [ ] Status changes announced
- [ ] Form labels read correctly
- [ ] Error messages announced
- [ ] Image alt text descriptive
- [ ] Modal title/description read

#### Color Contrast (WCAG AA)
- [ ] Text on background: 4.5:1 minimum
- [ ] Large text (18px+): 3:1 minimum
- [ ] UI components: 3:1 minimum
- [ ] Focus indicators: 3:1 minimum
- [ ] Status colors with text/icons

#### Zoom & Resize
- [ ] 200% zoom functional
- [ ] 400% zoom functional (text reflows)
- [ ] No horizontal scrolling at 320px width
- [ ] Touch targets 44x44px minimum

#### Reduced Motion
- [ ] Animations disabled
- [ ] Transitions instant
- [ ] No auto-playing content

#### Mobile Touch
- [ ] Touch targets 44x44px
- [ ] Swipe gestures work (if any)
- [ ] No hover-only interactions
- [ ] Viewport meta tag set