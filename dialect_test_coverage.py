import csv
import os
import re
from typing import Optional, List


REGEX_THAT_CAN_HANDLE_WHITESPACE = """(AddFunction(Agg|Real|Int)?([1234])?\([\s]*(?:Expression::|TS)(?:\(")?(\w+)(?:"\))?[\s\S(?!(\);))]+?\);)"""

REGEX_FOR_EXPRESSION_FUNCTIONS = """AddFunction(Agg|Real|Int)?([1234])?\((?:Expression::|TS)(?:\(")?(\w+)(?:"\))?.*\);"""
REGEX_FOR_FILE_PARSER = """([A-Za-z\_]+)(?:\((.+)\))"""
REGEX_FOR_FLOAT = """[0-9]+\.[0-9]+"""
REGEX_FOR_INT = """[0-9^\.]+"""


def dialect_file_parser(path_to_file):
    """
    Generates a list of test cases from expression test setup files.

    The function walks a given directory, takes any `*Dialect.cpp` files
     in it, and parses each file to extract Functions and Agg Function.
     The plain functions that it parses are those that take 1-4 arguments.

    :param path_to_file: str
    :return: List[Dict]
    """
    output = []
    new_output = []

    with open(path_to_file, 'r', encoding='latin-1') as infile:  # encoding is latin-1 bc not all files are utf-8
        text = infile.read()
        regex_to_match = re.compile(REGEX_THAT_CAN_HANDLE_WHITESPACE)
        for match in regex_to_match.finditer(text):
            output.append(match)

    for f in output:
        line, arg_type, num_args, fun = f.groups()

        if arg_type and num_args:
            # Takes care of AddFunctionReal[1-n] and AddFunctionInt[1-n] defs that have no arguments
            # explicit argument definitions.
            new_output.append(
                {
                    'function': fun,
                    'arguments': tuple(arg_type.lower() for num in range(int(num_args))),
                    'tested': False,
                    'skipped': False,
                }
            )
        elif num_args:
            num_args = int(num_args)
            f_list = line.split(',')
            if 'true' in f_list[-1]:
                arguments = tuple(thing.strip().strip(';)').lstrip('T_').lstrip('Type_').lower() for thing in f_list[-(num_args+1):-1])
            else:
                arguments = tuple(thing.strip().strip(';)').lstrip('T_').lstrip('Type_').lower() for thing in f_list[-num_args::])
            new_output.append(
                {
                    'function': fun,
                    'arguments': arguments,
                    'tested': False,
                    'skipped': False,
                }
            )
        elif arg_type == 'Agg':
            f_list = line.split(',')
            if 'true' in f_list[-1]:
                arguments = (f_list[-2:-1][0].strip().strip(';)').lstrip('T_').lstrip('Type_').lower(), )
            else:
                arguments = (f_list[-1::][0].strip().strip(';)').lstrip('T_').lstrip('Type_').lower(), )
            new_output.append(
                {
                    'function': fun,
                    'arguments': arguments,
                    'tested': False,
                    'skipped': False,
                }
            )
        else:
            new_output.append(
                {
                    'function': fun,
                    'arguments': None,
                    'tested': False,
                    'skipped': False,
                }
            )

    return new_output


def setup_file_parser(base_dir, excluded_filenames=[], excluded_regexes=[], process_arguments=True):
    """
     A function to walk through setup.*.txt files and extract test cases.

    The test cases extracted are only those written in the format:
        FUNCTION(args)
    Test cases are captured by regex and return as dict of tuples
    that contain two elements:
        'name.of.test.file': (FUNCTION, (arg1, ...))
    Regex for test cases are in the format
        FUNCTION('arg1',[arg2],...)

        ([A-Z]+)(?:\((.+)\))
            ^           ^
            |           |
            group 1     group 2
        (fn name)   (fn arguments)

    excluded_filenames: List[str]
    excluded_regexes: List[re]
    """
    # import pdb; pdb.set_trace()
    setup_dict = {}
    errors = {}
    for path, directory, files in os.walk(base_dir):
        for filename in files:
            if filename.startswith('setup') and filename.endswith('.txt'):
                fullpath = os.path.join(path, filename)
                # TODO: redo the below with os.path.split()
                test_key = path.split('\\')[-1] + '.' + filename.replace('setup.', '').replace('.txt', '')
                try:
                    with open(fullpath, 'r', encoding='latin-1') as infile:
                        out = []
                        for line in infile:
                            output = re.match(REGEX_FOR_FILE_PARSER, line.strip())
                            if output:
                                out.append(output)  # I think this is where we should do the regex processing
                        temp = []
                        for case in out:
                             tuple(regex_line_splitter(case.groups()[1]))
                        if process_arguments:
                            setup_dict[test_key] = {
                                'tests': [
                                    (case.groups()[0].lower(),
                                    tuple(translate_argument(tr) for tr in regex_line_splitter(case.groups()[1])),
                                    )
                                    for case in out
                                ],
                                'skip': False,
                            }
                        else:
                            setup_dict[test_key] = {
                                'tests': [
                                    (case.groups()[0].lower(),
                                    tuple(tr for tr in regex_line_splitter(case.groups()[1])),
                                    )
                                    for case in out
                                ],
                                'skip': False,
                            }
                except Exception as e:
                    errors[fullpath] = str(e)

    if excluded_filenames:
        for e in excluded_filenames:
            if e in setup_dict.keys():
                setup_dict[e]['skip'] = True

    if excluded_regexes:
        for key in setup_dict.keys():
            if len(excluded_regexes) > 1:
                for r in excluded_regexes:
                    if re.match(r, key):
                        setup_dict[key]['skip'] = True
            else:
                if re.match(excluded_regexes[0], key):
                     setup_dict[key]['skip'] = True

    return setup_dict


