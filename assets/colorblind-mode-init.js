/**
 * Colorblind Mode Initialization
 * Applies saved colorblind mode preference on page load before rendering
 */

(function() {
    // Check localStorage for saved colorblind mode preference
    // dcc.Store with storage_type='local' uses the store id as the key
    const savedColorblindMode = localStorage.getItem('colorblind-mode-store');

    // Apply colorblind mode immediately if it was previously enabled
    // The value is stored as a string by dcc.Store with storage_type='local'
    if (savedColorblindMode === 'true') {
        document.body.classList.add('colorblind-mode');
    }

    // Cross-tab sync: Update body class when localStorage changes in another tab
    // LIMITATION: This only syncs the CSS class (toggle appearance), NOT the dcc.Store state.
    // Charts in background tabs will not re-render until the page is refreshed, because
    // Dash callbacks depend on colorblind-mode-store.data which we don't update here.
    // To achieve full cross-tab chart re-rendering, we would need to:
    // 1. Update the dcc.Store value in the storage event handler, OR
    // 2. Add a dcc.Interval that polls localStorage and writes to the store
    // Current behavior: Toggle indicator syncs, charts sync on next refresh.
    window.addEventListener('storage', function(e) {
        if (e.key === 'colorblind-mode-store') {
            if (e.newValue === 'true') {
                document.body.classList.add('colorblind-mode');
            } else {
                document.body.classList.remove('colorblind-mode');
            }
        }
    });
})();
