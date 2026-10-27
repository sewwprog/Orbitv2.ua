'use strict';

const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const mime = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.webmanifest': 'application/manifest+json',
  '.png': 'image/png'
};
let server;
let browser;
let appUrl;

before(async () => {
  server = http.createServer((request, response) => {
    const pathname = new URL(request.url, 'http://localhost').pathname;
    const name = pathname === '/' ? 'index.html' : pathname.replace(/^\//, '');
    const filename = path.resolve(root, name);
    if (!filename.startsWith(root + path.sep)) {
      response.writeHead(403).end();
      return;
    }
    fs.readFile(filename, (error, data) => {
      if (error) {
        response.writeHead(404).end();
        return;
      }
      response.writeHead(200, {
        'content-type': mime[path.extname(filename)] || 'application/octet-stream',
        'cache-control': 'no-store'
      });
      response.end(data);
    });
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  appUrl = `http://127.0.0.1:${server.address().port}/`;
  browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.CHROMIUM_EXECUTABLE_PATH } : {}),
    args: ['--no-sandbox']
  });
});

after(async () => {
  if (browser) await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
});

async function openPage(t, viewport, mobile = false, serviceWorkers = 'block') {
  const context = await browser.newContext({
    viewport,
    isMobile: mobile,
    hasTouch: mobile,
    deviceScaleFactor: 1,
    reducedMotion: 'reduce',
    serviceWorkers
  });
  t.after(() => context.close());
  const page = await context.newPage();
  const errors = [];
  page.setDefaultTimeout(5000);
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.goto(appUrl);
  await page.locator('.board-card').first().waitFor();
  return { context, page, errors };
}

async function createBoard(page, name = 'Тестова дошка') {
  await page.locator('.create-card').click();
  const sheet = page.locator('.sheet');
  await sheet.locator('input').first().fill(name);
  await sheet.locator('button[type="submit"]').click();
  await page.locator('.editor').waitFor();
}

async function box(locator, label) {
  const result = await locator.boundingBox();
  assert.ok(result, `${label} must be visible`);
  return result;
}

function within(rect, viewport, label) {
  const tolerance = 1;
  assert.ok(rect.x >= -tolerance && rect.y >= -tolerance &&
    rect.x + rect.width <= viewport.width + tolerance &&
    rect.y + rect.height <= viewport.height + tolerance,
  `${label} is outside the viewport: ${JSON.stringify(rect)} in ${JSON.stringify(viewport)}`);
}

function overlap(a, b) {
  return a.x < b.x + b.width - 1 && a.x + a.width > b.x + 1 &&
    a.y < b.y + b.height - 1 && a.y + a.height > b.y + 1;
}

const viewports = [
  { name: '320px phone', width: 320, height: 568, mobile: true },
  { name: '360px phone', width: 360, height: 800, mobile: true },
  { name: '390px phone', width: 390, height: 844, mobile: true },
  { name: 'phone landscape', width: 844, height: 390, mobile: true },
  { name: 'wide phone landscape', width: 1024, height: 600, mobile: true },
  { name: 'tablet', width: 768, height: 1024, mobile: true },
  { name: 'short desktop', width: 1280, height: 600, mobile: false },
  { name: 'desktop', width: 1440, height: 900, mobile: false }
];

