import platform, os, re
import subprocess
from mooseutils import colorText
from collections import namedtuple
import json
from tempfile import TemporaryFile
from timeit import default_timer as clock

TERM_COLS = 110

LIBMESH_OPTIONS = {
  'mesh_mode' :    { 're_option' : r'#define\s+LIBMESH_ENABLE_PARMESH\s+(\d+)',
                     'default'   : 'REPLICATED',
                     'options'   :
                       {
      'DISTRIBUTED' : '1',
      'REPLICATED'  : '0'
      }
                     },
  'unique_ids' :   { 're_option' : r'#define\s+LIBMESH_ENABLE_UNIQUE_ID\s+(\d+)',
                     'default'   : 'FALSE',
                     'options'   :
                       {
      'TRUE'  : '1',
      'FALSE' : '0'
      }
                     },
  'dtk' :          { 're_option' : r'#define\s+LIBMESH_TRILINOS_HAVE_DTK\s+(\d+)',
                     'default'   : 'FALSE',
                     'options'   :
                       {
      'TRUE'  : '1',
      'FALSE' : '0'
      }
                     },
  'boost' :        { 're_option' : r'#define\s+LIBMESH_HAVE_EXTERNAL_BOOST\s+(\d+)',
                     'default'   : 'FALSE',
                     'options'   :
                       {
      'TRUE'  : '1',
      'FALSE' : '0'
      }
                     },
  'vtk' :          { 're_option' : r'#define\s+LIBMESH_HAVE_VTK\s+(\d+)',
                     'default'   : 'FALSE',
                     'options'   :
                       {
      'TRUE'  : '1',
      'FALSE' : '0'
      }
                     },
  'tecplot' :      { 're_option' : r'#define\s+LIBMESH_HAVE_TECPLOT_API\s+(\d+)',
                     'default'   : 'FALSE',
                     'options'   :
                       {
      'TRUE'  : '1',
      'FALSE' : '0'
      }
                     },
  'petsc_major' :  { 're_option' : r'#define\s+LIBMESH_DETECTED_PETSC_VERSION_MAJOR\s+(\d+)',
                     'default'   : '1'
                   },
  'petsc_minor' :  { 're_option' : r'#define\s+LIBMESH_DETECTED_PETSC_VERSION_MINOR\s+(\d+)',
                     'default'   : '1'
                   },
  'petsc_version_release' :  { 're_option' : r'#define\s+LIBMESH_DETECTED_PETSC_VERSION_RELEASE\s+(\d+)',
                     'default'   : 'TRUE',
                     'options'   : {'TRUE'  : '1', 'FALSE' : '0'}
                   },
  'slepc_major' :  { 're_option' : r'#define\s+LIBMESH_DETECTED_SLEPC_VERSION_MAJOR\s+(\d+)',
                     'default'   : '1'
                   },
  'slepc_minor' :  { 're_option' : r'#define\s+LIBMESH_DETECTED_SLEPC_VERSION_MINOR\s+(\d+)',
                     'default'   : '1'
                   },
  'slepc_subminor' :  { 're_option' : r'#define\s+LIBMESH_DETECTED_SLEPC_VERSION_SUBMINOR\s+(\d+)',
                     'default'   : '1'
                   },
  'dof_id_bytes' : { 're_option' : r'#define\s+LIBMESH_DOF_ID_BYTES\s+(\d+)',
                     'default'   : '4'
                   },
  'petsc_debug'  : { 're_option' : r'#define\s+LIBMESH_PETSC_USE_DEBUG\s+(\d+)',
                     'default'   : 'FALSE',
                     'options'   : {'TRUE'  : '1', 'FALSE' : '0'}
                   },
  'curl' :         { 're_option' : r'#define\s+LIBMESH_HAVE_CURL\s+(\d+)',
                     'default'   : 'FALSE',
                     'options'   : {'TRUE' : '1', 'FALSE' : '0'}
                   },
  'tbb' :          { 're_option' : r'#define\s+LIBMESH_HAVE_TBB_API\s+(\d+)',
                     'default'   : 'FALSE',
                     'options'   : {'TRUE' : '1', 'FALSE' : '0'}
                   },
  'superlu' :      { 're_option' : r'#define\s+LIBMESH_PETSC_HAVE_SUPERLU_DIST\s+(\d+)',
                     'default'   : 'FALSE',
                     'options'   : {'TRUE' : '1', 'FALSE' : '0'}
                   },
  'slepc' :        { 're_option' : r'#define\s+LIBMESH_HAVE_SLEPC\s+(\d+)',
                     'default'   : 'FALSE',
                     'options'   : {'TRUE' : '1', 'FALSE' : '0'}
                   },
  'cxx11' :        { 're_option' : r'#define\s+LIBMESH_HAVE_CXX11\s+(\d+)',
                     'default'   : 'FALSE',
                     'options'   : {'TRUE' : '1', 'FALSE' : '0'}
                   },
  'unique_id' :    { 're_option' : r'#define\s+LIBMESH_ENABLE_UNIQUE_ID\s+(\d+)',
                     'default'   : 'FALSE',
                     'options'   : {'TRUE' : '1', 'FALSE' : '0'}
                   },
}


