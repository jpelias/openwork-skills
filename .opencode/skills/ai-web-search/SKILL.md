---
name: ai-web-search
description: |
  Automate AI chat interactions via Vivaldi CDP on any AI chat platform.
  Anti-fragile design: behavioral detection over brittle selectors, multi-layer
  fallback chains, self-healing DOM discovery, MutationObserver for streaming,
  and universal methods that survive UI redesigns. Covers: Vivaldi launch with
  remote debugging, platform detection by URL, heuristic editor/send/response
  discovery, locale-agnostic operation, streaming polling, error handling.
  Use when comparing AI responses or running batch prompts across platforms.
---

# AI Web Search — Anti-Fragile Browser Automation for AI Chat Platforms

Automate sending prompts to web-based AI chatbots via Vivaldi + CDP (port 9222),
then extract and compare responses. Every operation uses **behavioral detection first,
structural selectors as hints only**, so the skill survives UI redesigns, framework
migrations, class name changes, and locale differences.

---

## Design Principles

1. **Behavior > Structure** — detect what an element DOES, not what class it HAS.
   An editor is "a visible contenteditable element near the bottom of the page",
   not "`.ProseMirror`" or "`#prompt-textarea`".
2. **Multi-layer fallback** — every operation tries 3+ strategies. Known selectors
   are hints (fast path), not requirements.
3. **Self-healing** — when a known selector breaks, heuristic DOM scanning finds
   the right element automatically.
4. **Universal methods** — `execCommand('insertText')` works on every framework.
   Use it as primary, not as last resort.
5. **MutationObserver > polling classes** — detect streaming by watching DOM
   mutations, not by checking specific class names that may be renamed.
6. **URL identifies platform** — `window.location.hostname` tells us which hints
   to try first, but the universal fallbacks work on ANY platform.

---

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

Verify:

```
browser_list { browser_url: "http://127.0.0.1:9222" }
```

> If Vivaldi is already running without CDP, kill it first — `--remote-debugging-port`
> only takes effect on launch. Profile, cookies, and extensions are preserved.

---

## Step 1: Navigate & Wait for SPA

```
browser_navigate { browser_url: "http://127.0.0.1:9222", url: "<url>" }
```

### Known Platform URLs (hints — any URL works with the universal methods)

| Platform | URL | Login |
|----------|-----|:-----:|
| DeepSeek | `https://chat.deepseek.com` | No |
| ChatGPT | `https://chatgpt.com` | Yes |
| Claude | `https://claude.ai` | Yes |
| Gemini | `https://gemini.google.com/app` | Yes |
| Kimi | `https://www.kimi.com/` | Yes |
| Perplexity | `https://www.perplexity.ai` | No |
| Grok | `https://grok.com` | Yes |
| Mistral | `https://chat.mistral.ai` | Yes |
| Copilot | `https://copilot.microsoft.com` | No |

### Wait for SPA Hydration

**Never assume the page is ready.** Use this universal wait:

```javascript
new Promise(r => {
  const check = () => {
    if (document.readyState === 'complete' && document.querySelector(
      '[contenteditable="true"], [contenteditable=""], textarea, [role="textbox"]'
    )) r('ready');
    else if (Date.now() - start > 15000) r('timeout');
    else setTimeout(check, 1000);
  };
  const start = Date.now();
  setTimeout(check, 3000);
})
```

This waits until `readyState === 'complete'` AND an editor element exists in the DOM.
Timeout: 15s. Works on any platform.

---

## Step 2: Detect Platform & Find Editor

### Platform Detection (URL-based, not selector-based)

```javascript
(() => {
  const h = window.location.hostname;
  const p = window.location.pathname;
  return {
    platform:
      h.includes('deepseek') ? 'deepseek' :
      h.includes('chatgpt') || h.includes('chat.openai') ? 'chatgpt' :
      h.includes('claude') ? 'claude' :
      h.includes('gemini') ? 'gemini' :
      h.includes('kimi') ? 'kimi' :
      h.includes('perplexity') ? 'perplexity' :
      h.includes('grok') ? 'grok' :
      h.includes('mistral') ? 'mistral' :
      h.includes('copilot') || h.includes('microsoft') ? 'copilot' :
      'unknown',
    hostname: h,
    path: p
  };
})()
```

### Universal Editor Finder (anti-fragile)

This script finds the editor by **behavior**, not by class name. It tries known
selectors first (fast path), then falls back to heuristic scanning.

