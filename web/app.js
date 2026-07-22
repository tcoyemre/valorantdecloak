"use strict";

/* ============================ i18n ============================ */
// Dil sözlükleri. Kullanıcıya görünen tüm metinler buradan gelir.
const I18N = {
  tr: {
    connecting: "Bağlanıyor...",
    loading: "Yükleniyor",
    loadingDots: "Yükleniyor...",
    waiting: "Bekleniyor",
    noPlayers: "Henüz oyuncu yok.",
    disconnected: "Bağlantı kesildi...",
    players: "oyuncu",
    playersTitle: "Oyuncular",
    copied: "Kopyalandı: ",
    hidden: "Gizli",
    close: "Kapat",
    skins: "Skinler",
    weaponSkins: "Silah Skinleri",
    playerCard: "OYUNCU KARTI",
    buddy: "Uğurluk",
    skinsEmpty: "Skin bilgisi yalnızca oyun sırasında (oyun içi) görüntülenebilir.",
    quitMsg: "Valorant Decloak kapatıldı. Bu sekmeyi kapatabilirsiniz.",
    web: "Web: ",
    teamA: "Takım A",
    teamB: "Takım B",
    teamFallback: "Takım ",
    defense: "Savunma",
    attack: "Atak",
    skinsTitleAttr: "Skinler",
    quitTitle: "Kapat",
    // lisans
    licenseError: "Lisans Hatası",
    accessDenied: "Erişim Reddedildi",
    licenseNotVerified: "Lisans doğrulanamadı",
    licenseFailedTitle: "Lisans Doğrulanamadı",
    machineNotAuthorized: "Bu makine yetkili değil",
    sendHwid: "Aşağıdaki HWID'yi yetkiliye gönderin:",
    clickToCopy: "Kopyalamak için tıkla",
    copyHwid: "HWID'yi Kopyala",
    state: { INGAME: "Oyunda", PREGAME: "Ajan Seçimi", MENUS: "Menüde", DISCONNECTED: "Bağlantı Kesildi" },
    mode: {
      // İngilizce kanonik anahtarlar
      Competitive: "Dereceli", Unrated: "Derecesiz", Swiftplay: "Tam Gaz",
      "Spike Rush": "Spike'a Hücum", Deathmatch: "Ölüm Maçı", Escalation: "Tırmanış",
      Replication: "Kopya", "Team Deathmatch": "Takımlı Ölüm Maçı",
      "Custom Game": "Özel Oyun", Custom: "Özel Oyun", "New Map": "Yeni Harita",
      "Snowball Fight": "Kartopu Savaşı", "All Random One Site": "ARAM",
      // Sunucudan gelen Türkçe ham değerler (constants.py gamemodes)
      "Dereceli": "Dereceli", "Derecesiz": "Derecesiz", "Tam Gaz": "Tam Gaz",
      "Spike'a Hücum": "Spike'a Hücum", "Ölüm Maçı": "Ölüm Maçı", "Tırmanış": "Tırmanış",
      "Kopya": "Kopya", "Takımlı Ölüm Maçı": "Takımlı Ölüm Maçı", "Özel": "Özel",
      "Kartopu Savaşı": "Kartopu Savaşı", "ARAM": "ARAM", "Yeni Harita": "Yeni Harita",
    },
    ranks: [
      "Unranked", "Unranked", "Unranked",
      "Demir 1", "Demir 2", "Demir 3",
      "Bronz 1", "Bronz 2", "Bronz 3",
      "Gümüş 1", "Gümüş 2", "Gümüş 3",
      "Altın 1", "Altın 2", "Altın 3",
      "Platin 1", "Platin 2", "Platin 3",
      "Elmas 1", "Elmas 2", "Elmas 3",
      "Yücelik 1", "Yücelik 2", "Yücelik 3",
      "Immortal 1", "Immortal 2", "Immortal 3",
      "Radyant",
    ],
    weaponCats: [
      "BEYLİK SİLAHLAR", "HAFİF MAKİNELİLER", "POMPALI TÜFEKLER", "TÜFEKLER",
      "YAKIN DÖVÜŞ SİLAHI", "KESKİN NİŞANCI TÜFEKLERİ", "MAKİNELİ TÜFEKLER",
    ],
  },
  en: {
    connecting: "Connecting...",
    loading: "Loading",
    loadingDots: "Loading...",
    waiting: "Waiting",
    noPlayers: "No players yet.",
    disconnected: "Disconnected...",
    players: "players",
    playersTitle: "Players",
    copied: "Copied: ",
    hidden: "Hidden",
    close: "Close",
    skins: "Skins",
    weaponSkins: "Weapon Skins",
    playerCard: "PLAYER CARD",
    buddy: "Buddy",
    skinsEmpty: "Skin information is only available while in a match (in-game).",
    quitMsg: "Valorant Decloak has been closed. You can close this tab.",
    web: "Web: ",
    teamA: "Team A",
    teamB: "Team B",
    teamFallback: "Team ",
    defense: "Defense",
    attack: "Attack",
    skinsTitleAttr: "Skins",
    quitTitle: "Close",
    // license
    licenseError: "License Error",
    accessDenied: "Access Denied",
    licenseNotVerified: "License could not be verified",
    licenseFailedTitle: "License Not Verified",
    machineNotAuthorized: "This machine is not authorized",
    sendHwid: "Send the HWID below to the administrator:",
    clickToCopy: "Click to copy",
    copyHwid: "Copy HWID",
    state: { INGAME: "In Game", PREGAME: "Agent Select", MENUS: "In Menu", DISCONNECTED: "Disconnected" },
    mode: {
      // English canonical keys
      Competitive: "Competitive", Unrated: "Unrated", Swiftplay: "Swift Play",
      "Spike Rush": "Spike Rush", Deathmatch: "Deathmatch", Escalation: "Escalation",
      Replication: "Replication", "Team Deathmatch": "Team Deathmatch",
      "Custom Game": "Custom Game", Custom: "Custom Game", "New Map": "New Map",
      "Snowball Fight": "Snowball Fight", "All Random One Site": "All Random",
      // Raw Turkish values sent by the server (constants.py gamemodes)
      "Dereceli": "Competitive", "Derecesiz": "Unrated", "Tam Gaz": "Swift Play",
      "Spike'a Hücum": "Spike Rush", "Ölüm Maçı": "Deathmatch", "Tırmanış": "Escalation",
      "Kopya": "Replication", "Takımlı Ölüm Maçı": "Team Deathmatch", "Özel": "Custom Game",
      "Kartopu Savaşı": "Snowball Fight", "ARAM": "All Random", "Yeni Harita": "New Map",
    },
    ranks: [
      "Unranked", "Unranked", "Unranked",
      "Iron 1", "Iron 2", "Iron 3",
      "Bronze 1", "Bronze 2", "Bronze 3",
      "Silver 1", "Silver 2", "Silver 3",
      "Gold 1", "Gold 2", "Gold 3",
      "Platinum 1", "Platinum 2", "Platinum 3",
      "Diamond 1", "Diamond 2", "Diamond 3",
      "Ascendant 1", "Ascendant 2", "Ascendant 3",
      "Immortal 1", "Immortal 2", "Immortal 3",
      "Radiant",
    ],
    weaponCats: [
      "SIDEARMS", "SMGS", "SHOTGUNS", "RIFLES",
      "MELEE", "SNIPER RIFLES", "MACHINE GUNS",
    ],
  },
};

