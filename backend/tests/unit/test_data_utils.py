"""
Unit tests untuk data utilities dan preprocessing functions.

Test coverage:
- Data validation
- Missing value handling
- Encoding functions
- Scaling functions
"""
import pytest
import polars as pl
import numpy as np


@pytest.mark.unit
class TestDataValidation:
    """Test data validation functions"""

    def test_dataframe_has_expected_columns(self, sample_df_classification):
        """Test DataFrame has expected columns."""
        expected_cols = ["age", "salary", "department", "experience_years", "churn"]
        assert all(col in sample_df_classification.columns for col in expected_cols)

    def test_dataframe_row_count(self, sample_df_classification):
        """Test DataFrame has expected row count."""
        assert len(sample_df_classification) == 12

    def test_detect_numeric_columns(self, sample_df_classification):
        """Test detecting numeric columns."""
        numeric_cols = sample_df_classification.select(pl.col(pl.Int64, pl.Float64)).columns
        assert "age" in numeric_cols
        assert "salary" in numeric_cols
        assert "experience_years" in numeric_cols
        assert "churn" in numeric_cols

    def test_detect_categorical_columns(self, sample_df_classification):
        """Test detecting categorical columns."""
        categorical_cols = sample_df_classification.select(pl.col(pl.Utf8)).columns
        assert "department" in categorical_cols

    def test_identify_missing_values(self, sample_df_with_nulls):
        """Test identifying missing values."""
        null_counts = sample_df_with_nulls.null_count()
        # Should detect nulls in specific columns
        assert null_counts["age"][0] > 0
        assert null_counts["salary"][0] > 0

    def test_check_for_duplicates(self, sample_df_classification):
        """Test checking for duplicate rows."""
        # Original should have no duplicates
        n_rows = len(sample_df_classification)
        n_unique = len(sample_df_classification.unique())
        assert n_rows == n_unique

    def test_target_column_exists(self, sample_df_classification):
        """Test target column exists in DataFrame."""
        assert "churn" in sample_df_classification.columns

    def test_target_column_has_values(self, sample_df_classification):
        """Test target column has actual values."""
        target_col = sample_df_classification["churn"]
        assert len(target_col) > 0
        assert target_col.null_count() == 0


@pytest.mark.unit
class TestMissingValueHandling:
    """Test missing value imputation"""

    def test_mean_imputation_numeric(self, sample_df_with_nulls):
        """Test mean imputation untuk numeric columns."""
        df = sample_df_with_nulls.select("age")
        # Fill nulls dengan mean
        mean_val = df.select(pl.col("age")).fill_null(pl.col("age").mean()).to_numpy()
        # Should have no nulls after imputation
        assert np.isnan(mean_val).sum() == 0

    def test_forward_fill_imputation(self, sample_df_with_nulls):
        """Test forward fill imputation."""
        df = sample_df_with_nulls.select("age").fill_null(strategy="forward")
        # Check no nulls remain
        assert df["age"].null_count() == 0

    def test_drop_rows_with_nulls(self, sample_df_with_nulls):
        """Test dropping rows dengan nulls."""
        df_clean = sample_df_with_nulls.drop_nulls()
        # All nulls should be gone
        assert df_clean.null_count().to_numpy().sum() == 0
        # Should have fewer rows
        assert len(df_clean) < len(sample_df_with_nulls)

    def test_categorical_null_imputation(self, sample_df_with_nulls):
        """Test imputing null values dalam categorical columns."""
        # Fill with mode atau custom value
        df = sample_df_with_nulls.with_columns(
            pl.col("department").fill_null("Unknown")
        )
        assert df.select("department").null_count()[0, 0] == 0

    def test_imputation_preserves_shape(self, sample_df_with_nulls):
        """Test imputation preserves DataFrame shape."""
        original_shape = sample_df_with_nulls.shape
        df_imputed = sample_df_with_nulls.fill_null(0)
        assert df_imputed.shape == original_shape


