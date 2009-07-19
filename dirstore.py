# dirstore - generic access to archive formats
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""This module provides a generic object (DirStore) to access files
stored in a directory, tar, rar, or zip archive. You can read
data from the archive as a string or a file-like object without
worrying about the underlying archive format.

It also provides a MetaStore object which contains multiple
DirStores, but acts as a single one. When a name is requested
from a MetaStore it returns the first object it finds in its
stores with that name.

It supports the following formats:
 (This information is inaccurate if dirstore is not currently in use)
"""

import os
import stat
import fnmatch
import exceptions

try: import cStringIO as StringIO
except ImportError: import StringIO

# Trick borrowed from Peter Norvig's Python IAQ:
# http://www.norvig.com/python-iaq.html
def _abstract():
    import inspect
    caller = inspect.getouterframes(inspect.currentframe())[1][3]
    raise NotImplementedError(caller + ' must be implemented in subclass')

# Defines available formats. The first is a predicate function that
# returns True if the second, a constructor, should be used.
FORMATS = []

# TODO:
# - A function that extracts a file and writes it to somewhere else.

version = '0.1.0'
__author__ = 'Joe Wreschnig <piman@sacredchao.net>'
__revision__ = "$Id: dirstore.py 32 2004-05-29 06:07:17Z piman $"
__license__ = "GNU GPL v2"

def require(ver):
    """You can use this function to require a specific version of the
dirstore module, e.g. dirstore.require("0.1.0") requires at least version
0.1.0. You don't need to specify trailing zeros, so the above example is
equivalent to dirstore.require("0.1").

If the dirstore module is not recent enough, an ImportError will be
raised."""
    if ver.split(".") > version.split("."):
        raise ImportError("you need at least dirstore %s to run this (you have %s)" % (ver, version))

class DirStoreError(exceptions.RuntimeError):
    """All exceptions specific to DirStores will be subclasses of this
type of exception."""
    pass

class UnknownStoreType(DirStoreError):
    """This exception is raised when you try to open an unsupported file
type as a DirStore."""

    def __init__(self, filename):
        DirStoreError.__init__(self)
        self.__filename = filename

    def __str__(self):
        return "%s is of an unknown/unsupported file type" % self.__filename

class WrongStoreError(DirStoreError):
    """This exception is raised when you pass a FileInfo object to
a DirStore, and that FileInfo did not originally come from that
DirStore."""

class InvalidStore(DirStoreError):
    """This exception is raised when something in a DirStore cannot be
opened properly. It differs from UnknownStoreType, in that if this
exception is raised, the file's type was (possibly incorrectly)
detected, but could not actually be read."""
    pass

class FileInfo(object):
    """FileInfo objects are the return type of the [] and info methods
of DirStores. They contain two important member, name and size.
name is the name of the object within whatever store it came from;
size is the (uncompressed) size of the object in bytes. If the size
could not be determined, this is -1."""

    def __init__(self, **kwargs):
        self.__dict__.update({ "size": -1 })
        self.__dict__.update(kwargs)

    def open(self):
        """Return a file-like object containing the contents
of this entry in the store.

store.info(name).open() is equivalent to store.open(name)."""
        return self._store.open(self.name)

    def read(self):
        """Return a string containing the contents
of this entry in the store.

store.info(name).read() is equivalent to store.read(name)."""
        return self._store.read(self.name)

class MetaStore(object):
    """A metastore is an object that acts like a single store, but is
actually a store of stores. It supports all the methods of a
DirStore, which apply to the first store with the given name found
in it.

It also supports additional methods for accessing the stores in it.
In particular, it supports the [], pop, remove, insert, append, and
extend operations just like a list does. It also supports slicing.

Note that iterating through a MetaStore returns the members of all of
its stores, not the stores themselves.