let LANG = localStorage.getItem("vd_lang") || "tr";
if (!I18N[LANG]) LANG = "tr";
const T = () => I18N[LANG];

// Sunucudan gelen ham veri "Gizli" olarak gelir; dile göre çevir.
function localizeHidden(v) { return v === "Gizli" ? T().hidden : v; }

// Takım kategorileri (silahlar dilden bağımsız aynı kalır; başlık çevrilir).
const WEAPON_GROUPS = [
  ["Classic", "Shorty", "Frenzy", "Ghost", "Sheriff"],
  ["Stinger", "Spectre"],
  ["Bucky", "Judge"],
  ["Bulldog", "Guardian", "Phantom", "Vandal"],
  ["Melee"],
  ["Marshal", "Outlaw", "Operator"],
  ["Ares", "Odin"],
];

function teamLabel(team, state, idx) {
  let label;
  if (team === "Blue") label = T().teamA;
  else if (team === "Red") label = T().teamB;
  else label = T().teamFallback + String.fromCharCode(65 + idx);
  if (state === "PREGAME" && (team === "Blue" || team === "Red")) {
    label += " - " + (team === "Blue" ? T().defense : T().attack);
  }
  return label;
}
function teamOrder(team) { return team === "Blue" ? 0 : team === "Red" ? 1 : 2; }

