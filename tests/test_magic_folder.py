from gridsync.magic_folder import MagicFolderMonitor

status_messages = [
    {"state": {"folders": {}, "synchronizing": False}},
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {"queued-at": 1636315601.769834, "relpath": "Empty"}
                    ],
                    "recent": [],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.769834,
                            "started-at": 1636315601.782498,
                            "relpath": "Empty",
                        }
                    ],
                    "recent": [],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.785104,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "queued-at": 1636315601.769834,
                            "started-at": 1636315601.782498,
                            "relpath": "Empty",
                        },
                    ],
                    "recent": [],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.803485,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "queued-at": 1636315601.785104,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "queued-at": 1636315601.769834,
                            "started-at": 1636315601.782498,
                            "relpath": "Empty",
                        },
                    ],
                    "recent": [],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.826877,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "queued-at": 1636315601.803485,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "queued-at": 1636315601.785104,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "queued-at": 1636315601.769834,
                            "started-at": 1636315601.782498,
                            "relpath": "Empty",
                        },
                    ],
                    "recent": [],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.850005,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "queued-at": 1636315601.826877,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "queued-at": 1636315601.803485,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "queued-at": 1636315601.785104,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "queued-at": 1636315601.769834,
                            "started-at": 1636315601.782498,
                            "relpath": "Empty",
                        },
                    ],
                    "recent": [],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.869304,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "queued-at": 1636315601.826877,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "queued-at": 1636315601.803485,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "queued-at": 1636315601.785104,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "queued-at": 1636315601.769834,
                            "started-at": 1636315601.782498,
                            "relpath": "Empty",
                        },
                    ],
                    "recent": [],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "queued-at": 1636315601.826877,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "queued-at": 1636315601.803485,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "queued-at": 1636315601.785104,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "queued-at": 1636315601.769834,
                            "started-at": 1636315601.782498,
                            "relpath": "Empty",
                        },
                    ],
                    "recent": [],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "queued-at": 1636315601.826877,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "queued-at": 1636315601.803485,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "queued-at": 1636315601.785104,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "queued-at": 1636315601.769834,
                            "started-at": 1636315601.782498,
                            "relpath": "Empty",
                        },
                    ],
                    "recent": [],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "queued-at": 1636315601.826877,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "queued-at": 1636315601.803485,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "queued-at": 1636315601.785104,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "queued-at": 1636315601.769834,
                            "started-at": 1636315601.782498,
                            "relpath": "Empty",
                        },
                    ],
                    "recent": [],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "queued-at": 1636315601.826877,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "queued-at": 1636315601.803485,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "queued-at": 1636315601.785104,
                            "started-at": 1636315602.663326,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "queued-at": 1636315601.769834,
                            "started-at": 1636315601.782498,
                            "relpath": "Empty",
                        },
                    ],
                    "recent": [],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "queued-at": 1636315601.826877,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "queued-at": 1636315601.803485,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "queued-at": 1636315601.785104,
                            "started-at": 1636315602.663326,
                            "relpath": "Garfield.jpg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        }
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "queued-at": 1636315601.826877,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "queued-at": 1636315601.803485,
                            "started-at": 1636315604.323327,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "queued-at": 1636315601.785104,
                            "started-at": 1636315602.663326,
                            "relpath": "Garfield.jpg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        }
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "queued-at": 1636315601.826877,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "queued-at": 1636315601.803485,
                            "started-at": 1636315604.323327,
                            "relpath": "lolcat.jpg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "queued-at": 1636315601.826877,
                            "started-at": 1636315605.855326,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "queued-at": 1636315601.803485,
                            "started-at": 1636315604.323327,
                            "relpath": "lolcat.jpg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "queued-at": 1636315601.826877,
                            "started-at": 1636315605.855326,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315605,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "started-at": 1636315607.096851,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "queued-at": 1636315601.826877,
                            "started-at": 1636315605.855326,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315605,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "started-at": 1636315607.096851,
                            "relpath": "Colonel Meow.jpg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315607,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315605,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "started-at": 1636315608.447307,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "queued-at": 1636315601.850005,
                            "started-at": 1636315607.096851,
                            "relpath": "Colonel Meow.jpg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315607,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315605,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "started-at": 1636315608.447307,
                            "relpath": "subdir/Nala.jpg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315608,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315607,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315605,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "started-at": 1636315609.67621,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "queued-at": 1636315601.869304,
                            "started-at": 1636315608.447307,
                            "relpath": "subdir/Nala.jpg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315608,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315607,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315605,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "started-at": 1636315609.67621,
                            "relpath": "subdir/Venus.jpg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315609,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315608,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315607,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315605,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "started-at": 1636315611.165948,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "queued-at": 1636315601.886723,
                            "started-at": 1636315609.67621,
                            "relpath": "subdir/Venus.jpg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315609,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315608,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315607,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315605,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "started-at": 1636315611.165948,
                            "relpath": "Waffles.jpg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315611,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315609,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315608,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315607,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315605,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "started-at": 1636315613.018086,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "queued-at": 1636315601.90681,
                            "started-at": 1636315611.165948,
                            "relpath": "Waffles.jpg",
                        },
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315611,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315609,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315608,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315607,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315605,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [
                        {
                            "queued-at": 1636315601.937953,
                            "started-at": 1636315613.018086,
                            "relpath": "Grumpy Cat.jpg",
                        }
                    ],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315613,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315611,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315609,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315608,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315607,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315605,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": True,
        }
    },
    {
        "state": {
            "folders": {
                "Cat Pics": {
                    "downloads": [],
                    "errors": [],
                    "uploads": [],
                    "recent": [
                        {
                            "conflicted": False,
                            "modified": 1634410734,
                            "last-updated": 1636315614,
                            "relpath": "Grumpy Cat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315613,
                            "relpath": "Waffles.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315611,
                            "relpath": "subdir/Venus.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315609,
                            "relpath": "subdir/Nala.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315608,
                            "relpath": "Colonel Meow.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315607,
                            "relpath": "Cheshire Cat.jpeg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1634226039,
                            "last-updated": 1636315605,
                            "relpath": "lolcat.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636314737,
                            "last-updated": 1636315604,
                            "relpath": "Garfield.jpg",
                        },
                        {
                            "conflicted": False,
                            "modified": 1636315559,
                            "last-updated": 1636315602,
                            "relpath": "Empty",
                        },
                    ],
                }
            },
            "synchronizing": False,
        }
    },
]


def test_compare_operations():
    monitor = MagicFolderMonitor(None)
    for msg in status_messages:
        state = msg.get("state")
        monitor.compare_operations(state, monitor._prev_state)
        monitor._prev_state = state
        # XXX
