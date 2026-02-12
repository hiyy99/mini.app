const API = window.location.origin;
const tg = window.Telegram?.WebApp;

let S = {
    player: null, businesses: [], legalCfg: [], shadowCfg: [], robberiesCfg: [],
    casinoCfg: {}, shopItems: {}, character: null, inventory: [],
    upgradesCfg: {}, upgrades: [],
    casesCfg: {}, playerCases: [], rarities: {},
    marketListings: [], myListings: [],
    incomePerSec: 0, suspicionPerSec: 0, playerLevel: 0,
    displayCash: 0, lastTick: Date.now(), currentShopTab: 'hat',
    referralCount: 0,
    // New features
    dailyMissions: [], loginData: null, loginRewards: [],
    achievements: [], achievementsCfg: [],
    prestigeCfg: {}, territories: [], territoryBonus: 0,
    missionTemplates: [],
    // VIP & Monetization
    vipStatus: { active: false, until: 0, days_left: 0 },
    adBoostUntil: 0,
    vipPackages: {}, cashPackages: {}, casePackages: {}, tonPrices: {}, vipItems: {},
};

// ── Adsgram SDK ──
let AdController = null;
try {
    if (window.Adsgram) {
        AdController = window.Adsgram.init({ blockId: "int-7686" });
    }
} catch(e) { console.log('Adsgram not available'); }

// ── TON Connect ──
let tonConnectUI = null;
try {
    if (window.TON_CONNECT_UI) {
        tonConnectUI = new window.TON_CONNECT_UI.TonConnectUI({
            manifestUrl: window.location.origin + '/static/tonconnect-manifest.json',
        });
    }
} catch(e) { console.log('TON Connect not available'); }

// ── Init ──
async function init() {
    if (tg) { tg.ready(); tg.expand(); tg.setHeaderColor('#0a0a0f'); tg.setBackgroundColor('#0a0a0f'); }
    const tid = tg?.initDataUnsafe?.user?.id || 12345;
    const uname = tg?.initDataUnsafe?.user?.username || 'player';
    // Get referral code from URL param or Telegram startParam
    const urlParams = new URLSearchParams(window.location.search);
    const refFromUrl = urlParams.get('ref') || '';
    const refFromTg = tg?.initDataUnsafe?.start_param || '';
    const refCode = refFromUrl || refFromTg;
    try {
        const r = await api('/api/init', { telegram_id: tid, username: uname, referral_code: refCode });
        S.player = r.player; S.businesses = r.businesses;
        S.legalCfg = r.legal_businesses; S.shadowCfg = r.shadow_businesses;
        S.robberiesCfg = r.robberies; S.casinoCfg = r.casino_games;
        S.shopItems = r.shop_items; S.character = r.character;
        S.inventory = r.inventory; S.incomePerSec = r.income_per_sec;
        S.suspicionPerSec = r.suspicion_per_sec; S.playerLevel = r.player_level;
        S.displayCash = r.player.cash; S.lastTick = Date.now();
        S.referralCount = r.referral_count || 0;
        S.upgradesCfg = r.upgrades_config || {};
        S.upgrades = r.upgrades || [];
        S.casesCfg = r.cases_config || {};
        S.playerCases = r.player_cases || [];
        S.rarities = r.rarities || {};
        S.marketListings = r.market_listings || [];
        S.myListings = r.my_listings || [];
        // New features
        S.dailyMissions = r.daily_missions || [];
        S.loginData = r.login_data || null;
        S.loginRewards = r.login_rewards || [];
        S.achievements = r.achievements || [];
        S.achievementsCfg = r.achievements_config || [];
        S.prestigeCfg = r.prestige_config || {};
        S.territories = r.territories || [];
        S.territoryBonus = r.territory_bonus || 0;
        // VIP & Monetization
        S.vipStatus = r.vip_status || { active: false, until: 0, days_left: 0 };
        S.adBoostUntil = r.ad_boost_until || 0;
        S.vipPackages = r.vip_packages || {};
        S.cashPackages = r.cash_packages || {};
        S.casePackages = r.case_packages || {};
        S.tonPrices = r.ton_prices || {};
        S.vipItems = r.vip_items || {};

        renderAll(); hideLoading(); startLoop();

        // Show login reward popup if can claim
        if (S.loginData && S.loginData.can_claim) {
            setTimeout(() => showLoginOverlay(), 800);
        }
    } catch(e) { document.querySelector('.loading-sub').textContent = 'Ошибка подключения'; }
}

async function api(url, body) {
    const opt = body ? { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) } : {};
    const r = await fetch(API + url, opt);
    if (!r.ok) { const e = await r.json(); throw e; }
    return r.json();
}

// ── Game Loop ──
function startLoop() {
    let lastAffordCheck = 0;
    setInterval(() => {
        const dt = (Date.now() - S.lastTick) / 1000; S.lastTick = Date.now();
        const prevCash = S.displayCash;
        if (S.incomePerSec > 0) S.displayCash += S.incomePerSec * dt;
        if (S.player) {
            S.player.suspicion = Math.max(0, Math.min(100, S.player.suspicion + S.suspicionPerSec * dt));
        }
        updateHUD();
        // Re-render buy buttons every 2 seconds so they enable as cash grows
        if (Date.now() - lastAffordCheck > 2000 && S.displayCash !== prevCash) {
            lastAffordCheck = Date.now();
            renderBusiness('legal'); renderBusiness('shadow');
            renderUpgrades(); renderCases(); renderShop();
        }
    }, 200);
    setInterval(sync, 10000);
}

async function sync() {
    if (!S.player) return;
    try {
        const r = await api('/api/collect', { telegram_id: S.player.telegram_id });
        S.player = r.player; S.displayCash = r.player.cash;
        S.incomePerSec = r.income_per_sec; S.suspicionPerSec = r.suspicion_per_sec;
    } catch(e) {}
}

// ── Helpers ──
function $(sel) { return document.querySelector(sel); }
function fmt(n) {
    if (n >= 1e9) return (n/1e9).toFixed(2)+'B';
    if (n >= 1e6) return (n/1e6).toFixed(2)+'M';
    if (n >= 1e4) return (n/1e3).toFixed(1)+'K';
    if (n >= 100) return Math.floor(n).toLocaleString('ru-RU');
    return n.toFixed(1);
}
function fmtTime(s) { s=Math.ceil(s); return Math.floor(s/60)+':'+String(s%60).padStart(2,'0'); }
function rarityColor(rarity) { return S.rarities[rarity]?.color || '#9e9e9e'; }
function rarityName(rarity) { return S.rarities[rarity]?.name || rarity; }
function itemBonusText(item) {
    if (!item || item.bonus_type === 'none') return '';
    const map = {
        fear: `😈 Страх +${item.bonus}`,
        respect: `🤝 Уважение +${item.bonus}`,
        income: `💰 Доход +${item.bonus}%`,
        suspicion_reduce: `🛡 Подозрение -${item.bonus}%`,
    };
    return map[item.bonus_type] || '';
}

// ── Render ──
function renderAll() {
    updateHUD(); renderBusiness('legal'); renderBusiness('shadow'); renderUpgrades();
    renderRobberies(); renderCharacter(); renderShop(); renderCases();
    renderWeapons(); renderMarketListings(); renderInventory(); renderMyListings();
    renderGang(); renderReferral();
    renderMissions(); renderPrestige(); renderTerritories(); renderAchievements();
    renderLeaderboard(); renderVipShop(); updateAdButtons(); updateVipBadges();
}

function updateHUD() {
    $('#cash').textContent = '$' + fmt(S.displayCash);
    $('#income-per-sec').textContent = '$' + fmt(S.incomePerSec) + '/с';
    if (!S.player) return;
    const s = S.player.suspicion;
    $('#suspicion-fill').style.width = s + '%';
    $('#suspicion-text').textContent = Math.floor(s) + '%';
    $('#suspicion-fill').style.background = s < 40 ? 'var(--green)' : s < 70 ? 'var(--gold)' : 'var(--red)';
    $('#rep-fear').textContent = S.player.reputation_fear;
    $('#rep-respect').textContent = S.player.reputation_respect;
    $('#player-level').textContent = S.playerLevel;

    // VIP badge in top bar
    const vipBadge = $('#vip-badge');
    if (vipBadge) vipBadge.classList.toggle('hidden', !S.vipStatus.active);

    // Ad boost indicator
    const adIndicator = $('#ad-boost-indicator');
    if (adIndicator) {
        const hasBoost = S.adBoostUntil > Date.now() / 1000;
        adIndicator.classList.toggle('hidden', !hasBoost);
    }
}

