import glob
import subprocess
import sys
from importlib.metadata import version, metadata


# Don't install/uninstall these as they are needed.

_skip = [
    'certifi',
    'charset-normalizer',
    'docopt',
    'docutils',
    'flit',
    'flit_core',
    'idna',
    'nodeenv',
    'pyright',
    'requests',
    'tomli',
    'tomli_w',
    'urllib3',
]


def install(package) -> None:
    """ Run a pip install and wait for completion. Raise a CalledProcessError on failure. """
    if package not in _skip:
        subprocess.run([sys.executable, "-m", "pip", "install", package, "--require-virtualenv"], check=True)


def uninstall(package) -> None:
    """ Run a pip uninstall and wait for completion. Raise a CalledProcessError on failure. """
    if package in _skip or package.endswith('-stubs'):
        return
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", package], check=True)


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
    files = glob.glob(f'{site_packages}/{package}-*.dist-info/top-level.txt')
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
                    

def get_score(module) -> str:
    try:
        s = subprocess.run([sys.executable, "-m", "pyright", "--", module], check=True, capture_output=True, text=True)
        for line in s.stdout:
            l = line.strip()
            if l.startswith('error: Module'):
                return '0%'
            elif l.startswith('Type completeness score'):
                return l[l.rfind(' ')+1:]
    except Exception:
        pass
    return '0%'

    
def process_package(package) -> dict[str, str]:
    rtn = {}
    try:
        install(package)
    except Exception as e:
        print(f'Failed to install {package}: {e}')
        return {}
    for module in get_toplevels(package):
        rtn[module] = get_score(module)
    try:
        uninstall(package)
    except:
        pass
    return rtn


def compute_scores(packagesfile, scorefile, verbose=True, sep=','):
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
                    score = get_score(module)
                    of.write(f'{package}{ver}{sep}{module}{sep}{score}{description}{extra}\n')

                try:
                    uninstall(package)
                except:
                    pass
            