## Run a command and return the output, or ERROR: + output if retcode != 0
def runCommand(cmd, cwd=None):
    # On Windows it is not allowed to close fds while redirecting output
    should_close = platform.system() != "Windows"
    p = subprocess.Popen([cmd], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=should_close, shell=True)
    output = p.communicate()[0]
    if (p.returncode != 0):
        output = 'ERROR: ' + output
    return output

# Execute a command and return the process, temporary output_file and time the process was launched
def returnCommand(tester, command):
    # It seems that using PIPE doesn't work very well when launching multiple jobs.
    # It deadlocks rather easy.  Instead we will use temporary files
    # to hold the output as it is produced
    try:
        f = TemporaryFile()
        # On Windows, there is an issue with path translation when the command is passed in
        # as a list.
        if platform.system() == "Windows":
            process = subprocess.Popen(command,stdout=f,stderr=f,close_fds=False, shell=True, creationflags=CREATE_NEW_PROCESS_GROUP, cwd=tester.getTestDir())
        else:
            process = subprocess.Popen(command,stdout=f,stderr=f,close_fds=False, shell=True, preexec_fn=os.setsid, cwd=tester.getTestDir())
    except:
        print "Error in launching a new task", command
        raise

    return (process, f, clock())

## print an optionally colorified test result
#
# The test will not be colored if
# 1) options.colored is False,
# 2) the environment variable BITTEN_NOCOLOR is true, or
# 3) the color parameter is False.
def printResult(tester, result, timing, options, color=True):
    f_result = ''
    caveats = ''
    first_directory = tester.specs['first_directory']
    test_name = tester.getTestName()
    status = tester.getStatus()

    cnt = (TERM_COLS-2) - len(test_name + result)
    color_opts = {'code' : options.code, 'colored' : options.colored}
    if color:
        if options.color_first_directory:
            test_name = colorText(first_directory, 'CYAN', **color_opts) + test_name.replace(first_directory, '', 1) # Strip out first occurence only
        # Color the Caveats CYAN
        m = re.search(r'(\[.*?\])', result)
        if m:
            caveats = m.group(1)
            f_result = colorText(caveats, 'CYAN', **color_opts)

        # Color test results based on status.
        # Keep any caveats that may have been colored
        if status:
            f_result += colorText(result.replace(caveats, ''), tester.getColor(), **color_opts)

        f_result = test_name + '.'*cnt + ' ' + f_result
    else:
        f_result = test_name + '.'*cnt + ' ' + result

    # Tack on the timing if it exists
    if timing:
        f_result += ' [' + '%0.3f' % float(timing) + 's]'
    if options.debug_harness:
        f_result += ' Start: ' + '%0.3f' % start + ' End: ' + '%0.3f' % tester.getEndTime()
    return f_result

## Color the error messages if the options permit, also do not color in bitten scripts because
# it messes up the trac output.
# supports weirded html for more advanced coloring schemes. \verbatim<r>,<g>,<y>,<b>\endverbatim All colors are bolded.

def getPlatforms():
    # We'll use uname to figure this out.  platform.uname() is available on all platforms
    #   while os.uname() is not (See bugs.python.org/issue8080).
    # Supported platforms are LINUX, DARWIN, ML, MAVERICKS, YOSEMITE, or ALL
    platforms = set(['ALL'])
    raw_uname = platform.uname()
    if raw_uname[0].upper() == 'DARWIN':
        platforms.add('DARWIN')
        if re.match("12\.", raw_uname[2]):
            platforms.add('ML')
        if re.match("13\.", raw_uname[2]):
            platforms.add("MAVERICKS")
        if re.match("14\.", raw_uname[2]):
            platforms.add("YOSEMITE")
    else:
        platforms.add(raw_uname[0].upper())
    return platforms