function renderBusiness(type) {
    const cfg = type === 'legal' ? S.legalCfg : S.shadowCfg;
    const el = $('#' + type + '-list'); el.innerHTML = '';
    for (const c of cfg) {
        const owned = S.businesses.find(b => b.business_id === c.id);
        const lvl = owned ? owned.level : 0;
        const locked = S.playerLevel < c.unlock_level;
        const income = c.base_income * Math.pow(c.income_multiplier, Math.max(lvl,1)-1);
        const cost = c.base_cost * Math.pow(c.cost_multiplier, Math.max(lvl,1)-1);
        const afford = S.displayCash >= cost;
        const susp = type==='shadow'
            ? `<span class="business-suspicion-up">🔥+${c.suspicion_add}/с</span>`
            : `<span class="business-suspicion-down">🛡-${c.suspicion_reduce}/с</span>`;
        const mgr = owned && !owned.has_manager
            ? `<button class="btn-manager" onclick="hireManager('${c.id}')" ${S.displayCash>=c.manager_cost?'':'disabled'}>👔 $${fmt(c.manager_cost)}</button>`
            : owned?.has_manager ? `<span class="manager-badge">👔</span>` : '';
        el.innerHTML += `<div class="business-card${locked?' locked':''}">
            <div class="business-emoji">${c.emoji}</div>
            <div class="business-info">
                <div class="business-name">${c.name}</div>
                <div class="business-stats">
                    ${lvl?`<span class="business-level">Ур.${lvl}</span>`:''}
                    <span class="business-income">$${fmt(income)}/с</span>${susp}
                </div>
            </div>
            <div class="business-actions">
                ${locked?`<span class="locked-text">🔒 Ур.${c.unlock_level}</span>`
                :`<button class="btn-buy ${type==='shadow'?'shadow-btn':''}" onclick="buyBiz('${c.id}')" ${afford?'':'disabled'}>${lvl?'⬆️':'Купить'}</button>
                <span class="business-cost">$${fmt(cost)}</span>${mgr}`}
            </div></div>`;
    }
}

function renderUpgrades() {
    const el = $('#upgrades-sub-list');
    if (!el) return;
    el.innerHTML = '';
    for (const [id, cfg] of Object.entries(S.upgradesCfg)) {
        const owned = S.upgrades.find(u => u.upgrade_id === id);
        const lvl = owned ? owned.level : 0;
        const cost = cfg.base_cost * Math.pow(cfg.cost_multiplier, lvl);
        const afford = S.displayCash >= cost;
        el.innerHTML += `<div class="business-card">
            <div class="business-emoji">${cfg.emoji}</div>
            <div class="business-info">
                <div class="business-name">${cfg.name}</div>
                <div class="business-stats">
                    ${lvl ? `<span class="business-level">Ур.${lvl}</span>` : ''}
                    <span style="color:var(--text2)">${cfg.description}</span>
                </div>
            </div>
            <div class="business-actions">
                <button class="btn-buy shadow-btn" onclick="buyUpgrade('${id}')" ${afford?'':'disabled'}>${lvl?'⬆️':'Купить'}</button>
                <span class="business-cost">$${fmt(cost)}</span>
            </div></div>`;
    }
}

function renderRobberies() {
    const el = $('#robbery-list'); el.innerHTML = '';
    const now = Date.now()/1000;
    for (const c of S.robberiesCfg) {
        const locked = S.playerLevel < c.unlock_level;
        const cd = S.player.robbery_cooldown_ts - now;
        const onCd = cd > 0;
        el.innerHTML += `<div class="robbery-card${locked?' locked':''}">
            <div class="robbery-header"><span class="robbery-emoji">${c.emoji}</span><div class="robbery-info"><div class="robbery-name">${c.name}</div></div></div>
            <div class="robbery-stats">
                <span class="robbery-reward">💰 $${fmt(c.min_reward)}-$${fmt(c.max_reward)}</span>
                <span class="robbery-chance">🎯 ${Math.floor(c.success_chance*100)}%</span>
                <span class="robbery-heat">🔥 +${c.suspicion_gain}%</span>
            </div>
            ${locked?`<span class="locked-text">🔒 Уровень ${c.unlock_level}</span>`
            :onCd?`<div class="cooldown-text" id="cd-${c.id}">⏳ ${fmtTime(cd)}</div>`
            :`<button class="btn-robbery" onclick="doRobbery('${c.id}')">Выполнить</button>`}
        </div>`;
        if (onCd && !locked) startCd(c.id, cd);
    }
}

// ── Missions ──
function renderMissions() {
    const el = $('#missions-list');
    if (!el) return;
    if (!S.dailyMissions.length) {
        el.innerHTML = '<div class="inv-empty">Нет миссий на сегодня</div>';
        return;
    }
    // Mission templates map
    const TEMPLATES = {
        robbery: {name:'Совершить ограбление', emoji:'🔫'},
        robbery_success: {name:'Успешное ограбление', emoji:'💰'},
        casino_play: {name:'Сыграть в казино', emoji:'🎰'},
        casino_win: {name:'Выиграть в казино', emoji:'🎲'},
        buy_business: {name:'Купить/улучшить бизнес', emoji:'🏢'},
        earn_cash_10k: {name:'Заработать $10,000', emoji:'💵'},
        earn_cash_50k: {name:'Заработать $50,000', emoji:'💵'},
        pvp_attack: {name:'Напасть на игрока', emoji:'⚔️'},
        pvp_win: {name:'Победить в PvP', emoji:'🏆'},
        shop_buy: {name:'Купить предмет', emoji:'🛒'},
        case_open: {name:'Открыть кейс', emoji:'📦'},
        case_open_1: {name:'Открыть кейс', emoji:'📦'},
    };
    let html = '';
    for (const m of S.dailyMissions) {
        const tmpl = TEMPLATES[m.mission_id] || {name: m.mission_id, emoji: '📋'};
        const pct = Math.min(100, Math.floor((m.progress / m.target) * 100));
        const done = m.completed && !m.claimed;
        const claimed = m.claimed;
        html += `<div class="mission-card ${claimed ? 'mission-claimed' : done ? 'mission-done' : ''}">
            <div class="mission-header">
                <span class="mission-emoji">${tmpl.emoji}</span>
                <div class="mission-info">
                    <div class="mission-name">${tmpl.name}</div>
                    <div class="mission-progress-text">${m.progress}/${m.target}</div>
                </div>
                <div class="mission-reward">$${fmt(m.reward)}</div>
            </div>
            <div class="mission-progress-bar">
                <div class="mission-progress-fill" style="width:${pct}%"></div>
            </div>
            ${claimed ? '<div class="mission-status">Получено</div>'
            : done ? `<button class="btn-buy" onclick="claimMission(${m.id})">Забрать</button>`
            : ''}
        </div>`;
    }
    el.innerHTML = html;
}

// ── Character (detailed card) ──
function renderCharacter() {
    if (!S.character) return;
    const slots = [
        { key: 'hat', label: '🎩 Головной убор' },
        { key: 'jacket', label: '🧥 Одежда' },
        { key: 'accessory', label: '💍 Аксессуар' },
        { key: 'weapon', label: '⚔️ Оружие' },
        { key: 'car', label: '🚗 Транспорт' },
    ];
    const eqEl = $('#char-equipment');
    const bonusEl = $('#char-bonuses');
    if (!eqEl) return;

    $('#char-nickname').textContent = S.character.nickname || 'Новичок';
    $('#char-level').textContent = S.playerLevel;

    let eqHtml = '';
    let totalBonuses = { fear: 0, respect: 0, income: 0, suspicion_reduce: 0 };

    for (const slot of slots) {
        const itemId = S.character[slot.key];
        const item = itemId && itemId !== 'none' ? S.shopItems[itemId] : null;
        if (item) {
            const r = item.rarity || 'common';
            eqHtml += `<div class="char-eq-row">
                <span class="char-eq-label">${slot.label}</span>
                <span class="char-eq-value" style="color:${rarityColor(r)}">${item.emoji} ${item.name}</span>
            </div>`;
            if (item.bonus_type && item.bonus_type !== 'none') {
                totalBonuses[item.bonus_type] = (totalBonuses[item.bonus_type] || 0) + item.bonus;
            }
        } else {
            eqHtml += `<div class="char-eq-row">
                <span class="char-eq-label">${slot.label}</span>
                <span class="char-eq-value empty">Пусто</span>
            </div>`;
        }
    }
    eqEl.innerHTML = eqHtml;

    let bonusHtml = '';
    if (totalBonuses.fear > 0) bonusHtml += `<span class="char-bonus-tag fear">😈 Страх +${totalBonuses.fear}</span>`;
    if (totalBonuses.respect > 0) bonusHtml += `<span class="char-bonus-tag respect">🤝 Уважение +${totalBonuses.respect}</span>`;
    if (totalBonuses.income > 0) bonusHtml += `<span class="char-bonus-tag income">💰 Доход +${totalBonuses.income}%</span>`;
    if (totalBonuses.suspicion_reduce > 0) bonusHtml += `<span class="char-bonus-tag suspicion">🛡 Подозрение -${totalBonuses.suspicion_reduce}%</span>`;
    if (!bonusHtml) bonusHtml = '<span class="char-bonus-tag empty-tag">Нет бонусов</span>';
    bonusEl.innerHTML = '<div class="char-bonus-title">Бонусы от экипировки</div>' + bonusHtml;
}

