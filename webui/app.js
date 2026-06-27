// OCR 웹 UI 상호작용 + 실제 파이프라인(/api/convert) 연동
(function () {
  // ---- 아이콘 (디자인 원본 SVG) ----
  const I = {
    chev: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>',
    pencil: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
    arrow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
    sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 1.5v3M12 19.5v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M1.5 12h3M19.5 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/></svg>',
    moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg>',
  };
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  $('.tb-chev').innerHTML = I.chev;
  $('.tb-pencil').innerHTML = I.pencil;
  $('.tb-convert').insertAdjacentHTML('afterbegin', I.check);
  $('.tb-arrow').innerHTML = I.arrow;
  $('.tb-round').innerHTML = I.plus;

  // ---- 테마 ----
  function setTheme(dark) {
    document.documentElement.classList.toggle('dark', dark);
    $('[data-theme]').innerHTML = dark ? I.sun : I.moon;
    try { localStorage.setItem('ocr-theme', dark ? 'dark' : 'light'); } catch (e) {}
  }
  $('[data-theme]').addEventListener('click', () =>
    setTheme(!document.documentElement.classList.contains('dark')));

  // ---- 단일 선택 그룹 ----
  function group(sel, cls) {
    $$(sel).forEach(el => el.addEventListener('click', e => {
      e.preventDefault();
      $$(sel).forEach(x => x.classList.remove(cls));
      el.classList.add(cls);
    }));
  }
  group('[data-uptab]', 'is-on');
  group('[data-model]', 'sel');
  $$('[data-opt]').forEach(o => o.addEventListener('click', () => o.classList.toggle('on')));
  $$('[data-cc]').forEach(c => c.addEventListener('click', e => { e.preventDefault(); c.classList.toggle('on'); }));
  $$('[data-check]').forEach(c => c.addEventListener('click', e => { e.preventDefault(); c.classList.toggle('is-on'); }));
  $('#accHead').addEventListener('click', () => $('#acc').classList.toggle('open'));

  // ---- 탭: Configuration / Results, 하위 탭 ----
  const subbar = $('[data-subbar]');
  function showPanel(name) {
    $$('.panel').forEach(p => p.classList.toggle('is-on', p.dataset.panel === name));
  }
  $$('[data-rtab]').forEach(t => t.addEventListener('click', () => {
    $$('[data-rtab]').forEach(x => x.classList.remove('is-on'));
    t.classList.add('is-on');
    const isCfg = t.dataset.rtab === 'config';
    subbar.style.display = isCfg ? 'none' : '';
    if (isCfg) showPanel('config');
    else { const cur = subbar.querySelector('[data-sub].is-on'); showPanel(cur ? cur.dataset.sub : 'blocks'); }
  }));
  $$('[data-sub]').forEach(t => t.addEventListener('click', () => {
    $$('[data-sub]').forEach(x => x.classList.remove('is-on'));
    t.classList.add('is-on');
    showPanel(t.dataset.sub);
  }));

  // ---- 파일 선택 / 드래그 ----
  let picked = null;
  const dz = $('#dz'), input = $('#fileInput'), dzText = $('#dzText');
  function setFile(f) { picked = f; dzText.textContent = f ? f.name : 'Drag a file here'; }
  $('#browseBtn').addEventListener('click', e => { e.stopPropagation(); input.click(); });
  dz.addEventListener('click', () => input.click());
  input.addEventListener('change', () => setFile(input.files[0] || null));
  ['dragover', 'dragenter'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add('drag'); }));
  ['dragleave', 'drop'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove('drag'); }));
  dz.addEventListener('drop', e => { if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); });

  // ---- 토스트 ----
  const toast = $('#toast');
  function showToast(msg, isErr) {
    toast.textContent = msg;
    toast.classList.toggle('err', !!isErr);
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2600);
  }

  // ---- 최소 마크다운 렌더러 (Rendered 탭용) ----
  function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function renderMarkdown(md) {
    const lines = md.split('\n');
    let html = '', i = 0;
    while (i < lines.length) {
      const ln = lines[i];
      const h = ln.match(/^(#{1,4})\s+(.*)/);
      if (h) { const lv = h[1].length; html += `<h${lv} style="color:var(--ink);margin:.6em 0 .3em">${esc(h[2])}</h${lv}>`; i++; continue; }
      if (/^\s*\|.*\|\s*$/.test(ln)) {  // 표 블록
        const tbl = [];
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) { tbl.push(lines[i]); i++; }
        const rows = tbl.filter(r => !/^\s*\|[\s:|-]+\|\s*$/.test(r))
          .map(r => r.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim()));
        if (rows.length) {
          html += '<table style="border-collapse:collapse;width:100%;margin:.6em 0">';
          rows.forEach((r, ri) => {
            html += '<tr>' + r.map(c =>
              `<${ri === 0 ? 'th' : 'td'} style="border:1px solid var(--hairline);padding:6px 10px;text-align:left">${c}</${ri === 0 ? 'th' : 'td'}>`).join('') + '</tr>';
          });
          html += '</table>';
        }
        continue;
      }
      if (/^>\s?/.test(ln)) { html += `<blockquote style="border-left:3px solid var(--primary);margin:.4em 0;padding-left:12px;color:var(--muted)">${esc(ln.replace(/^>\s?/, ''))}</blockquote>`; i++; continue; }
      if (ln.trim() === '') { i++; continue; }
      if (ln.trim() === '---') { html += '<hr style="border:0;border-top:1px solid var(--hairline);margin:1em 0">'; i++; continue; }
      html += `<p style="margin:.4em 0">${esc(ln)}</p>`; i++;
    }
    return html;
  }

  function modelToUseLlm() {
    const sel = $('[data-model].sel');
    return sel && sel.dataset.model === 'accurate';  // Accurate만 LLM 맥락 단계
  }

  // ---- Run: 실제 변환 호출 ----
  const run = $('#runBtn');
  run.addEventListener('click', async () => {
    if (run.classList.contains('is-running')) return;
    if (!picked) { showToast('먼저 문서를 올려주세요', true); return; }

    run.classList.add('is-running');
    const ico = run.querySelector('.ico'), lbl = run.querySelector('.lbl'), o = ico.innerHTML;
    ico.innerHTML = '<span class="spin"></span>'; lbl.textContent = 'Running…';

    try {
      const fd = new FormData();
      fd.append('file', picked);
      fd.append('use_llm', modelToUseLlm() ? 'true' : 'false');
      const res = await fetch('/api/convert', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '변환 실패');

      $('#mdRaw').textContent = data.markdown;
      $('#jsonRaw').textContent = data.json;
      $('#rendered').innerHTML = renderMarkdown(data.markdown);
      $('#emptyBlocks').style.display = 'none';
      $('#blocksTag').style.display = '';
      $('#blocksCard').style.display = '';

      // Results 탭으로 전환
      $$('[data-rtab]').forEach(x => x.classList.remove('is-on'));
      $('[data-rtab="results"]').classList.add('is-on');
      subbar.style.display = '';
      showPanel('blocks');
      showToast(`변환 완료 · ${data.elements} 요소`);
    } catch (err) {
      showToast(String(err.message || err), true);
    } finally {
      run.classList.remove('is-running'); ico.innerHTML = o; lbl.textContent = 'Run';
    }
  });

  // ---- 초기 테마 ----
  let dark = false; try { dark = localStorage.getItem('ocr-theme') === 'dark'; } catch (e) {}
  setTheme(dark);
})();