let AGENTS = {};   // displayName -> displayIcon
let TIERS = {};    // tier -> {color, icon}

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function loadAssets() {
  try {
    const j = await (await fetch("https://valorant-api.com/v1/agents?isPlayableCharacter=true")).json();
    j.data.forEach((a) => { AGENTS[a.displayName] = a.displayIcon; });
  } catch (e) {}
  try {
    const j = await (await fetch("https://valorant-api.com/v1/competitivetiers")).json();
    j.data[j.data.length - 1].tiers.forEach((t) => {
      TIERS[t.tier] = { color: "#" + (t.color ? t.color.slice(0, 6) : "8a909c"), icon: t.smallIcon };
    });
  } catch (e) {}
}

function rankInfo(idx) {
  const t = TIERS[idx];
  const name = (T().ranks[idx]) || "?";
  return { name, color: t ? t.color : "#8a909c", icon: t ? t.icon : null };
}
function splitName(full) {
  if (!full) return { name: "?", tag: "" };
  const i = full.lastIndexOf("#");
  return i < 0 ? { name: full, tag: "" } : { name: full.slice(0, i), tag: full.slice(i) };
}

function toast(text) {
  const el = $("toast");
  el.textContent = T().copied + text;
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 1300);
}
function copyText(text) {
  const done = () => toast(text);
  if (navigator.clipboard) navigator.clipboard.writeText(text).then(done).catch(() => {});
  else {
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); done(); } catch (e) {}
    document.body.removeChild(ta);
  }
}

function chip(value, label, cls) {
  if (value == null || value === "") return "";
  return `<div class="chip"><span class="v ${cls || ""}">${esc(value)}</span><span class="l">${esc(label)}</span></div>`;
}

// Peak rank tile: rank icon on top, peak RR below (no rank name).
function peakChip(p) {
  const idx = parseInt(p.peakRank, 10);
  if (isNaN(idx) || idx <= 2) return "";   // 0-2 = Unranked, nothing to show
  const pi = rankInfo(idx);
  if (!pi.icon) return "";
  let sub;
  if (p.peakRR === 0 || p.peakRR) sub = `${parseInt(p.peakRR, 10)} RR`;
  else sub = String(p.peakRankAct || "").replace(/[()\s]/g, "");  // fallback: peak act tag
  return `<div class="chip peak" title="Peak: ${esc(pi.name)}">
    <img class="peak-ic" src="${pi.icon}" alt="" onerror="this.style.display='none'">
    <span class="v peak-rr">${esc(sub)}</span>
  </div>`;
}

// Aynı gruptaki (premade) oyuncuları, kendi satırındaki gibi sol kenarda renkli
// bir parıltıyla işaretle. partyNumber > 0 olanlar bir gruba aittir; aynı numara
// aynı grup = aynı renk. 1. renk (sarı) kendi grubunla aynı tonda.
const PARTY_COLORS = ["#f5c451", "#4c97ed", "#43d17a", "#e0658a", "#b07cf0", "#5ad1cd"];
function partyColor(p) {
  const n = parseInt(p.partyNumber, 10);
  if (!n || n <= 0) return null;
  return PARTY_COLORS[(n - 1) % PARTY_COLORS.length];
}
// Tahmini grup rengi: presence ile gerçek tespit yapılamayan oyuncular için
// geçmiş maç birlikteliğinden kestirilir. Gerçek parti varsa bu kullanılmaz.
function predictedColor(p) {
  const n = parseInt(p.predictedParty, 10);
  if (!n || n <= 0) return null;
  return PARTY_COLORS[(n - 1) % PARTY_COLORS.length];
}

