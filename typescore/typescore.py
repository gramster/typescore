import glob
import os
import subprocess
import re
import sys
from importlib.metadata import version, metadata
import requests


def normalize_name(package: str) -> str:
    """ Normalize a package name to the folder name that would be used in site-packages. """
    # See https://packaging.python.org/en/latest/specifications/binary-distribution-format/#escaping-and-unicode
    return re.sub(r"[-_.]+", "_", package).lower()


def install(package: str, skiplist: list[str]) -> None:
    """ Run a pip install and wait for completion. Raise a CalledProcessError on failure. """
    if package not in skiplist:
        subprocess.run([sys.executable, "-m", "pip", "install", package, "--require-virtualenv"], capture_output=True, check=True)


def get_site_packages() -> str:
    """ Get the install location for packages. """
    paths = [p for p in sys.path if p.find('site-packages')>0]
    assert(len(paths) == 1)
    site_packages = paths[0]
    return site_packages


def get_toplevels(package: str) -> list[str]:
    """ Get the top-level modules associated with a package. """
    # See if there is a toplevel.txt file for the package
    site_packages = get_site_packages()
    norm = normalize_name(package)
    loc = f'{site_packages}/{norm}-*.dist-info'
    files = glob.glob(loc)
    if len(files) == 1:
        tl = f'{files[0]}/top_level.txt'
        if os.path.exists(tl):
            with open(tl) as f:
                modules = []
                for line in f:
                    line = line.strip()
                    if line:
                        modules.append(line)
            return modules
        else:
            return [norm] # dist-info has no top_level.txt; fall back to normalized package name
    elif len(files) > 1: # This should probably never happen to maybe should just assert here.
        print(f'Ambiguous dist-info file for {package}', file=sys.stderr)
    return [norm]
                    

def get_score(package: str, subpath: str) -> str:
    """ Use pyright to get type coverage score for a top-level module and its children
        in a package folder. pyright requires a py.typed file so we create one if needed.
        package - package name part of the folder under site-packages where dist-info is found
        subpath - module path under site-packages (which may be the same as package, but need not be)
    """
    tf = f'{get_site_packages()}/{subpath}/py.typed'
    if not os.path.exists(tf):
        # Crteate a dummy py.typed for now that we will clean up afterwards
        with open(tf, 'w') as f:
            pass
    else:
        tf = None  # Prevents py.typed from being removed.
    try:
        module = subpath.replace('/', '.')
        s = subprocess.run([sys.executable, "-m", "pyright", "--verifytypes", module], capture_output=True, text=True)
        for line in s.stdout.split('\n'):
            l = line.strip()
            if l.startswith('error: Module'):
                print(f'{package}/{module}: Scoring failed: {l}', file=sys.stderr)
                return '0%'
            elif l.startswith('Type completeness score'):
                return l[l.rfind(' ')+1:]
    except Exception as e:
        print(f'{package}/{module}: Scoring failed: {e}', file=sys.stderr)
    finally:
        # Clean up py.typed if needed
        if tf:
            os.remove(tf)
    print(f'{package}/{module}: Scoring failed: No score line found', file=sys.stderr)
    return '0%'

 
def get_name_from_metadata(metadata_file: str) -> str|None:
    """ Get the Name: entry from a METADATA file for a package. """
    with open(metadata_file) as f:
        for line in f:
             if line.startswith('Name:'):
                 return line[5:].strip()
    return None


def get_installed(skip: list[str]) -> list[str]:
    """ Get the list of installed packages except if they are in skip. """
    site_packages = get_site_packages()
    loc = f'{site_packages}/*.dist-info/METADATA'
    files = glob.glob(loc)
    pkgs = []
    for file in files:
        pkg = get_name_from_metadata(file)
        if pkg and pkg not in skip:
            pkgs.append(pkg)
    return pkgs


def get_skiplist() -> list[str]:
    """ Get the existing set of packages so that when we clean up after our installs
        we don't remove these.
    """

    # Don't install/uninstall these as they should already be present
    # and are needed for typescore to work properly.

    skip = [
        'certifi',
        'charset-normalizer',
        'distutils',
        'docopt',
        'docutils',
        'flit',
        'flit_core',
        'idna',
        'importlib-metadata',
        'nodeenv',
        'packaging',
        'pip',
        'pyright',
        'requests',
        'setuptools',
        'tomli',
        'tomli_w',
        'typescore',
        'urllib3',
        'wheel',
        'zipp',
    ]
    skip.extend(get_installed(skip))
    return skip


def cleanup(skiplist: list[str]) -> None:
    """ Remove all installed packages not in skiplist. """
    pkgs = get_installed(skiplist)
    if pkgs:
        cmd = [sys.executable, "-m", "pip", "uninstall", "-y"]
        cmd.extend(pkgs)
        subprocess.run(cmd, capture_output=True, check=True)


def single_file_to_folder(site_packages: str, subpath: str) -> None:
    """ Convert a module that is a single file to a folder form. 
        We need this in order to also create a temporary py.typed file.
    """
    os.mkdir(f'{site_packages}/{subpath}')
    os.rename(f'{site_packages}/{subpath}.py', f'{site_packages}/{subpath}/__init__.py')