def runExecutable(libmesh_dir, location, bin, args):
    # Installed location of libmesh executable
    libmesh_installed   = libmesh_dir + '/' + location + '/' + bin

    # Uninstalled location of libmesh executable
    libmesh_uninstalled = libmesh_dir + '/' + bin

    # Uninstalled location of libmesh executable
    libmesh_uninstalled2 = libmesh_dir + '/contrib/bin/' + bin

    # The eventual variable we will use to refer to libmesh's executable
    libmesh_exe = ''

    if os.path.exists(libmesh_installed):
        libmesh_exe = libmesh_installed

    elif os.path.exists(libmesh_uninstalled):
        libmesh_exe = libmesh_uninstalled

    elif os.path.exists(libmesh_uninstalled2):
        libmesh_exe = libmesh_uninstalled2

    else:
        print "Error! Could not find '" + bin + "' in any of the usual libmesh's locations!"
        exit(1)

    return runCommand(libmesh_exe + " " + args).rstrip()


def getCompilers(libmesh_dir):
    # Supported compilers are GCC, INTEL or ALL
    compilers = set(['ALL'])

    mpicxx_cmd = runExecutable(libmesh_dir, "bin", "libmesh-config", "--cxx")

    # Account for usage of distcc or ccache
    if "distcc" in mpicxx_cmd or "ccache" in mpicxx_cmd:
        mpicxx_cmd = mpicxx_cmd.split()[-1]

    # If mpi ic on the command, run -show to get the compiler
    if "mpi" in mpicxx_cmd:
        raw_compiler = runCommand(mpicxx_cmd + " -show")
    else:
        raw_compiler = mpicxx_cmd

    if re.match('icpc', raw_compiler) != None:
        compilers.add("INTEL")
    elif re.match('[cg]\+\+', raw_compiler) != None:
        compilers.add("GCC")
    elif re.match('clang\+\+', raw_compiler) != None:
        compilers.add("CLANG")

    return compilers

def getPetscVersion(libmesh_dir):
    major_version = getLibMeshConfigOption(libmesh_dir, 'petsc_major')
    minor_version = getLibMeshConfigOption(libmesh_dir, 'petsc_minor')
    if len(major_version) != 1 or len(minor_version) != 1:
        print "Error determining PETSC version"
        exit(1)

    return major_version.pop() + '.' + minor_version.pop()

def getSlepcVersion(libmesh_dir):
    major_version = getLibMeshConfigOption(libmesh_dir, 'slepc_major')
    minor_version = getLibMeshConfigOption(libmesh_dir, 'slepc_minor')
    subminor_version = getLibMeshConfigOption(libmesh_dir, 'slepc_subminor')
    if len(major_version) != 1 or len(minor_version) != 1 or len(major_version) != 1:
      return None

    return major_version.pop() + '.' + minor_version.pop() + '.' + subminor_version.pop()

# Break down petsc version logic in a new define
# TODO: find a way to eval() logic instead
def checkPetscVersion(checks, test):
    # If any version of petsc works, return true immediately
    if 'ALL' in set(test['petsc_version']):
        return (True, None, None)
    # Iterate through petsc versions in test[PETSC_VERSION] and match it against check[PETSC_VERSION]
    for petsc_version in test['petsc_version']:
        logic, version = re.search(r'(.*?)(\d\S+)', petsc_version).groups()
        # Exact match
        if logic == '' or logic == '=':
            if version == checks['petsc_version']:
                return (True, None, version)
            else:
                return (False, '!=', version)
        # Logical match
        if logic == '>' and checks['petsc_version'][0:3] > version[0:3]:
            return (True, None, version)
        elif logic == '>=' and checks['petsc_version'][0:3] >= version[0:3]:
            return (True, None, version)
        elif logic == '<' and checks['petsc_version'][0:3] < version[0:3]:
            return (True, None, version)
        elif logic == '<=' and checks['petsc_version'][0:3] <= version[0:3]:
            return (True, None, version)
    return (False, logic, version)