```javascript
(() => {
  // === LAYER 1: Known selectors (fast path, may break on updates) ===
  const knownSelectors = {
    deepseek:  ['textarea'],
    chatgpt:   ['#prompt-textarea', '.ProseMirror[contenteditable="true"]'],
    claude:    ['.ProseMirror[contenteditable="true"]', '[role="textbox"][contenteditable="true"]'],
    gemini:    ['.ql-editor[contenteditable="true"]'],
    kimi:      ['.chat-input-editor[contenteditable="true"]'],
    perplexity: ['textarea'],
    grok:      ['.ProseMirror[contenteditable="true"]'],
    mistral:   ['#query', 'textarea'],
    copilot:   ['[contenteditable="true"][role="textbox"]']
  };

  const platform = (() => {
    const h = window.location.hostname;
    if (h.includes('deepseek')) return 'deepseek';
    if (h.includes('chatgpt') || h.includes('chat.openai')) return 'chatgpt';
    if (h.includes('claude')) return 'claude';
    if (h.includes('gemini')) return 'gemini';
    if (h.includes('kimi')) return 'kimi';
    if (h.includes('perplexity')) return 'perplexity';
    if (h.includes('grok')) return 'grok';
    if (h.includes('mistral')) return 'mistral';
    if (h.includes('copilot') || h.includes('microsoft')) return 'copilot';
    return 'unknown';
  })();

  // Try platform-specific selectors first
  if (knownSelectors[platform]) {
    for (const sel of knownSelectors[platform]) {
      const el = document.querySelector(sel);
      if (el && el.getBoundingClientRect().width > 0) {
        return {
          found: true, layer: 'known', platform, selector: sel,
          tag: el.tagName, contenteditable: el.getAttribute('contenteditable'),
          id: el.id, class: el.className?.substring(0, 80)
        };
      }
    }
  }

  // === LAYER 2: Generic semantic selectors ===
  const genericSelectors = [
    '[contenteditable="true"][role="textbox"]',
    '[contenteditable="true"]',
    '[contenteditable=""]',
    'textarea',
    '[role="textbox"]'
  ];
  for (const sel of genericSelectors) {
    const el = document.querySelector(sel);
    if (el && el.getBoundingClientRect().width > 0) {
      return {
        found: true, layer: 'generic', platform, selector: sel,
        tag: el.tagName, contenteditable: el.getAttribute('contenteditable'),
        id: el.id, class: el.className?.substring(0, 80)
      };
    }
  }

  // === LAYER 3: Heuristic — find the lowest visible contenteditable on page ===
  const allEditable = Array.from(document.querySelectorAll(
    '[contenteditable="true"], [contenteditable=""], textarea, [role="textbox"]'
  )).filter(el => el.getBoundingClientRect().width > 50);

  if (allEditable.length > 0) {
    // Pick the one closest to the bottom of the viewport
    const sorted = allEditable.sort((a, b) =>
      b.getBoundingClientRect().top - a.getBoundingClientRect().top
    );
    const el = sorted[0];
    return {
      found: true, layer: 'heuristic-position', platform,
      tag: el.tagName, contenteditable: el.getAttribute('contenteditable'),
      id: el.id, class: el.className?.substring(0, 80),
      rect: el.getBoundingClientRect()
    };
  }

  return { found: false, platform, reason: 'No editable element found on page' };
})()
```

### Detect Editor Framework (behavioral, not class-based)

```javascript
(() => {
  const el = document.querySelector(
    '[contenteditable="true"], [contenteditable=""], textarea, [role="textbox"]'
  );
  if (!el) return { framework: 'none' };

  // Behavioral tests
  const isTextarea = el.tagName === 'TEXTAREA';
  const isContenteditable = el.getAttribute('contenteditable') === 'true' ||
                            el.getAttribute('contenteditable') === '';
  const hasProseMirror = el.querySelector('.ProseMirror') !== null ||
                          el.className?.includes('ProseMirror') ||
                          el.className?.includes('tiptap');
  const hasQuill = el.className?.includes('ql-editor') ||
                   el.querySelector('.ql-editor') !== null;
  const hasLexical = el.getAttribute('data-lexical-editor') !== null ||
                     el.querySelector('[data-lexical-editor]') !== null;

  // Check for React (fiber keys on element)
  const hasReact = Object.keys(el).some(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));

  return {
    framework:
      hasProseMirror ? 'prosemirror' :
      hasQuill ? 'quill' :
      hasLexical ? 'lexical' :
      isTextarea && hasReact ? 'react-textarea' :
      isTextarea ? 'native-textarea' :
      isContenteditable ? 'contenteditable' : 'unknown',
    tag: el.tagName,
    id: el.id,
    class: el.className?.substring(0, 80),
    insertMethod:
      isTextarea ? 'native-setter' :
      isContenteditable || hasProseMirror || hasQuill || hasLexical ? 'execCommand' :
      'unknown'
  };
})()
```

---

## Step 3: Insert Text — Universal Method First

### Universal Insert (works on ANY platform, ANY framework)

This single script handles all editor types. It detects the editor, picks the
right insertion method, and verifies the text was inserted.

