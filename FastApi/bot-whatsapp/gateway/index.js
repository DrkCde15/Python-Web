// Gateway WhatsApp — Node.js + Baileys + Express
// Conecta ao WhatsApp via WebSocket (Baileys), recebe mensagens e as encaminha
// via webhook para o bot Python. Expõe API REST para envio de mensagens.
const {
  makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  makeCacheableSignalKeyStore,
  downloadContentFromMessage,
} = require('@whiskeysockets/baileys');
const express = require('express');
const rateLimit = require('express-rate-limit');
const axios = require('axios');
const qrcode = require('qrcode-terminal');
const { readFileSync, existsSync } = require('fs');
const path = require('path');
const pino = require('pino');

require('dotenv').config({ path: path.join(__dirname, '.env') });

// Logger estruturado com pino (nível configurável via LOG_LEVEL)
const logger = pino({
  transport: {
    target: 'pino-pretty',
    options: { colorize: true, translateTime: 'SYS:standard' },
  },
  level: process.env.LOG_LEVEL || 'info',
});

const PORT = parseInt(process.env.PORT) || 3001;
const WEBHOOK_URL = process.env.WEBHOOK_URL || 'http://localhost:8000/webhook';

let sock = null;
let isConnecting = false;  // Flag para evitar múltiplas reconexões simultâneas

// Valida formato do JID do WhatsApp (número@ dominio)
const JID_RE = /^\d+@(s\.whatsapp\.net|lid)$/;
function isValidJid(jid) {
  return JID_RE.test(jid);
}

const app = express();
app.use(express.json());

// Rate limiting: protege os endpoints de send contra abuso
const sendLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 30,
  message: { error: 'Too many requests, please try again later' },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/send', sendLimiter);
app.use('/send-buttons', sendLimiter);
app.use('/send-image', sendLimiter);

// Endpoint de health check: retorna status da conexão WhatsApp
app.get('/health', (req, res) => {
  res.json({ connected: sock?.user ? true : false, user: sock?.user?.id || null });
});

// Envia mensagem de texto simples
app.post('/send', async (req, res) => {
  const { to, text } = req.body;
  if (!to || !text) return res.status(400).json({ error: 'Missing "to" or "text"' });
  if (!isValidJid(to)) return res.status(400).json({ error: 'Invalid JID format' });
  if (!sock?.user) return res.status(503).json({ error: 'WhatsApp not connected' });
  try {
    await sock.sendMessage(to, { text });
    logger.info({ to }, 'message_sent');
    res.json({ success: true });
  } catch (err) {
    logger.error({ to, error: err.message }, 'send_failed');
    res.status(500).json({ error: err.message });
  }
});

// Envia mensagem com botões interativos (list/sections)
app.post('/send-buttons', async (req, res) => {
  const { to, text, buttons } = req.body;
  if (!to || !text || !buttons) return res.status(400).json({ error: 'Missing fields' });
  if (!isValidJid(to)) return res.status(400).json({ error: 'Invalid JID format' });
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
    logger.info({ to }, 'buttons_sent');
    res.json({ success: true });
  } catch (err) {
    logger.error({ to, error: err.message }, 'buttons_failed');
    res.status(500).json({ error: err.message });
  }
});

// Envia imagem (baixada de URL) com caption opcional
app.post('/send-image', async (req, res) => {
  const { to, text, imageUrl } = req.body;
  if (!to || !imageUrl) return res.status(400).json({ error: 'Missing fields' });
  if (!isValidJid(to)) return res.status(400).json({ error: 'Invalid JID format' });
  if (!sock?.user) return res.status(503).json({ error: 'WhatsApp not connected' });
  try {
    const response = await axios.get(imageUrl, { responseType: 'arraybuffer' });
    const buffer = Buffer.from(response.data);
    await sock.sendMessage(to, {
      image: buffer,
      caption: text || '',
    });
    logger.info({ to }, 'image_sent');
    res.json({ success: true });
  } catch (err) {
    logger.error({ to, error: err.message }, 'image_failed');
    res.status(500).json({ error: err.message });
  }
});

// Inicia servidor HTTP e conexão WhatsApp
app.listen(PORT, () => {
  logger.info({ port: PORT }, 'gateway_http_started');
  startBot();
});

// Extrai o texto de diferentes formatos de mensagem do WhatsApp
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

// Identifica o tipo da mensagem para o webhook
function getMessageType(msg) {
  if (msg.message?.conversation || msg.message?.extendedTextMessage) return 'text';
  if (msg.message?.imageMessage) return 'image';
  if (msg.message?.audioMessage) return 'audio';
  if (msg.message?.listResponseMessage) return 'list_response';
  if (msg.message?.buttonsResponseMessage) return 'button_response';
  return 'unknown';
}

