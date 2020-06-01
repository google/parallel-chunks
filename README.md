<!--
SPDX-FileCopyrightText: 2020 Google LLC

SPDX-License-Identifier: Apache-2.0
-->

Parallel chunks

This is not an officially supported Google product.

Contains working useful code examples in multiple programming languages to
employ multiple threads to efficiently hash, compress/decompress, encrypt data.

For a number of years, there existed a number of useful commandline unix tools
that would process standard input or a single file, and provide information
about that file on standard output. These usually happen to be single threaded.

These days, having multiple cores in a system is the norm, even in sub $1 CPUs.
It has become reasonable to expect credit card sized computers costing less than
$50 to come with several gigabytes of ram, and multi gigabit io interfaces, and
to be able to run general purpose operating systems.

These good old, standard, unix command-line tools have not changed much, yet,
however, we at least have concurrency primitives available in a number of
programming languages that make utilizing multiple threads for such a thing
simple looking, albeit sometimes tricky.

Here's a number of simple example programs in several languages that demonstrate
how these primitives can be used to partially re-implement (in spirit) some of
the functionality offered by these widely spread standard utilities.
