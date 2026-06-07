// Site-wide behaviors for the redesign. Each feature guards on element existence
// so this single file is safe to load on every page.

(function () {
    'use strict';

    // ---------- Reading progress bar ----------
    var progressBar = document.getElementById('progress-bar');
    if (progressBar) {
        var progressTicking = false;
        window.addEventListener('scroll', function () {
            if (progressTicking) return;
            progressTicking = true;
            window.requestAnimationFrame(function () {
                var totalHeight = document.documentElement.scrollHeight - window.innerHeight;
                var progress = totalHeight > 0 ? (window.pageYOffset / totalHeight) * 100 : 0;
                progressBar.style.width = progress + '%';
                progressTicking = false;
            });
        }, { passive: true });
    }

    // ---------- Nav: subtle fade on scroll ----------
    var nav = document.getElementById('site-nav');
    if (nav) {
        window.addEventListener('scroll', function () {
            nav.classList.toggle('opacity-90', window.scrollY > 50);
        }, { passive: true });
    }

    // ---------- Nav: mobile menu toggle ----------
    var navToggle = document.getElementById('nav-toggle');
    var navMobile = document.getElementById('nav-mobile');
    if (navToggle && navMobile) {
        navToggle.addEventListener('click', function () {
            var isOpen = navMobile.classList.toggle('flex');
            navMobile.classList.toggle('hidden', !isOpen);
            navToggle.setAttribute('aria-expanded', String(isOpen));
            document.getElementById('nav-icon-open').classList.toggle('hidden', isOpen);
            document.getElementById('nav-icon-close').classList.toggle('hidden', !isOpen);
        });
    }

    // ---------- Scroll-to-top button ----------
    var scrollTop = document.getElementById('scroll-top');
    if (scrollTop) {
        window.addEventListener('scroll', function () {
            var visible = window.scrollY > 400;
            scrollTop.classList.toggle('opacity-0', !visible);
            scrollTop.classList.toggle('pointer-events-none', !visible);
        }, { passive: true });
        scrollTop.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // ---------- TOC: floating popover vs. static fallback ----------
    var tocTriggers = document.querySelectorAll('.toc-trigger');
    var lightToc = document.getElementById('light-toc');
    if (tocTriggers.length || lightToc) {
        var floatingSupported = CSS.supports('interpolate-size: allow-keywords');
        tocTriggers.forEach(function (el) {
            el.style.display = floatingSupported ? 'flex' : 'none';
        });
        if (lightToc) {
            lightToc.style.display = floatingSupported ? 'none' : 'block';
        }
    }

    // ---------- Homepage / archive: category filter + search ----------
    var grid = document.getElementById('article-grid');
    if (grid) {
        var tabs = Array.prototype.slice.call(document.querySelectorAll('.filter-tab'));
        var searchInput = document.getElementById('article-search');
        var noResults = document.getElementById('no-results');
        var cards = Array.prototype.slice.call(grid.querySelectorAll('article'));

        var ACTIVE_TAB = 'filter-tab text-white border-b-2 border-indigo-500 pb-2 px-1 font-semibold transition-colors';
        var INACTIVE_TAB = 'filter-tab text-slate-500 hover:text-slate-300 pb-2 px-1 transition-colors';

        var state = { filter: '', query: '' };

        var applyFilters = function () {
            var visibleCount = 0;
            cards.forEach(function (card) {
                var categories = (card.dataset.categories || '').split(',');
                var haystack = (card.dataset.title || '') + ' ' + (card.dataset.description || '');
                var matchesFilter = !state.filter || categories.indexOf(state.filter) !== -1;
                var matchesQuery = !state.query || haystack.indexOf(state.query) !== -1;
                var show = matchesFilter && matchesQuery;
                card.classList.toggle('hidden', !show);
                if (show) visibleCount++;
            });
            if (noResults) {
                noResults.classList.toggle('hidden', visibleCount > 0);
            }
        };

        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                state.filter = tab.dataset.filter || '';
                tabs.forEach(function (t) {
                    t.className = t === tab ? ACTIVE_TAB : INACTIVE_TAB;
                });
                applyFilters();
            });
        });

        if (searchInput) {
            var debounce;
            searchInput.addEventListener('input', function () {
                clearTimeout(debounce);
                debounce = setTimeout(function () {
                    state.query = searchInput.value.trim().toLowerCase();
                    applyFilters();
                }, 150);
            });
        }
    }
})();
