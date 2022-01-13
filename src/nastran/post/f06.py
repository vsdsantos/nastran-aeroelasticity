from nastran.post.flutter import parse_flutter_page, FlutterF06Page

PAGE_PARSING_FUNCTIONS = {
    'flutter': parse_flutter_page,
    'text': lambda ls: '\n'.join(ls)
}

FLUTTER_CHECK_LINE = 3


class F06Results:

    def __init__(self, pages=None):
        self.pages = pages

    def __repr__(self):
        return 'F06 Results with {} pages.'.format(len(self.pages))

    @property
    def flutter(self):
        return list(filter(lambda p: isinstance(p, FlutterF06Page), self.pages))


def read_f06(filename: str):
    with open(filename, 'r') as file:
        raw_lines = file.readlines()

    groups = _group_lines_by_page(raw_lines)

    pages = []

    for lines in groups:
        # TODO: Check Page Type and automatically send to function
        T = _check_page_type(lines)
        pages.append(PAGE_PARSING_FUNCTIONS[T](lines))

    return F06Results(pages)


def _check_page_type(lines):
    if len(lines)-1 >= FLUTTER_CHECK_LINE and 'FLUTTER  SUMMARY' in lines[FLUTTER_CHECK_LINE]:
        return 'flutter'
    else:
        return 'text'


def _group_lines_by_page(lines):
    groups = []
    group = []
    for i, line in enumerate(lines):
        if line[0] == '1' and len(group) > 0:
            groups.append(group)
            group = []
        group.append(line)
    return groups
