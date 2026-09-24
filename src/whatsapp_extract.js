// Dump one day of WhatsApp Web messages to whatsapp-YYYY-MM-DD.jsonl
// Open the chat, scroll up past 00:00 of that day, then paste this into the
// DevTools console on web.whatsapp.com. Only loaded messages get exported.
(async () => {
  const CHAT_ID = '120363164855599963@g.us';  // null = all chats (may be different across machines!)
  const DAYS_AGO = 1;                         // 0 = today, 1 = yesterday

  // Grab module exports from whichever loader this build uses (Comet require,
  // webpack, or legacy window.Store), then find collections by shape.
  const mods = [];
  if (typeof self.require === 'function') {
    for (const m of ['WAWebMsgCollection', 'WAWebChatCollection', 'WAWebCollections']) {
      try { mods.push(self.require(m)); } catch {}
    }
  }
  for (const key of Object.keys(self).filter((k) => k.startsWith('webpackChunk'))) {
    let req;
    try { self[key].push([[Symbol()], {}, (r) => { req = r; }]); } catch {}
    for (const i of Object.keys(req?.m ?? {})) { try { mods.push(req(i)); } catch {} }
  }
  if (self.Store) mods.push(self.Store);

  const modelsOf = (o) => { try { return o?.getModelsArray?.(); } catch { return null; } };
  const find = (pred) => {
    for (const mod of mods) {
      for (const v of [mod, ...Object.values(mod ?? {})]) {
        const ms = modelsOf(v);
        if (ms?.length && pred(ms)) return ms;
      }
    }
  };
  const msgs = find((ms) => ms.some((m) => typeof m?.t === 'number' && ('body' in m || 'caption' in m)));
  const chats = find((cs) => cs.some((c) => c && 'isGroup' in c)) ?? [];
  if (!msgs) return console.error('message store not found');

  const id = (x) => x?._serialized ?? (typeof x === 'string' ? x : null);
  const chatOf = (m) => id(m.id?.remote) ?? id(m.to) ?? id(m.from);
  const names = Object.fromEntries(chats.map((c) => [id(c.id), c.formattedTitle ?? c.name]));

  const day = new Date();
  day.setHours(0, 0, 0, 0);
  day.setDate(day.getDate() - DAYS_AGO);       // setDate, not -86400s: DST-safe
  const t0 = day / 1000;
  const t1 = new Date(day).setDate(day.getDate() + 1) / 1000;
  const label = day.toLocaleDateString('sv');  // YYYY-MM-DD

  const rows = msgs
    .filter((m) => m.t >= t0 && m.t < t1 && (!CHAT_ID || chatOf(m) === CHAT_ID))
    .sort((a, b) => a.t - b.t)
    .map((m) => ({
      ts: new Date(m.t * 1000).toISOString(),
      chat: names[chatOf(m)] ?? chatOf(m),
      chat_id: chatOf(m),
      from_me: Boolean(m.id?.fromMe),
      author: id(m.author) ?? id(m.from),      // groups put the sender in author
      type: m.type,
      text: m.body ?? m.caption ?? null,
    }));
  if (!rows.length) return console.warn(`nothing from ${label} loaded`);

  Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(new Blob([rows.map((r) => JSON.stringify(r)).join('\n')])),
    download: `whatsapp-${label}.jsonl`,
  }).click();
  console.log(`${rows.length} messages, first at ${new Date(rows[0].ts).toLocaleTimeString()}`);
})();