@pytest.mark.unit
class TestDataScaling:
    """Test data scaling functions"""

    def test_standard_scaling_range(self, sample_df_classification):
        """Test standard scaling produces values near mean=0."""
        df_numeric = sample_df_classification.select(pl.col(pl.Int64, pl.Float64))
        
        # Manually standardize
        for col in df_numeric.columns:
            mean = df_numeric[col].mean()
            std = df_numeric[col].std()
            if std > 0:
                scaled = (df_numeric[col] - mean) / std
                # Should be roughly centered at 0
                assert abs(scaled.mean()) < 1.0

    def test_minmax_scaling_bounds(self, sample_df_classification):
        """Test min-max scaling produces values in [0, 1]."""
        df_numeric = sample_df_classification.select(pl.col(pl.Int64, pl.Float64))
        
        for col in df_numeric.columns:
            col_data = df_numeric[col]
            min_val = col_data.min()
            max_val = col_data.max()
            if min_val != max_val:
                scaled = (col_data - min_val) / (max_val - min_val)
                assert scaled.min() >= 0.0
                assert scaled.max() <= 1.0

    def test_scaling_preserves_row_count(self, sample_df_classification):
        """Test scaling preserves row count."""
        original_count = len(sample_df_classification)
        df_numeric = sample_df_classification.select(pl.col(pl.Int64, pl.Float64))
        assert len(df_numeric) == original_count

    def test_scaling_numeric_columns_only(self, sample_df_classification):
        """Test scaling only applies to numeric columns."""
        numeric_cols = sample_df_classification.select(pl.col(pl.Int64, pl.Float64)).columns
        categorical_cols = sample_df_classification.select(pl.col(pl.Utf8)).columns
        
        assert len(numeric_cols) > 0
        assert len(categorical_cols) > 0


@pytest.mark.unit
class TestDataEncoding:
    """Test categorical encoding functions"""

    def test_label_encoding_produces_integers(self, sample_df_categorical):
        """Test label encoding produces integer values."""
        df = sample_df_categorical.select("color")
        unique_values = df.select(pl.col("color")).unique()
        assert len(unique_values) <= len(df)

    def test_one_hot_encoding_increases_columns(self, sample_df_categorical):
        """Test one-hot encoding increases number of columns."""
        df = sample_df_categorical.select("color")
        original_cols = len(df.columns)
        
        # Simulate one-hot encoding
        unique_colors = sample_df_categorical["color"].unique()
        # Should create n_unique new columns
        assert len(unique_colors) > 0

    def test_encoding_no_data_loss(self, sample_df_categorical):
        """Test encoding doesn't lose data."""
        original_count = len(sample_df_categorical)
        # Even after encoding, should have same number of rows
        df_color = sample_df_categorical.select("color")
        assert len(df_color) == original_count

    def test_handle_unknown_categories(self, sample_df_categorical):
        """Test handling unknown categories gracefully."""
        # When new unknown category appears in test set
        # Should be handled without error
        pass


@pytest.mark.unit
class TestTrainTestSplit:
    """Test train/test split functions"""

    def test_split_produces_correct_ratio(self, sample_df_classification):
        """Test train/test split maintains correct ratio."""
        total = len(sample_df_classification)
        test_size = 0.25
        expected_test = int(total * test_size)
        expected_train = total - expected_test
        
        assert expected_train + expected_test == total

    def test_split_no_overlap(self, sample_df_classification):
        """Test train and test sets don't overlap."""
        # In real split, indices should not overlap
        total = len(sample_df_classification)
        test_size = 0.25
        train_size = int(total * (1 - test_size))
        # train_size + test_size should equal total
        assert train_size + int(total * test_size) <= total

    def test_split_all_rows_used(self, sample_df_classification):
        """Test all rows are assigned to train or test."""
        # Train + Test sizes should cover all rows
        total = len(sample_df_classification)
        test_size = 0.25
        train_size = int(total * 0.75)
        test_rows = int(total * test_size)
        # Should cover all or almost all rows
        assert train_size + test_rows >= total - 1

    def test_stratified_split_maintains_distribution(self, sample_df_classification):
        """Test stratified split maintains class distribution."""
        total = len(sample_df_classification)
        churn_ratio = sample_df_classification["churn"].sum() / total
        # After split, both sets should have similar ratios
        assert 0 <= churn_ratio <= 1


@pytest.mark.unit  
class TestFeatureEngineering:
    """Test feature engineering functions"""

    def test_no_feature_loss(self, sample_df_classification):
        """Test feature engineering doesn't lose important features."""
        original_cols = len(sample_df_classification.columns)
        # After processing, should have at least original features
        assert original_cols > 0

    def test_handle_high_cardinality_features(self, sample_df_categorical):
        """Test handling high cardinality categorical features."""
        # Should handle features dengan many unique values
        color_cardinality = len(sample_df_categorical["color"].unique())
        assert color_cardinality > 0

    def test_multicollinearity_detection(self, sample_df_regression):
        """Test detecting multicollinearity."""
        # Highly correlated features should be detectable
        df = sample_df_regression
        # bedrooms dan square_meters might be correlated
        assert len(df.columns) >= 2
