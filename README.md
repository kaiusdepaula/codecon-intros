# codecon-intros

Interactive graph of the member intros from Codecon's *Linkedisney day* on WhatsApp.
People are grouped by professional area and linked by shared themes. Click a person to open their LinkedIn.

**Live:** https://kaiusdepaula.github.io/codecon-intros/

## How it works

1. `src/whatsapp_extract.js` exports one day of a WhatsApp Web chat to `whatsapp-YYYY-MM-DD.jsonl`.
2. `src/extract_intros.py` parses the intro messages, asks Claude to group people, and renders the graph as a standalone HTML page.

## Requirements

- WhatsApp Web open and logged in, in Chrome or Firefox
- Python 3.9+ (standard library only)
- [Claude Code](https://claude.com/claude-code) installed and logged in (`claude` on your `PATH`). Only needed for the grouping step.

## 1. Export the chat

1. Open the chat on web.whatsapp.com and **scroll up past 00:00** of the day you want. Only messages loaded in the tab get exported.
2. Edit the two settings at the top of `src/whatsapp_extract.js`:
   ```js
   const CHAT_ID = '120363164855599963@g.us';  // null = all chats
   const DAYS_AGO = 1;                         // 0 = today, 1 = yesterday
   ```
   Not sure of the chat id? Run it once with `CHAT_ID = null` and look at the `chat_id` column.
3. Open DevTools (`F12`), go to the **Console** tab, paste the script and press Enter. Chrome asks you to type `allow pasting` the first time.
4. `whatsapp-YYYY-MM-DD.jsonl` lands in your Downloads folder. The console logs the time of the first message, so you can check you scrolled far enough.

## 2. Build the graph

```bash
python src/extract_intros.py ~/Downloads/whatsapp-2026-09-23.jsonl --graph
```

This takes about a minute (one Claude call) and writes two files:

| File | Contents |
|---|---|
| `index.html` (repo root) | The interactive graph, overwritten on every run, ready to push |
| `whatsapp-….grupos.json` (next to the input) | Each person's name, area, curiosity and LinkedIn, plus `grupo`, `tags` and `temas` from Claude |

Without `--graph`, the script only prints the parsed intros as CSV and makes no LLM call:

```bash
python src/extract_intros.py ~/Downloads/whatsapp-2026-09-23.jsonl > intros.csv
```

To re-render `index.html` after changing the styling, pass the `.grupos.json` instead. This skips the Claude call:

```bash
python src/extract_intros.py ~/Downloads/whatsapp-2026-09-23.grupos.json
```

## 3. Publish

```bash
git commit -am "feat: a great commit message" && git push
```

GitHub Pages serves `index.html` from `main`. It updates about a minute after the push.

## Customizing

All in `src/extract_intros.py`:

- `MODEL`: the Claude model used for grouping (`sonnet` by default).
- `PROMPT`: how people are grouped. Groups and themes are chosen by the model and can change between runs. To keep them stable across exports, list the exact group and theme names in the prompt.
- `PALETTE`, `HTML`: colors, layout and click behavior of the page.

## Good to know

- The parser matches labels by keyword, so it copes with intros that don't follow the template exactly: missing numbers, WhatsApp bold, the answer on the next line, a bare LinkedIn URL.
- `ts` in the export is UTC. The day filter uses your local time.
- **Don't commit the raw `.jsonl` exports.** They contain the whole chat, not just the intros, and this repo is public. `.gitignore` excludes `whatsapp-*` files for that reason.
- The page has `noindex` set, so search engines skip it, but anyone with the link can open it.
