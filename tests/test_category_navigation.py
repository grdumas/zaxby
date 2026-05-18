"""Tests for category navigation UI drill-down and breadcrumbs (P1-C)."""

from app import competitive_performance_breadcrumb, investigation_drill_breadcrumb


class TestCompetitivePerformanceBreadcrumb:
    """Tests for competitive performance category breadcrumb navigation."""

    def test_breadcrumb_structure(self):
        """Breadcrumb should have two levels: root and category."""
        bc = competitive_performance_breadcrumb("Networking")
        items = bc.items
        assert len(items) == 2
        assert items[0]["label"] == "Competitive Performance"
        assert items[1]["label"] == "Networking"

    def test_category_marked_active(self):
        """Category level should be marked as active in breadcrumb."""
        bc = competitive_performance_breadcrumb("Storage/IO")
        items = bc.items
        assert items[1].get("active") is True
        # Root should not be active
        assert items[0].get("active") is not True

    def test_all_categories(self):
        """Test breadcrumb for all known categories."""
        categories = ["Networking", "Storage/IO", "HPC/Compute", "System"]
        for category in categories:
            bc = competitive_performance_breadcrumb(category)
            items = bc.items
            assert len(items) == 2
            assert items[1]["label"] == category
            assert items[1].get("active") is True

    def test_other_category(self):
        """Test breadcrumb for 'Other' category (unmapped benchmarks)."""
        bc = competitive_performance_breadcrumb("Other")
        items = bc.items
        assert len(items) == 2
        assert items[0]["label"] == "Competitive Performance"
        assert items[1]["label"] == "Other"
        assert items[1].get("active") is True

    def test_breadcrumb_has_correct_styling(self):
        """Breadcrumb should have proper CSS classes."""
        bc = competitive_performance_breadcrumb("Networking")
        assert bc.className == "mb-0 bg-transparent py-0"


class TestInvestigationDrillBreadcrumb:
    """Tests for investigation drill-down breadcrumb navigation (category → leaf)."""

    def test_breadcrumb_three_levels(self):
        """Breadcrumb should have three levels: root, category, benchmark."""
        bc = investigation_drill_breadcrumb("Networking", "uperf")
        items = bc.items
        assert len(items) == 3
        assert items[0]["label"] == "RHEL Regression Analysis"
        assert items[1]["label"] == "Networking"
        assert items[2]["label"] == "uperf"

    def test_leaf_marked_active(self):
        """Leaf (benchmark) level should be marked as active."""
        bc = investigation_drill_breadcrumb("Storage/IO", "fio")
        items = bc.items
        assert items[2].get("active") is True
        # Root and category should not be active
        assert items[0].get("active") is not True
        assert items[1].get("active") is not True

    def test_all_category_to_leaf_paths(self):
        """Test breadcrumb for various category → benchmark paths."""
        test_cases = [
            ("Networking", "uperf"),
            ("Storage/IO", "fio"),
            ("HPC/Compute", "streams"),
            ("HPC/Compute", "auto_hpl"),
            ("System", "coremark"),
            ("System", "sysbench"),
        ]
        for category, benchmark in test_cases:
            bc = investigation_drill_breadcrumb(category, benchmark)
            items = bc.items
            assert len(items) == 3
            assert items[0]["label"] == "RHEL Regression Analysis"
            assert items[1]["label"] == category
            assert items[2]["label"] == benchmark
            assert items[2].get("active") is True

    def test_other_category_fallback(self):
        """Unmapped benchmarks should show 'Other' category in breadcrumb."""
        bc = investigation_drill_breadcrumb("Other", "unknown_benchmark")
        items = bc.items
        assert len(items) == 3
        assert items[1]["label"] == "Other"
        assert items[2]["label"] == "unknown_benchmark"
        assert items[2].get("active") is True

    def test_breadcrumb_has_correct_styling(self):
        """Breadcrumb should have proper CSS classes."""
        bc = investigation_drill_breadcrumb("Networking", "uperf")
        assert bc.className == "mb-2 bg-transparent py-0"

    def test_special_characters_in_benchmark_name(self):
        """Breadcrumb should handle special characters in benchmark names."""
        bc = investigation_drill_breadcrumb("System", "benchmark-with_special.chars")
        items = bc.items
        assert len(items) == 3
        assert items[2]["label"] == "benchmark-with_special.chars"


class TestCategoryNavigationFlow:
    """Tests for end-to-end category navigation flow."""

    def test_competitive_to_investigation_navigation_structure(self):
        """Verify navigation structure from competitive performance to investigation."""
        # Step 1: User views competitive performance category
        comp_bc = competitive_performance_breadcrumb("Networking")
        assert len(comp_bc.items) == 2

        # Step 2: User drills down to specific benchmark investigation
        inv_bc = investigation_drill_breadcrumb("Networking", "uperf")
        assert len(inv_bc.items) == 3
        # Category should match between views
        assert comp_bc.items[1]["label"] == inv_bc.items[1]["label"]

    def test_back_navigation_hierarchy(self):
        """Verify breadcrumb hierarchy supports back navigation."""
        bc = investigation_drill_breadcrumb("Storage/IO", "fio")
        items = bc.items

        # Should be able to navigate back through:
        # [2] fio (current/active)
        # [1] Storage/IO (parent category)
        # [0] RHEL Regression Analysis (root)
        assert items[2].get("active") is True  # Current page
        assert items[1].get("active") is not True  # Can navigate here
        assert items[0].get("active") is not True  # Can navigate here

    def test_empty_category_navigation(self):
        """Test navigation for categories that might have no benchmarks."""
        # This should still render correctly even if category is empty
        bc = competitive_performance_breadcrumb("EmptyCategory")
        items = bc.items
        assert len(items) == 2
        assert items[1]["label"] == "EmptyCategory"

    def test_single_benchmark_category_navigation(self):
        """Test navigation for categories with only one benchmark."""
        # Networking has only one benchmark: uperf
        bc = investigation_drill_breadcrumb("Networking", "uperf")
        items = bc.items
        assert len(items) == 3
        assert items[1]["label"] == "Networking"
        assert items[2]["label"] == "uperf"