for (const viewport of viewports) {
  test(`dashboard and board controls remain usable: ${viewport.name}`, { timeout: 30000 }, async t => {
    const { page, errors } = await openPage(t, viewport, viewport.mobile);
    const card = await box(page.locator('.board-card').first(), 'board card');
    const menu = page.locator('.board-card .card-menu').first();
    const menuBox = await box(menu, 'board card menu');
    assert.ok(menuBox.x >= card.x && menuBox.x + menuBox.width <= card.x + card.width &&
      menuBox.y >= card.y && menuBox.y + menuBox.height <= card.y + card.height,
    'the card menu stays inside its card');
    await menu.click();
    assert.equal(await page.locator('.sheet').count(), 1);
    await page.getByRole('button', { name: 'Закрити меню' }).click();

    if (viewport.width <= 700) {
      const search = await box(page.locator('.dash-filters .search-field'), 'dashboard search');
      assert.ok(search.width >= viewport.width - 50, 'search has a usable width on narrow screens');
      await page.getByLabel('Знайти дошку').fill('немає такої дошки');
      assert.equal(await page.locator('.board-card').count(), 0);
      await page.getByLabel('Знайти дошку').fill('');
    }
    await createBoard(page, 'Дуже довга назва дошки '.repeat(5));
    const header = await box(page.locator('.editor-header'), 'editor header');
    const toolbar = await box(page.locator('.main-toolbar'), 'toolbar');
    const zoom = await box(page.locator('.zoom-controls'), 'zoom controls');
    within(toolbar, viewport, 'toolbar');
    within(zoom, viewport, 'zoom controls');
    assert.ok(!overlap(toolbar, header), 'toolbar does not cover the header');
    assert.ok(!overlap(toolbar, zoom), 'toolbar and zoom controls do not overlap');
    within(await box(page.getByRole('button', { name: 'Меню дошки' }), 'board menu'), viewport, 'board menu');
    assert.equal(await page.locator('.main-toolbar').evaluate(el => getComputedStyle(el).position), 'absolute');

    if (viewport.width <= 700 || (viewport.width <= 1200 && viewport.height <= 600)) {
      const buttons = page.locator('.main-toolbar .tool-button:not(.desktop-only)');
      assert.equal(await buttons.count(), 8);
      for (const button of await buttons.all()) {
        const buttonBox = await box(button, 'phone tool');
        within(buttonBox, viewport, 'phone tool');
        assert.ok(buttonBox.width >= 43 && buttonBox.height >= 44, 'tools have a touch-sized target');
      }
      assert.equal(await page.getByRole('button', { name: 'Зменшити масштаб' }).isVisible(), true);
      assert.equal(await page.getByRole('button', { name: 'Збільшити масштаб' }).isVisible(), true);
    }

    await page.getByRole('button', { name: 'Додати блок', exact: true }).click();
    const node = page.locator('.node').first();
    await node.waitFor();
    assert.deepEqual(await node.evaluate(el => ({
      position: getComputedStyle(el).position,
      overflow: getComputedStyle(el).overflow
    })), { position: 'absolute', overflow: 'visible' });
    const handle = page.getByRole('button', { name: 'Додати пов’язаний блок' });
    within(await box(handle, 'connected-block handle'), viewport, 'connected-block handle');
    await page.getByLabel('Текст блока').fill('Нотатка з телефону та ПК');
    await page.getByRole('button', { name: 'Готово', exact: true }).first().click();
    const selection = await box(page.locator('.selection-bar'), 'selection bar');
    within(selection, viewport, 'selection bar');
    assert.ok(!overlap(selection, header), 'selection bar does not cover the header');
    await handle.click();
    assert.equal(await page.locator('.node').count(), 2, 'connected-block handle works');
    assert.deepEqual(errors, []);
  });
}

test('safe-area insets and reduced transparency are respected', { timeout: 20000 }, async t => {
  for (const scenario of [
    { viewport: { width: 390, height: 844 }, safe: { top: 30, right: 0, bottom: 24, left: 0 } },
    { viewport: { width: 844, height: 390 }, safe: { top: 0, right: 44, bottom: 21, left: 44 } }
  ]) {
    const { page, context, errors } = await openPage(t, scenario.viewport, true);
    await page.evaluate(safe => {
      for (const [side, value] of Object.entries(safe)) {
        document.documentElement.style.setProperty(`--safe-${side}`, `${value}px`);
      }
    }, scenario.safe);
    await createBoard(page);
    const toolbar = await box(page.locator('.main-toolbar'), 'safe-area toolbar');
    assert.ok(toolbar.x >= scenario.safe.left && toolbar.x + toolbar.width <= scenario.viewport.width - scenario.safe.right);
    assert.ok(toolbar.y + toolbar.height <= scenario.viewport.height - scenario.safe.bottom);
    const headerButton = await box(page.getByRole('button', { name: 'Мої дошки' }), 'safe-area header button');
    assert.ok(headerButton.y >= scenario.safe.top);
    await page.getByRole('button', { name: 'Меню дошки' }).click();
    const close = await box(page.getByRole('button', { name: 'Закрити меню' }), 'safe-area close button');
    assert.ok(close.x >= scenario.safe.left && close.x + close.width <= scenario.viewport.width - scenario.safe.right);
    assert.ok(close.y >= scenario.safe.top);
    await page.getByRole('button', { name: 'Закрити меню' }).click();
    const cdp = await context.newCDPSession(page);
    assert.notEqual(await page.locator('.main-toolbar').evaluate(el => getComputedStyle(el).backdropFilter), 'none');
    await cdp.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-transparency', value: 'reduce' }] });
    assert.equal(await page.locator('.main-toolbar').evaluate(el => getComputedStyle(el).backdropFilter), 'none');
    assert.equal(await page.locator('.main-toolbar').evaluate(el => getComputedStyle(el).backgroundColor), 'rgb(27, 27, 38)');
    assert.deepEqual(errors, []);
  }
});

