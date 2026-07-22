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

    // Cross-tab synchronization is NOT implemented.
    //
    // Each browser tab maintains independent colorblind mode state.
    // The dcc.Store component is tab-local (not shared across tabs).
    //
    // This is an intentional design choice (as of commit 8916e95) to:
    // 1. Avoid complex store synchronization logic
    // 2. Prevent race conditions between tabs
    // 3. Maintain simple, predictable behavior
    //
    // Users can toggle colorblind mode independently in each tab.
    //
    // Historical context: Previous implementations attempted cross-tab sync via
    // localStorage events, but this created inconsistent state where the toggle
    // indicator appeared updated but charts remained in the old mode until refresh.
    // The storage event could update CSS classes but not the dcc.Store that drives
    // chart re-renders. Full sync would require Dash anti-patterns (bypassing
    // callbacks) or polling overhead (dcc.Interval).
})();
