/**
 * Colorblind Mode Initialization
 * Applies saved colorblind mode preference on page load before rendering
 */

(function() {
    // Check localStorage for saved colorblind mode preference
    // dcc.Store with storage_type='local' uses the store id as the key
    const savedColorblindMode = localStorage.getItem('colorblind-mode-store');

    // Apply colorblind mode immediately if it was previously enabled
    // The value is stored as JSON by dcc.Store, so it might be 'true' or 'false' as strings
    if (savedColorblindMode === 'true' || savedColorblindMode === '"true"' || savedColorblindMode === true) {
        document.body.classList.add('colorblind-mode');
    }

    // Listen for storage events from other tabs/windows
    // NOTE: This only syncs the CSS class (toggle button appearance).
    // Charts won't re-render in other tabs because the dcc.Store state
    // is not updated here. For full sync, the user must refresh the other tabs.
    window.addEventListener('storage', function(e) {
        if (e.key === 'colorblind-mode-store') {
            const newValue = e.newValue;
            if (newValue === 'true' || newValue === '"true"' || newValue === true) {
                document.body.classList.add('colorblind-mode');
            } else {
                document.body.classList.remove('colorblind-mode');
            }
        }
    });
})();
