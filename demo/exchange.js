/* In-browser exchange. RSA-PSS via Web Crypto, chain in localStorage.
   The signed payload is canonical JSON with sorted keys, same field set as
   the Flask app: quantity, recipient_address, sender_address, stock. */

const CHAIN_KEY = "blockchain-exchange-demo-v1";
const WALLET_KEY = "blockchain-exchange-demo-wallet";
const DIFFICULTY = "00";
const TICKER = /^[A-Za-z0-9.\-]{1,16}$/;

let mining = false;

function setStatus(element, message, kind) {
  if (!element) {
    return;
  }
  element.textContent = message || "";
  element.className = kind ? "status " + kind : "status";
}

function bytesToBase64(bytes) {
  let binary = "";
  const size = 0x8000;
  for (let index = 0; index < bytes.length; index += size) {
    binary += String.fromCharCode.apply(null, bytes.subarray(index, index + size));
  }
  return btoa(binary);
}

function base64ToBytes(value) {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

function bytesToHex(bytes) {
  return Array.from(bytes, function (byte) {
    return byte.toString(16).padStart(2, "0");
  }).join("");
}

function hexToBytes(hex) {
  if (!/^[0-9a-fA-F]+$/.test(hex) || hex.length % 2) {
    throw new Error("Key is not hex-encoded PEM.");
  }
  const bytes = new Uint8Array(hex.length / 2);
  for (let index = 0; index < bytes.length; index += 1) {
    bytes[index] = parseInt(hex.substr(index * 2, 2), 16);
  }
  return bytes;
}

function wrapPem(label, bytes) {
  const body = bytesToBase64(bytes).match(/.{1,64}/g).join("\n");
  return "-----BEGIN " + label + "-----\n" + body + "\n-----END " + label + "-----\n";
}

function pemToDer(pem) {
  const body = pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
  if (!body) {
    throw new Error("PEM was empty.");
  }
  return base64ToBytes(body);
}

function hexPemToDer(hex) {
  const pem = new TextDecoder().decode(hexToBytes(hex.trim()));
  return pemToDer(pem);
}

function sortValue(value) {
  if (Array.isArray(value)) {
    return value.map(sortValue);
  }
  if (value && typeof value === "object") {
    const sorted = {};
    Object.keys(value).sort().forEach(function (key) {
      if (key === "hash") {
        return;
      }
      sorted[key] = sortValue(value[key]);
    });
    return sorted;
  }
  return value;
}

function canonical(value) {
  return JSON.stringify(sortValue(value));
}

function canonicalTransaction(sender, recipient, stock, quantity) {
  return canonical({
    quantity: quantity,
    recipient_address: recipient,
    sender_address: sender,
    stock: stock
  });
}

async function sha256Hex(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return bytesToHex(new Uint8Array(digest));
}

function requireCrypto() {
  if (!window.crypto || !crypto.subtle) {
    throw new Error("Open this demo from https:// or http://localhost. Key generation does not run from a file:// page.");
  }
}

async function importPrivate(hex) {
  return crypto.subtle.importKey(
    "pkcs8",
    hexPemToDer(hex),
    { name: "RSA-PSS", hash: "SHA-256" },
    false,
    ["sign"]
  );
}

async function importPublic(hex) {
  return crypto.subtle.importKey(
    "spki",
    hexPemToDer(hex),
    { name: "RSA-PSS", hash: "SHA-256" },
    false,
    ["verify"]
  );
}

async function keysMatch(privateHex, publicHex) {
  const privateKey = await importPrivate(privateHex);
  const publicKey = await importPublic(publicHex);
  const payload = new TextEncoder().encode("exchange-key-check");
  const signature = await crypto.subtle.sign({ name: "RSA-PSS", saltLength: 32 }, privateKey, payload);
  return crypto.subtle.verify({ name: "RSA-PSS", saltLength: 32 }, publicKey, signature, payload);
}

async function signTransaction(privateHex, sender, recipient, stock, quantity) {
  const key = await importPrivate(privateHex);
  const payload = new TextEncoder().encode(canonicalTransaction(sender, recipient, stock, quantity));
  const signature = await crypto.subtle.sign({ name: "RSA-PSS", saltLength: 32 }, key, payload);
  return bytesToHex(new Uint8Array(signature));
}

async function verifyTransaction(publicHex, signatureHex, transaction) {
  try {
    const key = await importPublic(publicHex);
    const payload = new TextEncoder().encode(canonicalTransaction(
      transaction.sender_address,
      transaction.recipient_address,
      transaction.stock,
      transaction.quantity
    ));
    return await crypto.subtle.verify(
      { name: "RSA-PSS", saltLength: 32 },
      key,
      hexToBytes(signatureHex),
      payload
    );
  } catch (_error) {
    return false;
  }
}

function emptyChain() {
  return { chain: [], pending: [] };
}

function loadState() {
  try {
    const parsed = JSON.parse(localStorage.getItem(CHAIN_KEY) || "");
    if (!parsed || !Array.isArray(parsed.chain) || !Array.isArray(parsed.pending)) {
      return emptyChain();
    }
    return parsed;
  } catch (_error) {
    return emptyChain();
  }
}

function saveState(state) {
  localStorage.setItem(CHAIN_KEY, JSON.stringify(state));
}

async function ensureGenesis(state) {
  if (state.chain.length) {
    return state;
  }
  const block = {
    block_number: 1,
    timestamp: Date.now() / 1000,
    transactions: [],
    nonce: 0,
    previous_hash: "00"
  };
  block.hash = await sha256Hex(canonical(block));
  state.chain.push(block);
  saveState(state);
  return state;
}

function parseQuantity(raw) {
  const text = String(raw == null ? "" : raw).trim();
  if (!/^[1-9][0-9]*$/.test(text)) {
    return null;
  }
  const quantity = Number(text);
  if (!Number.isSafeInteger(quantity) || quantity > 1000000000) {
    return null;
  }
  return quantity;
}

async function queueTransaction(state, fields) {
  const quantity = parseQuantity(fields.quantity);
  const stock = String(fields.stock || "").trim();
  const sender = String(fields.sender_address || "").trim();
  const privateKey = String(fields.sender_private_key || "").trim();
  const recipient = String(fields.recipient_address || "").trim();
  if (!sender || !privateKey || !recipient) {
    throw new Error("Missing form value.");
  }
  if (quantity == null) {
    throw new Error("Quantity must be a whole number from 1 to 1000000000.");
  }
  if (!TICKER.test(stock)) {
    throw new Error("Stock must be 1 to 16 characters: letters, numbers, dot, or dash.");
  }
  let matched = false;
  try {
    matched = await keysMatch(privateKey, sender);
  } catch (_error) {
    throw new Error("Sender private key or address could not be read.");
  }
  if (!matched) {
    throw new Error("The private key does not match the sender address.");
  }
  try {
    await importPublic(recipient);
  } catch (_error) {
    throw new Error("Recipient address is not a public key.");
  }
  const signature = await signTransaction(privateKey, sender, recipient, stock, quantity);
  const transaction = {
    sender_address: sender,
    recipient_address: recipient,
    stock: stock,
    quantity: quantity,
    signature: signature
  };
  if (!await verifyTransaction(sender, signature, transaction)) {
    throw new Error("The signature could not be verified.");
  }
  state.pending.push(transaction);
  saveState(state);
  return state.pending.length;
}

async function minePending(state, onProgress) {
  if (!state.pending.length) {
    throw new Error("There are no transactions to mine.");
  }
  const previous = state.chain[state.chain.length - 1];
  const transactions = state.pending.map(function (transaction) {
    return {
      sender_address: transaction.sender_address,
      recipient_address: transaction.recipient_address,
      stock: transaction.stock,
      quantity: transaction.quantity,
      signature: transaction.signature
    };
  });
  const timestamp = Date.now() / 1000;
  for (let nonce = 0; nonce < 2000000; nonce += 1) {
    const block = {
      block_number: previous.block_number + 1,
      timestamp: timestamp,
      transactions: transactions,
      nonce: nonce,
      previous_hash: previous.hash
    };
    const hash = await sha256Hex(canonical(block));
    if (hash.startsWith(DIFFICULTY)) {
      block.hash = hash;
      state.chain.push(block);
      state.pending = [];
      saveState(state);
      return block;
    }
    if (nonce > 0 && nonce % 200 === 0) {
      if (onProgress) {
        onProgress(nonce);
      }
      await new Promise(function (resolve) {
        window.setTimeout(resolve, 0);
      });
    }
  }
  throw new Error("Mining did not finish.");
}

async function chainChecksOut(state) {
  const chain = state.chain;
  if (!chain.length || chain[0].block_number !== 1 || chain[0].previous_hash !== "00") {
    return false;
  }
  if ((chain[0].transactions || []).length) {
    return false;
  }
  for (let index = 0; index < chain.length; index += 1) {
    const block = chain[index];
    if (block.block_number !== index + 1) {
      return false;
    }
    const expected = await sha256Hex(canonical(block));
    if (block.hash !== expected) {
      return false;
    }
    for (let txIndex = 0; txIndex < (block.transactions || []).length; txIndex += 1) {
      const transaction = block.transactions[txIndex];
      const valid = await verifyTransaction(transaction.sender_address, transaction.signature, transaction);
      if (!valid) {
        return false;
      }
    }
    if (index > 0 && (block.previous_hash !== chain[index - 1].hash || !block.hash.startsWith(DIFFICULTY))) {
      return false;
    }
  }
  return true;
}

function shorten(value) {
  if (!value || value.length < 28) {
    return value || "";
  }
  return value.slice(0, 12) + "…" + value.slice(-8);
}

function formatTime(timestamp) {
  const date = new Date(Number(timestamp) * 1000);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString();
}

function cell(text, className) {
  const item = document.createElement("td");
  item.textContent = text;
  if (className) {
    item.className = className;
  }
  return item;
}

function transactionTable(transactions) {
  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  ["Stock", "Quantity", "Sender", "Recipient"].forEach(function (label) {
    const th = document.createElement("th");
    th.textContent = label;
    th.scope = "col";
    headRow.appendChild(th);
  });
  head.appendChild(headRow);
  table.appendChild(head);
  const body = document.createElement("tbody");
  transactions.forEach(function (transaction) {
    const row = document.createElement("tr");
    const sender = cell(shorten(transaction.sender_address), "mono");
    sender.title = transaction.sender_address || "";
    const recipient = cell(shorten(transaction.recipient_address), "mono");
    recipient.title = transaction.recipient_address || "";
    row.appendChild(cell(String(transaction.stock)));
    row.appendChild(cell(String(transaction.quantity)));
    row.appendChild(sender);
    row.appendChild(recipient);
    body.appendChild(row);
  });
  table.appendChild(body);
  return table;
}

function hashLine(label, value) {
  const wrap = document.createElement("div");
  const title = document.createElement("p");
  title.className = "hash-label";
  title.textContent = label;
  const code = document.createElement("p");
  code.className = "hash";
  code.textContent = value || "";
  wrap.appendChild(title);
  wrap.appendChild(code);
  return wrap;
}

async function renderChain(state) {
  const pending = document.getElementById("pending");
  const blocks = document.getElementById("blocks");
  const mine = document.getElementById("mine");
  const meta = document.getElementById("chain-meta");
  pending.replaceChildren();
  blocks.replaceChildren();
  const valid = await chainChecksOut(state);
  meta.textContent = "Difficulty prefix " + DIFFICULTY
    + " · " + state.chain.length + " blocks · chain "
    + (valid ? "checks out" : "does not check out");
  if (!state.pending.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No transactions waiting.";
    pending.appendChild(empty);
    mine.disabled = true;
  } else {
    pending.appendChild(transactionTable(state.pending));
    mine.disabled = mining;
  }
  state.chain.slice().reverse().forEach(function (block) {
    const article = document.createElement("article");
    article.className = "block";
    const header = document.createElement("header");
    const title = document.createElement("h3");
    title.textContent = "Block " + block.block_number;
    const when = document.createElement("p");
    when.className = "when";
    when.textContent = formatTime(block.timestamp) + " · nonce " + block.nonce;
    header.appendChild(title);
    header.appendChild(when);
    article.appendChild(header);
    article.appendChild(hashLine("Hash", block.hash));
    article.appendChild(hashLine("Previous hash", block.previous_hash));
    const transactions = block.transactions || [];
    if (!transactions.length) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "No transactions. This block starts the chain.";
      article.appendChild(empty);
    } else {
      article.appendChild(transactionTable(transactions));
    }
    blocks.appendChild(article);
  });
}

