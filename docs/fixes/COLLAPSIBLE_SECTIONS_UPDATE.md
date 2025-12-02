# Collapsible Dashboard Sections Update

**Date:** December 2, 2025  
**Status:** ✅ Complete

## Problem

The dashboard landing page had three major sections (RHEL Regression Analysis, Competitive Performance, and Cloud Scaling) that were always fully expanded, taking up significant screen space and making it difficult to focus on specific areas of interest.

## Solution

Made all three major sections of the dashboard landing page collapsible with the following features:

### 1. **Collapsible Section Headers**
Each section now has a clickable header button that toggles the visibility of its content:
- **RHEL Regression Analysis** (📊)
- **Competitive Performance** (📈)
- **Cloud Scaling** (☁️)

### 2. **Visual Indicators**
- Chevron icons (▼/▶) indicate whether a section is expanded or collapsed
- Icons animate when toggling between states
- Each section maintains its distinctive color scheme:
  - RHEL: Blue (#1e3a8a)
  - Competitive: Cyan (#0e7490)
  - Cloud: Green (#047857)

### 3. **Default State**
All sections start in the expanded state (`is_open=True`) so users see all content on initial page load.

## Implementation Details

### Code Changes

**File:** `app.py`

#### 1. Updated `create_overview_layout()` function (lines 230-395)

Wrapped each section's CardHeader with a Button component that contains:
- Chevron icon with dynamic ID
- Section emoji and title
- Consistent styling and color scheme

Each section's CardBody is now wrapped in a `dbc.Collapse` component with:
- Unique ID for the collapse state
- `is_open=True` as the default state

#### 2. Added Three New Callbacks (lines 488-527)

Created dedicated callbacks for each section:

```python
@app.callback(
    [Output('collapse-section-rhel', 'is_open'),
     Output('icon-section-rhel', 'className')],
    Input('btn-toggle-section-rhel', 'n_clicks'),
    State('collapse-section-rhel', 'is_open'),
    prevent_initial_call=True
)
def toggle_section_rhel(n_clicks, is_open):
    """Toggle RHEL Regression Analysis section."""
    new_state = not is_open
    icon_class = "bi bi-chevron-down me-2" if new_state else "bi bi-chevron-right me-2"
    return new_state, icon_class
```

Similar callbacks for:
- `toggle_section_competitive()` - Competitive Performance
- `toggle_section_cloud()` - Cloud Scaling

Each callback:
- Toggles the collapse state
- Updates the chevron icon direction
- Uses `prevent_initial_call=True` to avoid unnecessary initial triggers

### Component IDs Created

**Sections:**
- `collapse-section-rhel` - RHEL Regression Analysis collapse container
- `collapse-section-competitive` - Competitive Performance collapse container
- `collapse-section-cloud` - Cloud Scaling collapse container

**Buttons:**
- `btn-toggle-section-rhel` - Toggle button for RHEL section
- `btn-toggle-section-competitive` - Toggle button for Competitive section
- `btn-toggle-section-cloud` - Toggle button for Cloud section

**Icons:**
- `icon-section-rhel` - Chevron icon for RHEL section
- `icon-section-competitive` - Chevron icon for Competitive section
- `icon-section-cloud` - Chevron icon for Cloud section

## User Experience

### Before
- All three sections always visible
- Required significant scrolling to see all content
- Harder to focus on specific analyses

### After
- Users can collapse sections they're not currently reviewing
- Reduced scrolling required
- Better focus on relevant analysis
- Visual feedback with animated chevrons
- All sections start expanded by default (no change to initial view)

## Testing

✅ All sections start in expanded state  
✅ Clicking headers toggles visibility  
✅ Chevron icons update correctly (▼ when open, ▶ when closed)  
✅ Subsections within RHEL Regression Analysis still collapsible  
✅ No impact on data loading or analysis callbacks  
✅ Styling and colors maintained consistently

## Related Components

The RHEL Regression Analysis section already contained three collapsible subsections:
- Compare Latest Major Releases (9.X vs 10.X)
- Compare RHEL 9.X Versions (Sequential)
- Compare RHEL 10.X Versions (Sequential)

These subsections remain fully functional within the now-collapsible parent section.

## Benefits

1. **Improved Navigation:** Users can quickly collapse sections they're not interested in
2. **Better Focus:** Easier to concentrate on one analysis at a time
3. **Reduced Clutter:** Less visual noise when reviewing specific metrics
4. **Consistent UX:** Matches the existing collapsible pattern used in subsections
5. **No Performance Impact:** Collapsing doesn't affect data loading or processing

## Notes

- The implementation follows the existing pattern established by the Advanced Filters collapse
- Bootstrap Icons are used for chevrons (bi-chevron-down, bi-chevron-right)
- Each section maintains its unique color scheme and styling
- The feature is purely cosmetic and doesn't affect any data or analysis functionality

---

**Implementation verified and tested successfully.**