# Break down slepc version logic in a new define
def checkSlepcVersion(checks, test):
    # User does not require anything
    if len(test['slepc_version']) == 0:
       return (False, None, None)
    # SLEPc is not installed
    if checks['slepc_version'] == None:
       return (False, None, None)
    # If any version of SLEPc works, return true immediately
    if 'ALL' in set(test['slepc_version']):
        return (True, None, None)
    # Iterate through SLEPc versions in test[SLEPC_VERSION] and match it against check[SLEPC_VERSION]
    for slepc_version in test['slepc_version']:
        logic, version = re.search(r'(.*?)(\d\S+)', slepc_version).groups()
        # Exact match
        if logic == '' or logic == '=':
            if version == checks['slepc_version']:
                return (True, None, version)
            else:
                return (False, '!=', version)
        # Logical match
        if logic == '>' and checks['slepc_version'][0:5] > version[0:5]:
            return (True, None, version)
        elif logic == '>=' and checks['slepc_version'][0:5] >= version[0:5]:
            return (True, None, version)
        elif logic == '<' and checks['slepc_version'][0:5] < version[0:5]:
            return (True, None, version)
        elif logic == '<=' and checks['slepc_version'][0:5] <= version[0:5]:
            return (True, None, version)
    return (False, logic, version)

def getIfAsioExists(moose_dir):
    option_set = set(['ALL'])
    if os.path.exists(moose_dir+"/framework/contrib/asio/include/asio.hpp"):
        option_set.add('TRUE')
    else:
        option_set.add('FALSE')
    return option_set

def getLibMeshConfigOption(libmesh_dir, option):
    # Some tests work differently with parallel mesh enabled
    # We need to detect this condition
    option_set = set(['ALL'])

    filenames = [
      libmesh_dir + '/include/base/libmesh_config.h',   # Old location
      libmesh_dir + '/include/libmesh/libmesh_config.h' # New location
      ];

    success = 0
    for filename in filenames:
        if success == 1:
            break

        try:
            f = open(filename)
            contents = f.read()
            f.close()

            info = LIBMESH_OPTIONS[option]
            m = re.search(info['re_option'], contents)
            if m != None:
                if 'options' in info:
                    for value, option in info['options'].iteritems():
                        if m.group(1) == option:
                            option_set.add(value)
                else:
                    option_set.clear()
                    option_set.add(m.group(1))
            else:
                option_set.add(info['default'])

            success = 1

        except IOError:
            # print "Warning: I/O Error trying to read", filename, ":", e.strerror, "... Will try other locations."
            pass

    if success == 0:
        print "Error! Could not find libmesh_config.h in any of the usual locations!"
        exit(1)

    return option_set

def getSharedOption(libmesh_dir):
    # Some tests may only run properly with shared libraries on/off
    # We need to detect this condition
    shared_option = set(['ALL'])

    result = runExecutable(libmesh_dir, "contrib/bin", "libtool", "--config | grep build_libtool_libs | cut -d'=' -f2")

    if re.search('yes', result) != None:
        shared_option.add('DYNAMIC')
    elif re.search('no', result) != None:
        shared_option.add('STATIC')
    else:
        # Neither no nor yes?  Not possible!
        print "Error! Could not determine whether shared libraries were built."
        exit(1)

    return shared_option

def getInitializedSubmodules(root_dir):
    """
    Gets a list of initialized submodules.
    Input:
      root_dir[str]: path to execute the git command. This should be the root
        directory of the app so that the submodule names are correct
    Return:
      list[str]: List of iniitalized submodule names or an empty list if there was an error.
    """
    output = runCommand("git submodule status", cwd=root_dir)
    if output.startswith("ERROR"):
        return []
    # This ignores submodules that have a '-' at the beginning which means they are not initialized
    return re.findall(r'^[ +]\S+ (\S+)', output, flags=re.MULTILINE)

def addObjectsFromBlock(objs, node, block_name):
    """
    Utility function that iterates over a dictionary and adds keys
    to the executable object name set.
    """
    data = node.get(block_name, {})
    if data: # could be None so we can't just iterate over items
        for name, block in data.iteritems():
            objs.add(name)
            addObjectNames(objs, block)

def addObjectNames(objs, node):
    """
    Add object names that reside in this node.
    """
    if not node:
        return

    addObjectsFromBlock(objs, node, "subblocks")
    addObjectsFromBlock(objs, node, "subblock_types")

    star = node.get("star")
    if star:
        addObjectNames(objs, star)

