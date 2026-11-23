function setStatus(element, message, kind) {
  if (!element) {
    return;
  }
  element.textContent = message || "";
  element.className = kind ? "status " + kind : "status";
}

async function readJson(response) {
  let data = {};
  try {
    data = await response.json();
  } catch (_error) {
    data = {};
  }
  return { ok: response.ok, status: response.status, data: data };
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

async function copyFrom(textarea, button, label) {
  const value = textarea.value;
  if (!value) {
    return;
  }
  try {
    await navigator.clipboard.writeText(value);
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

function enableCopy(textarea, button) {
  button.disabled = !textarea.value;
}

function walletPage() {
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
      const result = await readJson(await fetch("/api/wallet/create"));
      if (!result.ok || !result.data.public_key || !result.data.private_key) {
        setStatus(status, "The wallet could not be generated.", "error");
        return;
      }
      publicKey.value = result.data.public_key;
      privateKey.value = result.data.private_key;
      sessionStorage.setItem("exchange-wallet", JSON.stringify({
        public_key: result.data.public_key,
        private_key: result.data.private_key
      }));
      enableCopy(publicKey, copyPublic);
      enableCopy(privateKey, copyPrivate);
      setStatus(status, "Wallet generated. It is not saved on the server. Copy the keys or open New transaction and fill them from this browser.", "ok");
    } catch (_error) {
      setStatus(status, "The wallet request failed.", "error");
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

function transactionPage() {
  const form = document.getElementById("transaction-form");
  const status = document.getElementById("tx-status");
  const fill = document.getElementById("fill-wallet");

  fill.addEventListener("click", function () {
    const raw = sessionStorage.getItem("exchange-wallet");
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
    setStatus(status, "Submitting…");
    try {
      const result = await readJson(await fetch("/api/transaction/new", {
        method: "POST",
        body: new FormData(form)
      }));
      if (!result.ok) {
        setStatus(status, result.data.error || "The transaction was rejected.", "error");
        return;
      }
      setStatus(status, "Transaction queued (" + result.data.pending + " pending). Mine it on the Chain page.", "ok");
    } catch (_error) {
      setStatus(status, "The transaction request failed.", "error");
    } finally {
      button.disabled = false;
    }
  });
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

function renderChain(data) {
  const pending = document.getElementById("pending");
  const blocks = document.getElementById("blocks");
  const mine = document.getElementById("mine");
  const meta = document.getElementById("chain-meta");
  pending.replaceChildren();
  blocks.replaceChildren();

  const waiting = data.pending || [];
  meta.textContent = "Difficulty prefix " + (data.difficulty_prefix || "00")
    + " · " + (data.length || 0) + " blocks · chain "
    + (data.valid ? "checks out" : "does not check out");

  if (!waiting.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No transactions waiting.";
    pending.appendChild(empty);
    mine.disabled = true;
  } else {
    pending.appendChild(transactionTable(waiting));
    mine.disabled = false;
  }

  (data.chain || []).slice().reverse().forEach(function (block) {
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

async function loadChain() {
  const status = document.getElementById("chain-status");
  const result = await readJson(await fetch("/api/transaction/view"));
  if (!result.ok) {
    setStatus(status, "The chain could not be loaded.", "error");
    return;
  }
  renderChain(result.data);
}

function chainPage() {
  const mine = document.getElementById("mine");
  const status = document.getElementById("chain-status");
  mine.addEventListener("click", async function () {
    mine.disabled = true;
    const original = mine.textContent;
    mine.textContent = "Mining…";
    setStatus(status, "Searching for a nonce…");
    try {
      const result = await readJson(await fetch("/api/mine", { method: "POST" }));
      if (!result.ok) {
        setStatus(status, result.data.error || "Mining failed.", "error");
      } else {
        setStatus(status, "Mined block " + result.data.block_number + " (nonce " + result.data.nonce + ").", "ok");
      }
      await loadChain();
    } catch (_error) {
      setStatus(status, "The mining request failed.", "error");
    } finally {
      mine.textContent = original;
    }
  });
  loadChain().catch(function () {
    setStatus(status, "The chain could not be loaded.", "error");
  });
}

document.addEventListener("DOMContentLoaded", function () {
  const page = document.body.dataset.page;
  if (page === "wallet") {
    walletPage();
  } else if (page === "new") {
    transactionPage();
  } else if (page === "chain") {
    chainPage();
  }
});