function showPanel(name) {
  document.querySelectorAll(".panel").forEach(function (panel) {
    const active = panel.dataset.panel === name;
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });
  document.querySelectorAll(".site-header nav a").forEach(function (link) {
    if (link.dataset.panel === name) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
  if (name === "chain") {
    const state = loadState();
    ensureGenesis(state).then(renderChain).catch(function (error) {
      setStatus(document.getElementById("chain-status"), error.message, "error");
    });
  }
}

function panelFromHash() {
  const name = (location.hash || "#wallet").slice(1);
  if (["wallet", "transaction", "chain", "about"].indexOf(name) === -1) {
    return "wallet";
  }
  return name;
}

async function copyFrom(textarea, button, label) {
  if (!textarea.value) {
    return;
  }
  try {
    await navigator.clipboard.writeText(textarea.value);
    button.textContent = "Copied";
  } catch (_error) {
    textarea.focus();
    textarea.select();
    button.textContent = "Select and copy";
  }
  window.setTimeout(function () {
    button.textContent = label;
  }, 1400);
}

function walletControls() {
  const generate = document.getElementById("generate");
  const publicKey = document.getElementById("public_key");
  const privateKey = document.getElementById("private_key");
  const copyPublic = document.getElementById("copy-public");
  const copyPrivate = document.getElementById("copy-private");
  const status = document.getElementById("wallet-status");

  generate.addEventListener("click", async function () {
    generate.disabled = true;
    setStatus(status, "Generating a 2048-bit key pair…");
    try {
      requireCrypto();
      const pair = await crypto.subtle.generateKey(
        {
          name: "RSA-PSS",
          modulusLength: 2048,
          publicExponent: new Uint8Array([1, 0, 1]),
          hash: "SHA-256"
        },
        true,
        ["sign", "verify"]
      );
      const spki = new Uint8Array(await crypto.subtle.exportKey("spki", pair.publicKey));
      const pkcs8 = new Uint8Array(await crypto.subtle.exportKey("pkcs8", pair.privateKey));
      const wallet = {
        public_key: bytesToHex(new TextEncoder().encode(wrapPem("PUBLIC KEY", spki))),
        private_key: bytesToHex(new TextEncoder().encode(wrapPem("PRIVATE KEY", pkcs8)))
      };
      publicKey.value = wallet.public_key;
      privateKey.value = wallet.private_key;
      sessionStorage.setItem(WALLET_KEY, JSON.stringify(wallet));
      copyPublic.disabled = false;
      copyPrivate.disabled = false;
      setStatus(status, "Wallet generated in this browser. It was not sent anywhere.", "ok");
    } catch (error) {
      setStatus(status, error.message || "The wallet could not be generated.", "error");
    } finally {
      generate.disabled = false;
    }
  });

  copyPublic.addEventListener("click", function () {
    copyFrom(publicKey, copyPublic, "Copy public key");
  });
  copyPrivate.addEventListener("click", function () {
    copyFrom(privateKey, copyPrivate, "Copy private key");
  });
}

function transactionControls() {
  const form = document.getElementById("transaction-form");
  const status = document.getElementById("tx-status");
  document.getElementById("fill-wallet").addEventListener("click", function () {
    const raw = sessionStorage.getItem(WALLET_KEY);
    if (!raw) {
      setStatus(status, "Generate a wallet on the Wallet page in this browser tab first.", "error");
      return;
    }
    try {
      const wallet = JSON.parse(raw);
      document.getElementById("sender_address").value = wallet.public_key || "";
      document.getElementById("sender_private_key").value = wallet.private_key || "";
      setStatus(status, "Sender fields filled from the wallet in this browser tab.", "ok");
    } catch (_error) {
      setStatus(status, "The saved wallet could not be read. Generate a new one.", "error");
    }
  });

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const button = document.getElementById("submit-transaction");
    button.disabled = true;
    setStatus(status, "Signing in this browser…");
    try {
      requireCrypto();
      const state = await ensureGenesis(loadState());
      const data = new FormData(form);
      const pending = await queueTransaction(state, {
        sender_address: data.get("sender_address"),
        sender_private_key: data.get("sender_private_key"),
        recipient_address: data.get("recipient_address"),
        stock: data.get("stock"),
        quantity: data.get("quantity")
      });
      setStatus(status, "Transaction queued (" + pending + " pending). Mine it on the Chain page.", "ok");
    } catch (error) {
      setStatus(status, error.message || "The transaction was rejected.", "error");
    } finally {
      button.disabled = false;
    }
  });
}

