/* logic.js - Strategic Mind & Pipeline v4.7 (Layout & Perf Fix) */

const PM = {
    notes: [],
    links: [],
    selectedId: null,
    mapPos: { x: 0, y: 0, s: 1 },
    visPos: { x: 0, y: 0, s: 1 },
    currentMode: 'map',
    today: new Date(2026, 0, 14),
    ganttOffsetDays: 7,
    linkingFrom: null,
    dayWidth: 41,
    showGoalsInGantt: false, // v5.3: Default hidden
    icons: ['📝', '📅', '🚀', '🎉', '💦', '⚠️', '💤', '🏠', '💰', '🛒', '🪵', '📐', '✨', '⚔️'],
    productionEvents: [],

    init() {
        try {
            this.today.setHours(0, 0, 0, 0);
            this.initGanttHeader();
            this.setupEvents();
            this.setupKeyboardEvents();
            this.render();
        } catch (e) {
            console.error("Init Error:", e);
            alert("初期化中にエラーが発生しました。");
        }
    },

    formatDate(d) {
        return `${d.getFullYear()}-${('0' + (d.getMonth() + 1)).slice(-2)}-${('0' + d.getDate()).slice(-2)}`;
    },
    getSafeDate(str) {
        if (!str) return new Date(this.today);
        const p = str.split('-');
        return new Date(p[0], p[1] - 1, p[2]);
    },
    getDayDiff(d1, d2) {
        const dt1 = d1 instanceof Date ? d1 : this.getSafeDate(d1);
        const dt2 = d2 instanceof Date ? d2 : this.getSafeDate(d2);
        dt1.setHours(0, 0, 0, 0); dt2.setHours(0, 0, 0, 0);
        return Math.round((dt1 - dt2) / 86400000);
    },

    setMode(mode) {
        this.currentMode = mode;
        document.querySelectorAll('.view-layer').forEach(el => el.classList.remove('active-view'));
        if (mode === 'goals') document.getElementById('view-goals').classList.add('active-view');
        else if (mode === 'cal') {
            document.getElementById('view-calendar').classList.add('active-view');
            this.renderCalendar();
        } else document.getElementById('view-main').classList.add('active-view');

        if (document.getElementById('btn-map')) {
            document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
            if (mode === 'map') document.getElementById('btn-map').classList.add('active');
        }
        this.updateTransform();
        this.render();
    },

    render() {
        document.querySelectorAll('.sticky-note').forEach(n => n.remove());

        this.notes.forEach(n => {
            if (n.isGoal) {
                const elV = this.createNoteDOM(n, 'vision-canvas');
                document.getElementById('vision-canvas').appendChild(elV);
                const elM = this.createNoteDOM(n, 'map-canvas');
                document.getElementById('map-canvas').appendChild(elM);
            } else {
                const el = this.createNoteDOM(n, 'map-canvas');
                document.getElementById('map-canvas').appendChild(el);
            }
        });
        this.drawLines();
        this.renderGantt();
    },

    createNoteDOM(n, parentId) {
        const el = document.createElement('div');

        // v5.7: Bottleneck Priority Fix
        let typeClass = '';
        if (n.type === 'bottleneck') {
            typeClass = 'bottleneck';
        } else if (n.isGoal) {
            typeClass = 'goal-node';
        }

        el.className = `sticky-note color-${n.member} ${this.selectedId === n.id ? 'selected' : ''} ${typeClass} ${n.complete ? 'completed' : ''}`;
        if (n.isGoal) el.classList.add(n.timeframe);

        el.style.left = n.x + 'px'; el.style.top = n.y + 'px';
        el.id = `note-${n.id}-${parentId}`;

        const iconOptions = this.icons.map(icon => `<option value="${icon}" ${n.icon === icon ? 'selected' : ''}>${icon}</option>`).join('');

        const inputHtml = n.isGoal ?
            `<div class="note-header"><select class="icon-select" onchange="PM.updateNote('${n.id}','icon',this.value)">${iconOptions}</select><textarea class="note-title" style="height:100px; resize:none;" oninput="PM.updateNote('${n.id}','title',this.value)" onfocus="PM.select('${n.id}')">${n.title}</textarea></div>` :
            `<div class="note-header"><select class="icon-select" onchange="PM.updateNote('${n.id}','icon',this.value)">${iconOptions}</select><input type="text" class="note-title" value="${n.title}" oninput="PM.updateNote('${n.id}','title',this.value)" onfocus="PM.select('${n.id}')"></div>`;

        // v5.4: Completion Check Button
        const checkBtn = `<button class="btn-check" onclick="PM.toggleComplete('${n.id}', event)">${n.complete ? '✅' : '⬜'}</button>`;

        el.innerHTML = `
            <div class="link-handle" onmousedown="PM.startLink(event, '${n.id}')">＋</div>
            ${checkBtn}
            ${inputHtml}
            <div class="note-meta">
                <select onchange="PM.updateNote('${n.id}','member',this.value)">
                    <option value="p" ${n.member === 'p' ? 'selected' : ''}>パパ</option>
                    <option value="m" ${n.member === 'm' ? 'selected' : ''}>ママ</option>
                    <option value="a" ${n.member === 'a' ? 'selected' : ''}>子A</option>
                    <option value="b" ${n.member === 'b' ? 'selected' : ''}>子B</option>
                </select>
            </div>
            <div class="note-meta">
                <input type="date" value="${n.start}" onchange="PM.updateNote('${n.id}','start',this.value)">
                <input type="date" value="${n.end}" onchange="PM.updateNote('${n.id}','end',this.value)">
            </div>
            ${n.isGoal ? `<div class="note-meta"><select onchange="PM.updateNote('${n.id}','timeframe',this.value)">
                <option value="year" ${n.timeframe === 'year' ? 'selected' : ''}>🏆 1年</option>
                <option value="month" ${n.timeframe === 'month' ? 'selected' : ''}>🎯 1ヶ月</option>
                <option value="week" ${n.timeframe === 'week' ? 'selected' : ''}>🗓️ 1週間</option>
            </select></div>` : ''}
            <textarea class="note-memo" placeholder="Memo..." oninput="PM.updateNote('${n.id}', 'memo', this.value)">${n.memo || ''}</textarea>
        `;

        el.onmousedown = (e) => {
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName) || e.target.className === 'link-handle') return;
            this.selectedId = n.id;
            e.stopPropagation();

            const isVis = parentId === 'vision-canvas';
            const s = isVis ? this.visPos.s : this.mapPos.s;
            let startX = e.clientX; let startY = e.clientY;
            let origX = n.x; let origY = n.y;

            const move = (me) => {
                n.x = origX + (me.clientX - startX) / s;
                n.y = origY + (me.clientY - startY) / s;
                document.querySelectorAll(`[id^='note-${n.id}-']`).forEach(dom => {
                    dom.style.left = n.x + 'px'; dom.style.top = n.y + 'px';
                });
                this.drawLines();
            };
            document.addEventListener('mousemove', move);
            document.addEventListener('mouseup', () => document.removeEventListener('mousemove', move), { once: true });
        };
        return el;
    },

    updateNote(id, key, val) {
        const n = this.notes.find(x => x.id == id);
        if (n) {
            n[key] = val;
            if (key !== 'title') { this.render(); if (this.currentMode === 'cal') this.renderCalendar(); }
        }
    },

    toggleComplete(id, e) {
        if (e) e.stopPropagation();
        const n = this.notes.find(x => x.id == id);
        if (n) {
            n.complete = !n.complete;
            if (n.complete && e) this.triggerConfetti(e.clientX, e.clientY);
            this.render();
            if (this.currentMode === 'cal') this.renderCalendar();
        }
    },

    triggerConfetti(x, y) {
        const colors = ['🎉', '✨', '🎊', '⭐', '🌈'];
        for (let i = 0; i < 12; i++) { // 増量
            const el = document.createElement('div');
            el.innerText = colors[Math.floor(Math.random() * colors.length)];
            el.style.position = 'fixed';
            el.style.left = x + 'px';
            el.style.top = y + 'px';
            el.style.fontSize = (30 + Math.random() * 20) + 'px'; // 巨大化
            el.style.pointerEvents = 'none';
            el.style.zIndex = '9999';
            el.style.transition = 'all 1.2s ease-out';
            document.body.appendChild(el);

            setTimeout(() => {
                const dx = (Math.random() - 0.5) * 400; // 拡散範囲拡大
                const dy = (Math.random() - 0.5) * 400 - 100; // 上方向へも
                el.style.transform = `translate(${dx}px, ${dy}px) scale(0)`;
                el.style.opacity = '0';
            }, 50);

            setTimeout(() => el.remove(), 1200);
        }
    },

    changeZoom(delta) {
        this.dayWidth = Math.max(20, Math.min(100, this.dayWidth + delta));
        this.renderGantt();
    },

    toggleGanttGoals() {
        this.showGoalsInGantt = !this.showGoalsInGantt;
        this.renderGantt();
        // alert削除 (Silent)
    },

    alignNotes() {
        // v6.4 Horizontal Zone Layout
        // 1. ノード分類
        const goals = this.notes.filter(n => n.isGoal && n.type !== 'bottleneck');
        const bottlenecks = this.notes.filter(n => n.type === 'bottleneck');

        // カテゴリ分け (Workshop vs Others)
        const workshopOps = this.notes.filter(n => !n.isGoal && n.type !== 'bottleneck' && n.category === 'workshop')
            .sort((a, b) => this.getDayDiff(a.start, b.start));

        const boothOps = this.notes.filter(n => !n.isGoal && n.type !== 'bottleneck' && n.category !== 'workshop')
            .sort((a, b) => this.getDayDiff(a.start, b.start));

        // 2. 配置ヘルパー (指定座標からタイル状に並べる)
        // param: cols (列数), xStep (横幅+マージン), yStep (縦幅+マージン)
        // return: エリアの高さ
        const layoutZone = (list, startX, startY, cols, xStep, yStep) => {
            if (list.length === 0) return 0;
            list.forEach((n, i) => {
                n.x = startX + (i % cols) * xStep;
                n.y = startY + Math.floor(i / cols) * yStep;
            });
            return Math.ceil(list.length / cols) * yStep;
        };

        // 3. 配置実行
        let currentY = 50;

        // --- 上段: ビジョン (横並び) ---
        // Goalsは大きいので xStep=360, yStep=240, 3列
        const visionH = layoutZone(goals, 100, currentY, 3, 360, 240);
        currentY += visionH + (visionH > 0 ? 50 : 0);

        // --- ボトルネック (横並び) ---
        // 通常サイズ xStep=220, yStep=180, 4列
        const botH = layoutZone(bottlenecks, 100, currentY, 4, 220, 180);
        currentY += botH + (botH > 0 ? 80 : 0); // 少し広めにスペース空ける

        // --- 下段: タスクエリア (左右分離) ---
        // [左] 作業場 (Workshop) - 2列
        layoutZone(workshopOps, 50, currentY, 2, 220, 160);

        // [右] ブース (Booth) - 2列
        layoutZone(boothOps, 600, currentY, 2, 220, 160);

        this.render();
        console.log("v6.4: Horizontal Zone Layout Applied.");
    },

    select(id) { this.selectedId = id; },

    syncGoalFromCalendar(type, text, date) {
        let target = null;
        if (type === 'week') {
            const dStr = this.formatDate(date);
            target = this.notes.find(n => n.isGoal && n.timeframe === 'week' && n.start === dStr);
        } else {
            target = this.notes.find(n => n.isGoal && n.timeframe === type);
        }

        if (target) {
            target.title = text;
        } else if (text.trim() !== "") {
            const id = Date.now();
            let start = this.formatDate(this.today);
            let end = start;

            if (type === 'week') {
                start = this.formatDate(date);
                const e = new Date(date); e.setDate(date.getDate() + 6);
                end = this.formatDate(e);
            } else if (type === 'year') {
                const e = new Date(this.today); e.setFullYear(e.getFullYear() + 1);
                end = this.formatDate(e);
            } else if (type === 'month') {
                const e = new Date(this.today); e.setMonth(e.getMonth() + 1);
                end = this.formatDate(e);
            }

            this.notes.push({
                id: id,
                x: 100 + (this.notes.length * 20),
                y: 100 + (this.notes.length * 20),
                title: text,
                start: start, end: end,
                member: "p",
                isGoal: true,
                timeframe: type,
                icon: type === 'year' ? '🏆' : (type === 'month' ? '🎯' : '🗓️')
            });
        }
    },

    renderGantt() {
        this.initGanttHeader();
        const target = document.getElementById('gantt-target');
        target.innerHTML = '';
        const dayWidth = this.dayWidth;

        // v5.5: Filter goals AND bottlenecks
        const sorted = this.notes.filter(n => {
            const visible = n.start && (this.showGoalsInGantt || (!n.isGoal && n.type !== 'bottleneck'));
            return visible;
        }).sort((a, b) => {
            // v5.8: Sort by Category (Booth > Workshop) then Date
            const catA = a.category || 'booth';
            const catB = b.category || 'booth';
            if (catA !== catB) return catA === 'workshop' ? 1 : -1; // Boothが上、Workshopが下
            return this.getDayDiff(a.start, b.start);
        });

        sorted.forEach(n => {
            const row = document.createElement('div'); row.className = 'gantt-row';
            row.innerHTML = `<div class="gantt-label">${n.icon || '📝'} ${n.title}</div>`;

            const diff = this.getDayDiff(n.start, this.today);
            const dur = Math.max(1, this.getDayDiff(n.end || n.start, n.start) + 1);

            const bar = document.createElement('div');
            bar.className = `gantt-bar color-${n.member} ${n.complete ? 'completed' : ''}`;
            bar.style.left = (180 + (diff + this.ganttOffsetDays) * dayWidth) + 'px';
            bar.style.width = (dur * dayWidth) + 'px';
            bar.innerHTML = `<span>${n.icon || ''}</span>`;
            bar.title = n.memo || '';
            bar.dataset.id = n.id;

            // ★修正: render()を使わない高速化ロジック
            bar.onmousedown = (e) => {
                // v5.5: Ctrl + Click to Complete
                if (e.ctrlKey) {
                    e.preventDefault();
                    this.toggleComplete(n.id, e);
                    return;
                }

                if (e.target.className === 'gantt-link-point') return;
                e.stopPropagation();
                const isResize = e.target.className === 'gantt-resizer';
                const startX = e.clientX;
                const origS = this.getSafeDate(n.start);
                const origE = this.getSafeDate(n.end || n.start);

                const move = (me) => {
                    const delta = Math.round((me.clientX - startX) / dayWidth);

                    if (isResize) {
                        const currentDur = Math.max(1, this.getDayDiff(origE, origS) + 1 + delta);
                        // DOM直接操作
                        bar.style.width = (currentDur * dayWidth) + 'px';

                        // データ更新のみ (renderしない)
                        const newE = new Date(origS); newE.setDate(origS.getDate() + currentDur - 1);
                        n.end = this.formatDate(newE);
                    } else {
                        // DOM直接操作
                        const newDiff = this.getDayDiff(origS, this.today) + delta;
                        bar.style.left = (180 + (newDiff + this.ganttOffsetDays) * dayWidth) + 'px';

                        // データ更新のみ (renderしない)
                        const newS = new Date(origS); newS.setDate(origS.getDate() + delta);
                        const newE = new Date(origE); newE.setDate(origE.getDate() + delta);
                        n.start = this.formatDate(newS); n.end = this.formatDate(newE);
                    }
                };

                // 終了時に1回だけ全体整合性を取る
                const up = () => {
                    document.removeEventListener('mousemove', move);
                    this.render(); // Map側への反映などのため最後に1回だけ呼ぶ
                };

                document.addEventListener('mousemove', move);
                document.addEventListener('mouseup', up, { once: true });
            };

            const resizer = document.createElement('div'); resizer.className = 'gantt-resizer';
            const linker = document.createElement('div'); linker.className = 'gantt-link-point';
            linker.onmousedown = (e) => this.startGanttLink(e, n.id);

            bar.appendChild(resizer);
            bar.appendChild(linker);
            row.appendChild(bar);
            target.appendChild(row);
        });
    },

    startGanttLink(e, id) {
        e.stopPropagation();
        this.linkingFrom = id;

        const up = (ev) => {
            const t = document.elementFromPoint(ev.clientX, ev.clientY);
            const bar = t?.closest('.gantt-bar');

            if (bar && bar.dataset.id && bar.dataset.id != this.linkingFrom) {
                this.links.push({ from: this.linkingFrom, to: bar.dataset.id });
                this.drawLines();
                alert("リンク完了！");
            }
            this.linkingFrom = null;
            document.removeEventListener('mouseup', up);
        };
        document.addEventListener('mouseup', up);
    },

    initGanttHeader() {
        const gh = document.getElementById('gantt-header');
        gh.innerHTML = ''; // Reset for zoom change
        for (let i = -this.ganttOffsetDays; i < 60; i++) {
            const d = new Date(this.today); d.setDate(this.today.getDate() + i);
            const div = document.createElement('div'); div.className = 'gantt-day';
            if (d.getDay() === 0) div.classList.add('weekend-sun');
            if (d.getDay() === 6) div.classList.add('weekend-sat');
            div.style.minWidth = this.dayWidth + "px"; // Dynamic width
            div.innerText = `${d.getMonth() + 1}/${d.getDate()}`;
            gh.appendChild(div);
        }
    },

    changeMonth(delta) {
        this.today.setMonth(this.today.getMonth() + delta);
        // Persist view date
        localStorage.setItem('pm_calendar_date', this.today.toISOString());
        this.renderCalendar();
    },

    renderCalendar() {
        const target = document.getElementById('cal-target'); target.innerHTML = '';

        // --- Header Navigation Injection ---
        // Find or create the header title container
        const titleEl = document.querySelector('.cal-top-bar h2');
        if (titleEl) {
            // Create nav buttons if not exists
            let navContainer = document.getElementById('cal-nav');
            if (!navContainer) {
                navContainer = document.createElement('span');
                navContainer.id = 'cal-nav';
                navContainer.style.marginLeft = '15px';
                navContainer.innerHTML = `
                    <button class="btn" style="padding: 2px 8px;" onclick="PM.changeMonth(-1)">◀ Prev</button>
                    <button class="btn" style="padding: 2px 8px;" onclick="PM.today = new Date(); PM.renderCalendar(); localStorage.removeItem('pm_calendar_date');">Today</button>
                    <button class="btn" style="padding: 2px 8px;" onclick="PM.changeMonth(1)">Next ▶</button>
                 `;
                titleEl.appendChild(navContainer);
            }
            // Update Title Text with current date
            // Keep the original text but append date? Or replace? 
            // Providing clean title update:
            titleEl.childNodes[0].nodeValue = `📅 戦略カレンダー (${this.today.getFullYear()}/${this.today.getMonth() + 1}) `;
        }

        const headers = ['🗓️ 週目標', '日', '月', '火', '水', '木', '金', '土'];
        headers.forEach(h => { const d = document.createElement('div'); d.className = 'cal-header'; d.innerText = h; target.appendChild(d); });

        const y = this.notes.find(n => n.isGoal && n.timeframe === 'year');
        const m = this.notes.find(n => n.isGoal && n.timeframe === 'month');

        document.getElementById('hud-year').innerHTML = `<input class="hud-input" value="${y ? y.title : ''}" placeholder="今年の野望を入力..." oninput="PM.syncGoalFromCalendar('year', this.value, null)">`;
        document.getElementById('hud-month').innerHTML = `<input class="hud-input" value="${m ? m.title : ''}" placeholder="今月のフォーカス..." oninput="PM.syncGoalFromCalendar('month', this.value, null)">`;

        const startDay = new Date(this.today.getFullYear(), this.today.getMonth(), this.today.getDate() - this.today.getDay());

        for (let i = 0; i < 35; i++) {
            const d = new Date(startDay); d.setDate(startDay.getDate() + i);
            const dStr = this.formatDate(d);

            if (i % 7 === 0) {
                const col = document.createElement('div'); col.className = 'cal-week-col';
                const wEnd = new Date(d); wEnd.setDate(d.getDate() + 6);
                const goal = this.notes.find(n => n.isGoal && n.timeframe === 'week' && n.start === dStr);
                col.innerHTML = `<textarea class="week-input" placeholder="週目標..." oninput="PM.syncGoalFromCalendar('week', this.value, new Date('${dStr}'))">${goal ? goal.title : ''}</textarea>`;
                target.appendChild(col);
            }

            const day = document.createElement('div'); day.className = 'cal-day';
            const todayStr = this.formatDate(new Date()); // Real today
            if (dStr === todayStr) day.style.background = '#444'; // Highlight real today

            day.innerHTML = `<div>${d.getMonth() + 1}/${d.getDate()}</div>`;

            // Existing Tasks
            this.notes.filter(n => !n.isGoal && n.start <= dStr && (n.end >= dStr || n.start === dStr)).forEach(n => {
                const t = document.createElement('div'); t.className = `cal-task color-${n.member}`;
                t.innerText = `${n.icon || ''} ${n.title}`;
                day.appendChild(t);
            });

            // Production Events Injection
            if (this.productionEvents && this.productionEvents.length > 0) {
                const events = this.productionEvents.filter(e => e.start === dStr);
                events.forEach(e => {
                    const div = document.createElement('div');
                    div.className = 'prod-event';
                    div.style.backgroundColor = e.extendedProps.confidence === 'high' ? '#2ecc71' : '#f39c12';
                    div.style.color = '#fff';
                    div.style.fontSize = '10px';
                    div.style.padding = '2px';
                    div.style.marginTop = '2px';
                    div.style.borderRadius = '2px';
                    div.style.cursor = 'pointer';
                    div.title = e.extendedProps.details;
                    div.innerText = (e.extendedProps.confidence === 'high' ? '⚔️ ' : '❓ ') + e.title;
                    div.onclick = () => {
                        if (confirm(`${e.title} の在庫反映リクエストを送信しますか？`)) {
                            // alert("Streamlit側の「承認待ちリスト」から確定してください。");
                        }
                    };
                    day.appendChild(div);
                });
            }

            target.appendChild(day);
        }
    },



    // --- Restored Methods ---
    drawLines() {
        ['svg-layer', 'vision-svg-layer', 'gantt-svg-layer'].forEach(lid => {
            const svg = document.getElementById(lid);
            if (!svg) return;
            svg.innerHTML = '';
            if (lid === 'gantt-svg-layer') return;

            this.links.forEach(l => {
                const n1 = this.notes.find(n => n.id == l.from); const n2 = this.notes.find(n => n.id == l.to);
                if (n1 && n2) {
                    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                    const w1 = n1.isGoal ? 340 : 190; const h1 = n1.isGoal ? 220 : 130;
                    const w2 = n2.isGoal ? 340 : 190; const h2 = n2.isGoal ? 220 : 130;
                    line.setAttribute("x1", n1.x + w1 / 2); line.setAttribute("y1", n1.y + h1 / 2);
                    line.setAttribute("x2", n2.x + w2 / 2); line.setAttribute("y2", n2.y + h2 / 2);
                    line.setAttribute("stroke", "#fecb52");
                    const s = lid === 'vision-svg-layer' ? this.visPos.s : this.mapPos.s;
                    line.setAttribute("stroke-width", 2 / s);
                    svg.appendChild(line);
                }
            });
        });
    },

    startLink(e, id) {
        e.stopPropagation(); this.linkingFrom = id;
        const up = (ev) => {
            const t = document.elementFromPoint(ev.clientX, ev.clientY);
            const el = t?.closest('.sticky-note');
            if (el) {
                const parts = el.id.split('-');
                const toId = parts[1];
                if (toId && toId != this.linkingFrom) this.links.push({ from: this.linkingFrom, to: toId });
            }
            this.linkingFrom = null; this.drawLines(); document.removeEventListener('mouseup', up);
        };
        document.addEventListener('mouseup', up);
    },

    setupEvents() {
        window.addEventListener('mousedown', (e) => {
            if (e.target.closest('.canvas')) {
                const isV = this.currentMode === 'goals';
                const t = isV ? this.visPos : this.mapPos;
                let sX = e.clientX - t.x; let sY = e.clientY - t.y;
                const m = (me) => {
                    t.x = me.clientX - sX; t.y = me.clientY - sY;
                    this.updateTransform();
                };
                document.addEventListener('mousemove', m);
                document.addEventListener('mouseup', () => document.removeEventListener('mousemove', m), { once: true });
            }
        });

        window.addEventListener('wheel', (e) => {
            if (!e.target.closest('#map-area') && !e.target.closest('#view-goals')) return;
            const t = this.currentMode === 'goals' ? this.visPos : this.mapPos;
            t.s *= e.deltaY > 0 ? 0.9 : 1.1;
            t.s = Math.min(Math.max(0.1, t.s), 3);
            this.updateTransform();
        }, { passive: false });

        window.addEventListener('dblclick', (e) => {
            if (e.target.closest('.canvas')) {
                const isV = this.currentMode === 'goals';
                const t = isV ? this.visPos : this.mapPos;
                const id = Date.now();
                const dStr = this.formatDate(this.today);
                this.notes.push({
                    id,
                    x: (e.clientX - t.x) / t.s,
                    y: (e.clientY - t.y) / t.s,
                    title: "新規",
                    start: dStr, end: dStr,
                    member: "p",
                    isGoal: isV,
                    timeframe: "year",
                    icon: '📝'
                });
                this.render();
                setTimeout(() => {
                    const pid = isV ? 'vision-canvas' : 'map-canvas';
                    const el = document.querySelector(`#note-${id}-${pid} .note-title`);
                    if (el) { el.focus(); el.select(); }
                }, 50);
            }
        });

        document.getElementById('resizer').addEventListener('mousedown', (e) => {
            const m = (me) => { document.getElementById('map-area').style.height = `${(me.clientY / window.innerHeight) * 100}%`; };
            document.addEventListener('mousemove', m);
            document.addEventListener('mouseup', () => document.removeEventListener('mousemove', m), { once: true });
        });
    },

    setupKeyboardEvents() {
        window.addEventListener('keydown', (e) => {
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;
            if ((e.key === 'Delete' || e.key === 'Backspace') && this.selectedId) {
                if (confirm('選択した付箋を削除しますか？')) this.deleteNote(this.selectedId);
            }
        });
    },

    deleteNote(id) {
        this.notes = this.notes.filter(n => n.id != id);
        this.links = this.links.filter(l => l.from != id && l.to != id);
        this.selectedId = null;
        this.render();
        if (this.currentMode === 'cal') this.renderCalendar();
    },

    updateTransform() {
        document.getElementById('map-canvas').style.transform = `translate(${this.mapPos.x}px, ${this.mapPos.y}px) scale(${this.mapPos.s})`;
        document.getElementById('vision-canvas').style.transform = `translate(${this.visPos.x}px, ${this.visPos.y}px) scale(${this.visPos.s})`;
    },

    saveData() {
        const b = new Blob([JSON.stringify({ notes: this.notes, links: this.links, mapPos: this.mapPos, visPos: this.visPos })], { type: 'application/json' });
        const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'strategy_v4_7.json'; a.click();
    },

    loadData(e) {
        const r = new FileReader();
        r.onload = (ev) => {
            try {
                const d = JSON.parse(ev.target.result);
                if (!d || !Array.isArray(d.notes)) throw new Error("無効なデータ形式");
                this.notes = d.notes;
                this.links = Array.isArray(d.links) ? d.links : [];
                this.mapPos = d.mapPos || { x: 0, y: 0, s: 1 };
                this.visPos = d.visPos || { x: 0, y: 0, s: 1 };
                this.updateTransform(); this.render();
                console.log("データを復元しました！");
            } catch (err) {
                alert("読込エラー: 正しいJSONファイルか確認してください。");
                console.error(err);
            }
        };
        r.readAsText(e.target.files[0]);
    },

    appendData(e) {
        const r = new FileReader();
        r.onload = (ev) => {
            try {
                const d = JSON.parse(ev.target.result);
                if (!d || !Array.isArray(d.notes)) throw new Error("無効なデータ形式");

                const currentIds = new Set(this.notes.map(n => n.id));
                let addedCount = 0;

                d.notes.forEach(n => {
                    if (!currentIds.has(n.id)) {
                        this.notes.push(n);
                        addedCount++;
                    }
                });

                if (Array.isArray(d.links)) {
                    d.links.forEach(l => {
                        const exists = this.links.some(ex => ex.from == l.from && ex.to == l.to);
                        if (!exists) this.links.push(l);
                    });
                }

                this.render();
                if (this.currentMode === 'cal') this.renderCalendar();

                alert(`${addedCount}件を追加しました。\n重なっている場合は「整列」ボタンを押してください。`);
                e.target.value = '';
            } catch (err) {
                console.error(err);
                alert("読込エラー");
            }
        };
        r.readAsText(e.target.files[0]);
    },

    renderProductionEvents() {
        // Obsolete (integrated into renderCalendar) but kept for safety/references
    },
};

// Init Logic with Persistence
(function () {
    const savedDate = localStorage.getItem('pm_calendar_date');
    if (savedDate) {
        PM.today = new Date(savedDate);
    } else {
        PM.today = new Date();
    }
    PM.init();
})();