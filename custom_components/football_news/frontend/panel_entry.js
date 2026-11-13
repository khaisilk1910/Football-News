/** Home Assistant custom panel bootstrap, v2026.11.13.12. */
const PANEL_TAG = 'football-news-panel';
try {
  await import('./panel.js?v=2026.11.13.12');
  if (!customElements.get(PANEL_TAG)) {
    throw new Error('The panel module did not register football-news-panel');
  }
} catch (error) {
  console.error('[Football News] Cannot load dashboard module', error);
  if (!customElements.get(PANEL_TAG)) {
    customElements.define(PANEL_TAG, class FootballNewsFallback extends HTMLElement {
      connectedCallback() {
        const box = document.createElement('div');
        box.style.cssText = 'min-height:90vh;padding:32px;background:#210d16;color:#ffedda;font:16px/1.6 system-ui';
        const title = document.createElement('h1');
        title.textContent = '⚽ Football News — Lỗi tải giao diện';
        const message = document.createElement('p');
        message.textContent = 'Không thể tải mã dashboard. Kiểm tra F12 → Console và Network → panel.js; cập nhật lại Football News và khởi động lại Home Assistant.';
        const details = document.createElement('pre');
        details.style.cssText = 'white-space:pre-wrap;overflow-wrap:anywhere;color:#ffd35d';
        details.textContent = String(error?.message || error);
        box.append(title, message, details);
        this.replaceChildren(box);
      }
    });
  }
}