function chainControls() {
  const mine = document.getElementById("mine");
  const status = document.getElementById("chain-status");
  mine.addEventListener("click", async function () {
    if (mining) {
      return;
    }
    mining = true;
    mine.disabled = true;
    mine.textContent = "Mining…";
    setStatus(status, "Searching for a nonce…");
    try {
      requireCrypto();
      const state = await ensureGenesis(loadState());
      const block = await minePending(state, function (nonce) {
        setStatus(status, "Searching for a nonce… tried " + nonce);
      });
      setStatus(status, "Mined block " + block.block_number + " (nonce " + block.nonce + ").", "ok");
      await renderChain(state);
    } catch (error) {
      setStatus(status, error.message || "Mining failed.", "error");
      await renderChain(await ensureGenesis(loadState()));
    } finally {
      mining = false;
      mine.textContent = "Mine block";
      if (loadState().pending.length) {
        mine.disabled = false;
      }
    }
  });

  document.getElementById("reset-chain").addEventListener("click", async function () {
    localStorage.removeItem(CHAIN_KEY);
    setStatus(status, "Demo chain reset in this browser.", "ok");
    await renderChain(await ensureGenesis(loadState()));
  });
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".site-header nav a").forEach(function (link) {
    link.addEventListener("click", function () {
      showPanel(link.dataset.panel);
    });
  });
  window.addEventListener("hashchange", function () {
    showPanel(panelFromHash());
  });
  walletControls();
  transactionControls();
  chainControls();
  showPanel(panelFromHash());
});
