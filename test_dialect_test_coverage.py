import pytest
from dialect_test_coverage import (
    translate_argument
)


class TestTranslateArgument:
    def test_all_lower_with_bracket_returns_text(self):
        assert translate_argument("[datetime") == 'datetime'

    def test_all_lower_with_single_quote_returns_str(self):
        assert translate_argument("'datetime'") == 'str'

    def test_all_lower_with_double_quote_returns_str(self):
        assert translate_argument("\"datetime\"") == "str"

    def test_all_lower_string_returns_itself(self):
        assert translate_argument("datetime") == "datetime"

    def test_function_call_returns_function_name(self):
        assert translate_argument("DATETIME([datetime0])") == "datetime"

    def test_str_of_int_converts_to_str(self):
        assert translate_argument("\"1234.\"") == 'str'

    def test_integer_converts_to_str_int(self):
        assert translate_argument("10") == 'int'

    def test_float_converts_to_str_float(self):
        assert translate_argument("1.5") == 'real'

    def test_real_converts_to_str_real(self):
        assert translate_argument("-7") == 'int'

    def test_bool_converts_to_str_bool(self):
        assert translate_argument('bool') == 'bool'

    def test_bool_variable_converts_to_str_bool(self):
        assert translate_argument("[bool1]") == 'bool'

    def test_bool_true_converts_to_str_bool(self):
        assert translate_argument('true') == 'bool'

    def test_bool_uppercase_false_converts_to_str_bool(self):
        assert translate_argument('False') == 'bool'

    def test_var_name_with_numeral_returns_only_var(self):
        assert translate_argument('[datetime2]') == 'datetime'

    def test_str_with_num_returns_str(self):
        assert translate_argument('str2') == 'str'


class TestCreateDictionaryOfTestAndSkippedCases:
    def test_dictionary_creates_correctly(self):
        pass


class TestRegexLineSplitter:
    def test_splits_three_strings_correctly(self):
        pass
