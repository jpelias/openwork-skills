---
name: ai-web-search
description: |
  Automate AI chat interactions via browser CDP on DeepSeek, ChatGPT, Claude, Gemini, and Kimi. 
  Covers: browser launch with remote debugging, DOM inspection, editor framework detection 
  (React textarea, ProseMirror, TipTap, Quill.js, Vue contenteditable), dynamic send button 
  discovery, response extraction, and platform-specific quirks. Use when comparing AI responses 
  or running batch prompts across platforms.
---

# AI Web Search — Browser Automation for AI Chat Platforms

Automate sending prompts to web-based AI chatbots via Vivaldi + CDP, then extract and compare responses.

## Step 0: Launch Vivaldi with CDP

```bash
pkill -f vivaldi 2>/dev/null
DISPLAY=:0.0 vivaldi \
  --remote-debugging-port=9222 \
  --no-first-run \
  --disable-session-crashed-bubble \
  > /tmp/vivaldi_cdp.log 2>&1 &
sleep 3
```

Verify: `browser_list { browser_url: "http://127.0.0.1:9222" }`

## Step 1: Navigate & Wait for SPA

```
browser_navigate { browser_url: "http://127.0.0.1:9222", url: "<url>" }
```

| Platform | URL | Login |
|----------|-----|-------|
| DeepSeek | `https://chat.deepseek.com` | No |
| ChatGPT | `https://chatgpt.com` | Yes |
| Claude | `https://claude.ai` | Yes |
| Gemini | `https://gemini.google.com/app` | Yes |
| Kimi | `https://www.kimi.com/` | Yes |

**Always wait 4-6s after navigation.** SPAs need time to hydrate. Check `document.readyState === 'complete'`.

## Step 2: DOM Inspection — Find Editor & Buttons

**Never assume the editor type.** Always run this diagnostic first:

```javascript
(() => {
  const inputs = document.querySelectorAll('input, textarea, [contenteditable="true"], [role="textbox"]');
  return Array.from(inputs).filter(el => el.getBoundingClientRect().width > 0).map(el => ({
    tag: el.tagName,
    role: el.getAttribute('role'),
    placeholder: el.placeholder || el.getAttribute('aria-label'),
    class: el.className?.substring(0,80),
    id: el.id,
    contenteditable: el.getAttribute('contenteditable'),
    framework: el.className.includes('ProseMirror') ? 'ProseMirror' :
               el.className.includes('tiptap') ? 'TipTap' :
               el.className.includes('ql-editor') ? 'Quill' :
               el.className.includes('chat-input-editor') ? 'Vue' :
               el.tagName === 'TEXTAREA' ? 'native-textarea' : 'unknown'
  }));
})()
```

### Real DOM Structures (verified July 2026)

| Platform | Editor Tag | Framework | Key Classes | ID |
|----------|-----------|-----------|-------------|-----|
| **DeepSeek** | `<textarea>` | React | `_27c9245 ds-scroll-area` | — |
| **ChatGPT** | `<div>` | **ProseMirror** | `ProseMirror` | `prompt-textarea` |
| **Claude** | `<div>` | **TipTap + ProseMirror** | `tiptap ProseMirror` | — |
| **Gemini** | `<div>` | **Quill.js** | `ql-editor ql-blank textarea new-input-ui` | — |
| **Kimi** | `<div>` | **Vue** | `chat-input-editor` | — |

**Critical insight:** ChatGPT's `id="prompt-textarea"` is a **DIV with ProseMirror**, not a `<textarea>`. Gemini uses Quill.js. Kimi uses Vue, not Lexical.

## Step 3: Insert Text — Framework-Specific

### 3a. Native `<textarea>` (DeepSeek only)

```javascript
const ta = document.querySelector('textarea');
ta.focus(); ta.click();
const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
setter.call(ta, 'your prompt');
ta.dispatchEvent(new Event('input', { bubbles: true }));
ta.dispatchEvent(new Event('change', { bubbles: true }));
```

### 3b. ProseMirror DIV (ChatGPT, Claude)

