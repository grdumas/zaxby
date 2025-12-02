# Quick Start Guide - New Dashboard

## Launch the Dashboard

```bash
cd /home/gdumas/src/zaxby
source venv/bin/activate
python app.py
```

Open browser: **http://127.0.0.1:8050**

## The Landing Page

You'll see three main sections answering these questions:

### 📊 Question 1: Did RHEL regress between OS versions?

- **Heatmap**: Each cell shows % change between OS versions
  - 🟩 Green = improvement or stable
  - 🟥 Red = regression
  - ⬜ Gray = no significant change
- **Action**: Click any red cell to investigate

### 🏆 Question 2: How does RHEL compare to peer OSes?

- **Bar Chart**: Shows RHEL vs Ubuntu, SLES, etc.
- **Baseline**: RHEL = 100%
- **Green zone**: 90-110% (competitive range)

### 📈 Question 3: How does RHEL scale across cloud instances?

- **Dropdowns**: Select cloud provider + OS version
- **Line Chart**: Shows scaling across instance sizes
- **Reference Line**: Ideal linear scaling

## Common Tasks

### Investigate a Regression

1. Look at Question 1 heatmap
2. Find a red cell (regression)
3. **Click the cell**
4. See detailed comparison, timeline, and test data
5. Click "← Back to Overview" to return

### Filter Data

1. Click **"Advanced Filters"** button (top right)
2. Select OS versions, instance types, benchmarks, etc.
3. All three questions update automatically
4. Click **"Reset Filters"** to clear

### Compare Different Setups

1. Scroll to Question 3
2. Change **Cloud Provider** dropdown (AWS/Azure/GCP)
3. Change **OS Version** dropdown
4. Chart updates showing scaling for that config

### Change Date Range

1. Use date picker in header (top right)
2. Select start and end dates
3. Dashboard refreshes with filtered date range

## Understanding the Results

### Status Icons

- ✅ **Green checkmark**: All good, no issues
- ⚠️ **Warning**: Minor issues (1-2 regressions)
- 🔴 **Red circle**: Significant issues (3+ regressions)

### Benchmark Categories

Tests are grouped by type:
- **Networking**: uperf
- **Storage/IO**: fio
- **HPC/Compute**: streams, specjbb, auto_hpl
- **System**: sysbench, coremark_pro, pig, etc.

### Summary Text

Each question card includes a text summary:
- Number of issues detected
- Top 3 most significant findings
- Actionable insights

## Tips

✨ **For Quick Check-ins**: Just read the three summaries
🔍 **For Deep Dives**: Click cells and use advanced filters
📸 **For Reports**: Take screenshots of any card
⚙️ **For Power Users**: Use advanced filters panel

## Troubleshooting

**Dashboard not loading?**
- Check that port 8050 is available
- Verify virtual environment is activated
- Look for errors in terminal

**No data showing?**
- Check date range filter
- Verify filters aren't too restrictive
- Click "Reset Filters" button

**Heatmap click not working?**
- Click directly on the colored cell
- Ensure you're not clicking the border
- Try clicking the center of the cell

## Need More Help?

- **Full documentation**: See `DASHBOARD_REDESIGN.md`
- **Technical details**: See `IMPLEMENTATION_SUMMARY.md`
- **Original project docs**: See `PROJECT_BRIEF.md`

## Rollback to Old Dashboard

If you prefer the old version:

```bash
mv app.py app_redesigned.py
mv app_old_backup.py app.py
python app.py
```

