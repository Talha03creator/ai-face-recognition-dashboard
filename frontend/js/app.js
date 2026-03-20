/**
 * app.js — FaceAI Application Logic
 * Handles routing, all view renders, upload, matching, user management.
 */

// ------------------------------------------------------------------ //
// State                                                                //
// ------------------------------------------------------------------ //
const App = {
    cameraOn: true,
    matchState: { target: null, group: null },
};

// ------------------------------------------------------------------ //
// Router                                                               //
// ------------------------------------------------------------------ //

function navigateTo(viewId) {
    document.getElementById('page-title').innerText =
        { dashboard: 'Dashboard', detect: 'Detect Faces', match: 'Face Match', users: 'Users', logs: 'Logs' }[viewId] || viewId;

    document.querySelectorAll('.nav-item').forEach(el =>
        el.classList.toggle('active', el.dataset.view === viewId)
    );

    const view = VIEWS[viewId];
    if (view) view();
}

document.querySelectorAll('.nav-item').forEach(el =>
    el.addEventListener('click', e => { e.preventDefault(); navigateTo(el.dataset.view); })
);

// ------------------------------------------------------------------ //
// Helpers                                                              //
// ------------------------------------------------------------------ //

function setContent(html) {
    document.getElementById('page-content').innerHTML = html;
}

function cloneTemplate(id) {
    return document.getElementById(id).content.cloneNode(true);
}

function renderMarkdown(md) {
    if (!md) return '';
    return md
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>[\s\S]+?<\/li>)/g, '<ul>$1</ul>')
        .replace(/\n{2,}/g, '</p><p>')
        .replace(/\n/g, '<br>');
}

function poll(taskId, onProgress, onComplete, onError, interval = 600) {
    const timer = setInterval(async () => {
        const data = await API.fetchProgress(taskId);
        if (data.error) {
            clearInterval(timer);
            onError(data.error);
            return;
        }
        onProgress(data.progress, data.status);
        if (data.complete) {
            clearInterval(timer);
            onComplete();
        }
    }, interval);
}

// ------------------------------------------------------------------ //
// Views                                                                //
// ------------------------------------------------------------------ //

const VIEWS = {

    /* ---- DASHBOARD ---- */
    async dashboard() {
        const content = document.getElementById('page-content');
        content.innerHTML = '';
        content.appendChild(cloneTemplate('tpl-dashboard'));

        const [users, logs] = await Promise.all([API.fetchUsers(), API.fetchLogs()]);

        const usersArr = users.error ? [] : (users.users || []);
        const logsArr  = logs.error  ? [] : (logs.logs   || []);

        document.getElementById('stat-users').innerText = usersArr.length;
        document.getElementById('stat-logs').innerText  = logsArr.length;

        const actEl = document.getElementById('dash-activity');
        if (logsArr.length === 0) {
            actEl.innerHTML = '<p class="muted">No recent detections</p>';
        } else {
            actEl.innerHTML = logsArr.slice(-8).reverse().map(l => `
                <div class="activity-item">
                    <strong>${l.name || 'Unknown'}</strong>
                    <span class="muted">${new Date(l.timestamp).toLocaleString()}</span>
                </div>`).join('');
        }
    },

    /* ---- DETECT ---- */
    detect() {
        const content = document.getElementById('page-content');
        content.innerHTML = '';
        content.appendChild(cloneTemplate('tpl-detect'));
        App.cameraOn = true;
    },

    /* ---- MATCH ---- */
    match() {
        const content = document.getElementById('page-content');
        content.innerHTML = '';
        content.appendChild(cloneTemplate('tpl-match'));
        App.matchState = { target: null, group: null };

        const targetInput = document.getElementById('target-input');
        const groupInput  = document.getElementById('group-input');
        const matchBtn    = document.getElementById('match-btn');

        function handleFile(input, zoneId, labelId, stateKey) {
            input.onchange = e => {
                const f = e.target.files[0];
                if (!f) return;
                App.matchState[stateKey] = f;
                document.getElementById(labelId).innerText = f.name;
                document.getElementById(zoneId).classList.add('ready');
                checkReady();
            };
        }

        function checkReady() {
            matchBtn.disabled = !(App.matchState.target && App.matchState.group);
        }

        handleFile(targetInput, 'target-zone', 'target-label', 'target');
        handleFile(groupInput,  'group-zone',  'group-label',  'group');

        matchBtn.onclick = runMatch;
    },

    /* ---- USERS ---- */
    async users() {
        const content = document.getElementById('page-content');
        content.innerHTML = '';
        content.appendChild(cloneTemplate('tpl-users'));
        await refreshUsers();
    },

    /* ---- LOGS ---- */
    async logs() {
        const content = document.getElementById('page-content');
        content.innerHTML = '';
        content.appendChild(cloneTemplate('tpl-logs'));
        await refreshLogs();
    },
};