```javascript
const editor = document.querySelector('.ProseMirror[contenteditable="true"], [role="textbox"][contenteditable="true"]');
editor.focus();
editor.click();
// execCommand is the ONLY reliable method for ProseMirror:
document.execCommand('selectAll', false, null);
document.execCommand('delete', false, null);
document.execCommand('insertText', false, 'your prompt');
```

### 3c. Quill.js DIV (Gemini)

```javascript
const editor = document.querySelector('.ql-editor[contenteditable="true"]');
editor.focus();
editor.click();
document.execCommand('insertText', false, 'your prompt');
```

### 3d. Vue contenteditable DIV (Kimi)

```javascript
const editor = document.querySelector('.chat-input-editor[contenteditable="true"]');
editor.focus();
editor.click();  // Expands from compact homepage input to full chat
document.execCommand('insertText', false, 'your prompt');
```

**Golden rule:** `document.execCommand('insertText')` is universally reliable across all frameworks. Native setter + synthetic events fail on ProseMirror and Quill.

## Step 4: Find & Click Send Button

### Send Button Map (verified)

| Platform | Button Exists | When Visible | Exact Selector |
|----------|--------------|--------------|----------------|
| DeepSeek | ✅ Static | Always | `button.ds-button--primary.ds-button--filled.ds-button--circle` |
| ChatGPT | ✅ Dynamic | After text input | `button[data-testid="send-button"]` or `button[aria-label="Enviar prompt"]` |
| Claude | ✅ Dynamic | After text input | `button[aria-label="Enviar mensaje"]` |
| Gemini | ✅ Dynamic | After text input | `button[aria-label="Enviar mensaje"]` |
| Kimi | ❌ None | Never | Use Enter key only |

### Send Button Discovery Script

```javascript
// Find send button after typing text
const btn =
  document.querySelector('button[data-testid="send-button"]') ||          // ChatGPT
  document.querySelector('button[aria-label="Enviar prompt"]') ||         // ChatGPT alt
  document.querySelector('button[aria-label="Enviar mensaje"]') ||        // Claude, Gemini
  document.querySelector('[class*="ds-button--primary"][class*="filled"]'); // DeepSeek

if (btn && !btn.disabled) {
  btn.click();
} else {
  // Fallback: Enter key (Kimi, or any platform)
  editor.dispatchEvent(new KeyboardEvent('keydown', {
    key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true, cancelable: true
  }));
}
```

### Dynamic Button Timing

Send buttons on ChatGPT, Claude, and Gemini are **not in the DOM until text is typed AND React/Vue re-renders**. After inserting text, wait 500-800ms before querying:

```javascript
document.execCommand('insertText', false, 'prompt');
setTimeout(() => {
  document.querySelector('button[aria-label="Enviar prompt"]')?.click();
}, 600);
```

### Avoid ChatGPT Attach Button Trap

ChatGPT has two adjacent buttons at the bottom:
- `button.composer-btn` at ~694,451 → **Attach** (`aria-label="Añadir archivos y más"`)
- `button.composer-submit-btn` at ~1410,451 → **Send** (`aria-label="Enviar prompt"`, `data-testid="send-button"`)

Always use `aria-label` or `data-testid`, never positional selectors.

## Step 5: Wait for Response

```bash
sleep 15  # Baseline
```

| Platform | Free Tier Wait | Thinking Indicators |
|----------|---------------|---------------------|
| DeepSeek | 8-12s | — |
| ChatGPT | 15-25s | — |
| Claude | 20-40s | "Cogitating" → "Picturing" → "Weighing" → "Synthesized..." |
| Gemini | 10-15s | — |
| Kimi | 12-20s | Search result count appears before text |

**Check if still thinking:**
```javascript
document.body.innerText.includes('Cogitating') ||
document.body.innerText.includes('Picturing') ||
document.body.innerText.includes('respondiendo')
```

## Step 6: Extract Response

### Platform Markers

| Platform | Response Starts With | Response Ends Before |
|----------|---------------------|---------------------|
| DeepSeek | Text in `[class*="ds-markdown"]` | Next UI chrome |
| ChatGPT | Text in `[data-message-author-role="assistant"]` | Next `[data-message-author-role="user"]` |
| Claude | Text after `Claude ha respondido` or topic keyword | `Has dicho:` |
| Gemini | `Gemini ha dicho` | `Has dicho` or `Flash` |
| Kimi | `Aquí tien` | `Pregunta cualquier cosa` or `Instantáneo` |

