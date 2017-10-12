# -*- coding: utf-8 -*-


def humanized_list(list_, kind='files'):
    if len(list_) == 1:
        return list_[0]
    elif len(list_) == 2:
        return " and ".join(list_)
    elif len(list_) == 3:
        return "{}, {}, and {}".format(*list_)
    return "{}, {}, and {} other {}".format(list_[0], list_[1],
                                            len(list_) - 2, kind)

def dehumanized_size(s):
    if not s:
        return 0
    elif not s[0].isdigit():
        raise ValueError("Prefix must be a digit (received '{}')".format(s))
    string = s.upper()
    if string.endswith('BYTES'):
        return int(s[:-5])
    suffixes = ('KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
    for i, suffix in enumerate(suffixes, start=1):
        if string.endswith(suffix):
            return int(float(s[:-2].strip()) * 1024 ** i)
    raise ValueError("Unknown suffix for '{}'".format(s))