// ── Prestige ──
function renderPrestige() {
    const el = $('#prestige-info');
    if (!el || !S.player) return;
    const pLvl = S.player.prestige_level || 0;
    const pMult = S.player.prestige_multiplier || 1.0;
    const cfg = S.prestigeCfg;
    const reqLevel = (cfg.base_level_required || 10) + pLvl * (cfg.level_increment || 5);
    const nextMult = (1.0 + (pLvl + 1) * (cfg.multiplier_bonus || 0.25));
    const canPrestige = S.playerLevel >= reqLevel;

    el.innerHTML = `
        <div class="prestige-card">
            <div class="prestige-stats">
                <div class="prestige-stat"><span>Престиж</span><strong>⚡ ${pLvl}</strong></div>
                <div class="prestige-stat"><span>Множитель дохода</span><strong style="color:var(--gold)">x${pMult.toFixed(2)}</strong></div>
                <div class="prestige-stat"><span>Требуемый уровень</span><strong>${reqLevel}</strong></div>
                <div class="prestige-stat"><span>Текущий уровень</span><strong>${S.playerLevel}</strong></div>
            </div>
            <div class="prestige-next">Следующий множитель: <strong style="color:var(--green)">x${nextMult.toFixed(2)}</strong></div>
            <button class="btn-prestige ${canPrestige ? '' : 'disabled'}" onclick="doPrestige()" ${canPrestige ? '' : 'disabled'}>
                ⚡ Престиж ${pLvl + 1}
            </button>
            <div class="prestige-warning">Сбрасывает: бизнесы, кэш, репутацию. Сохраняет: предметы, банду.</div>
        </div>`;
}

// ── Territories ──
function renderTerritories() {
    const el = $('#territories-list');
    const bonusEl = $('#territory-bonus-info');
    if (!el) return;

    if (bonusEl) {
        if (S.territoryBonus > 0) {
            bonusEl.innerHTML = `<div class="territory-bonus-badge">Бонус банды: <strong>+${S.territoryBonus}%</strong> к доходу</div>`;
        } else {
            bonusEl.innerHTML = '';
        }
    }

    if (!S.territories.length) {
        el.innerHTML = '<div class="inv-empty">Нет территорий</div>';
        return;
    }

    const gangId = S.player?.gang_id || 0;
    let html = '';
    for (const t of S.territories) {
        const owned = t.owner_gang_id === gangId && gangId > 0;
        const ownerText = t.gang_name ? `[${t.gang_tag}] ${t.gang_name}` : 'Свободна';
        html += `<div class="territory-card ${owned ? 'territory-owned' : ''}">
            <div class="territory-header">
                <span class="territory-emoji">${t.emoji}</span>
                <div class="territory-info">
                    <div class="territory-name">${t.name}</div>
                    <div class="territory-bonus">+${t.bonus_percent}% к доходу</div>
                    <div class="territory-owner">${ownerText}</div>
                </div>
            </div>
            ${owned ? '<div class="territory-status">Ваша территория</div>'
            : gangId ? `<button class="btn-attack" onclick="attackTerritory(${t.id})">Атаковать</button>`
            : '<div class="territory-status" style="color:var(--text2)">Нужна банда</div>'}
        </div>`;
    }
    el.innerHTML = html;
}

// ── Achievements ──
function renderAchievements() {
    const el = $('#achievements-list');
    if (!el) return;
    if (!S.achievementsCfg.length) {
        el.innerHTML = '<div class="inv-empty">Нет достижений</div>';
        return;
    }
    const unlocked = {};
    for (const a of S.achievements) {
        unlocked[a.achievement_id] = a;
    }
    let html = '';
    for (const ach of S.achievementsCfg) {
        const u = unlocked[ach.id];
        const isUnlocked = !!u;
        const isClaimed = u && u.claimed;
        html += `<div class="achievement-card ${isUnlocked ? 'achievement-unlocked' : 'achievement-locked'} ${isClaimed ? 'achievement-claimed' : ''}">
            <div class="achievement-header">
                <span class="achievement-emoji">${ach.emoji}</span>
                <div class="achievement-info">
                    <div class="achievement-name">${ach.name}</div>
                    <div class="achievement-desc">${ach.description}</div>
                </div>
                <div class="achievement-reward">$${fmt(ach.reward)}</div>
            </div>
            ${isClaimed ? '<div class="achievement-status">Получено</div>'
            : isUnlocked ? `<button class="btn-buy" onclick="claimAchievement('${ach.id}')">Забрать</button>`
            : ''}
        </div>`;
    }
    el.innerHTML = html;
}

// ── Leaderboard ──
function renderLeaderboard() {
    const el = $('#leaderboard-list');
    if (!el) return;
    el.innerHTML = '<div class="inv-empty">Загрузка...</div>';
    loadLeaderboard();
}

async function loadLeaderboard() {
    const el = $('#leaderboard-list');
    if (!el) return;
    try {
        const r = await fetch(API + '/api/leaderboard').then(r => r.json());
        if (!r.leaderboard.length) { el.innerHTML = '<div class="inv-empty">Пока нет игроков</div>'; return; }
        const medals = ['🥇', '🥈', '🥉'];
        let html = '';
        r.leaderboard.forEach((p, i) => {
            const isMe = S.player && p.telegram_id === S.player.telegram_id;
            const medal = i < 3 ? medals[i] : `#${i + 1}`;
            html += `<div class="lb-row ${isMe ? 'lb-me' : ''}">
                <span class="lb-rank">${medal}</span>
                <div class="lb-info">
                    <div class="lb-name">${p.username || 'Игрок'}</div>
                    <div class="lb-stats">💰 $${fmt(p.total_earned)} | 😈${p.reputation_fear} 🤝${p.reputation_respect}</div>
                </div>
                <div class="lb-cash">$${fmt(p.cash)}</div>
            </div>`;
        });
        el.innerHTML = html;
    } catch(e) { el.innerHTML = '<div class="inv-empty">Ошибка загрузки</div>'; }
}

// ── Inventory ──
function renderInventory() {
    const casesEl = $('#inv-cases');
    const listEl = $('#inv-list');
    if (!casesEl || !listEl) return;

    // Render owned cases
    if (S.playerCases.length === 0) {
        casesEl.innerHTML = '<div class="inv-empty">Нет кейсов — купи в Магазине</div>';
    } else {
        let html = '';
        for (const pc of S.playerCases) {
            const cfg = S.casesCfg[pc.case_id];
            if (!cfg) continue;
            html += `<div class="inv-case-card" style="border-color:${rarityColor(cfg.rarity)}" onclick="openCaseAnim(${pc.id},'${pc.case_id}')">
                <div class="inv-case-emoji">${cfg.emoji}</div>
                <div class="inv-case-name">${cfg.name}</div>
                <div class="inv-case-action">Открыть</div>
            </div>`;
        }
        casesEl.innerHTML = html;
    }

    // Render owned items
    const items = S.inventory.filter(i => S.shopItems[i.item_id]);
    if (items.length === 0) {
        listEl.innerHTML = '<div class="inv-empty">Инвентарь пуст</div>';
    } else {
        // Sort: equipped first, then by rarity
        const rarityOrder = { legendary: 0, epic: 1, rare: 2, uncommon: 3, common: 4 };
        items.sort((a, b) => {
            if (b.equipped !== a.equipped) return b.equipped - a.equipped;
            const ra = S.shopItems[a.item_id]?.rarity || 'common';
            const rb = S.shopItems[b.item_id]?.rarity || 'common';
            return (rarityOrder[ra] || 4) - (rarityOrder[rb] || 4);
        });
        let html = '';
        for (const inv of items) {
            const item = S.shopItems[inv.item_id];
            const r = item.rarity || 'common';
            const equipped = inv.equipped;
            const bonus = itemBonusText(item);
            const isOnMarket = S.myListings.some(l => l.item_id === inv.item_id);

            let actions = '';
            if (equipped) {
                actions = `<span class="inv-equipped-badge">Надето</span>`;
            } else if (isOnMarket) {
                actions = `<span class="inv-market-badge">На площадке</span>`;
            } else {
                actions = `<button class="btn-shop owned" onclick="equipItem('${inv.item_id}')">Надеть</button>
                    <button class="btn-sell-small" onclick="promptSell('${inv.item_id}')">Продать</button>`;
            }

            html += `<div class="inv-item" style="border-left:3px solid ${rarityColor(r)}">
                <div class="inv-item-left">
                    <div class="inv-item-emoji">${item.emoji}</div>
                    <div class="inv-item-info">
                        <div class="inv-item-name" style="color:${rarityColor(r)}">${item.name}</div>
                        <div class="inv-item-rarity">${rarityName(r)}</div>
                        <div class="inv-item-desc">${item.description || ''}</div>
                        ${bonus ? `<div class="inv-item-bonus">${bonus}</div>` : ''}
                    </div>
                </div>
                <div class="inv-item-actions">${actions}</div>
            </div>`;
        }
        listEl.innerHTML = html;
    }
}

// ── My Market Listings ──
function renderMyListings() {
    const el = $('#my-listings-list');
    const section = $('#my-listings-section');
    if (!el) return;
    if (S.myListings.length === 0) {
        if (section) section.classList.add('hidden');
        return;
    }
    if (section) section.classList.remove('hidden');
    let html = '';
    for (const l of S.myListings) {
        const item = S.shopItems[l.item_id];
        if (!item) continue;
        const r = item.rarity || 'common';
        html += `<div class="shop-item" style="border-left:3px solid ${rarityColor(r)}">
            <div class="shop-item-emoji">${item.emoji}</div>
            <div class="shop-item-info">
                <div class="shop-item-name" style="color:${rarityColor(r)}">${item.name}</div>
                <div class="shop-item-bonus">$${fmt(l.price)}</div>
            </div>
            <div class="shop-item-actions">
                <button class="btn-shop" style="background:var(--red)" onclick="cancelListing('${l.item_id}',${l.price})">Снять</button>
            </div>
        </div>`;
    }
    el.innerHTML = html;
}