test('chart form wraps its buttons, keeps the close button fixed, and fits the graph', { timeout: 30000 }, async t => {
  for (const viewport of [{ width: 320, height: 568 }, { width: 390, height: 844 }, { width: 844, height: 390 }]) {
    const { page, errors } = await openPage(t, viewport, true);
    await createBoard(page);
    await page.getByRole('button', { name: 'Додати графік' }).click();
    const sheet = page.locator('.chart-sheet');
    await sheet.waitFor();
    const checkbox = sheet.locator('.graph-options input[type="checkbox"]').first();
    assert.equal(Math.round((await box(checkbox, 'graph option checkbox')).width), 22);
    await checkbox.check();
    assert.equal(await checkbox.isChecked(), true);
    const modeSelect = sheet.locator('select').first();
    const selectImage = await modeSelect.evaluate(el => getComputedStyle(el).backgroundImage);
    assert.match(selectImage, /data:image\/svg\+xml/, 'select retains its dropdown arrow');
    if (viewport.width <= 384) {
      assert.ok((await box(modeSelect, 'chart mode select')).width >= viewport.width - 50,
        'chart mode has room for its full label on a narrow phone');
    }

    const close = sheet.getByRole('button', { name: 'Закрити меню' });
    const closeBefore = await box(close, 'close button');
    await sheet.locator('.sheet-content').evaluate(el => { el.scrollTop = el.scrollHeight; });
    const closeAfter = await box(close, 'close button after scrolling');
    assert.ok(Math.abs(closeBefore.y - closeAfter.y) < 1, 'close button stays fixed while the content scrolls');
    within(closeAfter, viewport, 'close button');
    for (const button of await sheet.locator('.graph-form-actions button').all()) {
      const fits = await button.evaluate(el => {
        const bounds = el.getBoundingClientRect();
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
          if (!walker.currentNode.textContent.trim()) continue;
          const range = document.createRange();
          range.selectNodeContents(walker.currentNode);
          for (const rect of range.getClientRects()) {
            if (rect.left < bounds.left - 1 || rect.right > bounds.right + 1 ||
                rect.top < bounds.top - 1 || rect.bottom > bounds.bottom + 1) return false;
          }
        }
        return true;
      });
      assert.ok(fits, 'graph action text is not clipped');
    }

    const value = sheet.locator('.graph-point-form input[inputmode="decimal"]').first();
    const date = sheet.locator('.graph-point-form input[type="date"]');
    const firstDate = await date.inputValue();
    for (const point of ['100', '22', '130']) {
      await value.fill(point);
      await sheet.getByRole('button', { name: 'Додати точку' }).click();
    }
    assert.equal(await sheet.locator('.graph-table tbody tr').count(), 3);
    await date.fill(firstDate);
    await value.fill('5');
    await sheet.getByRole('button', { name: 'Додати точку' }).click();
    assert.ok(await sheet.locator('.graph-error').isVisible(), 'duplicate date produces a validation error');
    assert.equal(await sheet.locator('.graph-table tbody tr').count(), 3);
    await sheet.locator('.graph-done').click();
    await page.locator('.chart-sheet').waitFor({ state: 'detached' });
    await page.waitForFunction(() => {
      const graph = document.querySelector('.graph-node')?.getBoundingClientRect();
      const zoom = document.querySelector('.zoom-controls')?.getBoundingClientRect();
      return graph && zoom && graph.left >= 0 && graph.right <= innerWidth && graph.bottom <= zoom.top + 1;
    });
    const graph = await box(page.locator('.graph-node'), 'graph');
    const header = await box(page.locator('.editor-header'), 'header');
    const zoom = await box(page.locator('.zoom-controls'), 'zoom');
    within(graph, viewport, 'focused graph');
    assert.ok(graph.y >= header.y + header.height - 1, 'graph stays below the header');
    assert.ok(graph.y + graph.height <= zoom.y + 1, 'graph is not hidden behind phone controls');
    await page.getByRole('button', { name: 'Редагувати графік' }).click();
    assert.equal(await page.locator('.graph-table tbody tr').count(), 3);
    assert.equal(await page.locator('.graph-options input[type="checkbox"]').first().isChecked(), true);
    await page.getByRole('button', { name: `Редагувати точку ${firstDate}` }).click();
    await page.locator('.graph-point-form input[inputmode="decimal"]').first().fill('42');
    await page.getByRole('button', { name: 'Зберегти точку' }).click();
    assert.match(await page.locator('.graph-table tbody').innerText(), /42/);
    await page.getByRole('button', { name: `Видалити точку ${firstDate}` }).click();
    assert.equal(await page.locator('.graph-table tbody tr').count(), 2);
    await page.getByRole('button', { name: 'Закрити меню' }).click();
    assert.deepEqual(errors, []);
  }
});

