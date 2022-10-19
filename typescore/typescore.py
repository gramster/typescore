import glob
import os
import subprocess
import sys
from importlib.metadata import version, metadata


# Don't install/uninstall these as they are needed.

_skip = [
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
    'pip',
    'pyright',
    'requests',
    'setuptools',
    'tomli',
    'tomli_w',
    'urllib3',
    'wheel',
    'zipp',
]


def install(package) -> None:
    """ Run a pip install and wait for completion. Raise a CalledProcessError on failure. """
    if package not in _skip:
        subprocess.run([sys.executable, "-m", "pip", "install", package, "--require-virtualenv"], capture_output=True, check=True)


def uninstall(package) -> None:
    """ Run a pip uninstall and wait for completion. Raise a CalledProcessError on failure. """
    if package in _skip or package.endswith('-stubs'):
        return
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", package], capture_output=True, check=True)


def get_site_packages() -> str:
    """ Get the install location for packages. """
    paths = [p for p in sys.path if p.find('site-packages')>0]
    assert(len(paths) == 1)
    site_packages = paths[0]
    return site_packages


def get_toplevels(package) -> list[str]:
    """ Get the top-level modules associated with a package. """
    # See if there is a toplevel.txt file for the package
    site_packages = get_site_packages()
    loc = f'{site_packages}/{package}-*.dist-info/top_level.txt'
    files = glob.glob(loc)
    if len(files) == 1:
        with open(files[0]) as f:
            modmap_changed = True
            modules = []
            for line in f:
                line = line.strip()
                if line:
                    modules.append(line)
        return modules
    return [package]
                    

def get_score(package: str, module: str) -> str:
    tf = f'{get_site_packages()}/{module}/py.typed'
    if not os.path.exists(tf):
        with open(tf, 'w') as f:
            pass
    else:
        tf = None
    try:
        s = subprocess.run([sys.executable, "-m", "pyright", "--verifytypes", module], capture_output=True, text=True)
        for line in s.stdout.split('\n'):
            l = line.strip()
            if l.startswith('error: Module'):
                print(f'{package}/{module}: Scoring failed: {l}')
                return '0%'
            elif l.startswith('Type completeness score'):
                return l[l.rfind(' ')+1:]
    except Exception as e:
        print(f'{package}/{module}: Scoring failed: {e}')
    finally:
        if tf:
            os.remove(tf)
    print(f'{package}/{module}: Scoring failed: No score line found')
    return '0%'

    
def compute_scores(packagesfile, scorefile, verbose=True, sep=','):
    site_packages = get_site_packages()
    with open(packagesfile) as f:
        with open(scorefile, 'w') as of:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split(sep, 1)]
                package = parts[0]
                extra = f'{sep}{parts[1]}' if len(parts) == 2 else ''
                try:
                    install(package)
                except Exception as e:
                    print(f'Failed to install {package}: {e}')
                    continue

                typed = os.path.exists(f'{site_packages}/{package}/py.typed')
                ver = ''
                description = ''
                if verbose:
                    try:
                        ver = sep + version(package)
                        description = metadata(package)['Summary']
                        if description.find(sep) >= 0:
                            description = sep + '"' + description.replace('"', "'") + '"'
                        else:
                            description = sep + description
                    except:
                        pass
    
                for module in get_toplevels(package):
                    hacky = False
                    if os.path.exists(f'{site_packages}/{module}.py'):
                        # We have to do some hoop jumping here to get around
                        # pyright wanting a py.typed file before it will
                        # allow --verifytypes to be used. We already cons
                        # up a py.typed file if needed elsewhere, but we
                        # need to convert the package to a folder-based one
                        # temporarily here...
                        os.mkdir(f'{site_packages}/{module}')
                        os.rename(f'{site_packages}/{module}.py', f'{site_packages}/{module}/__init__.py')
                        hacky = True
                    if os.path.exists(f'{site_packages}/{module}'):
                        score = get_score(package, module)
                        of.write(f'{package}{ver}{sep}{typed}{sep}{module}{sep}{score}{description}{extra}\n')
                    else:
                        print(f'Package {package} module {module} not found in site packages')
                    if hacky:
                        os.rename(f'{site_packages}/{module}/__init__.py',
                                  f'{site_packages}/{module}.py')
                        os.rmdir(f'{site_packages}/{module}')
                    
                try:
                    uninstall(package)
                except:
                    pass
            