```javascript
(() => {
  const prompt = 'YOUR_PROMPT_HERE';

  // 1. Find editor (reuse universal finder logic)
  const candidates = Array.from(document.querySelectorAll(
    '[contenteditable="true"], [contenteditable=""], textarea, [role="textbox"]'
  )).filter(el => el.getBoundingClientRect().width > 50);

  // Pick the lowest visible one (most likely the input)
  candidates.sort((a, b) => b.getBoundingClientRect().top - a.getBoundingClientRect().top);
  const editor = candidates[0];

  if (!editor) return { success: false, reason: 'No editor found' };

  // 2. Focus and activate
  editor.focus();
  editor.click();

  // 3. Insert text — method depends on editor type
  const isTextarea = editor.tagName === 'TEXTAREA';

  if (isTextarea) {
    // Native textarea: use property setter + events
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
    setter.call(editor, prompt);
    editor.dispatchEvent(new Event('input', { bubbles: true }));
    editor.dispatchEvent(new Event('change', { bubbles: true }));
  } else {
    // Contenteditable (ProseMirror, Quill, TipTap, Lexical, Vue, generic):
    // execCommand is the universal method that works everywhere
    editor.focus();
    // Clear existing content first
    document.execCommand('selectAll', false, null);
    document.execCommand('delete', false, null);
    const result = document.execCommand('insertText', false, prompt);

    // Fallback if execCommand fails (removed from browser, or editor not focused)
    if (!result || editor.innerText.trim().length === 0) {
      // Try InputEvent method
      const sel = window.getSelection();
      sel.selectAllChildren(editor);
      sel.deleteFromDocument();
      editor.dispatchEvent(new InputEvent('beforeinput', {
        inputType: 'insertText', data: prompt, bubbles: true, cancelable: true
      }));
      editor.dispatchEvent(new InputEvent('input', {
        inputType: 'insertText', data: prompt, bubbles: true
      }));
    }
  }

  // 4. Verify insertion
  const inserted = isTextarea ? editor.value : editor.innerText;
  const success = inserted.includes(prompt.substring(0, 30));

  return {
    success,
    method: isTextarea ? 'native-setter' : 'execCommand',
    insertedLength: inserted.trim().length,
    editorTag: editor.tagName,
    editorId: editor.id || null,
    editorClass: editor.className?.substring(0, 60) || null
  };
})()
```

### Platform-Specific Hints (optional fast paths)

These are shortcuts for known platforms. If they break, the universal method above
still works. Only use these if you want to skip the auto-detection.

| Platform | Editor Type | Fast Selector | Insert Method |
|----------|-----------|---------------|---------------|
| DeepSeek | textarea | `textarea` | native setter |
| ChatGPT | ProseMirror div | `#prompt-textarea` | execCommand |
| Claude | TipTap/PM div | `.ProseMirror[contenteditable]` | execCommand |
| Gemini | Quill div | `.ql-editor[contenteditable]` | execCommand |
| Kimi | Vue div | `.chat-input-editor[contenteditable]` | execCommand |
| Perplexity | textarea | `textarea` | native setter |
| Grok | ProseMirror div | `.ProseMirror[contenteditable]` | execCommand |
| Mistral | textarea | `#query` or `textarea` | native setter |
| Copilot | contenteditable div | `[contenteditable="true"]` | execCommand |

> **These selectors WILL break eventually.** The universal method won't.

---

## Step 4: Find & Click Send Button — Universal Discovery

### Universal Send Button Finder (anti-fragile)

Finds the send button by **behavioral properties**, not by class name. Tries
known selectors first, then scans for buttons near the editor.

```javascript
(() => {
  // 1. Find the editor (to locate nearby buttons)
  const candidates = Array.from(document.querySelectorAll(
    '[contenteditable="true"], [contenteditable=""], textarea, [role="textbox"]'
  )).filter(el => el.getBoundingClientRect().width > 50);
  candidates.sort((a, b) => b.getBoundingClientRect().top - a.getBoundingClientRect().top);
  const editor = candidates[0];
  if (!editor) return { action: 'failed', reason: 'No editor found' };

  const editorRect = editor.getBoundingClientRect();

  // === LAYER 1: Known selectors (fast path) ===
  const knownButtons = [
    'button[data-testid="send-button"]',                    // ChatGPT
    'button[data-testid*="send" i]',                        // Generic testid
    'button[data-testid*="submit" i]',                      // Generic testid
  ];

  for (const sel of knownButtons) {
    const btn = document.querySelector(sel);
    if (btn && !btn.disabled && !btn.getAttribute('aria-disabled')) {
      btn.click();
      return { action: 'clicked', layer: 'known-testid', selector: sel };
    }
  }

  // === LAYER 2: aria-label matching (locale-agnostic) ===
  const sendWords = [
    'Send', 'Submit', 'Enviar', 'Envoyer', 'Absenden', 'Invia',
    '送信', '发送', '전송', 'Отправить', 'Gönder'
  ];
  const allButtons = document.querySelectorAll('button, [role="button"], button[type="submit"]');
  for (const btn of allButtons) {
    const label = (btn.getAttribute('aria-label') || btn.title || btn.innerText || '').toLowerCase();
    if (sendWords.some(w => label.includes(w.toLowerCase()))) {
      if (!btn.disabled && !btn.getAttribute('aria-disabled') &&
          btn.getBoundingClientRect().width > 0) {
        // Exclude attach/upload buttons
        const excludeWords = ['attach', 'upload', 'adjuntar', 'subir', 'añadir', 'add file'];
        if (!excludeWords.some(w => label.includes(w))) {
          btn.click();
          return { action: 'clicked', layer: 'aria-label', label: btn.getAttribute('aria-label') };
        }
      }
    }
  }

  // === LAYER 3: Heuristic — find enabled button near the editor ===
  // Look for buttons within 150px below or beside the editor
  const nearbyButtons = Array.from(document.querySelectorAll(
    'button, [role="button"], button[type="submit"]'
  )).filter(btn => {
    if (btn.disabled || btn.getAttribute('aria-disabled')) return false;
    if (btn.getBoundingClientRect().width < 20) return false;  // invisible
    const r = btn.getBoundingClientRect();
    // Button must be near the editor (within 200px vertically, below or same level)
    const verticalDist = Math.abs(r.top - editorRect.bottom);
    const horizontalOverlap = !(r.right < editorRect.left || r.left > editorRect.right);
    return verticalDist < 200 && horizontalOverlap;
  });

  // Prefer the rightmost button (send is usually on the right, attach on the left)
  nearbyButtons.sort((a, b) => b.getBoundingClientRect().left - a.getBoundingClientRect().left);

  if (nearbyButtons.length > 0) {
    const btn = nearbyButtons[0];
    // Extra check: exclude buttons with attach/upload icons or labels
    const label = (btn.getAttribute('aria-label') || btn.title || '').toLowerCase();
    const excludeWords = ['attach', 'upload', 'adjuntar', 'subir', 'añadir', 'add file', 'file'];
    if (!excludeWords.some(w => label.includes(w))) {
      btn.click();
      return { action: 'clicked', layer: 'heuristic-nearby', label: btn.getAttribute('aria-label') || null };
    }
    // If the rightmost is attach, try the second rightmost
    if (nearbyButtons.length > 1) {
      nearbyButtons[1].click();
      return { action: 'clicked', layer: 'heuristic-nearby-2nd', label: nearbyButtons[1].getAttribute('aria-label') || null };
    }
  }

  // === LAYER 4: Platform-specific class patterns (last resort hints) ===
  const platformHints = [
    '[class*="ds-button--primary"][class*="filled"]',  // DeepSeek
    '[class*="send"]',                                  // Generic
    '[class*="submit"]',                                // Generic
  ];
  for (const sel of platformHints) {
    const btn = document.querySelector(sel);
    if (btn && !btn.disabled && btn.getBoundingClientRect().width > 0) {
      btn.click();
      return { action: 'clicked', layer: 'platform-hint', selector: sel };
    }
  }

  // === LAYER 5: Enter key fallback ===
  editor.dispatchEvent(new KeyboardEvent('keydown', {
    key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true, cancelable: true
  }));
  return { action: 'enter-key', layer: 'fallback', target: editor.tagName };
})()
```