def getExeObjects(exe):
    """
    Gets a set of object names that are in the executable JSON dump.
    """
    output = runCommand("%s --json" % exe)
    output = output.split('**START JSON DATA**\n')[1]
    output = output.split('**END JSON DATA**\n')[0]
    obj_names = set()
    data = json.loads(output)
    addObjectsFromBlock(obj_names, data, "blocks")
    return obj_names

def checkOutputForPattern(output, re_pattern):
    """
    Returns boolean of pattern match
    """
    if re.search(re_pattern, output, re.MULTILINE | re.DOTALL) == None:
        return False
    else:
        return True

def checkOutputForLiteral(output, literal):
    """
    Returns boolean of literal match
    """
    if output.find(literal) == -1:
        return False
    else:
        return True

def deleteFilesAndFolders(test_dir, paths, delete_folders=True):
    """
    Delete specified files

    test_dir:       The base test directory
    paths:          A list contianing files to delete
    delete_folders: Attempt to delete any folders created
    """
    for file in paths:
        full_path = os.path.join(test_dir, file)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except:
                print "Unable to remove file: " + full_path

    # Now try to delete directories that might have been created
    if delete_folders:
        for file in paths:
            path = os.path.dirname(file)
            while path != '':
                (path, tail) = os.path.split(path)
                try:
                    os.rmdir(os.path.join(test_dir, path, tail))
                except:
                    # There could definitely be problems with removing the directory
                    # because it might be non-empty due to checkpoint files or other
                    # files being created on different operating systems. We just
                    # don't care for the most part and we don't want to error out.
                    # As long as our test boxes clean before each test, we'll notice
                    # the case where these files aren't being generated for a
                    # particular run.
                    #
                    # TL;DR; Just pass...
                    pass

# Check if test has any redirected output, and if its ready to be read
def checkOutputReady(tester, options):
    for redirected_file in tester.getRedirectedOutputFiles(options):
        file_path = os.path.join(tester.getTestDir(), redirected_file)
        if not os.access(file_path, os.R_OK):
            return False

    return True

# return concatenated output from tests with redirected output
def getOutputFromFiles(tester, options):
    file_output = ''
    if checkOutputReady(tester, options):
        for iteration, redirected_file in enumerate(tester.getRedirectedOutputFiles(options)):
            file_path = os.path.join(tester.getTestDir(), redirected_file)
            with open(file_path, 'r') as f:
                file_output += "#"*80 + "\nOutput from processor " + str(iteration) + "\n" + "#"*80 + "\n" + readOutput(f, options)
    return file_output

# This function reads output from the file (i.e. the test output)
# but trims it down to the specified size.  It'll save the first two thirds
# of the requested size and the last third trimming from the middle
def readOutput(f, options, max_size=100000):
    first_part = int(max_size*(2.0/3.0))
    second_part = int(max_size*(1.0/3.0))
    output = ''

    f.seek(0)
    if options.sep_files != True:
        output = f.read(first_part)     # Limit the output to 1MB
        if len(output) == first_part:   # This means we didn't read the whole file yet
            output += "\n" + "#"*80 + "\n\nOutput trimmed\n\n" + "#"*80 + "\n"
            f.seek(-second_part, 2)       # Skip the middle part of the file

            if (f.tell() <= first_part):  # Don't re-read some of what you've already read
                f.seek(first_part+1, 0)

    output += f.read()              # Now read the rest
    return output

# See http://code.activestate.com/recipes/576570-dependency-resolver/
class DependencyResolver:
    """
    Class for returning dependency sets. That is, all of the vertices from a directed
    graph that a given vertex depends on (or can reach)
    """
    def __init__(self):
        self.dependency_dict = {}

    def insertDependency(self, key, values):
        """
        Insert all of the immediate dependencies for a given vertex. "values" should be a set
        """
        self.dependency_dict[key] = values

    def getSortedValuesSets(self):
        """
        Method to return the "execution order" for a directed graph (i.e. the order in which
        nodes must be visited to satistfy dependencies
        """
        d = dict((k, set(self.dependency_dict[k])) for k in self.dependency_dict)
        r = []
        while d:
            # values not in keys (items without dep)
            t = set(i for v in d.values() for i in v) - set(d.keys())
            # and keys without value (items without dep)
            t.update(k for k, v in d.items() if not v)

            if len(t) == 0 and len(d) > 0:
              raise Exception("Cyclic or Invalid Dependency Detected!")

            # can be done right away
            r.append(t)
            # and cleaned up
            d = dict(((k, v-t) for k, v in d.items() if v))
        return r