def create_regex_for_excluded_tests(test_name):
    """
    Helper function to turn .ini exclusions with wildcards ('*')
    into regex that can correctly match those files.

    Regex used:
        .+\.<string>
    String processing used:
        Replace * with [\w]+

    Example of input and return value:
        'date.*.nulls' -> re.compile(r'.+date.[\w]+.nulls', re.UNICODE)
    """
    regex = ".+\." + test_name.replace('*', '[\w]+')
    return re.compile(regex)


def find_all_dialect_files(directory, ini_directory):
    """
    Finds *Dialect.cpp files and their related .ini file, returning the dialect & excluded tests.

    This function looks in `directory` for dialect files, and then looks in
    another `ini_directory` for .ini files to see if any expression tests
    are excluded for this dialect.

    Returns a tuple:
        (filename, [excluded tests])
    """
    for dir_name, sdlist, files in os.walk(directory):
        for file in files:
            if file.endswith('Dialect.cpp'):
                dialect_filename = file.split('Dialect')[0].lower() + '.ini'
                ini_file = os.path.join(ini_directory, dialect_filename)
                ini_file_exists = os.path.isfile(ini_file)
                if ini_file_exists:
                    with open(ini_file, 'r') as inifile:
                        for line in inifile:
                            if line.startswith('ExpressionExclusions_Standard'):
                                excluded_tests = [
                                    'standard.' + thing for thing in line.split()[-1].split(',')
                                ]
                else:
                    excluded_tests = []
        return (dialect_filename, excluded_tests)


def ini_file_parser(dialect_name, ini_directory):
    """
    Looks for the .ini file for a specified dialect and checks for excluded standard tests.

    The expected file name is `dialect_name.ini`.

    dialect_name: str
    ini_directory: str
    """
    dialect_ini_filename = dialect_name + '.ini'
    dialect_ini_file_path = os.path.join(ini_directory, dialect_ini_filename)
    ini_file_exists = os.path.isfile(dialect_ini_file_path)
    if ini_file_exists:
        with open(dialect_ini_file_path, 'r') as inifile:
            for line in inifile:
                if line.startswith('ExpressionExclusions_Standard'):
                    excluded_tests = [
                        'standard.' + thing for thing in line.split()[-1].split(',')
                    ]
    else:
        excluded_tests = []
    excluded_test_names = []
    excluded_test_regex = []
    for test in excluded_tests:
        if '*' in test:
            excluded_test_regex.append(create_regex_for_excluded_tests(test))
        else:
            excluded_test_names.append(test)
    return (dialect_name, excluded_test_names, excluded_test_regex)



def translate_argument(text_in):
    """
    Uses regular expressions to describe the content of function arguments.

    Currently this breaks a string into three groups:
        1. [ or ' or " or #
        2. letters in a string 1-15 chars long.
        3. digits with or without a decimal point and/or (-) sign.

    """
    regex = re.compile("(\[?\'?\"?#?)([a-zA-Z]{1,15})?([-?0-9\.]+)?([<>])?")
    out = re.match(regex, text_in)

    if out.groups()[0]:
        if out.groups()[0] is '[':
            if 'num' in out.groups()[1]:
                return 'real'
            else:
                return out.groups()[1]
        elif out.groups()[0] is "\'" or out.groups()[0] is "\"":
            return 'str'
        elif out.groups()[0] == '#':
            return 'date'
    elif out.groups()[1]:
        if out.groups()[3]:
            return 'bool'
        elif out.groups()[1] in ["CHAR", "str"]:
            return 'str'
        elif out.groups()[1] == 'int':
            return 'int'
        elif out.groups()[1] == 'num':
            return 'real'
        elif out.groups()[1].lower() in ('true', 'false'):
            return 'bool'
        else:
            return out.groups()[1].lower()
    elif out.groups()[2]:
        # there's some ugly code below to figure out if a number is an int or a float
        # type(out.groups()[2]) won't work bc re.match returns a string. So we have to
        # inspect the contents of that string.
        try:
            int(out.groups()[2])
            return 'int'
        except ValueError:
            pass
        try:
            float(out.groups()[2])
            return 'real'
        except ValueError:
            pass
    else:
        pass