### Dynamic Button Timing

On many platforms, the send button is **not in the DOM until text is typed**.
After inserting text, wait 500-800ms before searching for the button:

```javascript
// After insertText...
await new Promise(r => setTimeout(r, 600));
// Then run the universal send button finder
```

### ChatGPT Attach Button Trap

ChatGPT places an Attach button next to the Send button. The heuristic finder
above handles this by:
1. Preferring `data-testid="send-button"` (exact match)
2. Excluding buttons with "attach/upload" in their label
3. Sorting nearby buttons right-to-left (send is rightmost)

---

## Step 5: Wait for Response — MutationObserver + Stability

**Never use fixed `sleep`.** Use MutationObserver to detect when the response
stops changing, plus a stability counter to confirm completion.

### Universal Streaming Poll (works on any platform)

```javascript
new Promise(r => {
  const start = Date.now();
  const maxWait = 120000;   // 2 min hard timeout
  const interval = 2000;    // check every 2s
  let lastText = '';
  let stableCount = 0;
  let observer = null;

  // === METHOD 1: MutationObserver (detects DOM changes in real-time) ===
  // Watch the main content area for mutations
  const watchRoot = document.querySelector('main, [role="main"], #root, #app, body');
  let mutationDetected = false;

  if (watchRoot && typeof MutationObserver !== 'undefined') {
    observer = new MutationObserver(() => { mutationDetected = true; });
    observer.observe(watchRoot, { childList: true, subtree: true, characterData: true });
  }

  const check = () => {
    // Find the response container (universal heuristic)
    const responseCandidates = Array.from(document.querySelectorAll(
      '[data-message-author-role="assistant"], ' +
      '[class*="markdown"], [class*="prose"], [class*="message-content"], ' +
      '[class*="response"], [class*="answer"], [class*="ds-markdown"]'
    ));
    // Take the last (most recent) visible one
    const response = responseCandidates.filter(el =>
      el.getBoundingClientRect().width > 0
    ).pop();

    const currentText = response?.innerText?.trim() || '';
    const currentLength = currentText.length;

    // Check if still streaming via known indicators
    const streamingIndicators = document.querySelector(
      '.result-streaming, [class*="streaming"], [class*="typing"], ' +
      '[class*="loading"]:not([class*="loaded"]), [class*="animate"]'
    );

    // Check thinking text (locale-agnostic)
    const bodyText = document.body.innerText;
    const thinkingWords = [
      'Cogitat', 'Pictur', 'Weigh', 'Synthesized',
      'Thinking', 'Generat', 'Searching',
      'respondiendo', 'pensando', 'buscando',
      'Search', 'Analyz'
    ];
    const isThinking = thinkingWords.some(w => bodyText.includes(w));

    if (streamingIndicators || isThinking || mutationDetected) {
      mutationDetected = false;
      stableCount = 0;
      if (Date.now() - start > maxWait) {
        observer?.disconnect();
        r({ done: false, reason: 'timeout', length: currentLength, text: currentText });
        return;
      }
      setTimeout(check, interval);
      return;
    }

    // Check stability: same text length for 3 consecutive checks
    if (currentLength > 0 && currentLength === lastText.length) {
      stableCount++;
      if (stableCount >= 3) {
        observer?.disconnect();
        r({ done: true, length: currentLength, text: currentText });
        return;
      }
    } else {
      stableCount = 0;
    }
    lastText = currentText;

    if (Date.now() - start > maxWait) {
      observer?.disconnect();
      r({ done: false, reason: 'timeout', length: currentLength, text: currentText });
      return;
    }
    setTimeout(check, interval);
  };

  // Initial delay — give the model time to start generating
  setTimeout(check, 5000);
})
```

