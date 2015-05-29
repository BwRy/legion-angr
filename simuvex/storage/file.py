from ..plugins.plugin import SimStatePlugin

import logging
l = logging.getLogger("simuvex.storage.file")

# TODO: symbolic file positions
import itertools
file_counter = itertools.count()

class Flags: # pylint: disable=W0232,
    O_RDONLY = 0
    O_WRTONLY = 1
    O_RDWR = 2
    O_APPEND = 4096
    O_ASYNC = 64
    O_CLOEXEC = 512
    # TODO mode for this flag
    O_CREAT = 256
    O_DIRECT = 262144
    O_DIRECTORY = 2097152
    O_EXCL = 2048
    O_LARGEFILE = 1048576
    O_NOATIME = 16777216
    O_NOCTTY = 1024
    O_NOFOLLOW = 4194304
    O_NONBLOCK = 8192
    O_NODELAY = 8192
    O_SYNC = 67174400
    O_TRUNC = 1024


class SimFile(SimStatePlugin):
    # Creates a SimFile
    def __init__(self, fd, name, mode, content=None):
        SimStatePlugin.__init__(self)
        self.fd = fd
        self.pos = 0
        self.name = name
        self.mode = mode
        self.content = SimSymbolicMemory(memory_id="file_%d_%d" % (fd, file_counter.next())) if content is None else content

        # TODO: handle symbolic names, special cases for stdin/out/err
        # TODO: read content for existing files

    def set_state(self, state):
        SimStatePlugin.set_state(self, state)
        self.content.set_state(state)

    # Reads some data from the current position of the file.
    def read(self, length, pos=None):
        if pos is None:
            print self.pos, length
            load_data = self.content.load(self.pos, length)
            self.pos += self.content._deps_unpack(length)[0]
        else:
            print pos, length
            load_data = self.content.load(pos, length)

        return load_data

    # Writes some data to the current position of the file.
    def write(self, content, length, pos=None):
        # TODO: error handling
        # TODO: symbolic length?
        if pos is None:
            self.content.store(self.pos, content)
            self.pos += self.content._deps_unpack(length)[0]

        else:
            self.content.store(pos, content)
        return length

    # Seeks to a position in the file.
    def seek(self, where):
        self.pos = where

    # Copies the SimFile object.
    def copy(self):
        c = SimFile(self.fd, self.name, self.mode, self.content.copy())
        c.pos = self.pos
        return c

    def all_bytes(self):
        indexes = self.content.mem.keys()
        if len(indexes) == 0:
            raise SimFileError('no content in file %s' % self.fd)

        min_idx = min(indexes)
        max_idx = max(indexes)
        buff = [ ]
        for i in range(min_idx, max_idx+1):
            buff.append(self.content.load(i, 1))
        return self.state.se.Concat(*buff)

    # Merges the SimFile object with others
    def merge(self, others, merge_flag, flag_values):
        all_files = list(others) + [ self ]
        if len(set(o.fd for o in all_files)) > 1:
            raise SimMergeError("files have different FDs")

        if len(set(o.pos for o in all_files)) > 1:
            l.warning("Cheap HACK to support multiple file positions in a merge.")
            # self.pos = max(o.pos for o in all_files)
            # max cannot be used as file positions might be symbolic.
            max_pos = None
            for o in all_files:
                if max_pos is not None:
                    comp = self.state.se.simplify(max_pos >= o.pos)
                    if self.state.se.symbolic(comp):
                        import ipdb; ipdb.set_trace()
                        raise SimMergeError("merging file positions with symbolic max position is not ye supported (TODO)")

                    max_pos = o.pos if self.state.se.is_false(comp) else max_pos
                else:
                    max_pos = o.pos
            self.pos = max_pos

        #if len(set(o.name for o in all_files)) > 1:
        #   raise SimMergeError("merging file names is not yet supported (TODO)")

        #if len(set(o.mode for o in all_files)) > 1:
        #   raise SimMergeError("merging modes is not yet supported (TODO)")

        return self.content.merge([ o.content for o in others ], merge_flag, flag_values)

from ..plugins.symbolic_memory import SimSymbolicMemory
from ..s_errors import SimMergeError, SimFileError