// ── Shop (regular items) ──
function renderShop() {
    const el = $('#shop-list'); el.innerHTML = '';
    const items = Object.entries(S.shopItems).filter(([k,v]) => v.slot === S.currentShopTab && !v.case_only && !v.vip_only);
    for (const [id, item] of items) {
        const owned = S.inventory.find(i => i.item_id === id);
        const equipped = owned?.equipped;
        const afford = S.displayCash >= item.price;
        const r = item.rarity || 'common';
        const bonus = itemBonusText(item);
        let btn;
        if (equipped) btn = `<button class="btn-shop equipped" disabled>Надето</button>`;
        else if (owned) btn = `<button class="btn-shop owned" onclick="equipItem('${id}')">Надеть</button>`;
        else btn = `<button class="btn-shop" onclick="buyItem('${id}')" ${afford?'':'disabled'}>$${fmt(item.price)}</button>`;
        el.innerHTML += `<div class="shop-item" style="border-left:3px solid ${rarityColor(r)}">
            <div class="shop-item-emoji">${item.emoji}</div>
            <div class="shop-item-info">
                <div class="shop-item-name" style="color:${rarityColor(r)}">${item.name}</div>
                <div class="shop-item-rarity">${rarityName(r)}</div>
                <div class="shop-item-desc">${item.description || ''}</div>
                ${bonus ? `<div class="shop-item-bonus">${bonus}</div>` : ''}
            </div>
            <div class="shop-item-actions">${btn}</div></div>`;
    }
}

// ── Cases ──
function renderCases() {
    const el = $('#cases-list');
    if (!el) return;
    el.innerHTML = '';
    for (const [id, cfg] of Object.entries(S.casesCfg)) {
        const r = cfg.rarity || 'common';
        const afford = S.displayCash >= cfg.price;
        // Count items by rarity in loot table
        const lootSummary = {};
        for (const l of cfg.loot) {
            const it = S.shopItems[l.item_id];
            if (it) {
                const ir = it.rarity || 'common';
                lootSummary[ir] = (lootSummary[ir] || 0) + 1;
            }
        }
        let lootTags = '';
        for (const [lr, count] of Object.entries(lootSummary)) {
            lootTags += `<span class="case-loot-tag" style="color:${rarityColor(lr)}">${count}x ${rarityName(lr)}</span> `;
        }

        el.innerHTML += `<div class="case-card" style="border-color:${rarityColor(r)}">
            <div class="case-card-top">
                <div class="case-emoji">${cfg.emoji}</div>
                <div class="case-info">
                    <div class="case-name" style="color:${rarityColor(r)}">${cfg.name}</div>
                    <div class="case-desc">${cfg.description}</div>
                    <div class="case-loot-tags">${lootTags}</div>
                </div>
            </div>
            <button class="btn-case-buy" style="background:${rarityColor(r)}" onclick="spinCase('${id}')" ${afford?'':'disabled'}>
                🎰 Крутить — $${fmt(cfg.price)}
            </button>
        </div>`;
    }
}

// ── Weapons (Black Market Shop) ──
function renderWeapons() {
    const el = $('#weapons-list');
    if (!el) return;
    el.innerHTML = '';
    const weapons = Object.entries(S.shopItems).filter(([k,v]) => v.slot === 'weapon' && !v.case_only);
    for (const [id, item] of weapons) {
        const owned = S.inventory.find(i => i.item_id === id);
        const equipped = owned?.equipped;
        const afford = S.displayCash >= item.price;
        const r = item.rarity || 'common';
        const bonus = itemBonusText(item);
        let btn;
        if (equipped) btn = `<button class="btn-shop equipped" disabled>Надето</button>`;
        else if (owned) btn = `<button class="btn-shop owned" onclick="equipItem('${id}')">Надеть</button>`;
        else btn = `<button class="btn-shop" onclick="buyItem('${id}')" ${afford?'':'disabled'}>$${fmt(item.price)}</button>`;
        el.innerHTML += `<div class="shop-item" style="border-left:3px solid ${rarityColor(r)}">
            <div class="shop-item-emoji">${item.emoji}</div>
            <div class="shop-item-info">
                <div class="shop-item-name" style="color:${rarityColor(r)}">${item.name}</div>
                <div class="shop-item-rarity">${rarityName(r)}</div>
                <div class="shop-item-desc">${item.description || ''}</div>
                ${bonus ? `<div class="shop-item-bonus">${bonus}</div>` : ''}
            </div>
            <div class="shop-item-actions">${btn}</div></div>`;
    }
}

// ── Market Listings (Player-to-Player) ──
function renderMarketListings() {
    const el = $('#market-listings-list');
    if (!el) return;
    if (S.marketListings.length === 0) {
        el.innerHTML = '<div class="inv-empty">Пока нет лотов от игроков</div>';
        return;
    }
    let html = '';
    for (const l of S.marketListings) {
        const item = S.shopItems[l.item_id];
        if (!item) continue;
        const r = item.rarity || 'common';
        const afford = S.displayCash >= l.price;
        const bonus = itemBonusText(item);
        const alreadyOwned = S.inventory.some(i => i.item_id === l.item_id);
        html += `<div class="shop-item" style="border-left:3px solid ${rarityColor(r)}">
            <div class="shop-item-emoji">${item.emoji}</div>
            <div class="shop-item-info">
                <div class="shop-item-name" style="color:${rarityColor(r)}">${item.name}</div>
                <div class="shop-item-rarity">${rarityName(r)} ${bonus ? '• ' + bonus : ''}</div>
                <div class="shop-item-desc">Продавец: ${l.seller_name || 'Игрок'}</div>
            </div>
            <div class="shop-item-actions">
                ${alreadyOwned ? '<button class="btn-shop" disabled>Уже есть</button>'
                : `<button class="btn-shop" onclick="buyFromMarket(${l.id})" ${afford?'':'disabled'}>$${fmt(l.price)}</button>`}
            </div>
        </div>`;
    }
    el.innerHTML = html;
}

function renderGang() {
    const el = $('#gang-section');
    if (S.player.gang_id) {
        el.innerHTML = `<div class="gang-info"><div class="gang-name">👥 Ты в банде #${S.player.gang_id}</div>
            <div class="gang-stats">Скоро: список участников, банк банды, войны</div></div>`;
    } else {
        el.innerHTML = `<div class="gang-create">
            <p style="margin-bottom:8px;font-size:.85rem">Создай свою банду или вступи в существующую</p>
            <input class="gang-input" id="gang-name-input" placeholder="Название банды">
            <input class="gang-input" id="gang-tag-input" placeholder="Тег (1-4 символа)">
            <button class="btn btn-primary" onclick="createGang()" style="width:100%">Создать банду ($10,000)</button>
            <div id="gangs-list" style="margin-top:12px"></div>
            <button class="btn btn-primary" onclick="loadGangs()" style="width:100%;margin-top:8px;background:var(--blue)">Показать банды</button>
        </div>`;
    }
}

function renderReferral() {
    if (!S.player) return;
    const tid = S.player.telegram_id;
    const link = `https://t.me/shadow_empire_game_bot?start=ref_${tid}`;
    const section = document.querySelector('.referral-section');
    if (!section) return;
    section.innerHTML = `
        <h3>🔗 Пригласи друга</h3>
        <p class="ref-info">Оба получите $${REFERRAL_BONUS}!</p>
        <div class="ref-link-box" onclick="copyRefLink()">${link}</div>
        <div class="ref-buttons">
            <button class="btn btn-primary" onclick="copyRefLink()">📋 Копировать</button>
            <button class="btn btn-primary" onclick="shareRefLink()">📤 Поделиться</button>
        </div>
        <div id="ref-count">Приглашено: ${S.referralCount}</div>`;
}

const REFERRAL_BONUS = 1000;

function copyRefLink() {
    const tid = S.player.telegram_id;
    const link = `https://t.me/shadow_empire_game_bot?start=ref_${tid}`;
    navigator.clipboard.writeText(link).then(() => {
        showPopup('✅', 'Скопировано!', '', 'Ссылка скопирована в буфер обмена', '');
    }).catch(() => {
        // fallback
        const ta = document.createElement('textarea');
        ta.value = link; document.body.appendChild(ta);
        ta.select(); document.execCommand('copy');
        document.body.removeChild(ta);
        showPopup('✅', 'Скопировано!', '', 'Ссылка скопирована в буфер обмена', '');
    });
}

function shareRefLink() {
    const tid = S.player.telegram_id;
    const link = `https://t.me/shadow_empire_game_bot?start=ref_${tid}`;
    const text = `Заходи в Shadow Empire! Построй свою криминальную империю 🕴️`;
    if (tg) {
        tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`);
    } else {
        window.open(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`);
    }
}

// ── Actions ──
async function buyBiz(id) {
    try {
        const r = await api('/api/buy', { telegram_id: S.player.telegram_id, business_id: id });
        S.player = r.player; S.businesses = r.businesses; S.displayCash = r.player.cash;
        S.incomePerSec = r.income_per_sec; S.suspicionPerSec = r.suspicion_per_sec;
        S.playerLevel = r.player_level; renderAll();
    } catch(e) { showPopup('❌', 'Не хватает', '', e.detail || 'Ошибка', ''); }
}

