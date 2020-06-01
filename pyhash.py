#!/usr/bin/env python3
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Prints sha256 hashes of chunks of a file from the command line.

Chunks are at most 8M in size (last chunk can be smaller). Chunks are hashed
using separate threads (number of threads depends on the number on CPUs).

Performance will depend almost entirely on the ability of the filesystem to
read a file sequentially in large blocks, or on the ability of python to hash
large blocks efficiently.

On most operating systems, Python will defer sha256 checksum computation to
openssl that contains multiple very optimized implementations of the sha256
algorithm, and will opportunistically use whatever specialized cpu instructions
are available to it to perform this computation as quickly as possible.

Computing hashes at rates of multiple gygabytes per second on a laptop using
this code is not unheard of.
"""

import contextlib
import hashlib
import io
import multiprocessing
import queue
import sys
import threading
from concurrent import futures
from typing import TYPE_CHECKING, List, Optional, Tuple

_result = Tuple[int, bytes]
if TYPE_CHECKING:
    _result_queue = queue.Queue[Optional[futures.Future[_result]]]
else:
    _result_queue = queue.Queue


_CHUNK_SIZE = 8 << 20  # size in bytes: 8MiB


def compute_hash(buf: bytes) -> _result:
    """Uses all the cpu :)

    According to documentation this should end up releasing the GIL,
    so that we get to use more threads.

    Attributes:
      buf: data to hash, immutable - so there's hope in zerocopy here.
    Returns:
      block size and digest
    """
    h = hashlib.sha256()
    h.update(buf)
    return len(buf), h.digest()


def read_file(
    f: io.RawIOBase,
    executor: futures.Executor,
    q: _result_queue,
    stop_reading: threading.Event,
):
    try:
        while not stop_reading.is_set():
            # make a bytearray and try very hard to fill it.
            buf = memoryview(bytearray(_CHUNK_SIZE))
            ntotal: int = 0
            nread: int = 1
            while nread > 0:
                # As of 2020-06-01: typeshed wrongly claims we can't
                # `readinto(memoryview)`, so we disable type checking.
                nread = f.readinto(buf[ntotal:]) or 0  # type: ignore
                ntotal += nread
            if ntotal == 0:  # end of file when we can't fill any
                return
            q.put(executor.submit(compute_hash, buf[:ntotal]))
    finally:
        q.put(None)  # signal end of queue to the printer


def print_hashes(q: _result_queue):
    total_size = 0
    while True:
        hash_future = q.get()
        if hash_future is None:  # end of queue
            break
        length, hash = hash_future.result()  # type int, bytes
        print("offset: {}, hash: {}".format(total_size, hash.hex()))
        total_size += length
    print(f"Total size: {total_size}")


def main(args: List[str]):
    if len(args) != 1:
        print("Usage: ./pyhash.py <filename>")
    filename = args[0]

    with contextlib.ExitStack() as stack:
        f = open(filename, "rb", buffering=0)
        stack.callback(f.close)

        q: _result_queue
        q = queue.Queue(maxsize=max(50, multiprocessing.cpu_count() * 2))

        cpus = multiprocessing.cpu_count()
        executor = futures.ThreadPoolExecutor(max_workers=cpus)
        stack.callback(executor.shutdown)

        stop_reading = threading.Event()

        # start filling the queue with eagerly evaluated futures.
        reader_t = threading.Thread(
            target=read_file, args=(f, executor, q, stop_reading)
        )
        reader_t.start()

        @stack.callback
        def stop_and_join_reader():
            stop_reading.set()
            try:
                while True:
                    q.get(block=False)
            except queue.Empty:
                pass  # we've emptied the queue
            reader_t.join()

        print_hashes(q)


if __name__ == "__main__":
    sys.exit(main(args=sys.argv[1:]))
