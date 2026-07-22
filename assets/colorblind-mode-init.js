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

    // Cross-tab synchronization behavior:
    //
    // - localStorage IS shared across all tabs (browser-level feature)
    // - dcc.Store state is NOT automatically synced across tabs (Dash limitation)
    //
    // What happens when toggling in one tab:
    // 1. localStorage updates immediately (visible to all tabs)
    // 2. CSS class applies immediately via callback (current tab only)
    // 3. Other tabs see the localStorage change but don't react to it
    // 4. Refreshing another tab picks up the new preference from localStorage
    //
    // This means: toggle appearance updates in current tab only, but the
    // preference persists for new tabs/refreshes. Charts don't re-render in
    // other open tabs until manual refresh.
    //
    // This is intentional (as of commit 8916e95) to avoid:
    // 1. Complex storage event listeners and cross-tab state management
    // 2. Race conditions when multiple tabs update simultaneously
    // 3. Partial updates (CSS syncs but charts don't re-render without
    //    triggering Dash callbacks, which would require anti-patterns)
    //
    // Full cross-tab sync would require storage events + forcing Dash to
    // re-run callbacks, breaking Dash's unidirectional data flow or adding
    // polling overhead (dcc.Interval). Current design is simpler and predictable.
})();