class ReverseReachability:
    """
    Calculates the Reverse Reachability of a graph. This class does this by
    computing the reachability of a graph (reversing the direction of edges)
    """
    def __init__(self):
        """
        Creats the dictionary to hold all of the reverse dependencies. (i.e. the key -> value
        pair is inserted in the dictionary such that the value -> key)
        """
        self.dependency_dict = {}

    def insertDependency(self, key, values):
        """
        Inserts all of the dependencies for a given key. "values" can either be
        a single value or a set of values.

        """
        for value in values:
            self.dependency_dict.setdefault(value, set()).add(key)

        # Also make sure the original key is in there with an empty set
        self.dependency_dict.setdefault(key, set())

    def getReverseReachabilitySets(self):
        """
        Method to retrieve all of the vertices that can reach a given vertex in a complete dictionary.
        """
        reachable = {}
        for key in self.dependency_dict:
            reachable[key] = self.getReverseReachableSet(key)

        return reachable

    def getReverseReachableSet(self, key):
        """
        Method to retrieve all of the verices for the passed in vertex (key)
        """
        return self._reverseReachability(key)

    def _reverseReachability(self, key, seen = None):
        """
        Helper method to discover all of the vertices that can reach this vertex. It uses recursion
        to populate the data structures.
        """
        seen = seen or []
        seen.append(key)
        reached = set()
        adjacent = self.dependency_dict.get(key)

        if adjacent:
            reached.update(adjacent)
            for subkey in adjacent:
                if subkey in adjacent and subkey not in seen:
                    reached.update(self._reverseReachability(subkey, seen))

        return reached


class TestStatus(object):
    """
    Class for handling test statuses
    """

    ###### bucket status discriptions
    ## The following is a list of statuses possible in the TestHarness
    ##
    ## PASS     =  Passing tests
    ## FAIL     =  Failing tests
    ## DIFF     =  Failing tests due to Exodiff, CSVDiff
    ## PENDING  =  A pending status applied by the TestHarness (RUNNING...)
    ## FINISHED =  A status that can mean it finished _in_ a pending status (like a queued status type)
    ## DELETED  =  A skipped test hidden from reporting. Under normal circumstances, this sort of test
    ##             is placed in the SILENT bucket. It is only placed in the DELETED bucket (and therfor
    ##             printed to stdout) when the user has specifically asked for more information while
    ##             running tests (-e)
    ## SKIP     =  Any test reported as skipped
    ## SILENT   =  Any test reported as skipped and should not alert the user (deleted, tests not
    ##             matching '--re=' options, etc)
    ######

    test_status     = namedtuple('test_status', 'status color')
    bucket_success  = test_status(status='PASS', color='GREEN')
    bucket_fail     = test_status(status='FAIL', color='RED')
    bucket_deleted  = test_status(status='DELETED', color='RED')
    bucket_diff     = test_status(status='DIFF', color='YELLOW')
    bucket_pending  = test_status(status='PENDING', color='CYAN')
    bucket_finished = test_status(status='FINISHED', color='CYAN')
    bucket_skip     = test_status(status='SKIP', color='RESET')
    bucket_silent   = test_status(status='SILENT', color='RESET')

    # Initialize the class with a pending status
    # TODO: don't do this? Initialize instead with None type? If we do
    # and forget to set a status, getStatus will fail with None type errors
    def __init__(self, status_message='initialized', status=bucket_pending):
        self.__status_message = status_message
        self.__status = status

    def setStatus(self, status_message, status_bucket):
        """
        Set bucket status
          setStatus("reason", TestStatus.bucket_tuple)
        """
        self.__status_message = status_message
        self.__status = status_bucket

    def getStatus(self):
        """
        Return status bucket namedtuple
        """
        return self.__status

    def getStatusMessage(self):
        """
        Return status message string
        """
        return self.__status_message

    def getColor(self):
        """
        Return enumerated color string
        """
        return self.__status.color

    def didPass(self):
        """
        Return boolean passing status (True if passed)
        """
        return self.getStatus() == self.bucket_success

    def didFail(self):
        """
        Return boolean failing status (True if failed)
        """
        status = self.getStatus()
        return status == self.bucket_fail or status == self.bucket_diff

    def didDiff(self):
        """
        Return boolean diff status (True if diff'd)
        """
        status = self.getStatus()
        return status == self.bucket_diff

    def isPending(self):
        """
        Return boolean pending status
        """
        status = self.getStatus()
        return status == self.bucket_pending

    def isSkipped(self):
        """
        Return boolean skipped status
        """
        status = self.getStatus()
        return status == self.bucket_skip

    def isSilent(self):
        """
        Return boolean silent status
        """
        status = self.getStatus()
        return status == self.bucket_silent

    def isDeleted(self):
        """
        Return boolean deleted status
        """
        status = self.getStatus()
        return status == self.bucket_deleted

    def isFinished(self):
        """
        Return boolean finished status
        """
        status = self.getStatus()
        return (status == self.bucket_finished or status is not self.bucket_pending)