async function hireManager(id) {
    try {
        const r = await api('/api/manager', { telegram_id: S.player.telegram_id, business_id: id });
        S.player = r.player; S.businesses = r.businesses; S.displayCash = r.player.cash; renderAll();
    } catch(e) {}
}

async function doRobbery(id) {
    try {
        const r = await api('/api/robbery', { telegram_id: S.player.telegram_id, robbery_id: id });
        S.player = r.player; S.displayCash = r.player.cash;
        if (r.success) showPopup('💰', 'Успешно!', '', '+$' + fmt(r.reward), '🔥 Подозрение +' + r.suspicion_gain + '%');
        else showPopup('🚨', 'Провал!', 'Тебя заметили', '$0', '🔥 Подозрение +' + r.suspicion_gain + '%');
        renderAll();
    } catch(e) { showPopup('⏳', 'Подожди', '', e.detail || '', ''); }
}

async function buyUpgrade(id) {
    try {
        const r = await api('/api/upgrade', { telegram_id: S.player.telegram_id, upgrade_id: id });
        S.player = r.player; S.upgrades = r.upgrades; S.displayCash = r.player.cash;
        const cfg = S.upgradesCfg[id];
        showPopup(cfg.emoji, cfg.name, cfg.description, '', '');
        renderAll();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

// ── Shop Actions ──
async function buyItem(id) {
    try {
        const r = await api('/api/shop/buy', { telegram_id: S.player.telegram_id, item_id: id });
        S.player = r.player; S.inventory = r.inventory; S.displayCash = r.player.cash;
        showPopup('🛍', 'Куплено!', S.shopItems[id].name, '', '');
        renderAll();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

async function equipItem(id) {
    try {
        const r = await api('/api/shop/equip', { telegram_id: S.player.telegram_id, item_id: id });
        S.character = r.character; S.inventory = r.inventory;
        renderCharacter(); renderShop(); renderWeapons(); renderInventory();
    } catch(e) {}
}

// ── Cases Actions ──
async function buyCase(caseId) {
    try {
        const r = await api('/api/case/buy', { telegram_id: S.player.telegram_id, case_id: caseId });
        S.player = r.player; S.playerCases = r.player_cases; S.displayCash = r.player.cash;
        const cfg = S.casesCfg[caseId];
        showPopup('📦', 'Кейс куплен!', cfg.name, 'Открой в инвентаре', '');
        renderCases(); renderInventory(); updateHUD();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

async function spinCase(caseId) {
    const cfg = S.casesCfg[caseId];
    if (!cfg) return;
    if (S.displayCash < cfg.price) {
        showPopup('❌', 'Недостаточно денег', '', `Нужно $${fmt(cfg.price)}`, '');
        return;
    }

    const overlay = $('#case-overlay');
    const roulette = $('#case-roulette');
    const result = $('#case-open-result');
    const okBtn = $('#case-ok-btn');

    result.classList.add('hidden');
    result.classList.remove('case-result-appear');
    okBtn.classList.add('hidden');
    roulette.classList.remove('hidden');
    overlay.classList.remove('hidden');

    // Build temp strip with random items while API loads
    const fakeLoot = cfg.loot || [];
    const totalWeight = fakeLoot.reduce((s, l) => s + l.weight, 0);
    const tempItems = [];
    for (let i = 0; i < 60; i++) {
        let rand = Math.random() * totalWeight, cum = 0;
        for (const l of fakeLoot) {
            cum += l.weight;
            if (rand <= cum) {
                const it = S.shopItems[l.item_id];
                if (it) tempItems.push({ ...it, item_id: l.item_id });
                break;
            }
        }
    }
    renderRouletteStrip(tempItems);

    // Buy + open in one API call
    let apiResult;
    try {
        apiResult = await api('/api/case/spin', { telegram_id: S.player.telegram_id, case_id: caseId });
    } catch(e) {
        closeCaseOverlay();
        showPopup('❌', 'Ошибка', '', e.detail || '', '');
        return;
    }

    S.player = apiResult.player;
    S.inventory = apiResult.inventory;
    S.playerCases = apiResult.player_cases;
    S.displayCash = apiResult.player.cash;

    // Build winning item
    let winItem;
    if (apiResult.won_item_id && apiResult.won_item) {
        winItem = apiResult.won_item;
    } else {
        winItem = { emoji: '💵', name: 'Компенсация', rarity: 'legendary' };
    }

    // Rebuild strip with real winner and animate
    const stripItems = buildRouletteStrip(caseId, winItem);
    renderRouletteStrip(stripItems);
    await animateRoulette(40);
    await new Promise(r => setTimeout(r, 800));

    // Show result
    roulette.classList.add('hidden');
    if (apiResult.won_item_id && apiResult.won_item) {
        const item = apiResult.won_item;
        const rr = item.rarity || 'common';
        $('#case-won-emoji').textContent = item.emoji;
        $('#case-won-name').textContent = item.name;
        $('#case-won-name').style.color = rarityColor(rr);
        $('#case-won-rarity').textContent = rarityName(rr);
        $('#case-won-rarity').style.color = rarityColor(rr);
        $('#case-won-desc').textContent = item.description || '';
    } else {
        $('#case-won-emoji').textContent = '💵';
        $('#case-won-name').textContent = 'Компенсация';
        $('#case-won-name').style.color = 'var(--gold)';
        $('#case-won-rarity').textContent = '+$' + fmt(apiResult.cash_compensation);
        $('#case-won-rarity').style.color = 'var(--green)';
        $('#case-won-desc').textContent = 'Все предметы из кейса уже есть';
    }

    result.classList.remove('hidden');
    result.classList.add('case-result-appear');
    okBtn.classList.remove('hidden');

    renderCases(); renderInventory(); renderCharacter(); updateHUD();
}

function buildRouletteStrip(caseId, winItem) {
    const cfg = S.casesCfg[caseId];
    if (!cfg) return [];
    const loot = cfg.loot || [];
    const totalWeight = loot.reduce((s, l) => s + l.weight, 0);
    const items = [];

    // Generate 60 random items for the strip
    for (let i = 0; i < 60; i++) {
        let rand = Math.random() * totalWeight, cum = 0;
        for (const l of loot) {
            cum += l.weight;
            if (rand <= cum) {
                const it = S.shopItems[l.item_id];
                if (it) items.push({ ...it, item_id: l.item_id });
                break;
            }
        }
    }

    // Place the winning item at index 40 (will land under pointer)
    if (winItem) {
        items[40] = { ...winItem };
    }
    return items;
}

function renderRouletteStrip(items) {
    const strip = $('#case-roulette-strip');
    strip.style.transition = 'none';
    strip.style.transform = 'translateX(0)';
    strip.innerHTML = items.map(it => {
        const r = it.rarity || 'common';
        const color = rarityColor(r);
        return `<div class="case-roulette-item" style="background:${color}15">
            <div style="position:absolute;bottom:0;left:0;right:0;height:3px;background:${color}"></div>
            <span class="ri-emoji">${it.emoji || '❓'}</span>
            <span class="ri-name" style="color:${color}">${it.name || '???'}</span>
        </div>`;
    }).join('');
    // Force reflow so browser registers initial position
    void strip.offsetWidth;
}

function animateRoulette(winIndex) {
    return new Promise(resolve => {
        const strip = $('#case-roulette-strip');
        const itemWidth = 90;
        const viewportWidth = strip.parentElement.offsetWidth;
        const targetX = (winIndex * itemWidth) - (viewportWidth / 2) + (itemWidth / 2);
        const offset = (Math.random() - 0.5) * (itemWidth * 0.4);
        const finalX = targetX + offset;

        // Force reflow before starting transition
        strip.style.transition = 'none';
        strip.style.transform = 'translateX(0)';
        void strip.offsetWidth;

        // Now start the animation
        requestAnimationFrame(() => {
            strip.style.transition = 'transform 4.5s cubic-bezier(0.15, 0.6, 0.15, 1)';
            strip.style.transform = `translateX(-${finalX}px)`;
        });

        setTimeout(resolve, 4700);
    });
}

async function openCaseAnim(pcId, caseId) {
    const overlay = $('#case-overlay');
    const roulette = $('#case-roulette');
    const result = $('#case-open-result');
    const okBtn = $('#case-ok-btn');

    result.classList.add('hidden');
    result.classList.remove('case-result-appear');
    okBtn.classList.add('hidden');
    roulette.classList.remove('hidden');
    overlay.classList.remove('hidden');

    // Build fake strip first to show spinning immediately
    const cfg = S.casesCfg[caseId];
    const fakeLoot = cfg?.loot || [];
    console.log('[CASE] caseId:', caseId, 'cfg:', cfg, 'loot:', fakeLoot.length, 'shopItems:', Object.keys(S.shopItems).length);

    // Build a temporary strip with random items while API loads
    const tempItems = [];
    const totalWeight = fakeLoot.reduce((s, l) => s + l.weight, 0);
    for (let i = 0; i < 60; i++) {
        let rand = Math.random() * totalWeight, cum = 0;
        for (const l of fakeLoot) {
            cum += l.weight;
            if (rand <= cum) {
                const it = S.shopItems[l.item_id];
                if (it) tempItems.push({ ...it, item_id: l.item_id });
                break;
            }
        }
    }
    console.log('[CASE] tempItems:', tempItems.length);

    renderRouletteStrip(tempItems);

    // Fire API call in parallel with animation start
    const apiPromise = api('/api/case/open', { telegram_id: S.player.telegram_id, player_case_id: pcId });

    // Wait a beat then start spinning
    await new Promise(r => setTimeout(r, 100));

    let apiResult;
    try {
        apiResult = await apiPromise;
    } catch(e) {
        closeCaseOverlay();
        showPopup('❌', 'Ошибка', '', e.detail || '', '');
        return;
    }

    S.player = apiResult.player;
    S.inventory = apiResult.inventory;
    S.playerCases = apiResult.player_cases;
    S.displayCash = apiResult.player.cash;

    // Build winning item for the strip
    let winItem;
    if (apiResult.won_item_id && apiResult.won_item) {
        winItem = apiResult.won_item;
    } else {
        winItem = { emoji: '💵', name: 'Компенсация', rarity: 'legendary' };
    }

    // Now rebuild strip with the real winner at position 40
    const stripItems = buildRouletteStrip(caseId, winItem);
    console.log('[CASE] stripItems:', stripItems.length, 'winItem:', winItem);
    renderRouletteStrip(stripItems);

    // Animate the roulette
    await animateRoulette(40);

    // Pause on winning item for a moment
    await new Promise(r => setTimeout(r, 800));

    // Show result
    roulette.classList.add('hidden');

    if (apiResult.won_item_id && apiResult.won_item) {
        const item = apiResult.won_item;
        const rr = item.rarity || 'common';
        $('#case-won-emoji').textContent = item.emoji;
        $('#case-won-name').textContent = item.name;
        $('#case-won-name').style.color = rarityColor(rr);
        $('#case-won-rarity').textContent = rarityName(rr);
        $('#case-won-rarity').style.color = rarityColor(rr);
        $('#case-won-desc').textContent = item.description || '';
    } else {
        $('#case-won-emoji').textContent = '💵';
        $('#case-won-name').textContent = 'Компенсация';
        $('#case-won-name').style.color = 'var(--gold)';
        $('#case-won-rarity').textContent = '+$' + fmt(apiResult.cash_compensation);
        $('#case-won-rarity').style.color = 'var(--green)';
        $('#case-won-desc').textContent = 'Все предметы из кейса уже есть';
    }

    result.classList.remove('hidden');
    result.classList.add('case-result-appear');
    okBtn.classList.remove('hidden');

    renderInventory(); renderCharacter(); updateHUD();
}

function closeCaseOverlay() {
    const overlay = $('#case-overlay');
    const roulette = $('#case-roulette');
    const result = $('#case-open-result');
    const okBtn = $('#case-ok-btn');
    overlay.classList.add('hidden');
    roulette.classList.add('hidden');
    result.classList.remove('case-result-appear');
    result.classList.add('hidden');
    okBtn.classList.add('hidden');
}

// ── Market Actions ──
function promptSell(itemId) {
    const item = S.shopItems[itemId];
    if (!item) return;
    const suggestedPrice = item.price > 0 ? Math.floor(item.price * 0.8) : 5000;
    const price = prompt(`Продать "${item.name}" на площадке.\nУкажи цену (мин. $100, комиссия 10%):`, suggestedPrice);
    if (!price) return;
    const p = parseFloat(price);
    if (isNaN(p) || p < 100) { showPopup('❌', 'Ошибка', 'Мин. цена $100', '', ''); return; }
    sellOnMarket(itemId, p);
}

async function sellOnMarket(itemId, price) {
    try {
        const r = await api('/api/market/sell', { telegram_id: S.player.telegram_id, item_id: itemId, price });
        S.inventory = r.inventory; S.myListings = r.my_listings;
        const item = S.shopItems[itemId];
        showPopup('🏪', 'Выставлено!', item.name, '$' + fmt(price), 'Комиссия 10% при продаже');
        renderInventory(); renderMyListings(); renderCharacter();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

async function buyFromMarket(listingId) {
    try {
        const r = await api('/api/market/buy', { telegram_id: S.player.telegram_id, listing_id: listingId });
        S.player = r.player; S.inventory = r.inventory; S.displayCash = r.player.cash;
        // Remove from local market listings
        S.marketListings = S.marketListings.filter(l => l.id !== listingId);
        const item = S.shopItems[r.bought_item_id];
        showPopup('🛍', 'Куплено!', item?.name || '', '', '');
        renderMarketListings(); renderInventory(); renderCharacter(); updateHUD();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

async function cancelListing(itemId, price) {
    try {
        const r = await api('/api/market/cancel', { telegram_id: S.player.telegram_id, item_id: itemId, price });
        S.inventory = r.inventory; S.myListings = r.my_listings;
        showPopup('↩️', 'Снято', 'Предмет возвращён', '', '');
        renderInventory(); renderMyListings();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

// ── Casino ──
function openCasinoGame(game) {
    $('#casino-menu').classList.add('hidden');
    $('#casino-game-view').classList.remove('hidden');
    document.querySelectorAll('.casino-game-inner').forEach(g => g.classList.add('hidden'));
    $(`#cg-${game}`).classList.remove('hidden');
}

function closeCasinoGame() {
    $('#casino-game-view').classList.add('hidden');
    $('#casino-menu').classList.remove('hidden');
}

function addBet(game, val) {
    const el = $(`#bet-${game}`);
    let current = parseFloat(el.value) || 0;
    el.value = current + val;
}

function setBetAll(game) {
    const max = Math.floor(S.displayCash);
    $(`#bet-${game}`).value = max > 0 ? max : 10;
}

async function playCasino(game, choice) {
    const betEl = $(`#bet-${game}`);
    const bet = parseFloat(betEl.value);
    if (!bet || bet <= 0) return;
    try {
        const r = await api('/api/casino', { telegram_id: S.player.telegram_id, game, bet, choice });
        S.player = r.player; S.displayCash = r.player.cash;
        const res = r.result;

        if (game === 'slots') {
            const display = $('#slot-display');
            display.classList.add('spinning');
            setTimeout(() => {
                display.classList.remove('spinning');
                display.textContent = res.reels.join(' ');
                if (r.payout > 0) showPopup('🎰', 'Джекпот!', res.reels.join(' '), '+$' + fmt(r.payout), '');
                else showPopup('🎰', 'Не повезло', res.reels.join(' '), '-$' + fmt(bet), '');
            }, 800);
            return;
        }
        if (game === 'coinflip') {
            const coin = $('#coinflip-anim');
            coin.classList.add('flip');
            setTimeout(() => {
                coin.textContent = res.flip === 'heads' ? '👑' : '🔢';
                coin.classList.remove('flip');
            }, 600);
            const flipText = res.flip === 'heads' ? '👑 Орёл' : '🔢 Решка';
            setTimeout(() => {
                if (res.win) showPopup('🪙', 'Выигрыш!', flipText, '+$' + fmt(r.payout), '');
                else showPopup('🪙', 'Проигрыш', flipText, '-$' + fmt(bet), '');
            }, 700);
        }
        if (game === 'dice') {
            const diceNums = ['', '⚀','⚁','⚂','⚃','⚄','⚅'];
            $('#dice-display').textContent = (diceNums[res.dice1]||'🎲') + '  ' + (diceNums[res.dice2]||'🎲');
            $('#dice-total').textContent = `Сумма: ${res.total}`;
            const diceText = `${res.dice1} + ${res.dice2} = ${res.total}`;
            if (res.win) showPopup('🎲', 'Выигрыш!', diceText, '+$' + fmt(r.payout), '');
            else showPopup('🎲', 'Проигрыш', diceText, '-$' + fmt(bet), '');
        }
        if (game === 'roulette') {
            const wheel = $('#roulette-display');
            wheel.classList.add('spin');
            setTimeout(() => wheel.classList.remove('spin'), 1000);
            const color = res.color === 'red' ? '🔴' : res.color === 'black' ? '⚫' : '🟢';
            const rt = `${color} ${res.number}`;
            setTimeout(() => {
                $('#roulette-result').textContent = rt;
                if (res.win) showPopup('🎡', 'Выигрыш!', rt, '+$' + fmt(r.payout), '');
                else showPopup('🎡', 'Проигрыш', rt, '-$' + fmt(bet), '');
            }, 500);
        }
        updateHUD();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || 'Нет денег', ''); }
}

function adjBet(game, amount) {
    const el = $(`#bet-${game}`);
    let v = parseFloat(el.value) + amount;
    if (v < 10) v = 10;
    el.value = v;
}

// ── Gang ──
async function createGang() {
    const name = $('#gang-name-input').value.trim();
    const tag = $('#gang-tag-input').value.trim();
    if (!name || !tag) return;
    try {
        const r = await api('/api/gang/create', { telegram_id: S.player.telegram_id, name, tag });
        S.player = r.player; S.displayCash = r.player.cash;
        showPopup('👥', 'Банда создана!', r.gang_name, '', '');
        renderAll();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

async function loadGangs() {
    try {
        const r = await fetch(API + '/api/gangs').then(r => r.json());
        const el = $('#gangs-list'); el.innerHTML = '';
        if (!r.gangs.length) { el.innerHTML = '<p style="color:var(--text2);font-size:.8rem">Банд пока нет</p>'; return; }
        for (const g of r.gangs) {
            el.innerHTML += `<div class="gang-card">
                <div><strong>[${g.tag}] ${g.name}</strong><br><small>${g.members || 1} чел.</small></div>
                <button class="btn-buy" onclick="joinGang(${g.id})">Вступить</button></div>`;
        }
    } catch(e) {}
}

async function joinGang(id) {
    try {
        const r = await api('/api/gang/join', { telegram_id: S.player.telegram_id, gang_id: id });
        S.player = r.player;
        showPopup('👥', 'Ты в банде!', '', '', '');
        renderAll();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

// ── PvP ──
async function loadPvpTargets() {
    try {
        const r = await fetch(API + '/api/pvp/targets/' + S.player.telegram_id).then(r => r.json());
        const el = $('#pvp-targets'); el.innerHTML = '';
        if (!r.targets.length) { el.innerHTML = '<p style="color:var(--text2);font-size:.8rem">Нет целей</p>'; return; }
        for (const t of r.targets) {
            el.innerHTML += `<div class="pvp-target">
                <div class="pvp-target-info"><strong>${t.username||'Игрок'}</strong><br>
                <small>😈${t.reputation_fear} 🤝${t.reputation_respect}</small></div>
                <button class="btn-attack" onclick="pvpAttack(${t.telegram_id})">⚔️ Напасть</button></div>`;
        }
    } catch(e) {}
}

async function pvpAttack(targetId) {
    try {
        const r = await api('/api/pvp/attack', { telegram_id: S.player.telegram_id, target_id: targetId });
        S.player = r.player; S.displayCash = r.player.cash;
        if (r.win) showPopup('⚔️', 'Победа!', `Сила: ${r.your_power} vs ${r.their_power}`, '+$' + fmt(r.cash_stolen), '');
        else showPopup('💀', 'Поражение', `Сила: ${r.your_power} vs ${r.their_power}`, '-$' + fmt(r.cash_stolen), '');
        updateHUD();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

// ── Mission Claim ──
async function claimMission(missionId) {
    try {
        const r = await api('/api/mission/claim', { telegram_id: S.player.telegram_id, mission_id: missionId });
        S.player = r.player; S.dailyMissions = r.daily_missions; S.displayCash = r.player.cash;
        showPopup('📋', 'Миссия выполнена!', '', '+$' + fmt(r.player.cash - S.displayCash + r.player.cash), '');
        renderMissions(); updateHUD();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

// ── Login Reward ──
function showLoginOverlay() {
    const overlay = $('#login-overlay');
    const daysEl = $('#login-days');
    if (!overlay || !daysEl || !S.loginData) return;

    const rewardDay = S.loginData.reward_day || 1;
    let html = '';
    for (let i = 0; i < S.loginRewards.length; i++) {
        const reward = S.loginRewards[i];
        const dayNum = i + 1;
        const isCurrent = dayNum === rewardDay;
        const isPast = dayNum < rewardDay;
        html += `<div class="login-day ${isCurrent ? 'login-day-current' : ''} ${isPast ? 'login-day-past' : ''}">
            <div class="login-day-num">День ${dayNum}</div>
            <div class="login-day-reward">${reward.label}</div>
        </div>`;
    }
    daysEl.innerHTML = html;
    overlay.classList.remove('hidden');
}

async function claimLoginReward() {
    try {
        const r = await api('/api/login/claim', { telegram_id: S.player.telegram_id });
        S.player = r.player; S.displayCash = r.player.cash;
        S.loginData = r.login_data;
        S.playerCases = r.player_cases || S.playerCases;
        $('#login-overlay').classList.add('hidden');
        showPopup('🎁', 'Бонус получен!', `День ${r.reward_day}`, r.reward_text, `Серия: ${r.streak} дней`);
        renderAll();
    } catch(e) {
        $('#login-overlay').classList.add('hidden');
        showPopup('❌', 'Ошибка', '', e.detail || '', '');
    }
}

// ── Prestige Action ──
async function doPrestige() {
    if (!confirm('Ты уверен? Престиж сбросит бизнесы, деньги и репутацию. Предметы и банда сохранятся.')) return;
    try {
        const r = await api('/api/prestige', { telegram_id: S.player.telegram_id });
        S.player = r.player; S.businesses = r.businesses; S.displayCash = r.player.cash;
        S.incomePerSec = r.income_per_sec; S.suspicionPerSec = r.suspicion_per_sec;
        S.playerLevel = r.player_level;
        showPopup('⚡', 'Престиж!', `Уровень ${r.prestige_level}`, `Множитель: x${r.prestige_multiplier.toFixed(2)}`, 'Бизнесы сброшены');
        renderAll();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

// ── Territory Attack ──
async function attackTerritory(territoryId) {
    try {
        const r = await api('/api/territory/attack', { telegram_id: S.player.telegram_id, territory_id: territoryId });
        S.territories = r.territories;
        if (r.win) showPopup('🗺', 'Победа!', r.territory_name + ' захвачена!', `Сила: ${r.attacker_power} vs ${r.defender_power}`, '');
        else showPopup('🛡', 'Отбито!', r.territory_name, `Сила: ${r.attacker_power} vs ${r.defender_power}`, '');
        renderTerritories();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

// ── Achievement Claim ──
async function claimAchievement(achievementId) {
    try {
        const r = await api('/api/achievement/claim', { telegram_id: S.player.telegram_id, achievement_id: achievementId });
        S.player = r.player; S.achievements = r.achievements; S.displayCash = r.player.cash;
        const ach = S.achievementsCfg.find(a => a.id === achievementId);
        showPopup('🏆', 'Достижение!', ach?.name || '', '+$' + fmt(ach?.reward || 0), '');
        renderAchievements(); updateHUD();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

// ── Tabs ──
function switchTab(name) {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    $(`.nav-btn[data-tab="${name}"]`).classList.add('active');
    $(`#tab-${name}`).classList.add('active');
}

function switchSubTab(type, btn) {
    const parent = btn.closest('.tab-content');
    parent.querySelectorAll('.sub-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    // Business sub-tabs
    if (parent.id === 'tab-business') {
        $('#legal-list').classList.toggle('hidden', type !== 'legal');
        $('#shadow-list').classList.toggle('hidden', type !== 'shadow');
        $('#upgrades-sub-list').classList.toggle('hidden', type !== 'upgrades-sub');
    }
}

function switchShopSection(section, btn) {
    // Update sub-tab buttons
    btn.closest('.sub-tabs').querySelectorAll('.sub-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    // Toggle sections
    $('#shop-items-section').classList.toggle('hidden', section !== 'items');
    $('#shop-cases-section').classList.toggle('hidden', section !== 'cases');
    $('#shop-market-section').classList.toggle('hidden', section !== 'market');
    $('#shop-vip-section').classList.toggle('hidden', section !== 'vip');
    if (section === 'vip') renderVipShop();
}

function switchShopTab(slot, btn) {
    document.querySelectorAll('.shop-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    S.currentShopTab = slot;
    renderShop();
}

// New sub-tab switchers
function switchDelaSubTab(section, btn) {
    btn.closest('.sub-tabs').querySelectorAll('.sub-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    $('#dela-robberies').classList.toggle('hidden', section !== 'robberies');
    $('#dela-missions').classList.toggle('hidden', section !== 'missions');
}

function switchCharSubTab(section, btn) {
    btn.closest('.sub-tabs').querySelectorAll('.sub-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    $('#char-main').classList.toggle('hidden', section !== 'char-main');
    $('#char-achievements').classList.toggle('hidden', section !== 'char-achievements');
}

function switchGangSubTab(section, btn) {
    btn.closest('.sub-tabs').querySelectorAll('.sub-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    $('#gang-main').classList.toggle('hidden', section !== 'gang-main');
    $('#gang-territories').classList.toggle('hidden', section !== 'gang-territories');
    $('#gang-pvp').classList.toggle('hidden', section !== 'gang-pvp');
    $('#gang-leaderboard').classList.toggle('hidden', section !== 'gang-leaderboard');
    if (section === 'gang-leaderboard') loadLeaderboard();
}

// ── Popup ──
function showPopup(icon, title, body, amount, sub) {
    $('#popup-icon').textContent = icon;
    $('#popup-title').textContent = title;
    $('#popup-body').textContent = body;
    $('#popup-amount').textContent = amount;
    $('#popup-amount').className = 'popup-amount' + (amount.startsWith?.('-') ? ' fail' : '');
    $('#popup-sub').textContent = sub;
    $('#popup-sub').classList.toggle('hidden', !sub);
    $('#popup-overlay').classList.remove('hidden');
}
function closePopup() { $('#popup-overlay').classList.add('hidden'); }

// ── Misc helpers ──
function startCd(id, sec) {
    let r = sec;
    const iv = setInterval(() => {
        r-=1; if(r<=0){clearInterval(iv);renderRobberies();return;}
        const el = $(`#cd-${id}`); if(el) el.textContent='⏳ '+fmtTime(r);
    }, 1000);
}
function hideLoading() {
    $('#loading-screen').classList.add('fade-out');
    $('#game').classList.remove('hidden');
    setTimeout(()=>$('#loading-screen').style.display='none',500);
}

// ── VIP Badges ──
function updateVipBadges() {
    const charBadge = $('#char-vip-badge');
    if (charBadge) charBadge.classList.toggle('hidden', !S.vipStatus.active);
}

// ── Ad Buttons Visibility ──
function updateAdButtons() {
    const isVip = S.vipStatus.active;
    const btns = ['#ad-btn-business', '#ad-btn-casino', '#ad-btn-robbery'];
    btns.forEach(sel => {
        const el = $(sel);
        if (el) el.classList.toggle('hidden', isVip);
    });
}

// ── Watch Ad (Adsgram) ──
async function watchAd(rewardType) {
    if (!AdController) {
        // Fallback: call API directly (for testing without Adsgram)
        claimAdReward(rewardType);
        return;
    }
    try {
        await AdController.show();
        // Ad watched successfully — claim reward
        claimAdReward(rewardType);
    } catch(e) {
        // User closed ad or ad failed
        console.log('Ad not completed', e);
    }
}

async function claimAdReward(rewardType) {
    try {
        const r = await api('/api/ad/reward', { telegram_id: S.player.telegram_id, reward_type: rewardType });
        S.player = r.player;
        S.displayCash = r.player.cash;
        if (rewardType === 'income_boost') {
            S.adBoostUntil = Date.now() / 1000 + 300;
        }
        showPopup('📺', 'Бонус!', '', r.reward.message, '');
        renderAll();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || 'Подожди перед следующей рекламой', ''); }
}

// ── VIP Shop Render ──
function renderVipShop() {
    const el = $('#vip-shop-content');
    if (!el) return;

    const vip = S.vipStatus;
    let html = '';

    // VIP Status Section
    html += `<div class="vip-status-card ${vip.active ? 'vip-active' : ''}">
        <div class="vip-status-header">
            <span class="vip-status-icon">${vip.active ? '👑' : '🔒'}</span>
            <div class="vip-status-info">
                <div class="vip-status-title">${vip.active ? 'VIP активен' : 'VIP не активен'}</div>
                ${vip.active ? `<div class="vip-status-days">Осталось: ${vip.days_left} дн.</div>` : ''}
            </div>
        </div>
        <div class="vip-benefits">
            <div class="vip-benefit">x2 к доходу</div>
            <div class="vip-benefit">Офлайн-кап 8ч</div>
            <div class="vip-benefit">Бесплатный кейс/день</div>
            <div class="vip-benefit">Комиссия 5%</div>
            <div class="vip-benefit">Без рекламы</div>
            <div class="vip-benefit">VIP-предметы</div>
        </div>
    </div>`;

    // VIP Daily Case
    if (vip.active) {
        const claimed = S.player.last_vip_case_claim === new Date().toISOString().split('T')[0];
        html += `<div class="vip-daily-case">
            <button class="btn-vip-daily ${claimed ? 'disabled' : ''}" onclick="claimVipDailyCase()" ${claimed ? 'disabled' : ''}>
                🎁 ${claimed ? 'Кейс получен сегодня' : 'Забрать бесплатный премиум кейс'}
            </button>
        </div>`;
    }

    // VIP Purchase
    html += '<h3 class="vip-section-title">👑 VIP-статус</h3><div class="vip-packages">';
    for (const [id, pkg] of Object.entries(S.vipPackages)) {
        const tonPrice = S.tonPrices[id];
        html += `<div class="vip-package-card">
            <div class="vip-package-info">
                <div class="vip-package-name">${pkg.label}</div>
                <div class="vip-package-stars">⭐ ${pkg.stars} Stars</div>
            </div>
            <div class="vip-package-actions">
                <button class="btn-stars" onclick="buyWithStars('${id}')">⭐ ${pkg.stars}</button>
                ${tonPrice ? `<button class="btn-ton" onclick="buyWithTon('${id}')">💎 ${tonPrice} TON</button>` : ''}
            </div>
        </div>`;
    }
    html += '</div>';

    // Cash Packages
    html += '<h3 class="vip-section-title">💰 Пакеты кэша</h3><div class="vip-packages">';
    for (const [id, pkg] of Object.entries(S.cashPackages)) {
        const tonPrice = S.tonPrices[id];
        html += `<div class="vip-package-card">
            <div class="vip-package-info">
                <div class="vip-package-name">${pkg.label}</div>
                <div class="vip-package-stars">⭐ ${pkg.stars} Stars</div>
            </div>
            <div class="vip-package-actions">
                <button class="btn-stars" onclick="buyWithStars('${id}')">⭐ ${pkg.stars}</button>
                ${tonPrice ? `<button class="btn-ton" onclick="buyWithTon('${id}')">💎 ${tonPrice} TON</button>` : ''}
            </div>
        </div>`;
    }
    html += '</div>';

    // Case Packages
    html += '<h3 class="vip-section-title">📦 Пакеты кейсов</h3><div class="vip-packages">';
    for (const [id, pkg] of Object.entries(S.casePackages)) {
        const tonPrice = S.tonPrices[id];
        html += `<div class="vip-package-card">
            <div class="vip-package-info">
                <div class="vip-package-name">${pkg.label}</div>
                <div class="vip-package-stars">⭐ ${pkg.stars} Stars</div>
            </div>
            <div class="vip-package-actions">
                <button class="btn-stars" onclick="buyWithStars('${id}')">⭐ ${pkg.stars}</button>
                ${tonPrice ? `<button class="btn-ton" onclick="buyWithTon('${id}')">💎 ${tonPrice} TON</button>` : ''}
            </div>
        </div>`;
    }
    html += '</div>';

    // VIP Items
    if (Object.keys(S.vipItems).length > 0) {
        html += '<h3 class="vip-section-title">👑 VIP-предметы</h3><div class="vip-items-list">';
        for (const [id, item] of Object.entries(S.vipItems)) {
            const owned = S.inventory.some(i => i.item_id === id);
            const bonus = itemBonusText(item);
            html += `<div class="vip-item-card" style="border-left:3px solid ${rarityColor(item.rarity)}">
                <div class="vip-item-left">
                    <span class="vip-item-emoji">${item.emoji}</span>
                    <div class="vip-item-info">
                        <div class="vip-item-name" style="color:${rarityColor(item.rarity)}">${item.name}</div>
                        <div class="vip-item-desc">${item.description}</div>
                        ${bonus ? `<div class="vip-item-bonus">${bonus}</div>` : ''}
                    </div>
                </div>
                <div class="vip-item-action">
                    ${owned ? '<span class="vip-item-owned">Получено</span>'
                    : vip.active ? `<button class="btn-vip-claim" onclick="claimVipItem('${id}')">Забрать</button>`
                    : '<span class="vip-item-locked">Нужен VIP</span>'}
                </div>
            </div>`;
        }
        html += '</div>';
    }

    el.innerHTML = html;
}

// ── Buy with Stars ──
async function buyWithStars(packageId) {
    try {
        const r = await api('/api/stars/invoice', { telegram_id: S.player.telegram_id, package_id: packageId });
        if (r.invoice_link && tg) {
            tg.openInvoice(r.invoice_link, (status) => {
                if (status === 'paid') {
                    showPopup('⭐', 'Оплачено!', '', 'Покупка активирована', '');
                    setTimeout(() => location.reload(), 1500);
                }
            });
        } else if (r.invoice_link) {
            window.open(r.invoice_link, '_blank');
        }
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || 'Не удалось создать счёт', ''); }
}

// ── Buy with TON ──
async function buyWithTon(packageId) {
    try {
        const r = await api('/api/ton/create', { telegram_id: S.player.telegram_id, package_id: packageId });
        if (!tonConnectUI) {
            // Fallback: show address for manual transfer
            showPopup('💎', 'Оплата TON', `Отправьте ${r.amount_ton} TON`, `Адрес: ${r.address}`, `Комментарий: ${r.comment}`);
            return;
        }

        // Check if wallet connected
        const connected = tonConnectUI.connected;
        if (!connected) {
            await tonConnectUI.connectWallet();
        }

        const tx = {
            validUntil: Math.floor(Date.now() / 1000) + 600,
            messages: [{
                address: r.address,
                amount: String(r.amount_nano),
                payload: r.comment,
            }],
        };
        const result = await tonConnectUI.sendTransaction(tx);
        showPopup('💎', 'Транзакция отправлена!', '', 'Покупка будет активирована после подтверждения', '');
        // Verify after delay
        setTimeout(async () => {
            try {
                await api('/api/ton/verify', { telegram_id: S.player.telegram_id, tx_hash: result.boc || 'manual' });
            } catch(e) {}
            setTimeout(() => location.reload(), 3000);
        }, 5000);

    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || 'TON оплата не удалась', ''); }
}

// ── VIP Daily Case ──
async function claimVipDailyCase() {
    try {
        const r = await api('/api/vip/daily-case', { telegram_id: S.player.telegram_id });
        S.player = r.player; S.playerCases = r.player_cases;
        showPopup('🎁', 'Кейс получен!', '', r.message, '');
        renderAll();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

// ── VIP Item Claim ──
async function claimVipItem(itemId) {
    try {
        const r = await api('/api/vip/claim-item', { telegram_id: S.player.telegram_id, item_id: itemId });
        S.player = r.player; S.inventory = r.inventory;
        showPopup('👑', 'VIP-предмет получен!', r.item?.name || '', '', '');
        renderAll();
    } catch(e) { showPopup('❌', 'Ошибка', '', e.detail || '', ''); }
}

document.addEventListener('DOMContentLoaded', init);