function playerRowHTML(puuid, p, isSelf) {
  const pc = partyColor(p);
  const pp = pc ? null : predictedColor(p);   // gerçek parti önceliklidir
  const edgeColor = pc || pp;
  const edgeClass = isSelf ? "" : (pc ? " party" : pp ? " party-pred" : "");
  const ri = rankInfo(parseInt(p.rank, 10) || 0);
  const { name, tag } = splitName(p.name);
  const full = p.name || "";
  const icon = AGENTS[p.agent];
  const VLOGO = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 300'%3E%3Cpolygon points='150,30 270,270 210,270 150,115 90,270 30,270' fill='%23FF4655'/%3E%3C/svg%3E";
  const card = p.playerCard
    ? `https://media.valorant-api.com/playercards/${p.playerCard}/smallart.png`
    : null;
  const avatarImg = icon || card || VLOGO;
  const avatar = `<div class="avatar"><img src="${avatarImg}" onerror="this.onerror=null;this.src='${VLOGO}'" alt=""></div>`;
  const rankImg = ri.icon ? `<img src="${ri.icon}" alt="">` : "";

  let rrHtml = "";
  if (p.rr === 0 || p.rr) {
    const n = parseInt(p.rr, 10);
    const cls = n > 0 ? "" : n < 0 ? "" : "";
    const sign = n > 0 ? "" : "";
    rrHtml = `<span class="rr ${cls}">${sign}${n} RR</span>`;
  }

  const kdRaw = p.kd != null ? String(p.kd) : null;
  const kdNum = parseFloat(kdRaw);
  const kdCls = isNaN(kdNum) ? "" : (kdNum >= 1 ? "good" : "bad");
  const hsValRaw = p.headshotPercentage;
  const hsRaw = (hsValRaw == null || hsValRaw === "") ? null
    : (isNaN(parseFloat(hsValRaw)) ? String(hsValRaw) : parseFloat(hsValRaw) + "%");
  const lvl = p.level != null ? p.level : null;
  const bothHidden = kdRaw === "Gizli" && hsRaw === "Gizli";
  const kd = localizeHidden(kdRaw);
  const hs = localizeHidden(hsRaw);

  const trackerUrl = "https://tracker.gg/valorant/profile/riot/" + encodeURIComponent(full) + "/overview";
  const vtlUrl = "https://vtl.lol/id/" + encodeURIComponent(puuid);

  return `
  <div class="player${isSelf ? " self" : ""}${edgeClass}"${edgeColor && !isSelf ? ` style="--pc:${edgeColor}"` : ""}>
    ${avatar}
    <div class="pmain">
      <div class="nmeta" data-copy="${esc(full)}" data-puuid="${esc(puuid)}">
        <span class="nick">${esc(name)}</span><span class="tag">${esc(tag)}</span>
      </div>
      <div class="rankline">
        <span class="rank-badge" style="color:${ri.color}">${rankImg}${esc(ri.name)}</span>
        ${rrHtml}
      </div>
    </div>
    <div class="stats">
      ${bothHidden ? chip(T().hidden, "tracker") : (chip(kd, "K/D", kdCls) + chip(hs, "HS"))}
      ${chip(lvl, "level")}
      ${peakChip(p)}
    </div>
    <div class="acts">
      <a href="${trackerUrl}" target="_blank" rel="noopener" title="Tracker">TRK</a>
      <a href="${vtlUrl}" target="_blank" rel="noopener" title="VTL">VTL</a>
      <button type="button" class="skins-btn" data-puuid="${esc(puuid)}" title="${esc(T().skinsTitleAttr)}">${esc(T().skins)}</button>
    </div>
  </div>`;
}

function teamCardHTML(title, cls, players, selfPuuid) {
  const rows = players.map(([puuid, p]) => playerRowHTML(puuid, p, puuid === selfPuuid)).join("");
  return `<div class="team-card ${cls}">
    <div class="team-head"><span class="team-title">${esc(title)}</span><span class="team-count">${players.length} ${esc(T().players)}</span></div>
    ${rows}
  </div>`;
}

let LATEST = { players: {} };
let _hasData = false;
let _teamsRendered = false;

function weaponsByName(weapons) {
  const map = {};
  Object.values(weapons || {}).forEach((w) => {
    if (w && w.weapon) map[String(w.weapon).toLowerCase()] = w;
  });
  return map;
}

function weaponCardHTML(displayName, w) {
  const icon = w && w.skinDisplayIcon ? w.skinDisplayIcon : null;
  const buddy = w && w.buddy_displayIcon ? w.buddy_displayIcon : null;
  const skinName = w && w.skinDisplayName ? w.skinDisplayName : "";
  const img = icon
    ? `<img class="wpn-skin" src="${esc(icon)}" alt="" loading="lazy" onerror="this.style.display='none'">`
    : `<div class="wpn-empty"></div>`;
  const buddyImg = buddy
    ? `<img class="wpn-buddy" src="${esc(buddy)}" alt="" loading="lazy" title="${esc(T().buddy)}">`
    : "";
  return `
  <div class="wpn" title="${esc(skinName)}">
    <div class="wpn-art">${img}${buddyImg}</div>
    <div class="wpn-name">${esc(displayName)}</div>
  </div>`;
}

