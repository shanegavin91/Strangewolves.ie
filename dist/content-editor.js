(() => {
  'use strict';
  const preview = new URLSearchParams(location.search).has('editor-preview') && parent !== window;
  const schema = fetch('./editor-schema.json').then(r => { if (!r.ok) throw Error('Schema unavailable'); return r.json(); });
  function apply(data, definition) {
    if (!data?.values) return;
    for (const f of definition.fields) {
      const value = data.values[f.id], node = document.querySelector(f.selector);
      if (!node || typeof value !== 'string') continue;
      if (f.kind === 'image') {
        if (!/^\.\/assets\/[a-zA-Z0-9._-]+$/.test(value) && !/^\.\/uploads\/[a-f0-9-]+\.(webp|png|jpg)$/.test(value)) continue;
        if (node.getAttribute('src') !== value) node.src = value;
        const gallery = node.closest('[data-gallery-src]');
        if (gallery) gallery.dataset.gallerySrc = value;
        if (node.closest('.course-poster')) node.closest('a').href = value;
      } else if (f.kind === 'alt') {
        node.alt=value;
        const gallery=node.closest('[data-gallery-src]');
        if(gallery)gallery.dataset.galleryAlt=value;
      } else if (node.textContent !== value) node.textContent = value;
    }
  }
  if (preview) {
    window.addEventListener('message', async event => {
      if (event.origin !== location.origin || event.source !== parent || event.data?.type !== 'wolves-preview') return;
      try { apply(event.data.content, await schema); } catch { /* The approved HTML remains visible. */ }
    });
    parent.postMessage({type:'wolves-preview-ready'},location.origin);
  } else {
    Promise.all([schema,fetch('./content/site.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('No published content');return r.json();})])
      .then(([definition,data])=>apply(data,definition)).catch(()=>{});
  }
})();