// Conecta ao WhatsApp via Baileys e configura listeners de eventos
async function startBot() {
  // Evita múltiplas chamadas simultâneas de reconexão
  if (isConnecting) {
    logger.warn('already_connecting_skipping');
    return;
  }
  isConnecting = true;

  try {
    // Carrega ou cria estado de autenticação persistente
    const { state, saveCreds } = await useMultiFileAuthState(
      path.join(__dirname, 'auth_info')
    );

    // Cria socket do WhatsApp com as credenciais carregadas
    sock = makeWASocket({
      auth: {
        creds: state.creds,
        keys: makeCacheableSignalKeyStore(state.keys),
      },
      printQRInTerminal: false,   // Geramos QR manualmente com qrcode-terminal
      syncFullHistory: false,      // Evita sincronizar histórico completo
      markOnlineOnConnect: true,
      logger: pino({ level: 'warn' }),  // Log interno do Baileys (warn+ apenas)
    });

    // Monitora mudanças na conexão (QR code, conectado, desconectado)
    sock.ev.on('connection.update', async (update) => {
      const { qr, connection, lastDisconnect } = update;

      if (qr) {
        logger.info('qr_code_generated');
        qrcode.generate(qr, { small: true });
      }

      if (connection === 'open') {
        isConnecting = false;
        logger.info({ user: sock.user?.name || sock.user?.id }, 'whatsapp_connected');
      }

      if (connection === 'close') {
        isConnecting = false;
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        const reason = lastDisconnect?.error?.message || 'Unknown';

        if (statusCode === DisconnectReason.loggedOut) {
          // Se foi deslogado manualmente, não tenta reconectar
          logger.error('logged_out_delete_auth_info');
          sock = null;
        } else {
          // Reconexão automática após 5 segundos
          logger.warn({ reason, statusCode }, 'disconnected_reconnecting');
          await new Promise((r) => setTimeout(r, 5000));
          startBot();
        }
      }
    });

    // Fila interna de webhook com retry exponencial (3 tentativas: 1s, 5s, 15s)
    const webhookQueue = [];
    let webhookProcessing = false;

    async function processWebhookQueue() {
      if (webhookProcessing) return;
      webhookProcessing = true;
      while (webhookQueue.length > 0) {
        const item = webhookQueue.shift();
        const delays = [1000, 5000, 15000];
        for (let attempt = 0; attempt <= delays.length; attempt++) {
          try {
            await axios.post(WEBHOOK_URL, item.payload, { timeout: 30000 });
            logger.debug({ from: item.payload.from, attempt }, 'webhook_sent');
            break;
          } catch (err) {
            const errInfo = {
              message: err.message,
              code: err.code,
              status: err.response?.status,
              responseData: err.response?.data,
            };
            if (attempt < delays.length) {
              logger.warn({ from: item.payload.from, attempt, delay: delays[attempt], error: errInfo }, 'webhook_retry');
              await new Promise((r) => setTimeout(r, delays[attempt]));
            } else {
              logger.error({ from: item.payload.from, error: errInfo }, 'webhook_failed');
            }
          }
        }
      }
      webhookProcessing = false;
    }

    // Persiste credenciais atualizadas (mantém sessão ativa)
    sock.ev.on('creds.update', saveCreds);

    // Baixa uma imagem e retorna como base64
    async function downloadImageBase64(msg) {
      try {
        const stream = await downloadContentFromMessage(msg.message.imageMessage, 'image');
        const chunks = [];
        for await (const chunk of stream) {
          chunks.push(chunk);
        }
        return Buffer.concat(chunks).toString('base64');
      } catch (err) {
        logger.error({ error: err.message }, 'image_download_failed');
        return null;
      }
    }

    // Baixa um áudio e retorna como base64
    async function downloadAudioBase64(msg) {
      try {
        const stream = await downloadContentFromMessage(msg.message.audioMessage, 'audio');
        const chunks = [];
        for await (const chunk of stream) {
          chunks.push(chunk);
        }
        return Buffer.concat(chunks).toString('base64');
      } catch (err) {
        logger.error({ error: err.message }, 'audio_download_failed');
        return null;
      }
    }

    // Escuta novas mensagens e encaminha via webhook para o bot Python
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
      logger.debug({ type, count: messages.length }, 'messages_upsert');
      if (type !== 'notify') return;

      for (const msg of messages) {
        if (msg.key.fromMe) continue;       // Ignora mensagens enviadas por nós
        if (!msg.message) continue;

        const from = msg.key.remoteJid;
        const text = getMessageContent(msg) || '';
        const msgType = getMessageType(msg);
        logger.info({ from, text: text.slice(0, 50), msgType }, 'message_received_raw');

        // Ignora newsletters, broadcasts e status
        if (from.endsWith('@newsletter') || from.endsWith('@broadcast') || from.endsWith('status@broadcast')) {
          logger.debug({ from }, 'ignored_non_personal');
          continue;
        }

        // Se for imagem, baixa e converte para base64
        let imageBase64 = null;
        if (msgType === 'image') {
          imageBase64 = await downloadImageBase64(msg);
          if (imageBase64) {
            logger.info({ from }, 'image_downloaded_base64');
          } else {
            logger.warn({ from }, 'image_download_failed_skipping');
          }
        }

        // Se for áudio, baixa e converte para base64
        let audioBase64 = null;
        let audioMimetype = null;
        if (msgType === 'audio') {
          audioBase64 = await downloadAudioBase64(msg);
          if (audioBase64) {
            audioMimetype = msg.message.audioMessage?.mimetype || 'audio/ogg';
            logger.info({ from, mimetype: audioMimetype }, 'audio_downloaded_base64');
          } else {
            logger.warn({ from }, 'audio_download_failed_skipping');
          }
        }

        // Se não tem texto, imagem nem áudio, ignora
        if (!text && !imageBase64 && !audioBase64) continue;

        webhookQueue.push({
          payload: {
            from,
            text,
            type: msgType,
            image: imageBase64,
            audio: audioBase64,
            mimetype: audioMimetype,
            timestamp: msg.messageTimestamp,
            msgId: msg.key.id,
          }
        });
        processWebhookQueue();
      }
    });
  } catch (err) {
    isConnecting = false;
    logger.error({ error: err.message }, 'start_bot_failed');
    await new Promise((r) => setTimeout(r, 5000));
    startBot();
  }
}

// Graceful shutdown ao pressionar Ctrl+C
process.on('SIGINT', () => {
  logger.info('shutting_down');
  process.exit(0);
});