function openSkins(puuid) {
  const p = (LATEST.players || {})[puuid];
  const modal = $("skins-modal");
  if (!p) return;

  const { name, tag } = splitName(p.name);
  const byName = weaponsByName(p.weapons);
  const hasWeapons = Object.keys(byName).length > 0;

  let columns = "";
  if (hasWeapons) {
    columns = WEAPON_GROUPS.map((names, i) => {
      const cards = names
        .map((nm) => weaponCardHTML(nm, byName[nm.toLowerCase()]))
        .join("");
      return `<div class="wpn-cat"><div class="wpn-cat-title">${esc(T().weaponCats[i])}</div>${cards}</div>`;
    }).join("");
  }

  const cardArt = p.playerCard
    ? `https://media.valorant-api.com/playercards/${p.playerCard}/largeart.png`
    : null;
  const pcPanel = `
    <div class="wpn-cat pc-cat">
      <div class="wpn-cat-title">${esc(T().playerCard)}</div>
      <div class="pc-card">
        ${p.level != null ? `<div class="pc-level">${esc(p.level)}</div>` : ""}
        ${cardArt ? `<img class="pc-art" src="${esc(cardArt)}" alt="" onerror="this.style.display='none'">` : `<div class="pc-art pc-empty"></div>`}
        <div class="pc-pname">${esc(name)}</div>
      </div>
    </div>`;

  const body = hasWeapons
    ? `<div class="skins-grid">${columns}${pcPanel}</div>`
    : `<div class="skins-grid"><div class="skins-empty">${esc(T().skinsEmpty)}</div>${pcPanel}</div>`;

  modal.innerHTML = `
    <div class="skins-backdrop"></div>
    <div class="skins-box" role="dialog" aria-modal="true">
      <div class="skins-head">
        <div class="skins-title"><span class="nick">${esc(name)}</span><span class="tag">${esc(tag)}</span><span class="skins-sub">${esc(T().weaponSkins)}</span></div>
        <button type="button" class="skins-close" title="${esc(T().close)}">✕</button>
      </div>
      <div class="skins-body">${body}</div>
    </div>`;

  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
  modal.querySelector(".skins-backdrop").addEventListener("click", closeSkins);
  modal.querySelector(".skins-close").addEventListener("click", closeSkins);
}

function closeSkins() {
  const modal = $("skins-modal");
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
  modal.innerHTML = "";
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeSkins();
});

function renderLicenseError(data) {
  $("status-text").textContent = T().licenseError;
  $("status-dot").classList.remove("live");
  $("state-badge").textContent = T().licenseError;
  $("hero").style.backgroundImage = "none";
  $("map-name").textContent = T().accessDenied;
  $("mode-name").textContent = data.message || T().licenseNotVerified;

  const hwid = data.hwid || "";
  const teams = $("teams");
  teams.className = "teams single";
  teams.innerHTML =
    '<div class="placeholder license-error">' +
    '<div class="le-icon">🔒</div>' +
    '<h2>' + esc(T().licenseFailedTitle) + '</h2>' +
    '<p class="le-msg">' + esc(data.message || T().machineNotAuthorized) + '</p>' +
    '<p class="le-hint">' + esc(T().sendHwid) + '</p>' +
    '<div id="hwid-box" class="hwid-box" title="' + esc(T().clickToCopy) + '">' + esc(hwid) + '</div>' +
    '<button id="hwid-copy" class="quit hwid-copy">' + esc(T().copyHwid) + '</button>' +
    '</div>';

  const copy = () => copyText(hwid);
  const box = $("hwid-box"); if (box) box.addEventListener("click", copy);
  const btn = $("hwid-copy"); if (btn) btn.addEventListener("click", copy);
}

