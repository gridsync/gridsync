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