### How It Works

1. **MutationObserver** watches the main content area for DOM changes in real-time.
   While mutations are firing, the response is still being written.
2. **Known streaming indicators** (`.result-streaming`, etc.) are checked as hints.
3. **Thinking text** is checked with partial word matches (locale-agnostic).
4. **Stability counter** confirms the response is complete when the text length
   stays the same for 3 consecutive checks (6 seconds).
5. **Hard timeout** at 120s prevents infinite waits.

> **CDP timeout caveat:** The polling script runs inside `browser_eval` which has a
> 130s CDP limit. For very long responses (complex questions with code examples),
> the polling may time out before the response completes. In that case, **fall back
> to fixed `sleep` + manual extraction**:
>
> ```bash
> sleep 30  # adjust based on expected response length
> ```
>
> Then run the extractor directly (Step 6). If the response is still incomplete,
> wait another 15s and extract again. Check for streaming indicators between sleeps.

---

## Step 6: Extract Response — Universal Heuristic

### Universal Response Extractor (works on any platform)

```javascript
(() => {
  // === LAYER 1: Semantic selectors (hints, may break) ===
  const semanticSelectors = [
    '[data-message-author-role="assistant"]',   // ChatGPT
    '[class*="ds-markdown"]',                    // DeepSeek
    '[class*="model-response"]',                 // Gemini
    '[class*="message-content"]',                // Kimi, Grok, Copilot
    '[class*="prose"]',                          // Claude, Perplexity, Mistral
    '[class*="response-text"]',                  // Generic
    '[class*="answer"]',                         // Perplexity
    '[class*="assistant-message"]',              // Generic alt
    '[class*="bot-message"]',                    // Generic alt
    '[class*="ai-message"]',                     // Generic alt
    '[data-is-streaming="false"]',               // Generic streaming-done marker
  ];

  let text = '';
  let source = '';

  for (const sel of semanticSelectors) {
    try {
      const elements = document.querySelectorAll(sel);
      const last = elements[elements.length - 1];
      if (last && last.innerText.trim().length > text.length) {
        text = last.innerText.trim();
        source = sel;
      }
    } catch (e) { /* selector syntax may be invalid on some browsers */ }
  }

  // === LAYER 2: Heuristic — find the last large text block in the conversation ===
  if (!text || text.length < 20) {
    // Find the main conversation container
    const mainAreas = document.querySelectorAll(
      'main, [role="main"], [role="log"], [class*="conversation"], ' +
      '[class*="chat"], [class*="messages"], [id*="chat"], [id*="messages"]'
    );

    for (const area of mainAreas) {
      // Find direct children that look like message blocks
      const blocks = Array.from(area.children).filter(child => {
        const t = child.innerText?.trim();
        return t && t.length > 50 && t.length < 200000;
      });

      // Take the last block (most recent response)
      if (blocks.length > 0) {
        const last = blocks[blocks.length - 1];
        if (last.innerText.trim().length > text.length) {
          text = last.innerText.trim();
          source = 'heuristic-conversation-last';
        }
      }
    }
  }

  // === LAYER 3: Brute force — longest visible text block on page ===
  if (!text || text.length < 20) {
    const allBlocks = document.querySelectorAll('div, article, section, p');
    let maxLen = 0;
    allBlocks.forEach(b => {
      const t = b.innerText?.trim();
      // Heuristic: long text, few direct children (not UI chrome), visible
      if (t && t.length > maxLen && t.length < 200000 &&
          b.children.length < 15 &&
          b.getBoundingClientRect().width > 100) {
        maxLen = t.length;
        text = t;
        source = 'heuristic-longest-block';
      }
    });
  }

  // === LAYER 4: Distinguish user vs assistant text ===
  // If we found text but it might be the user's prompt, check for markers
  if (text.length > 0) {
    // Look for the user's prompt text in the page
    const userText = document.querySelector(
      '[data-message-author-role="user"], [class*="user-message"], [class*="human-message"]'
    )?.innerText?.trim();

    // If the extracted text starts with the user's prompt, strip it
    if (userText && text.startsWith(userText)) {
      text = text.substring(userText.length).trim();
      source += ' (stripped-user-prefix)';
    }
  }

  // Return FULL text. No substring truncation.
  // For responses >50k chars stored in innerText, the text IS the full text
  // (browser innerText limit is ~65k per DOM node, and the heuristic already
  //  filters blocks < 200k chars to avoid grabbing the entire body).
  return { text, source, length: text.length, truncated: false };

  // If innerText was capped by the browser (rare), the agent can do a
  // second extraction pass with a different heuristic (e.g., iterate
  // child paragraphs of the response container and concatenate).
})()
```

### Chunked Extraction for Long Responses (>10k chars)

When the response is very long, `browser_eval` may hit CDP timeouts during extraction.
The polling script also times out at 130s if the response generation takes too long.

**Strategy: extract landmarks first, then fetch by chunks.**