def folder_to_single_file(site_packages: str, subpath: str) -> None:
    """ Convert a folder module that is a single file to a top-level one. 
        Used to undo the changes from the function above.
    """
    os.rename(f'{site_packages}/{subpath}/__init__.py',
              f'{site_packages}/{subpath.replace("-", "_")}.py')
    os.rmdir(f'{site_packages}/{subpath}')
 

def namespace_module_resolve(site_packages: str, package: str, toplevel: str) -> str|None:
    """ A real kludge to handle (some) namespace modules,
        because I don't want to write an import resolver 
        and can't think of a better simple way right now...
    """
    np_subpath = normalize_name(package.replace('-', '/'))
    if not os.path.exists(f'{site_packages}/{toplevel}/__init__.py') and \
       package.startswith(toplevel) and package != toplevel and \
       os.path.exists(f'{site_packages}/{np_subpath}/__init__.py'):
       return np_subpath
    return None


def get_stub_package(package: str) -> str | None:
    """ See if typeshed or PyPI has a package that looks like it is likely type
        stubs for package, and if so, return that. """

    uri = f'https://github.com/python/typeshed/tree/master/stubs/{package}'
    r = requests.get(uri, stream=True)
    if r.status_code == 200:
        return 'typeshed'

    for stub_package in [package + '-stubs', 'types-' + package]:
        uri = f'https://pypi.org/project/{stub_package}/'
        r = requests.get(uri, stream=True)
        if r.status_code == 200:
            # Kludge to get version
            page = r.text
            start = page.find('<h1 class="package-header__name">')
            if start > 0:
                start += 33
                end = page.find('<', start)
                return page[start:end].strip()
            return stub_package
    return None


def compute_scores(packages: list[str]|None, packagesfile: str|None, scorefile: str|None=None,
                   verbose: bool=True, sep: str=',') -> None:
    """ Read a list of packages (and extra columns) from a packagesfile,
        or get them passed in as packages (and then append those in the file),
        and compute the type coverage scores, writing the results as a CSV
        file to scorefile, using column separator sep.
        If scorefile is None, print results to standard output instead
        (currently this can conmingle with error messages as those are
        going to stdout too).
        
        If verbose is true, include package version and description in the output.
    """
    skiplist = get_skiplist()
    pkgs = packages if packages else []
    if packagesfile:
        with open(packagesfile) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                pkgs.append(line)

    site_packages = get_site_packages()
    of = open(scorefile, 'w') if scorefile else None

    if verbose:
        header = f'package{sep}version{sep}typed{sep}module{sep}score{sep}stubs{sep}description'
    else:
        header = f'package{sep}typed{sep}module{sep}score'
    if of:
        of.write(header)
        of.write('\n')
    else:
        print(header)

    msg = "Can't include extra columns in package file if packages are also specified on command line; ignoring"
    for line in pkgs:

        # Get package and extra columns from line

        parts = [p.strip() for p in line.split(sep, 1)]
        package = parts[0]
        extra = f'{sep}{parts[1]}' if len(parts) == 2 else ''
        if extra and packages:
            if msg:
                print(msg, file=sys.stderr)
                msg = None
            extra = ''

        # Install package

        try:
            install(package, skiplist)
        except Exception as e:
            print(f'Failed to install {package}: {e}', file=sys.stderr)
            continue

        # Get attributes

        cpackage = normalize_name(package)
        typed = os.path.exists(f'{site_packages}/{cpackage}/py.typed')
        ver = ''
        description = ''
        stubs = ''
        if verbose:
            try:
                ver = version(package)
                stubs = str(get_stub_package(package))
                description = metadata(package)['Summary']
                if description.find(sep) >= 0:
                    description = '"' + description.replace('"', "'") + '"'
            except Exception as e:
                pass

        paths = get_toplevels(package)
        if len(paths) == 1:
            nm_path = namespace_module_resolve(site_packages, package, paths[0])
            if nm_path:
                paths = [nm_path]

        # Iterate through toplevel modules to get scores

        for subpath in paths:
            module = subpath.replace('/', '.')
            hacky = False
            if os.path.exists(f'{site_packages}/{subpath.replace("-", "_")}.py') and \
                not os.path.exists(f'{site_packages}/{subpath}'):
                # We have to do some hoop jumping here to get around
                # pyright wanting a py.typed file before it will
                # allow --verifytypes to be used. We already cons
                # up a py.typed file if needed elsewhere, but we
                # need to convert the package to a folder-based one
                # temporarily here...
                single_file_to_folder(site_packages, subpath)
                typed = False
                hacky = True
            else:
                typed = os.path.exists(f'{site_packages}/{subpath}/py.typed')

            if os.path.exists(f'{site_packages}/{subpath}'):
                score = get_score(package, subpath)
                if verbose:
                    result = f'{package}{sep}{ver}{sep}{typed}{sep}{module}{sep}{score}{sep}{stubs}{sep}{description}{extra}'
                else:
                    result = f'{package}{sep}{typed}{sep}{module}{sep}{score}{extra}'
                if of:
                    of.write(result)
                    of.write('\n')
                else:
                    print(result)
            else:
                print(f'Package {package} module {module} not found in site packages', file=sys.stderr)
            if hacky:
                folder_to_single_file(site_packages, subpath)
                
        try:
            cleanup(skiplist)
        except Exception as e:
            print(e, file=sys.stderr)
            
    if of:
        of.close()
