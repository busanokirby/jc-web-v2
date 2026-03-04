// Customers autocomplete - Vanilla JS
(function(){
    const input = document.getElementById('customers-search');
    const resultsEl = document.getElementById('customers-search-results');
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
            a.href = `/customers/${it.id}`;
            
            let displayText = `<div class="fw-bold">${it.name}`;
            if (it.business_name) {
                displayText += ` &nbsp; <small class="text-muted">${it.business_name}</small>`;
            }
            displayText += `</div>`;
            
            let subtext = '';
            if (it.phone) subtext += it.phone;
            if (it.email) {
                if (subtext) subtext += ' • ';
                subtext += it.email;
            }
            if (subtext) {
                displayText += `<div class="small text-muted">${subtext}</div>`;
            }
            
            a.innerHTML = displayText;
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
            const url = `/customers/search/api?q=${encodeURIComponent(q)}&limit=8`;
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