```javascript
// STEP 6a: Get landmarks (section titles + response length)
(() => {
  const b = document.body.innerText;
  const idx = b.indexOf('Aquí tien') || b.indexOf('Gemini ha dicho') ||
              b.indexOf('Claude ha respondido') || 0;
  const text = b.substring(idx);
  // Find section headers (lines ending with numbers, or short lines followed by blocks)
  const lines = text.split('\n');
  const landmarks = [];
  lines.forEach((l, i) => {
    const t = l.trim();
    if (t.length > 0 && t.length < 80 && (
        /^\d+\.\s/.test(t) || /^[A-ZÁÉÍÓÚ]/.test(t)
    ) && i > 0) {
      landmarks.push({ index: i, title: t.substring(0, 60) });
    }
  });
  return { totalLength: text.length, landmarks, firstChunk: text.substring(0, 500) };
})()
```

```javascript
// STEP 6b: Fetch specific chunk by character range
(() => {
  const b = document.body.innerText;
  const start = 0;      // set by agent based on landmarks
  const chunkSize = 4000; // safe for CDP
  return b.substring(start, start + chunkSize);
})()
```

**When to use chunked extraction:**
- Response length > 8000 chars → extract in 4k chunks
- CDP timeout on single `browser_eval` → switch to chunked
- Polling with MutationObserver times out → fall back to fixed `sleep` + manual extraction

### Detect Truncated or Refused Responses

```javascript
(() => {
  const refusalPatterns = [
    /I (?:can't|cannot|won't) (?:help|assist|provide|do that|comply)/i,
    /I'm (?:not able|unable) to/i,
    /No puedo (?:ayudar|asistir|proporcionar)/i,
    /This content may violate/i,
    /against my (?:guidelines|policies)/i,
    /I must (?:decline|refuse)/i,
    /I will not/i,
    /not appropriate/i,
    /cannot be completed/i,
  ];

  const truncationPatterns = [
    /\[.*truncat/i,
    /response was cut/i,
    /continu[ae]\s*\.{2,}$/im,
    /output limited/i,
    /hit the (?:length|token) limit/i,
  ];

  const bodyText = document.body.innerText;
  const isRefused = refusalPatterns.some(p => p.test(bodyText));
  const isTruncated = truncationPatterns.some(p => p.test(bodyText));

  return { isRefused, isTruncated };
})()
```

---

## Step 7: Follow-up Questions

1. Re-run the **universal editor finder** (DOM may have shifted after response)
2. Insert text with the **universal insert** method
3. Wait 600ms for dynamic button
4. Run the **universal send button finder**
5. Run the **streaming poll**
6. Run the **universal response extractor**

> Always re-discover elements on each turn. Never cache selectors between turns —
> the DOM changes after every response.

### Start New Chat vs. Continue

| Platform | New Chat Action | Continue Existing |
|----------|----------------|-------------------|
| DeepSeek | Navigate to root URL | Stay on current page |
| ChatGPT | Navigate to `https://chatgpt.com/` | URL has `/c/` + UUID |
| Claude | Navigate to `https://claude.ai/` | URL has `/chat/` + UUID |
| Gemini | Navigate to `https://gemini.google.com/app` | Stay on current page |
| Kimi | Click new chat icon | Stay on current page |
| Perplexity | Navigate to `https://www.perplexity.ai/` | URL has thread ID |
| Grok | Navigate to `https://grok.com/` | Stay on current page |
| Mistral | Navigate to `https://chat.mistral.ai/` | Stay on current page |
| Copilot | Navigate to `https://copilot.microsoft.com/` | Stay on current page |

### Chat Recovery (any platform with sidebar)

```javascript
// Find chat links in sidebar by keyword
(() => {
  const links = document.querySelectorAll('a[href*="/chat/"], a[href*="/c/"], a[href*="thread"]');
  return Array.from(links).map(l => ({
    text: l.innerText.trim().substring(0, 60),
    href: l.href
  })).filter(l => l.text.length > 0);
})()
```

---

## Step 8: Error Handling — Universal Detection

### Universal Error Detector

```javascript
(() => {
  const bodyText = document.body.innerText;
  const url = window.location.href;

  // Login detection
  const loginSignals = [
    () => document.querySelector('input[type="password"]') !== null,
    () => document.querySelector('form[action*="login"], form[action*="auth"], form[action*="signin"]') !== null,
    () => /\/(login|signin|auth|sign-up|signup)\b/i.test(url),
    () => /log\s*in|sign\s*in|create\s*account|sign\s*up/i.test(bodyText.substring(0, 2000)),
  ];

  // CAPTCHA detection
  const captchaSignals = [
    () => document.querySelector('iframe[src*="recaptcha"]') !== null,
    () => document.querySelector('iframe[src*="hcaptcha"]') !== null,
    () => document.querySelector('iframe[src*="turnstile"]') !== null,
    () => document.querySelector('[class*="captcha"], [id*="captcha"]') !== null,
    () => /captcha|challenge/i.test(bodyText.substring(0, 2000)),
  ];

  // Rate limit detection
  const rateLimitPatterns = [
    /too many requests/i,
    /rate limit/i,
    /slow down/i,
    /try again (?:in|later|after)\s*\d/i,
    /demasiadas solicitudes/i,
    /limite.*tasa/i,
    /espera.*\d+\s*(min|sec)/i,
    /429/i,  // HTTP status in page text
  ];

  // Network error detection
  const networkErrorPatterns = [
    /ERR_/, /net::/i,
    /this site can't be reached/i,
    /connection (?:refused|reset|timed out)/i,
    /no se puede acceder/i,
  ];

  return {
    needsLogin: loginSignals.some(fn => fn()),
    hasCaptcha: captchaSignals.some(fn => fn()),
    isRateLimited: rateLimitPatterns.some(p => p.test(bodyText)),
    hasNetworkError: networkErrorPatterns.some(p => p.test(bodyText)),
    pageTitle: document.title,
    url: url.substring(0, 200)
  };
})()
```