MetaStores do not have ZipFile compatibility methods."""
    def __init__(self, stores = []):
        """Initialize a metastore. The list of stores can a string (valid
for the DirStore constructor), or any DirStore-like object."""

        # Convert strings to stores.
        self.__stores = [(((str(s) == s) and DirStore(s)) or s)
                         for s in stores]

    def __iter__(self): return iter([self.info(name) for name in self.ls()])
    def append(self, store):  self.__stores.append(store)
    def extend(self, stores): self.__stores.extend(stores)
    def __getitem__(self, i): return self.__stores[i]
    def __delitem__(self, i): del(self.__stores[i])
    def __setitem__(self, i, store): self.__stores[i] = store
    def __delslice__(self, i, j): del(self.__stores[i:j])
    def __getslice__(self, i, j): return self.__stores[i:j]
    def __setslice__(self, i, j, y): self.__stores[i:j] = y
    def pop(self, index = -1): return self.__stores.pop(index)
    def remove(self, value): self.__stores.remove(value)
    def insert(self, i, store): self.__stores.insert(i, store)

    def verify(self):
        ret = DirStore.OK
        for store in self.__stores:
            v = store.verify()
            if v == DirStore.BAD: return DirStore.BAD
            elif v == DirStore.UNKNOWN: ret = DirStore.UNKNOWN
        return ret

    def ls(self, glob = None):
        names = []
        for store in self.__stores: names.extend(store.ls(glob))
        # only include each name once
        names = list(dict(map(None, names, [])).keys())
        names.sort()
        return names

    def read(self, name):
        return self.find(name).read(name)

    def open(self, name):
        return self.find(name).open(name)

    def info(self, name):
        return self.find(name).info(name)

    def info_all(self, name):
        """Returns FileInfo objects for every object with the given
name, in every store."""
        return [s.info(name) for s in self.find_all(name)]

    def find(self, name):
        """Find the first store with the given name in it."""
        for store in self.__stores:
            if name in store: return store
        else: raise ValueError("%s not found in any contained store" % name)

    def find_all(self, name):
        """Like find, but returns all stores with the given name in them."""
        stores = []
        for store in self.__stores:
            if name in store: stores.append(store)
        return stores

# This store is an abstract type. It should be subclassed by types
# that implement its abstract functions.
#
# Certain functions are given some default implementations. These are
# defined in terms of other functions that must be implemented, and
# are usually not the most efficient way to do it. So, you should
# override them if at all possible.
class DirStore(object):
    """This is the basic store type. Certain other types of stores
subclass this, and when you instantiate this, you will actually get
one of its subclasses. However, you shouldn't instantiate the
subclasses directly.

Aliases exist to provide compatibility with ZipFile and TarFileCompat:
  getinfo  -> info
  namelist -> ls
  testzip  -> verify
  read     -> read

close, infolist, printdir, write, and writestr have no equivalents.
 """

    # Return codes for DirStore.verify.
    BAD, OK, UNKNOWN = range(3)

    def __new__(cls, filename):
        """Use this to create a DirStore, e.g. 'DirStore("foo/bar.zip").
This will return an instance of one of DirStore's child classes;
which exact one doesn't matter. You shouldn't instantiate these
classes directly, since their names might change in the future,
or the way in which they are instantiated. Using
isinstance(some_store, DirStore) will always be true, however.

All stores have one public member, self.name, which is the name
the store was created with.

All the functions in a store that can take a name, can also take
a FileInfo object from that store.

If you request a name that is not in the store, a ValueError will
be raised."""

        if (cls == DirStore):
            for pred, Ctr in FORMATS:
                if pred(filename): return Ctr(filename)
            raise UnknownStoreType(filename)
        else:
            return super(DirStore, cls).__new__(cls)
    
    def __init__(self, filename):
        self.name = os.path.abspath(filename)
        self.getinfo = self.info
        self.namelist = self.ls
        self.testzip = self.verify

    def _read(self, name): _abstract()
    def _info(self, name): _abstract()
    def _ls(self): _abstract()

    def ls(self, glob = None):
        """Return a list of names available within the store. Any
names in 'subdirectories' will be returned as something
like 'dir/name'.