test('numeric graph coordinates accept decimals and reject duplicates', { timeout: 15000 }, async t => {
  const { page, errors } = await openPage(t, { width: 320, height: 568 }, true);
  await createBoard(page, 'Числовий графік');
  await page.getByRole('button', { name: 'Додати графік' }).click();
  await page.getByLabel('Вісь X').selectOption('number');
  const inputs = page.locator('.graph-point-form input[inputmode="decimal"]');
  await inputs.nth(0).fill('-2,5');
  await inputs.nth(1).fill('1,5');
  await page.getByRole('button', { name: 'Додати точку' }).click();
  assert.match(await page.locator('.graph-table tbody').innerText(), /1,5\s+-2,5/);
  await inputs.nth(0).fill('0');
  await inputs.nth(1).fill('1,5');
  await page.getByRole('button', { name: 'Додати точку' }).click();
  assert.match(await page.locator('.graph-error').innerText(), /координата X вже є/);
  assert.equal(await page.locator('.graph-table tbody tr').count(), 1);
  assert.deepEqual(errors, []);
});

test('touch pinch, keyboard resizing, and visual viewport offsets', { timeout: 30000 }, async t => {
  const viewport = { width: 390, height: 844 };
  const { page, context, errors } = await openPage(t, viewport, true);
  const canPinchOutsideCanvas = await page.evaluate(() => {
    const first = new Touch({ identifier: 1, target: document.body, clientX: 10, clientY: 10 });
    const second = new Touch({ identifier: 2, target: document.body, clientX: 20, clientY: 20 });
    const event = new TouchEvent('touchstart', { bubbles: true, cancelable: true, touches: [first, second] });
    document.body.dispatchEvent(event);
    return !event.defaultPrevented;
  });
  assert.equal(canPinchOutsideCanvas, true, 'multi-touch is not blocked globally');
  await createBoard(page);
  const cdp = await context.newCDPSession(page);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: 150, y: 350, id: 1 }, { x: 230, y: 350, id: 2 }] });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: 110, y: 350, id: 1 }, { x: 270, y: 350, id: 2 }] });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await page.waitForFunction(() => document.querySelector('.zoom-value')?.textContent !== '100%');
  const zoomText = await page.locator('.zoom-value').textContent();
  assert.equal(await page.locator('.zoom-value').getAttribute('aria-label'), `Масштаб ${zoomText}`);

  await page.getByRole('button', { name: 'Додати блок', exact: true }).click();
  await page.getByLabel('Текст блока').focus();
  await page.setViewportSize({ width: 390, height: 500 });
  await page.waitForFunction(() => document.documentElement.classList.contains('pwa-keyboard'));
  assert.equal(await page.locator('.main-toolbar').isVisible(), false);
  assert.equal(Math.round((await box(page.locator('.editor'), 'resized editor')).height), 500);
  await page.setViewportSize(viewport);
  await page.waitForFunction(() => !document.documentElement.classList.contains('pwa-keyboard'));
  assert.equal(await page.locator('.main-toolbar').isVisible(), true);
  await page.getByRole('button', { name: 'Готово', exact: true }).first().click();

  await page.getByRole('button', { name: 'Додати графік' }).click();
  const value = page.locator('.graph-point-form input[inputmode="decimal"]').first();
  await value.focus();
  await page.evaluate(() => {
    Object.defineProperty(window.visualViewport, 'height', { configurable: true, get: () => 480 });
    Object.defineProperty(window.visualViewport, 'offsetTop', { configurable: true, get: () => 23 });
    window.visualViewport.dispatchEvent(new Event('resize'));
  });
  await page.waitForFunction(() => document.documentElement.classList.contains('pwa-keyboard'));
  await page.waitForTimeout(100);
  const overlay = await box(page.locator('.sheet-overlay'), 'keyboard sheet overlay');
  assert.ok(Math.abs(overlay.y - 23) < 1 && Math.abs(overlay.height - 480) < 1);
  const content = await box(page.locator('.sheet-content'), 'sheet scroll area');
  const field = await box(value, 'focused field');
  assert.ok(field.y >= content.y - 1 && field.y + field.height <= content.y + content.height + 1,
    'focused field is scrolled into the visible portion of the sheet');
  assert.deepEqual(errors, []);
});