// ------------------------------------------------------------------ //
// Camera                                                               //
// ------------------------------------------------------------------ //

function toggleCamera() {
    const feed = document.getElementById('webcam-feed');
    const btn  = document.getElementById('cam-btn');
    if (!feed || !btn) return;

    if (App.cameraOn) {
        feed.src = '';
        feed.style.visibility = 'hidden';
        btn.innerText = 'Start Camera';
        App.cameraOn = false;
    } else {
        feed.src = '/api/detect/video_feed?t=' + Date.now();
        feed.style.visibility = 'visible';
        btn.innerText = 'Stop Camera';
        App.cameraOn = true;
    }
}

// ------------------------------------------------------------------ //
// Upload Detection                                                     //
// ------------------------------------------------------------------ //

async function handleUpload(input) {
    const file = input.files[0];
    if (!file) return;

    const progressArea = document.getElementById('progress-area');
    const progressFill = document.getElementById('progress-fill');
    const statusEl     = document.getElementById('progress-status');
    const pctEl        = document.getElementById('progress-pct');
    const resultEl     = document.getElementById('upload-result');
    const zone         = document.getElementById('upload-zone');

    resultEl.innerHTML = '';
    progressArea.classList.remove('hidden');
    zone.style.pointerEvents = 'none';
    zone.style.opacity = '0.6';

    const setProgress = (pct, status) => {
        progressFill.style.width = pct + '%';
        statusEl.innerText = status;
        pctEl.innerText    = pct + '%';
    };

    setProgress(10, 'Uploading…');

    const res = await API.uploadDetect(file);
    if (res.error || !res.task_id) {
        setProgress(0, 'Upload failed');
        resultEl.innerHTML = makeAlert('danger', res.error || 'Upload failed');
        zone.style.pointerEvents = 'auto';
        zone.style.opacity = '1';
        return;
    }

    poll(
        res.task_id,
        (pct, status) => setProgress(pct, status),
        async () => {
            const result = await API.fetchResult(res.task_id);
            progressArea.classList.add('hidden');
            zone.style.pointerEvents = 'auto';
            zone.style.opacity = '1';
            renderDetectResult(result, resultEl);
        },
        (err) => {
            setProgress(100, 'Error');
            resultEl.innerHTML = makeAlert('danger', err);
            zone.style.pointerEvents = 'auto';
            zone.style.opacity = '1';
        }
    );
}

function renderDetectResult(res, container) {
    if (res.error) {
        container.innerHTML = makeAlert('danger', res.error);
        return;
    }

    const faces = res.detections || [];
    const facesHtml = faces.length === 0
        ? '<p class="muted">No faces detected</p>'
        : faces.map(d => `
            <div class="detection-item">
                <strong>${d.name}</strong>
                <span class="${d.confidence > 0.5 ? 'stat-val healthy' : 'muted'}" style="font-size:0.875rem">
                    ${d.name === 'Unknown' ? '—' : (d.confidence * 100).toFixed(0) + '% match'}
                </span>
            </div>`).join('');

    container.innerHTML = `
        <div class="result-card">
            <h4>Detection Result — ${faces.length} face${faces.length !== 1 ? 's' : ''} found</h4>
            <img src="${res.image}" style="width:100%;border-radius:8px;margin:0.75rem 0;border:1px solid var(--border);">
            ${facesHtml}
        </div>`;
}

// ------------------------------------------------------------------ //
// Face Match                                                           //
// ------------------------------------------------------------------ //

async function runMatch() {
    const { target, group } = App.matchState;
    if (!target || !group) return;

    const btn         = document.getElementById('match-btn');
    const progSection = document.getElementById('match-progress-section');
    const progFill    = document.getElementById('match-progress-fill');
    const statusEl    = document.getElementById('match-status-text');
    const pctEl       = document.getElementById('match-pct');
    const resultSec   = document.getElementById('match-result-section');
    const resultBody  = document.getElementById('match-result-body');

    btn.disabled = true;
    progSection.classList.remove('hidden');
    resultSec.classList.add('hidden');
    resultBody.innerHTML = '';

    const setProgress = (pct, status) => {
        progFill.style.width = pct + '%';
        statusEl.innerText = status;
        pctEl.innerText    = pct + '%';
    };

    setProgress(5, 'Starting…');

    const res = await API.matchFaces(target, group);
    if (res.error || !res.task_id) {
        setProgress(0, 'Failed to start');
        resultSec.classList.remove('hidden');
        resultBody.innerHTML = makeAlert('danger', res.error || 'Failed to start match task');
        btn.disabled = false;
        return;
    }

    poll(
        res.task_id,
        (pct, status) => setProgress(pct, status),
        async () => {
            const result = await API.fetchResult(res.task_id);
            progSection.classList.add('hidden');
            resultSec.classList.remove('hidden');
            btn.disabled = false;
            renderMatchResult(result, resultBody);
        },
        (err) => {
            setProgress(100, 'Error');
            resultSec.classList.remove('hidden');
            resultBody.innerHTML = makeAlert('danger', err);
            btn.disabled = false;
        }
    );
}

