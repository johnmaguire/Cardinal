import re


def strip_formatting(line):
    return re.sub("(?:\x03\d\d?,\d\d?|\x03\d\d?|[\x01-\x1f])", "", line)