class StatusDependency():
    """
    A class used to determine if a tester can run based on other current tester statuses.

    """

    def __init__(self, tester, testers, options):
        self.tester = tester
        self.__testers = set(testers) - set([tester])
        self.options = options

    # A method that returns bool if the test can run or sets the appropriate status why it could not run
    # or does nothing if the test needs to be placed back into the queue
    def checkAndSetStatus(self):
        if self.noRaceConditions():
            if self.isRunnable():
                return True
            elif not self.isAppendable() and self.prereqsExists():
                self.tester.setStatus('skipped dependency', self.tester.bucket_skip)
            elif not self.prereqsExists():
                self.tester.setStatus('unknown dependency', self.tester.bucket_fail)
            else:
                return
        else:
            self.tester.setStatus('OUTFILE RACE CONDITION', self.tester.bucket_fail)

    # check if all prereq tests have passed and none were skipped/failed
    def isRunnable(self):
        if len(set(self.tester.getPrereqs()) - self._passing_tests()) == 0 or self.skipPrereqs():
            return True

    # check if any prereqs are not yet complete (means this test _will_ be runnable... just not right now)
    def isAppendable(self):
        if len(set(self.tester.getPrereqs()).intersection(self._skipped_tests())) == 0 or self.skipPrereqs():
            return True

    # check if all prereqs are available
    def prereqsExists(self):
        if len(set(self.tester.getPrereqs()) - set([x.getTestName() for x in self.__testers])) == 0:
            return True

    # return a set of passing tests
    def _passing_tests(self):
        passing = set([])
        for tester in self.__testers:
            if tester.didPass():
                passing.add(tester.getTestName())
        return passing

    # return a set of finished non-passing or will be skipped tests
    def _skipped_tests(self):
        skipped_failed = set([])
        for tmp_tester in self.__testers:
            if (tmp_tester.isFinished() and not tmp_tester.didPass()) \
               or not tmp_tester.getRunnable(self.options) \
               or not tmp_tester.shouldExecute():
                skipped_failed.add(tmp_tester.getTestName())
        return skipped_failed

    # return bool if we want to ignore prereqs requirements
    def skipPrereqs(self):
        if self.options.ignored_caveats:
            caveat_list = [x.lower() for x in self.options.ignored_caveats.split()]
            if 'all' in self.options.ignored_caveats or 'prereq' in self.options.ignored_caveats:
                return True
        return False

    # return bool for output file race conditions
    # NOTE: we return True for exceptions, but they are handled later (because we set a failure status)
    def noRaceConditions(self):
        d = DependencyResolver()
        name_to_object = {}
        all_testers = set(self.__testers).union(set([self.tester]))

        for tester in all_testers:
            name_to_object[tester.getTestName()] = tester
            d.insertDependency(tester.getTestName(), tester.getPrereqs())
        try:
            # May fail, which will trigger an exception due cyclic dependencies
            concurrent_tester_sets = d.getSortedValuesSets()
            for concurrent_testers in concurrent_tester_sets:
                output_files_in_dir = set()
                for tester in concurrent_testers:
                    if self.prereqsExists() and name_to_object[tester].getTestName() not in self._skipped_tests():
                        output_files = name_to_object[tester].getOutputFiles()
                        duplicate_files = output_files_in_dir.intersection(output_files)
                        if len(duplicate_files):
                            return False
                        output_files_in_dir.update(output_files)
        except:
            self.tester.setStatus('Cyclic or Invalid Dependency Detected!', self.tester.bucket_fail)

        return True
