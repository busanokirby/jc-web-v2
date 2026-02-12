// Repairs autocomplete - Vanilla JS
(function(){
    const input = document.getElementById('repairs-search');
    const resultsEl = document.getElementById('repairs-search-results');
    if (!input || !resultsEl) return;

    let timer = null;
    let focusedIndex = -1;
    let lastResults = [];

    function debounce(fn, delay){
        return function(...args){
            clearTimeout(timer);
            timer = setTimeout(()=> fn.apply(this, args), delay);
        }
    }

    function clearResults(){
        resultsEl.innerHTML = '';
        resultsEl.style.display = 'none';
        focusedIndex = -1;
        lastResults = [];
    }

    function renderResults(items){
        resultsEl.innerHTML = '';
        if (!items || items.length === 0){
            clearResults();
            return;
        }
        items.forEach((it, idx) => {
            const a = document.createElement('a');
            a.className = 'list-group-item list-group-item-action';
            a.dataset.idx = idx;
            a.href = `/repairs/${it.id}`;
            a.innerHTML = `<div class="fw-bold">${it.ticket} &nbsp; <small class="text-muted">${it.customer || ''}</small></div><div class="small text-muted">${it.device || ''}</div>`;
            a.addEventListener('click', (e)=>{
                // Let the link navigate normally
                clearResults();
            });
            resultsEl.appendChild(a);
        });
        resultsEl.style.display = 'block';
        lastResults = items;
    }

    async function fetchResults(q){
        if (!q || q.length < 2){
            clearResults();
            return;
        }
        try {
            const url = `/repairs/search/api?q=${encodeURIComponent(q)}&limit=8`;
            const res = await fetch(url, {credentials: 'same-origin'});
            if (!res.ok){
                clearResults();
                return;
            }
            const data = await res.json();
            renderResults(data);
        } catch (err){
            console.error('Autocomplete error', err);
            clearResults();
        }
    }

    const debouncedFetch = debounce((ev)=> fetchResults(ev.target.value.trim()), 200);

    input.addEventListener('input', debouncedFetch);
    input.addEventListener('blur', ()=> setTimeout(clearResults, 150)); // allow click to register

    // Keyboard navigation
    input.addEventListener('keydown', (ev)=>{
        if (resultsEl.style.display === 'none') return;
        const items = resultsEl.querySelectorAll('.list-group-item');
        if (!items.length) return;
        if (ev.key === 'ArrowDown'){
            ev.preventDefault();
            focusedIndex = (focusedIndex + 1) % items.length;
            items[focusedIndex].focus();
        } else if (ev.key === 'ArrowUp'){
            ev.preventDefault();
            focusedIndex = (focusedIndex - 1 + items.length) % items.length;
            items[focusedIndex].focus();
        } else if (ev.key === 'Enter'){
            // If a result is focused, follow it
            const active = document.activeElement;
            if (active && active.classList.contains('list-group-item')){
                window.location = active.href;
            }
        }
    });
})();