### Actions per Error

| Error | Action |
|-------|--------|
| Login required | Inform user — they must log in manually in Vivaldi |
| CAPTCHA detected | Inform user — they must solve it manually |
| Rate limited | Parse wait time from message, wait, then retry |
| Network error | Check internet, retry navigation |
| Empty response | Re-run editor finder, check if still streaming, scroll down |

---

## Full Workflow — Universal (works on ANY platform)

This single workflow works on every platform without platform-specific code:

```javascript
// === 1. NAVIGATE ===
browser_navigate { browser_url: "http://127.0.0.1:9222", url: "<PLATFORM_URL>" }

// === 2. WAIT FOR SPA + EDITOR ===
browser_eval { browser_url: "http://127.0.0.1:9222",
  expression: "new Promise(r => { const s=Date.now(); const c=()=>{ if(document.readyState==='complete'&&document.querySelector('[contenteditable=\"true\"],[contenteditable=\"\"],textarea,[role=\"textbox\"]'))r('ready'); else if(Date.now()-s>15000)r('timeout'); else setTimeout(c,1000); }; setTimeout(c,3000); })" }

// === 3. CHECK FOR ERRORS ===
browser_eval { browser_url: "http://127.0.0.1:9222",
  expression: "(()=>{ const b=document.body.innerText; const u=window.location.href; return { login: !!document.querySelector('input[type=\"password\"]'), captcha: !!document.querySelector('iframe[src*=\"captcha\"],[class*=\"captcha\"]'), rateLimit: /too many|rate limit|slow down|429/i.test(b), title: document.title }; })()" }

// === 4. INSERT PROMPT (universal) ===
browser_eval { browser_url: "http://127.0.0.1:9222",
  expression: "(()=>{ const p='YOUR_PROMPT'; const c=Array.from(document.querySelectorAll('[contenteditable=\"true\"],[contenteditable=\"\"],textarea,[role=\"textbox\"]')).filter(e=>e.getBoundingClientRect().width>50); c.sort((a,b)=>b.getBoundingClientRect().top-a.getBoundingClientRect().top); const e=c[0]; if(!e)return{success:false,reason:'no editor'}; e.focus();e.click(); if(e.tagName==='TEXTAREA'){const s=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;s.call(e,p);e.dispatchEvent(new Event('input',{bubbles:true}));}else{document.execCommand('selectAll',false,null);document.execCommand('delete',false,null);document.execCommand('insertText',false,p);} const t=e.tagName==='TEXTAREA'?e.value:e.innerText; return{success:t.includes(p.substring(0,30)),length:t.trim().length,tag:e.tagName}; })()" }

// === 5. WAIT FOR DYNAMIC BUTTON + SEND ===
browser_eval { browser_url: "http://127.0.0.1:9222",
  expression: "new Promise(r=>{ setTimeout(()=>{ const b=document.querySelector('button[data-testid=\"send-button\"]')||(()=>{const ws=['Send','Submit','Enviar','Envoyer'];const bs=document.querySelectorAll('button,[role=\"button\"]');for(const b of bs){const l=(b.getAttribute('aria-label')||b.title||'').toLowerCase();if(ws.some(w=>l.includes(w.toLowerCase()))&&!b.disabled&&b.getBoundingClientRect().width>0)return b;} return null;})(); if(b&&!b.disabled){b.click();r('clicked');}else{const e=document.querySelector('[contenteditable=\"true\"],textarea,[role=\"textbox\"]');if(e){e.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',keyCode:13,bubbles:true,cancelable:true}));r('enter');}else{r('failed');}} },600); })" }

// === 6. POLL FOR RESPONSE COMPLETION ===
browser_eval { browser_url: "http://127.0.0.1:9222",
  expression: "new Promise(r=>{ const s=Date.now();let last=0;let stable=0;let obs=null; const root=document.querySelector('main,[role=\"main\"],#root,#app,body'); let mut=false; if(root&&typeof MutationObserver!=='undefined'){obs=new MutationObserver(()=>{mut=true;});obs.observe(root,{childList:true,subtree:true,characterData:true});} const c=()=>{ const si=document.querySelector('.result-streaming,[class*=\"streaming\"],[class*=\"typing\"]'); const bt=document.body.innerText; const th=['Cogitat','Pictur','Weigh','Synthesized','Thinking','Generat','Search','respondiendo','pensando'].some(w=>bt.includes(w)); if(si||th||mut){mut=false;stable=0;if(Date.now()-s>120000){obs?.disconnect();r('timeout');return;}setTimeout(c,2000);return;} const rc=Array.from(document.querySelectorAll('[data-message-author-role=\"assistant\"],[class*=\"markdown\"],[class*=\"prose\"],[class*=\"message-content\"],[class*=\"response\"],[class*=\"answer\"]')).filter(e=>e.getBoundingClientRect().width>0).pop(); const len=rc?.innerText?.trim().length||0; if(len>0&&len===last){stable++;if(stable>=3){obs?.disconnect();r({done:true,length:len});return;}}else{stable=0;} last=len; if(Date.now()-s>120000){obs?.disconnect();r({done:false,reason:'timeout',length:last});return;} setTimeout(c,2000); }; setTimeout(c,5000); })" }

// === 7. EXTRACT RESPONSE (universal) ===
browser_eval { browser_url: "http://127.0.0.1:9222",
  expression: "(()=>{ const sels=['[data-message-author-role=\"assistant\"]','[class*=\"ds-markdown\"]','[class*=\"model-response\"]','[class*=\"message-content\"]','[class*=\"prose\"]','[class*=\"response-text\"]','[class*=\"answer\"]','[class*=\"assistant-message\"]']; let t='';let src=''; for(const s of sels){try{const es=document.querySelectorAll(s);const l=es[es.length-1];if(l&&l.innerText.trim().length>t.length){t=l.innerText.trim();src=s;}}catch(e){}} if(!t||t.length<20){const bs=document.querySelectorAll('div,article,section');let m=0;bs.forEach(b=>{const x=b.innerText?.trim();if(x&&x.length>m&&x.length<200000&&b.children.length<15&&b.getBoundingClientRect().width>100){m=x.length;t=x;src='heuristic';}});} return{text:t,source:src,length:t.length}; })()" }
```