test('task and node settings controls stay usable on a narrow phone', { timeout: 15000 }, async t => {
  const { page, errors } = await openPage(t, { width: 320, height: 568 }, true);
  await createBoard(page, 'Завдання');
  await page.getByRole('button', { name: 'Додати блок', exact: true }).click();
  await page.getByLabel('Текст блока').fill('Виконати тест');
  await page.getByRole('button', { name: 'Готово', exact: true }).first().click();
  await page.getByRole('button', { name: 'Налаштування блока' }).click();
  await page.getByRole('combobox', { name: 'Тип' }).selectOption('task');
  await page.getByRole('button', { name: 'Синій', exact: true }).click();
  await page.getByRole('button', { name: 'Закрити меню' }).click();
  const task = page.getByRole('button', { name: 'Позначити виконаною' });
  const menu = page.getByRole('button', { name: 'Дії з блоком' });
  const taskBox = await box(task, 'task checkbox');
  const menuBox = await box(menu, 'node menu');
  assert.ok(taskBox.width >= 44 && taskBox.height >= 44);
  assert.ok(menuBox.width >= 44 && menuBox.height >= 44);
  assert.ok(!overlap(taskBox, menuBox));
  await task.click();
  assert.match(await page.locator('.node').getAttribute('class'), /completed/);
  assert.match(await page.locator('.node').getAttribute('class'), /color-blue/);
  assert.deepEqual(errors, []);
});

test('connected blocks and connection mode remain usable', { timeout: 20000 }, async t => {
  const { page, errors } = await openPage(t, { width: 390, height: 844 }, true);
  await createBoard(page, 'Зв’язки');
  await page.getByRole('button', { name: 'Додати блок', exact: true }).click();
  await page.getByLabel('Текст блока').fill('Перший');
  await page.getByRole('button', { name: 'Готово', exact: true }).first().click();
  await page.getByRole('button', { name: 'Додати пов’язаний блок' }).click();
  await page.getByLabel('Текст блока').fill('Другий');
  await page.getByRole('button', { name: 'Готово', exact: true }).first().click();
  assert.equal(await page.locator('.edge').count(), 1);
  await page.getByRole('button', { name: 'Показати всю дошку' }).click();
  await page.waitForFunction(() => [...document.querySelectorAll('.node')].every(el => {
    const rect = el.getBoundingClientRect();
    return rect.left >= 0 && rect.right <= innerWidth;
  }));
  await page.getByRole('button', { name: 'Зв’язок', exact: true }).click();
  within(await box(page.locator('.mode-banner'), 'connection-mode banner'), { width: 390, height: 844 }, 'connection-mode banner');
  await page.locator('.node').nth(1).click({ position: { x: 30, y: 20 } });
  assert.match(await page.locator('.mode-banner').innerText(), /другого блока/);
  await page.locator('.node').nth(0).click({ position: { x: 30, y: 20 } });
  assert.equal(await page.locator('.edge').count(), 2);
  assert.deepEqual(errors, []);
});

