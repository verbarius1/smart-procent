// Дела двоих — логика хранилища. Загружается скриптом Google Apps Script из этого репозитория.
// PIN здесь не хранится: его передаёт скрипт в Google.
var DAY = 24 * 60 * 60 * 1000;

// Столбцы: A — Дело, B — Готово, C — Выполнено (дата), D — Приоритет (1, 2, 3)
function sheet() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  if (sh.getLastRow() === 0) {
    sh.getRange(1, 1, 1, 4).setValues([['Дело', 'Готово', 'Выполнено', 'Приоритет']]).setFontWeight('bold');
    sh.setColumnWidth(1, 320);
  } else if (sh.getRange(1, 3).getValue() !== 'Выполнено') {
    sh.getRange(1, 3, 1, 2).setValues([['Выполнено', 'Приоритет']]).setFontWeight('bold');
  }
  return sh;
}

function rows(sh) {
  var n = sh.getLastRow() - 1;
  if (n < 1) return [];
  var vals = sh.getRange(2, 1, n, 4).getValues();
  var now = new Date(), out = [];
  for (var i = 0; i < vals.length; i++) {
    var r = vals[i], t = String(r[0]).trim();
    if (!t) continue;
    var d = r[1] === true;
    var at = r[2] instanceof Date ? r[2] : null;
    var p = [1, 2, 3].indexOf(Number(r[3])) >= 0 ? Number(r[3]) : 2;
    // отметили прямо в таблице — проставляем дату и приоритет
    if (d && !at) { at = now; sh.getRange(i + 2, 3).setValue(now); }
    if (!d && at) { at = null; sh.getRange(i + 2, 3).clearContent(); }
    if (String(r[3]) === '') sh.getRange(i + 2, 4).setValue(p);
    out.push({ t: t, d: d, at: at ? at.getTime() : null, p: p, row: i + 2 });
  }
  return out;
}

function split(all) {
  var now = Date.now(), items = [], history = [];
  all.forEach(function (x) {
    var o = { t: x.t, d: x.d, at: x.at, p: x.p };
    if (x.d && x.at && now - x.at > DAY) history.push(o); else items.push(o);
  });
  history.sort(function (a, b) { return b.at - a.at; });
  return { items: items, history: history };
}

function out(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

module.exports = {
  setup: function () { sheet(); return 'ok'; },

  // без PIN список не отдаётся
  doGet: function () {
    return out({ ok: false, error: 'locked' });
  },

  doPost: function (e, PIN) {
    var req;
    try { req = JSON.parse(e.postData.contents); } catch (err) { return out({ ok: false, error: 'bad_request' }); }
    if (!PIN || String(req.pin) !== String(PIN)) return out({ ok: false, error: 'bad_pin' });

    var lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      var sh = sheet();
      var all = rows(sh);
      var t = String(req.t || '').trim().slice(0, 200);
      var hit = null;
      for (var i = 0; i < all.length; i++) if (all[i].t === t) { hit = all[i]; break; }
      var p = [1, 2, 3].indexOf(Number(req.p)) >= 0 ? Number(req.p) : 2;

      if (req.action === 'toggle' && hit) {
        sh.getRange(hit.row, 2).setValue(req.d === true);
        if (req.d === true) sh.getRange(hit.row, 3).setValue(new Date()); else sh.getRange(hit.row, 3).clearContent();
      } else if (req.action === 'restore' && hit) {
        sh.getRange(hit.row, 2).setValue(false);
        sh.getRange(hit.row, 3).clearContent();
      } else if (req.action === 'prio' && hit) {
        sh.getRange(hit.row, 4).setValue(p);
      } else if (req.action === 'add' && t && !hit) {
        var r = sh.getLastRow() + 1;
        sh.getRange(r, 1, 1, 4).setValues([[t, false, '', p]]);
        sh.getRange(r, 2).insertCheckboxes();
      } else if (req.action === 'remove' && hit) {
        sh.deleteRow(hit.row);
      }
      SpreadsheetApp.flush();
      var s = split(rows(sh));
      return out({ ok: true, items: s.items, history: s.history });
    } finally {
      lock.releaseLock();
    }
  }
};
