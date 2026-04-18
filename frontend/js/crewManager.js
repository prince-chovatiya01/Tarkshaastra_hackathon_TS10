// Crew Manager — loads crew list and manages Telegram Chat IDs

function toggleCrewManager() {
    var overlay = document.getElementById('crew-manager-overlay');
    if (!overlay) return;
    if (overlay.classList.contains('active')) {
        overlay.classList.remove('active');
    } else {
        overlay.classList.add('active');
        loadCrewList();
    }
}

function initCrewManager() {
    loadCrewList();
}

function loadCrewList() {
    fetch('/api/crew', { headers: authHeader() })
        .then(function(r) { return r.json(); })
        .then(function(crew) {
            renderCrewTable(crew);
        })
        .catch(function(err) {
            console.error('Failed to load crew:', err);
        });
}

function renderCrewTable(crewList) {
    var tbody = document.getElementById('crewTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (crewList.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:rgba(255,255,255,0.3);">No crew members found</td></tr>';
        return;
    }

    crewList.forEach(function(c) {
        var tr = document.createElement('tr');

        var zoneCls = 'crew-zone-a';
        if (c.zone === 'Zone B') zoneCls = 'crew-zone-b';
        if (c.zone === 'Zone C') zoneCls = 'crew-zone-c';

        var hasId = c.telegram_chat_id && c.telegram_chat_id.length > 0;
        var keyDotCls = hasId ? 'key-dot-ok' : 'key-dot-missing';

        var statusCls = c.is_available ? 'crew-status-active' : 'crew-status-busy';
        var statusTxt = c.is_available ? '● Available' : '● Busy';

        tr.innerHTML =
            '<td class="crew-name">' + c.name + '</td>' +
            '<td class="crew-phone">' + c.phone + '</td>' +
            '<td><span class="crew-zone-badge ' + zoneCls + '">' + c.zone + '</span></td>' +
            '<td><span class="' + statusCls + '">' + statusTxt + '</span></td>' +
            '<td>' +
                '<div class="crew-key-status">' +
                    '<span class="key-dot ' + keyDotCls + '"></span>' +
                    '<input type="text" class="crew-chatid-input" ' +
                        'id="chatid-' + c.id + '" ' +
                        'value="' + (c.telegram_chat_id || '') + '" ' +
                        'placeholder="Chat ID...">' +
                '</div>' +
            '</td>' +
            '<td>' +
                '<button class="crew-save-btn" id="save-btn-' + c.id + '" onclick="saveCrewTelegram(' + c.id + ')">Save</button>' +
                '<span id="saved-msg-' + c.id + '" style="display:none;" class="crew-saved-msg"> ✓</span>' +
            '</td>';

        tbody.appendChild(tr);
    });
}

function saveCrewTelegram(crewId) {
    var input = document.getElementById('chatid-' + crewId);
    var btn = document.getElementById('save-btn-' + crewId);
    var msg = document.getElementById('saved-msg-' + crewId);
    if (!input || !btn) return;

    var chatId = input.value.trim();
    btn.disabled = true;
    btn.textContent = '...';

    fetch('/api/crew/' + crewId + '/telegram', {
        method: 'PUT',
        headers: authHeader(),
        body: JSON.stringify({ chat_id: chatId })
    })
    .then(function(r) {
        if (!r.ok) throw new Error('Failed to save');
        return r.json();
    })
    .then(function() {
        btn.textContent = 'Save';
        btn.disabled = false;
        if (msg) {
            msg.style.display = 'inline';
            setTimeout(function() { msg.style.display = 'none'; }, 2500);
        }
        var dot = input.parentElement.querySelector('.key-dot');
        if (dot) {
            if (chatId) {
                dot.classList.remove('key-dot-missing');
                dot.classList.add('key-dot-ok');
            } else {
                dot.classList.remove('key-dot-ok');
                dot.classList.add('key-dot-missing');
            }
        }
        if (typeof showToast === 'function') showToast('Telegram ID saved', 'success');
    })
    .catch(function(err) {
        btn.textContent = 'Save';
        btn.disabled = false;
        if (typeof showToast === 'function') showToast('Failed: ' + err.message, 'error');
    });
}
