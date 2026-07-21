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
    // Use strict normalization: only 'true' is considered enabled
    if (savedColorblindMode === 'true') {
        document.body.classList.add('colorblind-mode');
    }

    // Cross-tab sync is intentionally NOT implemented.
    // Reason: Syncing only the CSS class creates inconsistent state where the toggle
    // indicator appears updated but charts remain in the old mode until page refresh.
    // This is because:
    // 1. The storage event can update document.body.classList (CSS only)
    // 2. But it cannot directly update the dcc.Store which triggers chart re-renders
    // 3. Dash callbacks depend on colorblind-mode-store.data for chart updates
    //
    // Full cross-tab sync would require either:
    // - Updating the dcc.Store from the storage event (not recommended - bypasses Dash)
    // - Adding a dcc.Interval polling component (adds unnecessary overhead)
    //
    // Current behavior: Each tab maintains its own independent colorblind mode state.
    // Users must manually toggle in each tab, which is simple and predictable.
})();
