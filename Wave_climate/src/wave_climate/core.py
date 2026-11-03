"""Site context, credentials (Colab Secrets or environment variables), folders, file helpers."""
import os, json, hashlib, datetime as dt
import numpy as np
import pandas as pd
from .options import check

OKABE_ITO = ['#0072B2', '#E69F00', '#009E73', '#D55E00', '#56B4E9', '#CC79A7', '#F0E442', '#000000']


class MissingSecret(RuntimeError):
    pass


def secret(name, required=True, purpose=''):
    """Colab Secret (key icon in Colab) or, outside Colab, an environment variable of the same name.
    Values are never printed or written to files."""
    v = None
    try:
        from google.colab import userdata
        try:
            v = userdata.get(name)
        except Exception:
            v = None
    except ImportError:
        pass
    v = v or os.environ.get(name)
    if not v and required:
        raise MissingSecret(f"Secret {name} is missing ({purpose}). In Colab: key icon on the left -> Add new secret "
                            f"'{name}' -> switch on Notebook access. Locally: set the environment variable {name}.")
    return v


class Context:
    """Site options, folders and the results of each step (kept in memory and saved to files)."""
    def __init__(self, site):
        self.site = check('site', site)
        if not self.site['OUTPUT_DIR']:
            raise ValueError("SITE['OUTPUT_DIR'] is not set (the notebook sets it to <toolkit folder>/outputs)")
        self.root = os.path.join(self.site['OUTPUT_DIR'], self.site['NAME'])
        self.cache = os.path.join(self.site['OUTPUT_DIR'], '_cache')
        for d in (self.root, self.cache): os.makedirs(d, exist_ok=True)
        self.opts = {}
        self.data = {}
        self.today = dt.datetime.now(dt.timezone.utc).date()
        self.log_path = os.path.join(self.root, 'sources.json')
        self.log = json.load(open(self.log_path)) if os.path.exists(self.log_path) else {}

    def path(self, *parts):
        p = os.path.join(self.root, *parts)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p

    def note(self, key, value):
        """Record where data came from (datasets, model cells, periods); saved to sources.json."""
        self.log[key] = value
        tmp = self.log_path + '.tmp'
        json.dump(self.log, open(tmp, 'w'), indent=1, default=str); os.replace(tmp, self.log_path)

    @property
    def lon(self): return float(self.site['POINT'][0])

    @property
    def lat(self): return float(self.site['POINT'][1])

    def __repr__(self):
        return f"Context({self.site['NAME']} at {self.lon:.3f}, {self.lat:.3f} -> {self.root})"


def setup(site):
    """Check the site options and create the output folder <OUTPUT_DIR>/<NAME>."""
    ctx = Context(site)
    print(f"Site {ctx.site['NAME']}: point {ctx.lon:.3f} E, {ctx.lat:.3f} N; Copernicus Marine region '{ctx.site['REGION']}'")
    print(f'Outputs: {ctx.root}   (downloads cached in {ctx.cache})')
    return ctx


def req_hash(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()[:12]


def save_csv(ctx, df, name, index=False):
    p = ctx.path('tables', f"{ctx.site['NAME']}_{name}.csv")
    df.to_csv(p + '.tmp', index=index); os.replace(p + '.tmp', p)
    return p


def save_fig(ctx, fig, name):
    for ext in ('png', 'pdf'):
        fig.savefig(ctx.path('figures', f"{ctx.site['NAME']}_{name}.{ext}"), dpi=200, bbox_inches='tight')


def figure_style():
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 8, 'axes.titlesize': 9, 'axes.labelsize': 8, 'legend.fontsize': 7,
                         'xtick.labelsize': 7, 'ytick.labelsize': 7, 'axes.spines.top': False, 'axes.spines.right': False,
                         'figure.dpi': 110})


def km(lon1, lat1, lon2, lat2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(np.asarray(lon2) - lon1) / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))