function render(data) {
  LATEST = data;
  const state = data.state;
  if (state === "LICENSE_ERROR") { renderLicenseError(data); return; }
  const live = state && state !== "DISCONNECTED";
  $("status-text").textContent =
    (T().state[state] || T().waiting) + (data.mode ? " · " + (T().mode[data.mode] || data.mode) : "");
  $("status-dot").classList.toggle("live", !!live);
  $("state-badge").textContent = T().state[state] || T().waiting;

  const hero = $("hero");
  hero.style.backgroundImage = data.map_image ? `url("${data.map_image}")` : "none";
  $("map-name").textContent = data.map_name || "Valorant Decloak";
  const modeText = data.mode ? (T().mode[data.mode] || data.mode) : "";
  const srv = data.server || "";
  $("mode-name").textContent = modeText + (srv ? (modeText ? " • " : "") + srv : "");

  const teams = $("teams");
  const entries = Object.entries(data.players || {});

  if (entries.length === 0) {
    teams.className = "teams single";
    teams.innerHTML = `<div class="placeholder"><div class="spinner"></div><p>${
      state === "DISCONNECTED" ? T().disconnected : T().noPlayers
    }</p></div>`;
    return;
  }

  const selfPuuid = data.puuid;
  const distinct = [...new Set(entries.map(([, p]) => p.team).filter(Boolean))];
  const cssClass = (team) => (team === "Blue" ? "blue" : team === "Red" ? "red" : "");

  let html = "";
  if (distinct.length === 2) {
    teams.className = "teams";
    const order = distinct.slice().sort((a, b) => teamOrder(a) - teamOrder(b));
    order.forEach((team, idx) => {
      const list = entries.filter(([, p]) => p.team === team);
      html += teamCardHTML(teamLabel(team, state, idx), cssClass(team), list, selfPuuid);
    });
  } else if (distinct.length === 1) {
    teams.className = "teams single";
    const team = distinct[0];
    html = teamCardHTML(teamLabel(team, state, 0), cssClass(team), entries, selfPuuid);
  } else {
    teams.className = "teams single";
    html = teamCardHTML(T().playersTitle, "", entries, selfPuuid);
  }
  // Suppress the entrance animation on live updates so refreshes don't flash;
  // it only plays on the very first render.
  if (_teamsRendered) teams.classList.add("no-anim");
  _teamsRendered = true;
  teams.innerHTML = html;
  teams.querySelectorAll(".nmeta").forEach((el) =>
    el.addEventListener("click", () => {
      // Telefonda nicke basınca skinleri aç; masaüstünde kopyala.
      if (window.matchMedia("(max-width: 600px)").matches) {
        openSkins(el.getAttribute("data-puuid"));
      } else {
        copyText(el.getAttribute("data-copy"));
      }
    }));
  teams.querySelectorAll(".skins-btn").forEach((el) =>
    el.addEventListener("click", () => openSkins(el.getAttribute("data-puuid"))));
}

let _lastHash = "";
async function poll() {
  try {
    const data = await (await fetch("/data", { cache: "no-store" })).json();
    const hash = JSON.stringify(data);
    if (hash !== _lastHash) { _lastHash = hash; _hasData = true; render(data); }
    $("status-dot").classList.toggle("live", !!(data.state && data.state !== "DISCONNECTED"));
  } catch (e) {
    $("status-dot").classList.remove("live");
  }
}

$("quit-btn").addEventListener("click", () => {
  fetch("/quit").catch(() => {});
  document.body.innerHTML =
    "<p style='text-align:center;margin-top:120px;color:#8a909c;font-family:Inter,sans-serif'>" + esc(T().quitMsg) + "</p>";
});

async function showLanInfo() {
  try {
    const info = await (await fetch("/info", { cache: "no-store" })).json();
    if (info && info.lan_ip && info.port) {
      const url = `http://${info.lan_ip}:${info.port}`;
      $("lan-info").innerHTML =
        `${esc(T().web)}<a class="cred" href="${esc(url)}">${esc(url)}</a> • `;
    }
  } catch (e) {}
}

// Dil değiştirmeden hemen etkilenen statik (JS render dışı) öğeleri tazele.
function applyStaticI18n() {
  document.documentElement.lang = LANG;
  const qb = $("quit-btn"); if (qb) qb.title = T().quitTitle;
  // Henüz veri gelmediyse statik yer tutucuları çevir; geldiyse render hallediyor.
  if (!_hasData) {
    $("status-text").textContent = T().connecting;
    $("state-badge").textContent = T().loading;
    const ph = document.querySelector("#teams .placeholder p");
    if (ph) ph.textContent = T().loadingDots;
  }
}

function setLang(lang) {
  if (I18N[lang]) { LANG = lang; localStorage.setItem("vd_lang", lang); }
  // aktif buton işaretle
  document.querySelectorAll(".lang-opt").forEach((b) =>
    b.classList.toggle("active", b.getAttribute("data-lang") === LANG));
  applyStaticI18n();
  showLanInfo();
  if (_hasData) render(LATEST);   // mevcut veriyi yeni dilde yeniden çiz
  // Discord RPC'nin de aynı dili kullanması için backend'e bildir.
  try { fetch("/lang?l=" + encodeURIComponent(LANG)).catch(() => {}); } catch (e) {}
}

function initLangSwitch() {
  document.querySelectorAll(".lang-opt").forEach((b) =>
    b.addEventListener("click", () => setLang(b.getAttribute("data-lang"))));
  setLang(LANG);
}

(async function init() {
  initLangSwitch();
  await loadAssets();
  showLanInfo();
  poll();
  setInterval(poll, 1500);
})();