def regex_line_splitter(text_in):
    """Breaks up a line of text using prescribed regex.

    Splits on:
        `', `
        `',`
        `<digit>+`,
        `), `
        `], `
        `<digit>, `
        `", "


    Arguments:
        text_in {str}
    """
    return re.split("""[\'\"], |\',|\d\+|\), |], |\d, ?""", text_in)


def create_dictionary_of_tested_and_skipped_cases(input_dict):
    """Iterates through a dictionary of file names and test cases to create a {test case: {tested, skipped}} dict.

    Arguments:
        input_dict {Dict[Dict['tests': List[tuple], 'skip': bool]]}
    """

    master_dict = {}

    for key in input_dict.keys():
        for value in input_dict[key]['tests']:
            if input_dict[key]['skip'] == True:
                if master_dict.get(value[0]):
                    if not value[1] in master_dict[value[0]]['skipped']:
                        master_dict[value[0]]['skipped'].append(value[1])
                else:
                    master_dict[value[0]] = {'tested': [], 'skipped': [value[1], ]}
            elif input_dict[key]['skip'] == False:
                if master_dict.get(value[0]):
                    if not value[1] in master_dict[value[0]]['tested']:
                        master_dict[value[0]]['tested'].append(value[1])
                else:
                    master_dict[value[0]] = {'tested': [value[1], ], 'skipped': []}

    return master_dict


def check_function_definitions_against_test_cases(test_cases, function_definitions):
    for f in function_definitions:
        if test_cases.get(f['function'].lower()):
            if f['arguments'] in test_cases[f['function'].lower()]['tested']:
                f['tested'] = True
                f['skipped'] = False
            elif (f['arguments'] in test_cases[f['function'].lower()]['skipped']) and not f['tested'] == True:
                    f['skipped'] = True
        else:
            pass

    return function_definitions


def dialect_file_coverage_checker(dialect_file_path, ini_directory, setup_file_path, output_dir=None):
    # TODO: When moving this into TDVT dir, can set ini_dir, setup_file_path as vars.
    # TODO: Take care of output_dir after moving into TDVT dir.

    # 1. Determine the name of the dialect being evaluated.
    dialect_name = os.path.split(dialect_file_path)[-1].split('Dialect')[0].lower()

    # 2a. find its ini file for skipped tests
    # 2b. process the skipped tests; generate regex if necessary. return two lists: str & regex.
    _, excluded_tests, excluded_regex = ini_file_parser(dialect_name, ini_directory)

    # 3. generate a list of dicts of functions defined in dialect file.
    dialect_defs = dialect_file_parser(dialect_file_path)

    # 4. go through the existing tests and filter out the ones that should be skipped
    all_test_cases = setup_file_parser(
        base_dir=setup_file_path,
        excluded_filenames=excluded_tests,
        excluded_regexes=excluded_regex,
    )

    # 5. Clean up the existing test case args so they can be compared to the dialect args.
    cleaned_test_cases = create_dictionary_of_tested_and_skipped_cases(all_test_cases)

    # 6. iterate through the dialect list of dicts and see if each exists in existing tests
    to_output = check_function_definitions_against_test_cases(cleaned_test_cases, dialect_defs)

    # 7. generate a csv file that shows coverage of each function defined in dialect file.
    if to_output:
        with open((dialect_name + '.csv'), 'w') as csv_file:
            keys = to_output[0].keys()
            fieldnames = ['function', 'arguments', 'tested', 'skipped']
            dict_writer = csv.DictWriter(csv_file, fieldnames)
            dict_writer.writeheader()
            dict_writer.writerows(to_output)
            return "Results written to " + output_dir
    else:
        print("No test cases for", dialect_name)


def extract_all_test_cases(input_directory, output_directory=None):
    """Finds all test setup files and extracts & organizes their cases.

    Arguments:
        whatever_input {string} -- Path to directory of setup files.
        output_directory {string} -- Path where csv should be saved.
    """
    setup_file_cases = setup_file_parser(input_directory, process_arguments=False)
    all_test_cases = create_dictionary_of_tested_and_skipped_cases(setup_file_cases)
    if all_test_cases:
        with open('all_test_cases.csv', 'w') as csv_file:
            keys = all_test_cases.keys()
            fieldnames = ['function', 'argument(s)']
            dict_writer = csv.writer(csv_file)
            dict_writer.writerow(['function', 'args'])
            for key in keys:
                for item in all_test_cases[key]['tested']:
                    dict_writer.writerow([key, item])
            return "CSV file written."
    return all_test_cases


if __name__ == '__main__':
    pass