test('notes, history, duplicate notifications, and local persistence', { timeout: 30000 }, async t => {
  const { page, errors } = await openPage(t, { width: 390, height: 844 }, true);
  await createBoard(page, 'Збереження');
  await page.getByRole('button', { name: 'Додати блок', exact: true }).click();
  await page.getByLabel('Текст блока').fill('Текст, який має залишитися');
  await page.getByRole('button', { name: 'Готово', exact: true }).first().click();
  await page.getByRole('button', { name: 'Дублювати блок' }).click();
  assert.equal(await page.locator('.node').count(), 2);
  assert.equal(await page.locator('.toast').textContent(), 'Блоки дубльовано');
  await page.locator('.toast').waitFor({ state: 'detached', timeout: 5000 });
  await page.getByRole('button', { name: 'Скасувати дію' }).click();
  assert.equal(await page.locator('.node').count(), 1);
  await page.getByRole('button', { name: 'Повторити дію' }).click();
  assert.equal(await page.locator('.node').count(), 2);
  await page.waitForFunction(() => document.querySelector('.save-status.saved'));
  await page.getByRole('button', { name: 'Мої дошки' }).click();
  await page.reload();
  await page.getByRole('button', { name: 'Відкрити Збереження' }).click();
  assert.equal(await page.locator('.node').count(), 2);
  assert.equal(await page.locator('.node-text-display').first().textContent(), 'Текст, який має залишитися');
  assert.deepEqual(errors, []);
});

test('offline shell activates and board data survives an offline reload', { timeout: 30000 }, async t => {
  const { page, context, errors } = await openPage(t, { width: 390, height: 844 }, true, 'allow');
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await page.waitForFunction(() => navigator.serviceWorker.controller);
  const cacheNames = await page.evaluate(() => caches.keys());
  assert.ok(cacheNames.some(name => name.endsWith(':v4-responsive-glass')));
  await createBoard(page, 'Офлайн дошка');
  await page.getByRole('button', { name: 'Додати блок', exact: true }).click();
  await page.getByLabel('Текст блока').fill('Збережено без мережі');
  await page.getByRole('button', { name: 'Готово', exact: true }).first().click();
  await page.waitForFunction(() => document.querySelector('.save-status.saved'));
  await context.setOffline(true);
  await page.reload();
  await page.getByRole('button', { name: 'Відкрити Офлайн дошка' }).click();
  assert.equal(await page.locator('.node-text-display').first().textContent(), 'Збережено без мережі');
  assert.deepEqual(errors, []);
});

test('chart CSV, board JSON/PNG exports, and JSON import work', { timeout: 30000 }, async t => {
  const { page, errors } = await openPage(t, { width: 390, height: 844 }, true);
  await createBoard(page, 'Експорт та імпорт');
  await page.getByRole('button', { name: 'Додати графік' }).click();
  await page.locator('.graph-point-form input[inputmode="decimal"]').first().fill('100');
  await page.getByRole('button', { name: 'Додати точку' }).click();
  const [csv] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'CSV', exact: true }).click()
  ]);
  const csvText = await fs.promises.readFile(await csv.path(), 'utf8');
  assert.match(csvText, /"100"/);
  await page.locator('.graph-done').click();
  await page.getByRole('button', { name: 'Усі інструменти' }).click();
  const [json] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: /Експорт JSON/ }).click()
  ]);
  const data = await fs.promises.readFile(await json.path());
  const exported = JSON.parse(data.toString('utf8'));
  assert.equal(exported.format, 'orbit-whiteboard');
  assert.equal(exported.board.nodes[0].chart.points[0].value, 100);
  const [png] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: /Експорт PNG/ }).click()
  ]);
  const pngBytes = await fs.promises.readFile(await png.path());
  assert.deepEqual([...pngBytes.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  await page.getByRole('button', { name: 'Імпорт JSON' }).click();
  await page.locator('.sheet input[type="file"]').setInputFiles({
    name: 'orbit.json', mimeType: 'application/json', buffer: data
  });
  await page.getByText('Дошку імпортовано').waitFor();
  await page.getByRole('button', { name: 'Мої дошки' }).click();
  assert.equal(await page.getByRole('button', { name: 'Відкрити Експорт та імпорт' }).count(), 2);
  await page.getByRole('button', { name: 'Відкрити Експорт та імпорт' }).first().click();
  assert.equal(await page.locator('.graph-node').count(), 1);
  assert.match(await page.locator('.graph-node').textContent(), /100/);
  assert.deepEqual(errors, []);
});

test('the standalone local HTML still opens', { timeout: 15000 }, async t => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  t.after(() => context.close());
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(pathToFileURL(path.join(root, 'index.html')).href);
  await page.locator('.create-card').waitFor();
  await createBoard(page, 'Локальний файл');
  await page.getByRole('button', { name: 'Додати блок', exact: true }).click();
  assert.equal(await page.locator('.node').count(), 1);
  assert.deepEqual(errors, []);
});
