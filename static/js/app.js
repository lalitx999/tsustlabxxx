/* TRUST LAB front-end helpers (plain JavaScript, no framework).
 * TL.api()        - JSON Ajax call with CSRF token and the {ok, data, message} envelope
 * TL.toast()      - top-right notification
 * TL.formData()   - read a <form> into a plain object
 * TL.readImage()  - file -> resized JPEG data URL (smaller uploads)
 * TL.waitForFile()- poll a background-built file (PDF/ZIP) until ready
 */
(function () {
  'use strict';

  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }

  async function api(url, options) {
    const opts = options || {};
    const method = (opts.method || 'GET').toUpperCase();
    const headers = { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' };
    const init = { method: method, headers: headers, credentials: 'same-origin' };
    if (method !== 'GET') {
      headers['X-CSRFToken'] = getCookie('csrftoken');
      headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(opts.body || {});
    }
    let response;
    try {
      response = await fetch(url, init);
    } catch (err) {
      throw new Error('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองใหม่');
    }
    let payload = null;
    try { payload = await response.json(); } catch (err) { payload = null; }
    if (!response.ok || !payload || payload.ok === false) {
      const error = new Error((payload && payload.message) || 'เกิดข้อผิดพลาด (' + response.status + ')');
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function icon(name, cls) {
    const sprite = document.body.dataset.sprite || '/static/icons/sprite.svg';
    return '<svg class="tl-icon ' + (cls || '') + '" aria-hidden="true"><use href="' + sprite + '#' + name + '"></use></svg>';
  }

  function toast(message, type) {
    const kind = type || 'success';
    let box = document.querySelector('.tl-toasts');
    if (!box) {
      box = document.createElement('div');
      box.className = 'tl-toasts';
      document.body.appendChild(box);
    }
    const names = { success: 'circle-check', error: 'triangle-alert', warning: 'triangle-alert', info: 'info' };
    const el = document.createElement('div');
    el.className = 'tl-toast ' + kind;
    el.setAttribute('role', 'status');
    el.innerHTML = icon(names[kind] || 'info', 'tl-icon-lg');
    const text = document.createElement('span');
    text.textContent = message;
    el.appendChild(text);
    box.appendChild(el);
    setTimeout(function () { el.remove(); }, 3500);
  }

  function formData(form) {
    const out = {};
    new FormData(form).forEach(function (value, key) {
      if (value instanceof File) return;
      out[key] = typeof value === 'string' ? value.trim() : value;
    });
    form.querySelectorAll('input[type=checkbox][name]').forEach(function (cb) { out[cb.name] = cb.checked; });
    return out;
  }

  function readImage(file, maxSide, quality) {
    const side = maxSide || 1600;
    return new Promise(function (resolve, reject) {
      if (!file || !/^image\//.test(file.type)) { reject(new Error('กรุณาเลือกไฟล์รูปภาพ')); return; }
      const reader = new FileReader();
      reader.onerror = function () { reject(new Error('อ่านไฟล์ไม่สำเร็จ')); };
      reader.onload = function () {
        const img = new Image();
        img.onerror = function () { reject(new Error('ไฟล์รูปภาพเสียหาย')); };
        img.onload = function () {
          const scale = Math.min(1, side / Math.max(img.width, img.height));
          const canvas = document.createElement('canvas');
          canvas.width = Math.round(img.width * scale);
          canvas.height = Math.round(img.height * scale);
          canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL('image/jpeg', quality || 0.85));
        };
        img.src = reader.result;
      };
      reader.readAsDataURL(file);
    });
  }

  async function waitForFile(statusUrl, onProgress) {
    for (let i = 0; i < 60; i++) {
      const res = await api(statusUrl);
      if (res.data.status === 'ready') return res.data.download_url;
      if (res.data.status === 'failed') throw new Error(res.data.error || 'สร้างไฟล์ไม่สำเร็จ');
      if (onProgress) onProgress(i);
      await new Promise(function (r) { setTimeout(r, 1500); });
    }
    throw new Error('ใช้เวลานานเกินไป กรุณาลองใหม่');
  }

  /* Button busy state: TL.busy(btn, true)
   * The original label is kept in data-tl-busy-label so it never overwrites a
   * page's own data-* attributes (e.g. data-label="<job id>" on Operations). */
  function busy(button, on) {
    if (!button) return;
    if (on) {
      button.dataset.tlBusyLabel = button.innerHTML;
      button.disabled = true;
      button.innerHTML = icon('loader-circle', 'tl-spin') + ' <span>กำลังดำเนินการ...</span>';
    } else {
      button.disabled = false;
      if (button.dataset.tlBusyLabel) button.innerHTML = button.dataset.tlBusyLabel;
      delete button.dataset.tlBusyLabel;
    }
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function baht(value) {
    const n = Number(value || 0);
    return n.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function badge(status, label) {
    return '<span class="badge-status st-' + escapeHtml(status) + '">' + escapeHtml(label || status) + '</span>';
  }

  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-flash]').forEach(function (el) { toast(el.textContent, el.dataset.flash); });
  });

  window.TL = { api: api, toast: toast, formData: formData, readImage: readImage, waitForFile: waitForFile,
    busy: busy, esc: escapeHtml, baht: baht, badge: badge, icon: icon, uuid: uuid };
})();