The optional glob argument is a string to filter results on (via
Python's fnmatch module)."""
        if glob is None: return self._ls()
        else: return fnmatch.filter(self._ls(), glob)

    def info(self, name):
        """Return a FileInfo object describing the member of the store
with the given name."""
        if name not in self:
            raise ValueError("%s is not in this store" % name)
        try:
            if name._store is self: return self._info(name.name)
            else: raise WrongStoreError("%s is not from %s" % (name, self))
        except AttributeError: return self._info(name)

    def read(self, name):
        """Read the data in the member with the given name and return
it as a string."""
        if name not in self:
            raise ValueError("%s is not in this store" % name)
        try:
            if name._store is self: return self._read(name.name)
            else: raise WrongStoreError("%s is not from %s" % (name, self))
        except AttributeError: return self._read(name)

    def verify(self):
        """Verify the integrity of the archive. Returns zero when
the archive is known to be bad; non-zero otherwise. Possible
return values are currently DirStore.BAD, DirStore.OK, and
DirStore.UNKNOWN."""
        return DirStore.UNKNOWN

    def __iter__(self):
        """DirStores are iteraterable objects. The member names are
given in succession, as FileInfo objects."""
        return iter([self.info(name) for name in self.ls()])

    def __contains__(self, name):
        try:
            if name._store is self: return (name.name in self.ls())
            else: return False
        except AttributeError:
            return (name in self.ls())

    def __getitem__(self, name):
        """Equivalent to DirStore.info, you can access members by
store[name], giving a FileInfo object."""
        return self.info(name)

    def open(self, name):
        """Return a file-like object containing the data in the
given member."""
        if name not in self:
            raise ValueError("%s is not in this store" % name)
        try:
            if name._store is self: return self._open(name.name)
            else: raise WrongStoreError("%s is not from %s" % (name, self))
        except AttributeError: return self._open(name)

    def _open(self, name):
        return StringIO.StringIO(self.read(name))

def _visit(arg, dirname, names):
    ns, selfname = arg
    for name in names:
        fname = os.path.join(dirname, name)
        if os.path.isfile(fname):
            ns.append(fname[len(selfname) + 1:])

class _FSStore(DirStore):
    def verify(self):
        if os.path.isdir(self.name): return DirStore.OK
        else: return DirStore.BAD

    def _ls(self):
        try:
            return self._namelist
        except AttributeError:
            names = []
            os.path.walk(self.name, _visit, (names, self.name))
            self._namelist = names
            return self._namelist

    def _open(self, name):
        name = os.path.join(self.name, name)
        return file(name, "rb")

    def _info(self, name):
        fullname = os.path.join(self.name, name)
        st = os.stat(fullname)
        return FileInfo(name = name, size = st[stat.ST_SIZE], _store = self)

    def _read(self, name):
        name = os.path.join(self.name, name)
        return file(name).read()
    
__doc__ += " - Directories in a local filesystem hierarchy. (Enabled)\n"
FORMATS.append((os.path.isdir, _FSStore))

try:
    __doc__ += " - ZIP compressed archives. "
    import zipfile

    class _ZipStore(DirStore):
        def __init__(self, filename):
            DirStore.__init__(self, filename)
            self.__zip = zipfile.ZipFile(filename)

        def verify(self):
            if self.__zip.testzip() is None: return DirStore.OK
            else: return DirStore.BAD

        def _info(self, name):
            inf = self.__zip.getinfo(name)
            return FileInfo(name = inf.filename, size = inf.file_size,
                            _store = self)

        def _ls(self): return self.__zip.namelist()

        def _read(self, name):
            return self.__zip.read(name)

    __doc__ += "(Enabled)\n"
    FORMATS.append(((lambda x: os.path.isfile(x) and zipfile.is_zipfile(x)),
                    _ZipStore))
except ImportError: __doc__ += "(Disabled)\n"

try:
    __doc__ += " - Tar compressed archives (gzip or bzip2). "
    import tarfile

    class _TarStore(DirStore):
        def __init__(self, filename):
            DirStore.__init__(self, filename)
            try:
                self.__tar = tarfile.TarFile.open(filename)
            except tarfile.ReadError:
                raise InvalidStore("%s could not be read" % filename)
            except tarfile.CompressionError:
                raise InvalidStore("%s could not be decompressed" % filename)

        def _ls(self): return self.__tar.getnames()

        def _info(self, name):
            return FileInfo(name = name, _store = self)

        def _open(self, name):
            return self.__tar.extractfile(name)

        def _read(self, name):
            return self.__tar.extractfile(name).read()

    __doc__ += "(Enabled)\n"
    FORMATS.append(((lambda x: os.path.isfile(x) and tarfile.is_tarfile(x)),
                    _TarStore))
except ImportError: __doc__ += "(Disabled)\n"

try:
    __doc__ += " - RAR archives. "

    if os.name != "posix": raise ImportError

    for path in os.environ["PATH"].split(os.pathsep):
         if os.path.isfile(os.path.join(path, 'unrar')):
             break
    else: raise ImportError

    class _RarStore(DirStore):
        def __init__(self, filename):
            DirStore.__init__(self, filename)
            fls = os.popen2(["unrar", "vb", "-c-", filename])[1].readlines()
            self.__files = [name.strip() for name in fls]

        def _ls(self): return list(self.__files)
        def _info(self, name):
            return FileInfo(name = name, _store = self)

        def _read(self, name):
            f = os.popen2(["unrar", "p", "-c-", "-inul",
                           self.name, name])[1]
            return f.read()

        def _open(self, name):
            return os.popen2(["unrar", "p", "-c-", "-inul",
                              self.name, name])[1]

    __doc__ += """(Enabled)
    Note that RAR support comes via your unrar binary and popen,
    and so can be very fragile. The RAR format is not recommended."""
    FORMATS.append((lambda s:os.path.isfile(s) and s.lower().endswith(".rar"),
                    _RarStore))
except ImportError: __doc__ += "(Disabled)\n"