### Universal Extraction Strategy

```javascript
// 1. Try semantic selector first
let text = document.querySelector('[data-message-author-role="assistant"]')?.innerText;

// 2. If not found, search body text for platform marker
if (!text) {
  const body = document.body.innerText;
  const markers = ['Gemini ha dicho', 'Claude ha respondido', 'Aquí tien'];
  for (const m of markers) {
    const idx = body.indexOf(m);
    if (idx >= 0) {
      const after = body.substring(idx);
      const endMarkers = ['Has dicho', 'Pregunta cualquier cosa', 'Instantáneo', 'Flash\n'];
      let end = after.length;
      for (const em of endMarkers) {
        const i = after.indexOf(em, 30);
        if (i > 0 && i < end) end = i;
      }
      text = after.substring(0, end);
      break;
    }
  }
}

// 3. DeepSeek: longest ds-markdown block
if (!text) {
  document.querySelectorAll('[class*="ds-markdown"]').forEach(m => {
    if (m.innerText.length > (text?.length || 0)) text = m.innerText;
  });
}
```

## Step 7: Follow-up Questions

1. Locate editor again (DOM may have shifted after response)
2. Focus → selectAll → delete → insertText
3. Wait 600ms for dynamic button
4. Click send or press Enter
5. Wait for response
6. Extract

**Claude chat recovery:** If you navigate away, Claude auto-renames chats. Find the link in sidebar:

```javascript
const links = document.querySelectorAll('a[href*="/chat/"]');
const chatLink = Array.from(links).find(l => l.innerText.includes('guerra'));
// Navigate to chatLink.href
```

## Full Workflow: ChatGPT (hardest platform)

```javascript
// 1. Navigate
browser_navigate { url: "https://chatgpt.com" }
sleep 5

// 2. Inspect
browser_eval { expression: "document.querySelector('.ProseMirror')?.getAttribute('role')" }

// 3. Type (ProseMirror needs execCommand)
browser_eval { expression: `
  (() => {
    const editor = document.querySelector('#prompt-textarea');
    editor.focus(); editor.click();
    document.execCommand('selectAll', false, null);
    document.execCommand('insertText', false, 'la historia de la guerra de troya');
    return editor.innerText;
  })()
` }

// 4. Wait for React re-render, then click send
browser_eval { expression: `
  new Promise(r => setTimeout(() => {
    document.querySelector('button[data-testid="send-button"]')?.click();
    r('clicked');
  }, 600))
` }

// 5. Wait
sleep 20

// 6. Extract
browser_eval { expression: `
  document.querySelector('[data-message-author-role="assistant"]')?.innerText
` }
```

## Framework Detection Reference

| Class Pattern | Framework | Editor Behavior |
|---------------|-----------|-----------------|
| `.ProseMirror` (DIV) | ProseMirror | Rich text, needs `execCommand` |
| `.tiptap` | TipTap (ProseMirror wrapper) | Same as ProseMirror |
| `.ql-editor` | Quill.js | Rich text, `execCommand` works |
| `.chat-input-editor` | Vue custom | contenteditable, Enter to send |
| `<textarea>` (native) | React controlled | Native setter + input event |

## Troubleshooting

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| `browser_snapshot` returns RootWebArea only | SPA doesn't populate AXTree | Use `browser_eval` exclusively |
| `execCommand` returns false | Editor not focused or not contenteditable | Call `.focus()` + `.click()` first |
| Send button not found | Dynamic button not yet rendered | Wait 600-1000ms after text input |
| Text appears but React ignores it | Synthetic events not bubbling | Use `execCommand('insertText')` instead |
| Claude stuck "Cogitating" >30s | Free tier slow | Wait up to 60s, then check with eval |
| Kimi text disappears | Editor re-rendered on click | Click editor first, wait 500ms, then insert |
| Lost conversation after navigate | Single CDP target replaced page | Navigate back to chat UUID URL |
| Wrong button clicked on ChatGPT | Attach button near send button | Always use `data-testid="send-button"` |