---

## Framework Detection Reference

| Detection Method | Framework | Insert Method |
|-----------------|-----------|---------------|
| `el.querySelector('.ProseMirror')` or class contains `ProseMirror` | ProseMirror / TipTap | `execCommand('insertText')` |
| class contains `ql-editor` | Quill.js | `execCommand('insertText')` |
| `data-lexical-editor` attribute | Lexical | `execCommand('insertText')` |
| `el.tagName === 'TEXTAREA'` | Native / React | property setter + events |
| `contenteditable="true"` + no framework class | Generic | `execCommand('insertText')` |
| `__reactFiber*` keys on element | React | depends on tag (textarea vs div) |

> **When in doubt:** `execCommand('insertText')` works on everything. Use it.

---

## Troubleshooting

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| `browser_list` empty | Vivaldi not running with CDP | Kill and relaunch with `--remote-debugging-port=9222` |
| `browser_snapshot` = RootWebArea only | SPA doesn't populate AXTree | Use `browser_eval` exclusively |
| Editor not found | Platform changed DOM structure | Re-run universal editor finder (Layer 3 heuristic) |
| `execCommand` returns false | Editor not focused | Call `.focus()` + `.click()`, wait 200ms, retry |
| Send button not found | Dynamic button not yet rendered | Wait 600-1000ms after text input |
| Send button still not found | Platform removed/renamed button | Universal finder falls back to Enter key |
| Text inserted but ignored | Wrong insert method for framework | Universal insert auto-detects and retries |
| Response extraction empty | Selectors broke after update | Universal extractor falls back to heuristic |
| Response seems incomplete | Still streaming or truncated | Check stability counter; send "continue" if truncated |
| Login page instead of chat | Session expired | User must log in manually in Vivaldi |
| CAPTCHA blocking | Anti-bot | User must solve manually |
| Rate limit | Too many requests | Parse wait time, wait, retry |
| Wrong button clicked | Attach vs send confusion | Universal finder excludes attach labels |
| `browser_eval` returns undefined | Expression didn't return | Wrap in IIFE: `(() => { ... })()` |
| Page blank after navigate | SPA still loading | Wait 5-8s, check `document.readyState` |
| CDP connection refused | Vivaldi crashed or port taken | `pkill -f vivaldi` and relaunch |
| New platform not in list | Unknown platform | Universal methods work on any platform — no special handling needed |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ANTI-FRAGILE WORKFLOW                               │
│                                                                        │
│  1. Navigate → wait for SPA + editor to appear                         │
│  2. Check errors (login, CAPTCHA, rate limit)                          │
│  3. Find editor → universal finder (3 layers)                         │
│  4. Insert text → universal insert (auto-detect textarea vs CE)        │
│  5. Wait 600ms → find send button → universal finder (5 layers)       │
│  6. Poll response → MutationObserver + stability counter               │
│  7. Extract → universal extractor (4 layers)                           │
│                                                                        │
│  KNOWN SELECTORS ARE HINTS, NOT REQUIREMENTS.                           │
│  IF A SELECTOR BREAKS, THE HEURISTIC FALLBACK FINDS THE ELEMENT.       │
│                                                                        │
│  Platform hints (fast path):          Universal fallback (always works):│
│  ─────────────────────────            ─────────────────────────────────  │
│  data-testid="send-button"     →     rightmost button near editor      │
│  .ProseMirror                  →     lowest contenteditable on page     │
│  #prompt-textarea              →     [contenteditable="true"]          │
│  [data-message-author-role]     →     last large text block in <main>   │
│  .result-streaming             →     MutationObserver on content area  │
└─────────────────────────────────────────────────────────────────────────┘
```