function renderMatchResult(res, container) {
    if (res.error) {
        container.innerHTML = makeAlert('danger', res.error);
        return;
    }

    const m = res.match_data || {};
    const alertType = m.status === 'Strong Match' ? 'success' :
                      m.status === 'Possible Match' ? 'warn' : 'danger';

    container.innerHTML = `
        <div class="alert alert-${alertType}">
            <strong>${m.status || 'Result'}</strong> &mdash; Confidence: ${(m.confidence || 0).toFixed(1)}%
        </div>
        ${res.image ? `<img src="${res.image}" class="match-result-img">` : ''}
        ${m.explanation_markdown ? `
            <div class="explanation-box">
                ${renderMarkdown(m.explanation_markdown)}
            </div>` : ''}
        <div class="result-card" style="margin-top:1rem;font-size:0.875rem">
            <div class="detection-item"><span class="muted">Face Index</span><strong>Face #${m.face_index || '?'}</strong></div>
            <div class="detection-item"><span class="muted">Position</span><strong>${m.position || '—'}</strong></div>
            <div class="detection-item"><span class="muted">Distance Score</span><strong>${m.distance?.toFixed(4) || '—'}</strong></div>
            <div class="detection-item"><span class="muted">Confidence</span><strong>${(m.confidence || 0).toFixed(1)}%</strong></div>
        </div>`;
}

// ------------------------------------------------------------------ //
// Users                                                                 //
// ------------------------------------------------------------------ //

async function refreshUsers() {
    const tbody = document.getElementById('users-tbody');
    if (!tbody) return;
    const data = await API.fetchUsers();
    const users = data.error ? [] : (data.users || []);
    tbody.innerHTML = users.length === 0
        ? '<tr><td colspan="3" class="muted">No registered users</td></tr>'
        : users.map(u => `
            <tr>
                <td>${u}</td>
                <td><span class="badge-known">Known</span></td>
                <td><button class="btn btn-danger" onclick="deleteUser('${u}')">Delete</button></td>
            </tr>`).join('');
}

function openRegModal()  { document.getElementById('reg-modal').classList.remove('hidden'); }
function closeRegModal() { document.getElementById('reg-modal').classList.add('hidden');    }

async function submitReg() {
    const name = document.getElementById('reg-name').value.trim();
    const file = document.getElementById('reg-file').files[0];
    const msg  = document.getElementById('reg-msg');

    if (!name || !file) {
        msg.innerHTML = makeAlert('danger', 'Name and photo are required');
        return;
    }

    msg.innerHTML = '<span class="muted">Registering…</span>';
    const res = await API.registerUser(name, file);

    if (res.error || res.status === 'error') {
        msg.innerHTML = makeAlert('danger', res.error || res.message || 'Registration failed');
    } else {
        closeRegModal();
        await refreshUsers();
    }
}

async function deleteUser(name) {
    if (!confirm(`Delete user "${name}"?`)) return;
    await API.deleteUser(name);
    await refreshUsers();
}

// ------------------------------------------------------------------ //
// Logs                                                                  //
// ------------------------------------------------------------------ //

async function refreshLogs() {
    const tbody = document.getElementById('logs-tbody');
    if (!tbody) return;
    const data = await API.fetchLogs();
    const logs = data.error ? [] : (data.logs || []);
    tbody.innerHTML = logs.length === 0
        ? '<tr><td colspan="4" class="muted">No detection logs yet</td></tr>'
        : [...logs].reverse().map(l => `
            <tr>
                <td>${new Date(l.timestamp).toLocaleString()}</td>
                <td><strong>${l.name || 'Unknown'}</strong></td>
                <td>${l.confidence ? (l.confidence * 100).toFixed(0) + '%' : '—'}</td>
                <td>${l.source || '—'}</td>
            </tr>`).join('');
}

// ------------------------------------------------------------------ //
// Alert helper                                                          //
// ------------------------------------------------------------------ //

function makeAlert(type, msg) {
    return `<div class="alert alert-${type}">${msg}</div>`;
}

// ------------------------------------------------------------------ //
// Boot                                                                  //
// ------------------------------------------------------------------ //

navigateTo('dashboard');
