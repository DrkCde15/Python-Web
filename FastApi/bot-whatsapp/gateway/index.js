const {
  makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  makeCacheableSignalKeyStore,
} = require('@whiskeysockets/baileys');
const express = require('express');
const axios = require('axios');
const qrcode = require('qrcode-terminal');
const { readFileSync, existsSync } = require('fs');
const path = require('path');

require('dotenv').config({ path: path.join(__dirname, '.env') });

const PORT = parseInt(process.env.PORT) || 3001;
const WEBHOOK_URL = process.env.WEBHOOK_URL || 'http://localhost:8000/webhook';

let sock = null;

const app = express();
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ connected: sock?.user ? true : false, user: sock?.user?.id || null });
});

app.post('/send', async (req, res) => {
  const { to, text } = req.body;
  if (!to || !text) return res.status(400).json({ error: 'Missing "to" or "text"' });
  if (!sock?.user) return res.status(503).json({ error: 'WhatsApp not connected' });
  try {
    await sock.sendMessage(to, { text });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/send-buttons', async (req, res) => {
  const { to, text, buttons } = req.body;
  if (!to || !text || !buttons) return res.status(400).json({ error: 'Missing fields' });
  if (!sock?.user) return res.status(503).json({ error: 'WhatsApp not connected' });
  try {
    const rows = buttons.map((b, i) => ({
      title: b,
      rowId: `opt_${i + 1}`,
    }));
    const sections = [{ title: 'Menu', rows }];
    await sock.sendMessage(to, {
      text,
      footer: 'Escolha uma opção:',
      title: '📋 Menu',
      buttonText: 'Ver opções',
      sections,
    });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/send-image', async (req, res) => {
  const { to, text, imageUrl } = req.body;
  if (!to || !imageUrl) return res.status(400).json({ error: 'Missing fields' });
  if (!sock?.user) return res.status(503).json({ error: 'WhatsApp not connected' });
  try {
    const response = await axios.get(imageUrl, { responseType: 'arraybuffer' });
    const buffer = Buffer.from(response.data);
    await sock.sendMessage(to, {
      image: buffer,
      caption: text || '',
    });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`[Gateway] HTTP server running on port ${PORT}`);
  startBot();
});

function getMessageContent(msg) {
  if (msg.message?.conversation) return msg.message.conversation;
  if (msg.message?.extendedTextMessage?.text) return msg.message.extendedTextMessage.text;
  if (msg.message?.imageMessage?.caption) return msg.message.imageMessage.caption;
  if (msg.message?.listResponseMessage?.singleSelectReply?.selectedRowId) {
    return msg.message.listResponseMessage.singleSelectReply.selectedRowId;
  }
  if (msg.message?.buttonsResponseMessage?.selectedButtonId) {
    return msg.message.buttonsResponseMessage.selectedButtonId;
  }
  return null;
}

function getMessageType(msg) {
  if (msg.message?.conversation || msg.message?.extendedTextMessage) return 'text';
  if (msg.message?.imageMessage) return 'image';
  if (msg.message?.listResponseMessage) return 'list_response';
  if (msg.message?.buttonsResponseMessage) return 'button_response';
  return 'unknown';
}

async function startBot() {
  const { state, saveCreds } = await useMultiFileAuthState(
    path.join(__dirname, 'auth_info')
  );

  sock = makeWASocket({
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys),
    },
    printQRInTerminal: false,
    syncFullHistory: false,
    markOnlineOnConnect: true,
  });

  sock.ev.on('connection.update', async (update) => {
    const { qr, connection, lastDisconnect } = update;

    if (qr) {
      console.log('\n[Gateway] Scan the QR code with WhatsApp:');
      qrcode.generate(qr, { small: true });
    }

    if (connection === 'open') {
      console.log(`[Gateway] Connected as ${sock.user?.name || sock.user?.id}`);
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const reason = lastDisconnect?.error?.message || 'Unknown';

      if (statusCode === DisconnectReason.loggedOut) {
        console.log('[Gateway] Logged out. Delete auth_info folder and restart.');
        sock = null;
      } else {
        console.log(`[Gateway] Disconnected (${reason}). Reconnecting in 5s...`);
        await new Promise((r) => setTimeout(r, 5000));
        startBot();
      }
    }
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;

    for (const msg of messages) {
      if (msg.key.fromMe) continue;
      if (!msg.message) continue;

      const text = getMessageContent(msg);
      if (!text) continue;

      const from = msg.key.remoteJid;
      const msgType = getMessageType(msg);

      try {
        await axios.post(WEBHOOK_URL, {
          from,
          text,
          type: msgType,
          timestamp: msg.messageTimestamp,
          msgId: msg.key.id,
        }, { timeout: 30000 });
      } catch (err) {
        console.error(`[Gateway] Webhook error for ${from}: ${err.message}`);
      }
    }
  });
}

process.on('SIGINT', () => {
  console.log('\n[Gateway] Shutting down...');
  process.exit(0);
});
