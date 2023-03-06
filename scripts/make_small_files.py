#!/usr/bin/env python3
import math
import random
from pathlib import Path
from hashlib import sha256

import click


# Description: Creates a lot of directories and small files to
# performance test GridSync/Magic Folder with.
# Author: Meejah
# Date: 2023-01-20


_hash = sha256("a random seed".encode("utf8"))


def random_file_segment():
    """
    A random filename segment for a directory or file
    """
    _hash.update("a".encode("utf8"))
    digest = _hash.hexdigest()
    return digest[:random.randrange(1, len(digest))]


def generate_directories(base, count):
    """
    A generator that creates a certain number of random
    directories-names below the base
    """
    # XXX would be nice to use hypothesis strategies to generate
    # stuff, but .. that's hard?
    for _ in range(count):
        seg = random_file_segment()
        yield base / seg


def generate_filename_segments(files):
    """
    Generate some number of random filename segments
    """
    for _ in range(files):
        yield random_file_segment()


def generate_local_paths(output, files, directories):
    """
    generator for a sequence of path names
    """
    dir_names = generate_directories(output, directories)
    file_names = generate_filename_segments(files)

    # since we need at least one file in each directory (because we
    # don't directly store directories) we place one of our files in
    # each subdir

    reusable_dirs = []

    for d in dir_names:
        reusable_dirs.append(d)
        f = next(file_names)
        d.mkdir()
        path = d / f
        yield path

    idx = 0
    for f in file_names:
        idx = (idx + 1) % len(reusable_dirs)
        yield reusable_dirs[idx] / f


@click.command()
@click.option(
    "--files",
    default=665,
    help="Number of files to put data in"
)
@click.option(
    "--directories",
    default=237,
    help="Number of folders to split data into"
)
@click.option(
    "--output",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    default="./small-test-case",
)
@click.option(
    "--size",
    default=3*1024*1024,
)
def small_files(files, directories, output, size):
    """
    small-files test-case creator
    """
    print(output)
    if directories > files:
        raise click.UsageError(
            "Must have more files than directories"
        )

    data_per_file = math.ceil(float(size) / files)

    with open("/dev/urandom", "rb") as urandom:

        def generate_data():
            # could introduce some variance...
            for _ in range(files):
                yield urandom.read(data_per_file)

        outp = Path(output)
        outp.mkdir()

        data = generate_data()

        for path in generate_local_paths(outp, files, directories):
            print(path)
            with path.open('wb') as output:
                output.write(next(data))


if __name__ == "__main__":
    small_files()

