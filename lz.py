#!/usr/bin/env python3
# -*- coding: future_fstrings -*-

import matplotlib

# matplotlib.use('Gtk3Agg')
# matplotlib.use('TkAgg')
# matplotlib.use('Agg')
import matplotlib.pyplot as plt
# plt.switch_backend('Agg')
# plt.switch_backend('TkAgg')
# print(matplotlib.get_backend())

import os, sys, time, \
    random, \
    subprocess, glob, re, \
    numpy as np, \
    multiprocessing as mp, \
    logging, \
    collections, \
    functools, signal
from os import path as osp
from IPython import embed
from easydict import EasyDict as edict
import cv2, cvbase as cvb, copy, pandas as pd, math
import collections, h5py
from sklearn.preprocessing import normalize
from scipy.spatial.distance import cdist

# import redis, networkx as nx, \
#  yaml, subprocess, pprint, json, \
# csv, argparse, string, colorlog, \
# shutil, itertools,pathlib,
# from IPython import embed
# from tensorboardX import SummaryWriter

glvars = {}

root_path = osp.normpath(
    osp.join(osp.abspath(osp.dirname(__file__)), )
) + '/'
home_path = os.environ['HOME'] + '/'
work_path = home_path + '/work/'
share_path = '/data1/share/'
share_path3 = '/home/share/'
share_path2 = '/data2/share/'

sys.path.insert(0, root_path)

os.environ.setdefault('log', '1')
os.environ.setdefault('pytorch', '1')
os.environ.setdefault('tensorflow', '0')
os.environ.setdefault('chainer', '0')
# os.environ['MXNET_CPU_WORKER_NTHREADS'] = '3'
# os.environ['MXNET_ENGINE_TYPE'] = 'ThreadedEnginePerDevice'
timer = cvb.Timer()
stream_handler = None


def set_stream_logger(log_level=logging.INFO):
    # return None
    global stream_handler
    import colorlog
    sh = colorlog.StreamHandler()
    sh.setLevel(log_level)
    sh.setFormatter(
        colorlog.ColoredFormatter(
            ' %(asctime)s %(filename)s [line:%(lineno)d] %(log_color)s%(levelname)s%(reset)s %(message)s'))
    # if stream_handler is not None:
    #     logging.root.removeHandler(stream_handler)
    logging.root.addHandler(sh)
    return sh


file_hander = None


def set_file_logger(work_dir=None, log_level=logging.INFO):
    # return None
    global file_hander
    work_dir = work_dir or root_path
    if not osp.exists(work_dir):
        os.system(f"mkdir -p '{work_dir}'")
    fh = logging.FileHandler(os.path.join(work_dir, 'log-ing'))
    fh.setLevel(log_level)
    fh.setFormatter(
        logging.Formatter('%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s'))
    # if file_hander is not None:
    #     logging.root.removeHandler(file_hander)
    logging.root.addHandler(fh)
    return fh


if os.environ.get('log', '0') == '1':
    logging.root.setLevel(logging.INFO)
    stream_handler = set_stream_logger(logging.INFO)
    file_hander = set_file_logger(log_level=logging.INFO)

if os.environ.get('chainer', "1") == "1":
    import chainer
    from chainer import cuda

    # xp = cuda.get_array_module( )
    old_repr = chainer.Variable.__repr__
    chainer.Variable.__str__ = lambda obj: (f'ch {tuple(obj.shape)} {obj.dtype} '
                                            f'{old_repr(obj)} '
                                            f'type: {obj.dtype} shape: {obj.shape} ch')
    chainer.Variable.__repr__ = chainer.Variable.__str__
    logging.info(f'import chainer {timer.since_last_check()}')

if os.environ.get('pytorch', "1") == "1":
    tic = time.time()
    # os.environ["MKL_NUM_THREADS"] = "4"
    # os.environ["OMP_NUM_THREADS"] = "4"
    os.environ["NCCL_DEBUG"] = "INFO"
    # os.environ["NCCL_DEBUG_SUBSYS"] = "ALL"
    import torch
    import torchvision
    import torch.utils.data
    from torch import nn
    import torch.nn.functional as F

    old_repr = torch.Tensor.__repr__
    torch.Tensor.__repr__ = lambda obj: (f'th {tuple(obj.shape)} {obj.type()} '
                                         f'{old_repr(obj)} '
                                         f'type: {obj.type()} shape: {obj.shape} th') if obj.is_contiguous() else (
        f'{tuple(obj.shape)} {obj.type()} '
        f'{old_repr(obj.contiguous())} '
        f'type: {obj.type()} shape: {obj.shape}')
    logging.info(f'import pytorch {time.time() - tic}')


def allow_growth():
    import tensorflow as tf
    oldinit = tf.Session.__init__

    def myinit(session_object, target='', graph=None, config=None):
        if config is None:
            config = tf.ConfigProto()
        config.gpu_options.allow_growth = True
        oldinit(session_object, target, graph, config)

    tf.Session.__init__ = myinit
    return oldinit


if os.environ.get('tensorflow', '0') == '1':
    tic = time.time()
    import tensorflow as tf

    # import tensorflow.contrib

    oldinit = allow_growth()
    print('import tf', time.time() - tic)

'''
%load_ext autoreload
%autoreload 2
%matplotlib inline
import matplotlib
matplotlib.style.use('ggplot')

from IPython.core.interactiveshell import InteractiveShell
InteractiveShell.ast_node_interactivity = "all"
'''

# torch.set_default_tensor_type(torch.cuda.DoubleTensor)
# ori_np_err = np.seterr(all='raise') # 1/100000=0 will be error

## ndarray will be pretty
np.set_string_function(lambda arr: f'np {arr.shape} {arr.dtype} '
f'{arr.__str__()} '
f'dtype:{arr.dtype} shape:{arr.shape} np', repr=True)

## print(ndarray) will be pretty (and pycharm dbg)
# np.set_string_function(lambda arr: f'np {arr.shape} {arr.dtype} \n'
#                                    f'{arr.__repr__()} \n'
#                                    f'dtype:{arr.dtype} shape:{arr.shape} np', repr=False)

## fail
# old_np_repr = np.ndarray.__repr__
# np.ndarray.__repr__ = lambda arr: (f'{arr.shape} {arr.dtype} \n'
#                                    f'{old_np_repr(arr)} \n'
#                                    f'dtype:{arr.dtype} shape:{arr.shape}')

logging.info('import lz')


def init_dev(n=(0,)):
    import os
    import logging
    if not isinstance(n, collections.Sequence):
        n = (n,)
    logging.info('use gpu {}'.format(n))
    home = os.environ['HOME']
    if isinstance(n, int) or n is None:
        n = (n,)
    devs = ''
    for n_ in n:
        devs += str(n_) + ','
    devs = devs.strip(',')
    os.environ["CUDA_VISIBLE_DEVICES"] = devs
    set_env('PATH', home + '/local/cuda/bin')
    set_env('LD_LIBRARY_PATH', home + '/local/cuda/lib64:' +
            home + '/local/cuda/extras/CUPTI/lib64')


def set_env(key, value):
    if key in os.environ:
        os.environ[key] = value + ':' + os.environ[key]
    else:
        os.environ[key] = value


# todo occupy and release
def occupy(dev=range(8)):
    import tensorflow as tf
    init_dev(dev)
    newinit = tf.Session.__init__
    if 'oldinit' in locals():
        tf.Session.__init__ = oldinit
    var = tf.constant(1)
    with tf.Session() as sess:
        sess.run([var])
    while True:
        time.sleep(10)
    # tf.Session.__init__ = newinit


# if something like Runtime Error : an illegal memory access was encountered occur
# os.environ['CUDA_LAUNCH_BLOCKING'] = "1"

'''
oldinit = Session.__init__

def myinit(session_object, target='', graph=None, config=None):
    if config is None:
        config = ConfigProto()
    config.gpu_options.allow_growth = True
    oldinit(session_object, target, graph, config)

Session.__init__ = myinit
'''


def allow_growth_conf():
    import tensorflow as tf
    _sess_config = tf.ConfigProto(allow_soft_placement=True)
    _sess_config.gpu_options.allow_growth = True
    return _sess_config


def allow_growth_sess():
    import tensorflow as tf
    tf_graph = tf.get_default_graph()
    _sess_config = tf.ConfigProto(allow_soft_placement=True)
    _sess_config.gpu_options.allow_growth = True
    sess = tf.Session(config=_sess_config, graph=tf_graph)
    return sess


def allow_growth_keras():
    import keras
    keras.backend.set_session(allow_growth_sess())


def judgenan(x):
    return not not torch.isnan(x).any().item() or not not torch.isinf(x).any().item()


def get_mem():
    import psutil
    while True:
        try:
            mem = psutil.virtual_memory()
            break
        except:
            pass
    free = mem.free / 1024 ** 3
    available = mem.available / 1024 ** 3
    return available


import gpustat

ndevs = len(gpustat.GPUStatCollection.new_query().gpus)


def get_gpu_mem(ind=0):
    gpus = gpustat.GPUStatCollection.new_query().gpus
    return gpus[ind].entry['memory.used'] / gpus[ind].entry['memory.total'] * 100


def get_utility(ind=0):
    import gpustat
    gpus = gpustat.GPUStatCollection.new_query().gpus
    return gpus[ind].entry['utilization.gpu']


def show_dev():
    res = []
    for ind in range(ndevs):
        mem = get_gpu_mem(ind)
        print(ind, mem)
        res.append(mem)
    return res


def get_dev(n=1, ok=range(ndevs), mem_thresh=(0.1, 0.15), sleep=23.3):  # 0.3: now occupy smaller than 0.3
    if not isinstance(mem_thresh, collections.Sequence):
        mem_thresh = (mem_thresh,)

    def get_poss_dev():
        mems = [get_gpu_mem(ind) for ind in ok]
        inds, mems = cosort(ok, mems, return_val=True)
        devs = [ind for ind, mem in zip(inds, mems) if mem < mem_thresh[0] * 100]

        return devs

    devs = get_poss_dev()
    logging.info('Auto select gpu')
    # gpustat.print_gpustat()
    show_dev()
    while len(devs) < n:
        devs = get_poss_dev()

        print('no enough device available')
        # gpustat.print_gpustat()
        show_dev()

        sleep = int(sleep)
        time.sleep(random.randint(max(0, sleep - 20), sleep + 20))
    return devs[:n]


def wrapped_partial(func, *args, **kwargs):
    partial_func = functools.partial(func, *args, **kwargs)
    functools.update_wrapper(partial_func, func)
    return partial_func


def cpu_priority(level=19):
    import psutil
    p = psutil.Process(os.getpid())
    p.nice(level)


def mkdir_p(path, delete=True, verbose=True):
    path = str(path)
    if path == '':
        return
    if delete and osp.exists(path):
        rm(path)
    if not osp.exists(path):
        os.makedirs(path, exist_ok=True)


class Logger(object):
    def __init__(self, fpath=None, console=sys.stdout):
        self.console = console
        self.file = None
        if fpath is not None:
            mkdir_p(os.path.dirname(fpath), delete=False)
            # rm(fpath)
            self.file = open(fpath, 'a')

    def __del__(self):
        self.close()

    def __enter__(self):
        pass

    def __exit__(self, *args):
        self.close()

    def write(self, msg):
        self.console.write(msg)
        if self.file is not None:
            self.file.write(msg)

    def flush(self):
        self.console.flush()
        if self.file is not None:
            self.file.flush()
            os.fsync(self.file.fileno())

    def close(self):
        self.console.close()
        if self.file is not None:
            self.file.close()


def set_file_logger_prt(path=root_path):
    # todo
    path = str(path) + '/'
    # sys.stdout = Logger(path + 'log-prt')
    # sys.stderr = Logger(path + 'log-prt-err')


if os.environ.get('log', '0') == '1':
    set_file_logger_prt()


class Timer(object):
    """A flexible Timer class.

    :Example:

    >>> import time
    >>> import cvbase as cvb
    >>> with cvb.Timer():
    >>>     # simulate a code block that will run for 1s
    >>>     time.sleep(1)
    1.000
    >>> with cvb.Timer(print_tmpl='hey it taks {:.1f} seconds'):
    >>>     # simulate a code block that will run for 1s
    >>>     time.sleep(1)
    hey it taks 1.0 seconds
    >>> timer = cvb.Timer()
    >>> time.sleep(0.5)
    >>> print(timer.since_start())
    0.500
    >>> time.sleep(0.5)
    >>> print(timer.since_last_check())
    0.500
    >>> print(timer.since_start())
    1.000

    """

    def __init__(self, print_tmpl=None, start=True, ):
        self._is_running = False
        self.print_tmpl = print_tmpl if print_tmpl else '{:.3f}'
        if start:
            self.start()

    @property
    def is_running(self):
        """bool: indicate whether the timer is running"""
        return self._is_running

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        print(self.print_tmpl.format(self.since_last_check()))
        self._is_running = False

    def start(self):
        """Start the timer."""
        if not self._is_running:
            self._t_start = time.time()
            self._is_running = True
        self._t_last = time.time()

    def since_start(self, aux=''):
        """Total time since the timer is started.

        Returns(float): the time in seconds
        """
        if not self._is_running:
            raise ValueError('timer is not running')
        self._t_last = time.time()
        logging.info(f'{aux} time {self.print_tmpl.format(self._t_last - self._t_start)}')
        return self._t_last - self._t_start

    def since_last_check(self, aux='', verbose=True):
        """Time since the last checking.

        Either :func:`since_start` or :func:`since_last_check` is a checking operation.

        Returns(float): the time in seconds
        """
        if not self._is_running:
            raise ValueError('timer is not running')
        dur = time.time() - self._t_last
        self._t_last = time.time()
        if verbose:
            logging.info(f'{aux} time {self.print_tmpl.format(dur)}')
        return dur


timer = Timer()


def get_md5(url):
    if isinstance(url, str):
        url = url.encode('utf-8')
    import hashlib
    m = hashlib.md5()
    m.update(url)
    return m.hexdigest()


def load_cfg(cfg_file):
    from importlib import import_module
    sys.path.append(osp.dirname(cfg_file))
    module_name = osp.basename(cfg_file).rstrip('.py')
    cfg = import_module(module_name)
    return cfg


# Based on an original idea by https://gist.github.com/nonZero/2907502 and heavily modified.
class Uninterrupt(object):
    """
    Use as:
    with Uninterrupt() as u:
        while not u.interrupted:
            # train
    """

    def __init__(self, sigs=(signal.SIGINT,), verbose=False):
        self.sigs = sigs
        self.verbose = verbose
        self.interrupted = False
        self.orig_handlers = None

    def __enter__(self):
        if self.orig_handlers is not None:
            raise ValueError("Can only enter `Uninterrupt` once!")

        self.interrupted = False
        self.orig_handlers = [signal.getsignal(sig) for sig in self.sigs]

        def handler(signum, frame):
            self.release()
            self.interrupted = True
            if self.verbose:
                print("Interruption scheduled...", )

        for sig in self.sigs:
            signal.signal(sig, handler)

        return self

    def __exit__(self, type_, value, tb):
        self.release()

    def release(self):
        if self.orig_handlers is not None:
            for sig, orig in zip(self.sigs, self.orig_handlers):
                signal.signal(sig, orig)
            self.orig_handlers = None


def mail(content, to_mail=('907682447@qq.com',)):
    import datetime, collections

    user_passes = json_load(home_path + 'Dropbox/mail.json')
    user_pass = user_passes[0]

    time_str = datetime.datetime.now().strftime('%m-%d %H:%M')

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    s = smtplib.SMTP(host=user_pass['host'], port=user_pass['port'], timeout=10)
    s.starttls()
    s.login(user_pass['username'], user_pass['password'])

    title = 'ps: ' + content.split('\r\n')[0]
    title = title[:20]
    content = time_str + '\r\n' + content
    if isinstance(to_mail, collections.Sequence):
        to_mail = ', '.join(to_mail)
    msg = MIMEMultipart('alternative')
    msg['Subject'] = title
    msg['From'] = user_pass['username']
    msg['To'] = to_mail
    # msg['Cc'] = to_mail
    msg.attach(MIMEText(content, 'plain'))
    s.sendmail(msg['From'], msg['To'], msg.as_string())
    s.quit()


def df2md(df1):
    import tabulate
    return tabulate.tabulate(df1, headers="keys", tablefmt="pipe")


def stat(arr):
    def stat_np(array):
        array = np.asarray(array)
        return dict(zip(
            ['min', 'mean', 'median', 'max', 'shape'],
            [np.min(array), np.mean(array), np.median(array), np.max(array), np.shape(array)]
        ))

    def stat_th(tensor):
        return dict(zip(
            ['min', 'mean', 'median', 'max', ],
            [torch.min(tensor).item(), torch.mean(tensor).item(), torch.median(tensor).item(), torch.max(
                tensor).item()]
        ))

    if type(arr).__module__ == 'torch':
        return stat_th(arr)
    else:
        return stat_np(arr)


def sel_np(A):
    import json
    dtype = str(A.dtype)
    shape = A.shape
    A = A.ravel().tolist()
    sav = {'shape': shape, 'dtype': dtype,
           'A': A}
    return json.dumps(sav)


def desel_np(s):
    import json
    sav = json.loads(s)
    A = sav['A']
    A = np.array(A, dtype=sav['dtype']).reshape(sav['shape'])
    return A


def to_image(arr):
    from PIL import Image
    if type(arr).__module__ == 'PIL.Image':
        return arr
    if type(arr).__module__ == 'numpy':
        return Image.fromarray(arr)


def to_numpy(tensor):
    import PIL
    if isinstance(tensor, torch.autograd.Variable):
        tensor = tensor.detach()
    if torch.is_tensor(tensor):
        if tensor.shape == ():
            tensor = tensor.item()
            tensor = np.asarray([tensor])
        elif np.prod(tensor.shape) == 1:
            tensor = tensor.item()
            tensor = np.asarray([tensor])
        else:
            tensor = tensor.cpu().numpy()
            tensor = np.asarray(tensor)
    if type(tensor).__module__ == 'PIL.Image':
        tensor = np.asarray(tensor)
    # elif type(tensor).__module__ != 'numpy':
    #     raise ValueError("Cannot convert {} to numpy array"
    #                      .format(type(tensor)))
    return tensor


def to_torch(ndarray):
    if ndarray is None:
        return None
    if isinstance(ndarray, collections.Sequence):
        return [to_torch(ndarray_) for ndarray_ in ndarray if ndarray_ is not None]
    # if isinstance(ndarray, torch.autograd.Variable):
    #     ndarray = ndarray.data
    if type(ndarray).__module__ == 'numpy':
        return torch.from_numpy(ndarray)
    elif not torch.is_tensor(ndarray):
        raise ValueError("Cannot convert {} to torch tensor"
                         .format(type(ndarray)))
    return ndarray


def norm_np(tensor):
    min, max = tensor.min(), tensor.max()
    tensor += min
    tensor /= (max - min)
    tensor *= 255
    return tensor


def norm_th(tensor):
    min, max = tensor.min(), tensor.max()
    return tensor.add_(min).div_(max - min)


def load_state_dict(model, state_dict, prefix='', de_prefix=''):
    own_state = model.state_dict()
    success = []
    if prefix != '':
        state_dict = {prefix + name: param for name, param in state_dict.items()}
    elif de_prefix != '':
        state_dict = {name.replace(de_prefix, ''): param for name, param in state_dict.items()}
    for name, param in state_dict.items():
        if name not in own_state:
            print('ignore key "{}" in his state_dict'.format(name))
            continue

        if isinstance(param, nn.Parameter):
            param = param.clone()

        if own_state[name].size() == param.size():
            own_state[name].copy_(param)
            # print('{} {} is ok '.format(name, param.size()))
            success.append(name)
        else:
            logging.error('dimension mismatch for param "{}", in the model are {}'
                          ' and in the checkpoint are {}, ...'.format(
                name, own_state[name].size(), param.size()))

    missing = set(own_state.keys()) - set(success)
    if len(missing) > 0:
        print('missing keys in my state_dict: "{}"'.format(missing))


def grid_iter(*args):
    import itertools
    res = list(itertools.product(*args))
    np.random.shuffle(res)
    for arg in res:
        if len(arg) == 1:
            yield arg[0]
        else:
            yield arg


def cross_iter(*args):
    start = [t[0] for t in args]
    yield start
    for ind, arg in enumerate(args):
        if len(arg) > 1:
            bak = start[ind]
            for ar in arg[1:]:
                start[ind] = ar
                yield start
            start[ind] = bak


def shuffle_iter(iter):
    iter = list(iter)
    np.random.shuffle(iter)
    for iter_ in iter:
        yield iter_


def optional_arg_decorator(fn):
    def wrapped_decorator(*args):
        if len(args) == 1 and callable(args[0]):
            return fn(args[0])
        else:
            def real_decorator(decoratee):
                return fn(decoratee, *args)

            return real_decorator

    return wrapped_decorator


def randomword(length=9, ):
    import random
    import string
    return ''.join(random.choice(string.ascii_letters + string.digits + '_') for _ in range(length))


def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func

    return decorate


def cosort(ind, val, return_val=False):
    ind = np.asarray(ind)
    val = np.asarray(val)
    comb = zip(ind, val)
    comb_sorted = sorted(comb, key=lambda x: x[1])
    if not return_val:
        return np.array([comb_[0] for comb_ in comb_sorted])
    else:
        return np.array([comb_[0] for comb_ in comb_sorted]), np.array([comb_[1] for comb_ in
                                                                        comb_sorted])


@optional_arg_decorator
def timeit(fn, info=''):
    def wrapped_fn(*arg, **kwargs):
        start = time.time()
        res = fn(*arg, **kwargs)
        diff = time.time() - start
        logging.info((info + 'takes time {}').format(diff))
        return res

    return wrapped_fn


class Database(object):
    def __init__(self, file, mode='a'):
        import h5py
        if mode == 'r':
            try:
                self.fid = h5py.File(file, mode)
            except OSError as inst:
                logging.error(f'{inst}')
                cp(file, file + f'.{randomword()}')
                self.fid = h5py.File(file, mode)
        else:
            self.fid = h5py.File(file, mode)
        #     rm(file)
        #     self.fid = h5py.File(file, 'w')
        #     logging.error(f'{file} is delete and write !!')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fid.close()

    def __getitem__(self, keys):
        if isinstance(keys, (tuple, list)):
            return [self._get_single_item(k) for k in keys]
        return self._get_single_item(keys)

    def _get_single_item(self, key):
        return np.asarray(self.fid[key])

    def __setitem__(self, key, value):
        value = np.asarray(value)
        if key in self.fid:
            if self.fid[key].shape == value.shape and \
                    self.fid[key].dtype == value.dtype:
                logging.debug('shape type same, old is updated, {} {} '.format(value, np.count_nonzero(value == -1))
                              )
                self.fid[key][...] = value
            else:
                logging.debug('old shape {} new shape {} updated'.format(
                    self.fid[key].shape, value.shape))
                del self.fid[key]
                self.fid.create_dataset(key, data=value)
        else:
            self.fid.create_dataset(key, data=value)

    def __delitem__(self, key):
        del self.fid[key]

    def __len__(self):
        return len(self.fid)

    def __iter__(self):
        return iter(self.fid)

    def flush(self):
        self.fid.flush()

    def close(self):
        self.flush()
        self.fid.close()

    def keys(self):
        return self.fid.keys()


def pickle_dump(data, file, **kwargs):
    import pickle, pathlib
    # python2 can read 2
    kwargs.setdefault('protocol', pickle.HIGHEST_PROTOCOL)
    if isinstance(file, str) or isinstance(file, pathlib.Path):
        mkdir_p(osp.dirname(file), delete=False)
        print('pickle into', file)
        with open(file, 'wb') as f:
            pickle.dump(data, f, **kwargs)
    elif hasattr(file, 'write'):
        pickle.dump(data, file, **kwargs)
    else:
        raise TypeError("file must be str of file-object")


def get_img_size(img='/data1/xinglu/prj/test.jpg', verbose=True):
    try:
        out, err = shell(f'convert "{img}" -print "(%w, %h)" ', verbose=verbose)
        out = eval(out)
        out = (out[1], out[0])
    except:
        out = cv2.imread(img).shape[:2]
    return out


def pickle_load(file, **kwargs):
    import pickle
    if isinstance(file, str):
        with open(file, 'rb') as f:
            data = pickle.load(f, **kwargs)
    elif hasattr(file, 'read'):
        data = pickle.load(file, **kwargs)
    return data


def df_dump(df, path, name='df'):
    df.to_hdf(path, name, mode='w')


def df_load(path, name='df'):
    import pandas as pd
    return pd.read_hdf(path, name)


import struct

cv_type_to_dtype = {
    5: np.dtype('float32'),
    7: np.dtype('float16')
}

dtype_to_cv_type = {v: k for k, v in cv_type_to_dtype.items()}


def read_mat(f):
    """
    Reads an OpenCV mat from the given file opened in binary mode
    """
    rows, cols, stride, type_ = struct.unpack('iiii', f.read(4 * 4))
    mat = np.fromstring(f.read(rows * stride), dtype=cv_type_to_dtype[type_])
    return mat.reshape(rows, cols)


def load_mat(filename):
    """
    Reads a OpenCV Mat from the given filename
    """
    return read_mat(open(filename, 'rb'))


def write_mat(f, m):
    """Write mat m to file f"""
    import struct

    if len(m.shape) == 1:
        rows = m.shape[0]
        cols = 1
    else:
        rows, cols = m.shape
    header = struct.pack('iiii', rows, cols, cols * 4, dtype_to_cv_type[m.dtype])
    f.write(header)
    f.write(m.data)


def save_mat(filename, m):
    """Saves mat m to the given filename"""
    return write_mat(open(filename, 'wb'), m)


def yaml_load(file, **kwargs):
    from yaml import Loader
    import yaml
    kwargs.setdefault('Loader', Loader)
    if isinstance(file, str):
        with open(file, 'r') as f:
            obj = yaml.load(f, **kwargs)
    elif hasattr(file, 'read'):
        obj = yaml.load(file, **kwargs)
    else:
        raise TypeError('"file" must be a filename str or a file-object')
    return obj


def yaml_dump(obj, file=None, **kwargs):
    import yaml
    from yaml import Dumper
    kwargs.setdefault('Dumper', Dumper)
    if file is None:
        return yaml.dump(obj, **kwargs)
    elif isinstance(file, str):
        with open(file, 'w') as f:
            yaml.dump(obj, f, **kwargs)
    elif hasattr(file, 'write'):
        yaml.dump(obj, file, **kwargs)
    else:
        raise TypeError('"file" must be a filename str or a file-object')


# torch.nn.utils.clip_grad_value_(self.model.parameters(), 5)

def clip_grad_value_(parameters, clip_value=5):
    r"""Clips gradient of an iterable of parameters at specified value.

    Gradients are modified in-place.

    Arguments:
        parameters (Iterable[Tensor] or Tensor): an iterable of Tensors or a
            single Tensor that will have gradients normalized
        clip_value (float or int): maximum allowed value of the gradients.
            The gradients are clipped in the range
            :math:`\left[\text{-clip\_value}, \text{clip\_value}\right]`
    """
    if isinstance(parameters, torch.Tensor):
        parameters = [parameters]
    clip_value = float(clip_value)
    for p in filter(lambda p: p.grad is not None, parameters):
        if torch.isnan(p.grad.data).any().item():
            print('nan ', p.shape)
        if torch.isinf(p.grad.data).any().item():
            print('nan ', p.shape)
        p.grad.data.clamp_(min=-clip_value, max=clip_value)


def json_dump(obj, file, mode='a'):  # write not append!
    # import codecs
    import json
    if isinstance(file, str):
        # with codecs.open(file, mode, encoding='utf-8') as fp:
        with open(file, 'w') as fp:
            json.dump(obj, fp, sort_keys=True, indent=4
                      # ensure_ascii=False
                      )
    elif hasattr(file, 'write'):
        json.dump(obj, file)


def json_load(file):
    import json
    if isinstance(file, str):
        with open(file, 'r') as f:
            obj = json.load(f)
    elif hasattr(file, 'read'):
        obj = json.load(file)
    else:
        raise TypeError('"file" must be a filename str or a file-object')
    return obj


def msgpack_dump(obj, file, **kwargs):
    file = str(file)
    import msgpack, msgpack_numpy as m
    kwargs.setdefault('allow_np', True)
    allow_np = kwargs.pop('allow_np')
    if allow_np:
        kwargs.setdefault('default', m.encode)
    kwargs.setdefault('use_bin_type', True)
    try:
        with open(file, 'wb') as fp:
            msgpack.pack(obj, fp, **kwargs)
    except Exception  as e:
        logging.warning(f'{e}')
        logging.warning('cannot dump')
        obj = copy.deepcopy(obj)
        obj2 = to_json_format(obj)
        with open(file, 'wb') as fp:
            msgpack.pack(obj2, fp, **kwargs)
        logging.warning('dump succes')


def msgpack_dumps(obj, **kwargs):
    import msgpack, msgpack_numpy as m
    kwargs.setdefault('allow_np', True)
    allow_np = kwargs.pop('allow_np')
    if allow_np:
        kwargs.setdefault('default', m.encode)
    kwargs.setdefault('use_bin_type', True)
    return msgpack.packb(obj, **kwargs)


def msgpack_load(file, **kwargs):
    assert osp.exists(file)
    import msgpack, gc, msgpack_numpy as m
    gc.disable()
    kwargs.setdefault('allow_np', True)
    allow_np = kwargs.pop('allow_np')
    if allow_np:
        kwargs.setdefault('object_hook', m.decode)
    kwargs.setdefault('use_list', False)
    kwargs.setdefault('raw', False)
    with open(file, 'rb') as f:
        res = msgpack.unpack(f, **kwargs)
    gc.enable()
    return res


def msgpack_loads(file, **kwargs):
    import msgpack, gc, msgpack_numpy as m
    gc.disable()
    kwargs.setdefault('use_list', False)
    kwargs.setdefault('raw', False)
    # todo support numpy
    obj = msgpack.unpackb(file, **kwargs)
    gc.enable()
    return obj

def append_file(line, file=None):
    file = file or 'append.txt'
    with open(file, 'a') as f:
        f.writelines(line + '\n')


def write_list(file, l, sort=False, delimiter=' ', fmt='%.18e'):
    l = np.array(l)
    if sort:
        l = np.sort(l, axis=0)
    np.savetxt(file, l, delimiter=delimiter, fmt=fmt)


class AsyncDumper(mp.Process):
    def __init__(self):
        self.queue = mp.Queue()
        super(AsyncDumper, self).__init__()

    def run(self):
        while True:
            data, out_file = self.queue.get()
            if data is None:
                break
            pickle_dump(data, out_file)

    def dump(self, obj, filename):
        self.queue.put((obj, filename))


def aria(url, dir_, fn):
    return shell(f'aria2c -c -s16 -k1M -x16 "{url}" -o "{fn}" -d "{dir_}"', )


def hostname():
    msg = shell('hostname')[0]
    return msg.strip('\n')


def shell(cmd, block=True, return_msg=True, verbose=True, timeout=None):
    import os
    my_env = os.environ.copy()
    home = os.path.expanduser('~')
    my_env['PATH'] = home + "/anaconda3/bin/:" + my_env['PATH']
    my_env['http_proxy'] = ''
    my_env['https_proxy'] = ''
    if verbose:
        logging.info('cmd is ' + cmd)
    if block:
        # subprocess.call(cmd.split())
        task = subprocess.Popen(cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=my_env,
                                preexec_fn=os.setsid
                                )
        if return_msg:
            msg = task.communicate(timeout)
            msg = [msg_.decode('utf-8') for msg_ in msg]
            if msg[0] != '' and verbose:
                logging.info('stdout {}'.format(msg[0]))
            if msg[1] != '' and verbose:
                logging.error(f'stderr {msg[1]}, cmd {cmd}')
            return msg
        else:
            return task
    else:
        logging.debug('Non-block!')
        task = subprocess.Popen(cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=my_env,
                                preexec_fn=os.setsid
                                )
        return task


def ln(path, to_path):
    if osp.exists(to_path):
        print('error! exist ' + to_path)
    path = osp.abspath(path)
    cmd = "ln -s " + path + " " + to_path
    # print(cmd)
    proc = subprocess.Popen(cmd, shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    return proc


def tar(path, to_path=None):
    if not osp.exists(path):
        return
    if not osp.exists(to_path):
        mkdir_p(to_path)
    if os.path.exists(to_path) and not len(os.listdir(to_path)) == 0:
        rm(path)
        return
    if to_path is not None:
        cmd = "tar xf " + path + " -C " + to_path
        print(cmd)
    else:
        cmd = "tar xf " + path
    shell(cmd, block=True)
    if os.path.exists(path):
        rm(path)


def rm(path, block=True, remove=False):
    path = osp.abspath(path)
    if not osp.exists(path):
        logging.info(f'no need rm {path}')
    stdout, _ = shell('which trash', verbose=False)
    if remove:
        return shell(f'rm -rf "{path}"', block=block)
    if 'trash' not in stdout:
        dst = glob.glob('{}.bak*'.format(path))
        parsr = re.compile(r'{}.bak(\d+?)'.format(path))
        used = [0, ]
        for d in dst:
            m = re.match(parsr, d)
            if not m:
                used.append(0)
            elif m.groups()[0] == '':
                used.append(0)
            else:
                used.append(int(m.groups()[0]))
        dst_path = '{}.bak{}'.format(path, max(used) + 1)
        cmd = 'mv {} {} '.format(path, dst_path)
        return shell(cmd, block=block)
    else:
        return shell(f'trash -r "{path}"', block=block)


def show_img(path):
    from IPython.display import Image

    fig = Image(filename=path)
    return fig


def plt_imshow(img, ax=None, keep_ori_size=False, inp_mode='rgb'):
    img = to_img(img)
    if inp_mode == 'bgr':
        img = img[..., ::-1]
    if ax is None:
        h, w,  = img.shape[0], img.shape[1]
        inchh = h / 100
        inchw = w / 100
        if keep_ori_size:
            plt.figure(figsize=(inchw, inchh,))
        else:
            plt.figure()
        plt.imshow(img)
        plt.axis('off')
    else:
        ax.imshow(img)
        ax.set_yticks([])
        ax.set_xticks([])
        ax.axis('off')


def plt_imshow_board(img, ax=None, color=None):
    img = to_img(img)
    if ax is None:
        plt.figure()
        plt.imshow(img)
        plt.axis('off')
    else:
        ax.imshow(img)
        import matplotlib.patches as patches
        M, N = img.shape[0], img.shape[1]
        line = [(0, 0), (0, M),
                (N, M), (N, 0),
                ]
        path = patches.Polygon(line, facecolor='none', edgecolor=color,
                               linewidth=5, closed=True, joinstyle='round')
        ax.add_patch(path)
        ax.axis('off')
        ax.set_yticks([])
        ax.set_xticks([])
        margin = 2
        ax.set_xlim(-margin, N + margin)
        ax.set_ylim(M + margin, -margin)


def plt_imshow_tensor(imgs, ncol=10, limit=None):
    import torchvision
    if isinstance(imgs, list):
        imgs = np.asarray(imgs)
    if imgs.shape[-1] == 3:
        imgs = np.transpose(imgs, (0, 3, 1, 2))

    imgs_thumb = torchvision.utils.make_grid(
        to_torch(imgs), normalize=False, scale_each=True,
        nrow=ncol, ).numpy()
    imgs_thumb = to_img(imgs_thumb)
    maxlen = max(imgs_thumb.shape)
    if limit is not None:
        imgs_thumb = cvb.resize_keep_ar(imgs_thumb, limit, limit, )
    #     print(imgs_thumb.shape)
    plt_imshow(imgs_thumb, keep_ori_size=True)


def plt2tensor():
    import io
    from torchvision import transforms as trans
    from PIL import Image
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    roc_curve = Image.open(buf)
    roc_curve_tensor = trans.ToTensor()(roc_curve)
    return roc_curve_tensor


def to_img(img, target_shape=None):
    from PIL import Image
    img = np.asarray(img)
    img = img.copy()
    shape = img.shape
    if len(shape) == 3 and shape[-1] == 4:
        img = img[..., :3]
    if len(shape) == 3 and shape[0] == 3:
        img = img.transpose(1, 2, 0)
        img = np.array(img, order='C')
    # if img.dtype == np.float32 or img.dtype == np.float64:
    img -= img.min()
    img = img / (img.max() + 1e-6)
    img *= 255
    img = np.array(img, dtype=np.uint8)
    if len(shape) == 3 and shape[-1] == 1:
        img = img[..., 0]
    if target_shape:
        # img = np.uint8(Image.fromarray(img).resize(target_shape, Image.ANTIALIAS)) # 128,256
        img = img.astype('float32')
        img = to_torch(img).unsqueeze(0).unsqueeze(0)
        img = F.interpolate(img, size=(256, 128), mode='bilinear', align_corners=True)
        img = img.squeeze(0).squeeze(0)
        img = to_numpy(img).astype('uint8')
    return img.copy()


def plt_matshow(mat, figsize=(6, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.matshow(mat)
    ax.axis('off')

    # plt.figure(figsize=(6,6))
    # plt.matshow(mat, fignum=1)
    # plt.axis('off')
    # plt.colorbar()


def apply_colormap_on_image(org_im, activation, colormap_name='viridis', alpha=.4, thresh=30):
    """
        Apply heatmap on image
    Args:
        org_img (PIL img): Original image
        activation_map (numpy arr): Activation map (grayscale) 0-255
        colormap_name (str): Name of the colormap
    """
    import matplotlib.cm as mpl_color_map
    from PIL import Image
    org_im = Image.fromarray(to_img(org_im))
    # Get colormap
    color_map = mpl_color_map.get_cmap(colormap_name)
    no_trans_heatmap = color_map(activation)
    # Change alpha channel in colormap to make sure original image is displayed
    heatmap = copy.copy(no_trans_heatmap)
    heatmap[:, :, 3] = alpha
    heatmap[:, :, 3][activation < thresh] = 0
    heatmap = Image.fromarray((heatmap * 255).astype(np.uint8))
    no_trans_heatmap = Image.fromarray((no_trans_heatmap * 255).astype(np.uint8))

    # Apply heatmap on iamge
    heatmap_on_image = Image.new("RGBA", org_im.size)
    heatmap_on_image = Image.alpha_composite(heatmap_on_image, org_im.convert('RGBA'))
    heatmap_on_image = Image.alpha_composite(heatmap_on_image, heatmap)
    no_trans_heatmap = to_img(no_trans_heatmap)
    heatmap_on_image = to_img(heatmap_on_image)
    return no_trans_heatmap, heatmap_on_image


def show_pdf(path):
    from IPython.display import IFrame
    path = osp.relpath(path)
    return IFrame(path, width=600, height=300)


def print_graph_info():
    import tensorflow as tf
    graph = tf.get_default_graph()
    graph.get_tensor_by_name("Placeholder:0")
    layers = [op.name for op in graph.get_operations() if op.type ==
              "Placeholder"]
    print([graph.get_tensor_by_name(layer + ":0") for layer in layers])
    print([op.type for op in graph.get_operations()])
    print([n.name for n in tf.get_default_graph().as_graph_def().node])
    print([v.name for v in tf.global_variables()])
    print(graph.get_operations()[20])


def chdir_to_root(fn):
    def wrapped_fn(*args, **kwargs):
        restore_path = os.getcwd()
        os.chdir(root_path)
        res = fn(*args, **kwargs)
        os.chdir(restore_path)
        return res

    return wrapped_fn


def scp(src, dest, dry_run=False):
    cmd = ('scp -r ' + src + ' ' + dest)
    print(cmd)
    if dry_run:
        return
    return shell(cmd, block=False)


def read_list(file, delimi=" "):
    if osp.exists(file):
        lines = np.genfromtxt(file, dtype='str', delimiter=delimi)
        return lines
    else:
        return []


def cp(from_path, to):
    dst_dir = osp.dirname(to)
    if not osp.exists(dst_dir):
        mkdir_p(dst_dir)
    shell('cp -r ' + from_path + ' ' + to)


def mv(from_path, to):
    if isinstance(from_path, list):
        for from_ in from_path:
            mv(from_, to)
    elif isinstance(to, list):
        for to_ in to:
            mv(from_path, to_)
    else:
        shell(f'''mv  "{from_path}" "{to}"''')


def dict_concat(d_l):
    d1 = d_l[0].copy()
    for d in d_l[1:]:
        d1.update(d)
    return d1


def dict_update(to, from_dict, must_exist=True):
    to = to.copy()
    from_dict = from_dict.copy()
    to = edict(to)
    from_dict = edict(from_dict)
    for k, v in from_dict.items():
        if k not in to:
            if not must_exist:
                logging.debug('ori dict do not have key {}'.format(k))
            else:
                raise ValueError('ori dict do not have key {}'.format(k))
        try:
            assert to[k] == v
        except Exception as inst:
            logging.debug(
                'update ori key {} from {} to {}'.format(k, to.get(k, None), v))
            to[k] = v
    return to


def face_detect(path='/data1/xinglu/prj/test.jpg'):
    cmd = f'''
curl -X POST "https://api-cn.faceplusplus.com/facepp/v3/detect" \
-F "api_key=cmWxHgmGAIglR3iWeJSZLioxkQop4EqW" \
-F "api_secret=nluB3GvYghHG4f5qb106uKwZbpGzxq94" \
-F "image_file=@{path}" \
-F "return_landmark=1" \
-F "return_attributes=gender,age,headpose,facequality"
    '''
    out, err = shell(cmd)
    return out


def clean_name(name):
    if isinstance(name, list):
        return [clean_name(n) for n in name]
    import re
    name = re.findall('([a-zA-Z0-9/-]+)(?::\d+)?', name)[0]
    name = re.findall('([a-zA-Z0-9/-]+)(?:_\d+)?', name)[0]
    return name


class Struct(object):
    def __init__(self, entries):
        self.__dict__.update(entries)

    def __getitem__(self, item):
        return self.__dict__[item]


def dict2obj(d):
    return Struct(d)


def dict2str(others):
    name = ''
    for key, val in others.iteritems():
        name += '_' + str(key)
        if isinstance(val, dict):
            name += '_' + dict2str(val)
        elif isinstance(val, list):
            for val_ in val:
                name += '-' + str(val_)
        else:
            name += '_' + str(val)
    return name


def list2str(li, delimier=''):
    name = ''
    for name_ in li:
        name += (str(name_) + delimier)

    return name


def rsync(from_, to):
    cmd = ('rsync -avzP ' + from_ + ' ' + to)
    print(cmd)
    return shell(cmd, block=False)


def i_vis_graph(graph_def, max_const_size=32):
    """Visualize TensorFlow graph."""
    import tensorflow as tf
    from IPython.display import display, HTML, SVG
    import os

    def strip_consts(graph_def, max_const_size=32):
        """Strip large constant values from graph_def."""
        import tensorflow as tf

        strip_def = tf.GraphDef()
        for n0 in graph_def.node:
            n = strip_def.node.add()
            n.MergeFrom(n0)
            if n.op == 'Const':
                tensor = n.attr['value'].tensor
                size = len(tensor.tensor_content)
                if size > max_const_size:
                    tensor.tensor_content = tf.compat.as_bytes(
                        "<stripped %d bytes>" % size)
        return strip_def

    if hasattr(graph_def, 'as_graph_def'):
        graph_def = graph_def.as_graph_def()
    strip_def = strip_consts(graph_def, max_const_size=max_const_size)
    code = """
        <script>
          function load() {{
            document.getElementById("{id}").pbtxt = {data};
          }}
        </script>
        <link rel="import" href="https://tensorboard.appspot.com/tf-graph-basic.build.html" onload=load()>
        <div style="height:600px">
          <tf-graph-basic id="{id}"></tf-graph-basic>
        </div>
    """.format(data=repr(str(strip_def)), id='graph' + str(np.random.rand()))

    iframe = """
        <iframe seamless style="width:800px;height:620px;border:0" srcdoc="{}"></iframe>
    """.format(code.replace('"', '&quot;'))
    display(HTML(iframe))


def my_wget(fid, fname):
    shell('rm -rf /tmp/cookies.txt')
    task = shell(
        f"wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id={fid}' -O- ",
        return_msg=False
    )
    out, err = task.communicate()
    out = out.decode('utf-8')
    print(out)
    if len(re.findall(r'.*confirm=([0-9a-zA-Z_]+).*', out)) == 0:
        print('no confirm continue')
        return 100
    confirm = re.findall(r'.*confirm=([0-9a-zA-Z_]+).*', out)[0]
    if task.poll() != 0:
        print(confirm)
        raise ValueError('fail')
    task = shell(
        f"wget -c --load-cookies /tmp/cookies.txt 'https://docs.google.com/uc?export=download&confirm={confirm}&id={fid}' -O {fname}",
        block=False)
    return task


# caution: may be shallow!
def to_json_format(obj, allow_np=True):
    import collections, torch
    if isinstance(obj, np.ndarray):
        if obj.dtype == object:
            return obj.tolist()
        else:
            if allow_np:
                return np.asarray(obj, order="C")
            else:
                return to_json_format(obj.tolist())
    elif isinstance(obj, (list, tuple, collections.deque)):
        return [to_json_format(subobj, allow_np) for subobj in obj]
    elif isinstance(obj, dict):
        for key in obj.keys():
            obj[key] = to_json_format(obj[key], allow_np)
        return obj
    elif isinstance(obj, (int, str, float)):
        return obj
    elif isinstance(obj, torch.Tensor):
        return obj.cpu().numpy()
    elif isinstance(obj, np.int64):
        return int(obj)
    elif isinstance(obj, np.float32):
        return float(obj)
    elif obj is None:
        return obj
    else:
        raise ValueError(f'unkown  {type(obj)}')
    # return obj


# todo imtate this

# def default_collate(batch):
#     "Puts each data field into a tensor with outer dimension batch size"
#     if torch.is_tensor(batch[0]):
#         out = None
#         if _use_shared_memory:
#             # If we're in a background process, concatenate directly into a
#             # shared memory tensor to avoid an extra copy
#             #   batch
#             numel = sum([x.numel() for x in batch])
#             storage = batch[0].storage()._new_shared(numel)
#             out = batch[0].new(storage)
#         return torch.stack(batch, 0, out=out)
#     elif type(batch[0]).__module__ == 'numpy':
#         elem = batch[0]
#         if type(elem).__name__ == 'ndarray':
#             return torch.stack([torch.from_numpy(b) for b in batch], 0)
#         if elem.shape == ():  # scalars
#             py_type = float if elem.dtype.name.startswith('float') else int
#             return numpy_type_map[elem.dtype.name](list(map(py_type, batch)))
#     elif isinstance(batch[0], int):
#         return torch.LongTensor(batch)
#     elif isinstance(batch[0], float):
#         return torch.DoubleTensor(batch)
#     elif isinstance(batch[0], string_classes):
#         return batch
#     elif isinstance(batch[0], collections.Mapping):
#         return {key: default_collate([d[key] for d in batch]) for key in batch[0]}
#     elif isinstance(batch[0], collections.Sequence):
#         transposed = zip(*batch)
#         return [default_collate(samples) for samples in transposed]
#
#     raise TypeError(("batch must contain tensors, numbers, dicts or lists; found {}"
#                      .format(type(batch[0]))))

def preprocess(img, landmark, **kwargs):
    from skimage import transform as trans
    if isinstance(img, str):
        img = cvb.read_img(img, **kwargs)
    assert img is not None
    img = img.copy()
    # image_size = []
    # str_image_size = kwargs.get('image_size', '')
    # if len(str_image_size) > 0:
    #     image_size = [int(x) for x in str_image_size.split(',')]
    #     if len(image_size) == 1:
    #         image_size = [image_size[0], image_size[0]]
    #     assert len(image_size) == 2
    #     assert image_size[0] == 112
    #     assert image_size[0] == 112 or image_size[1] == 96
    image_size = [112, 112]
    assert len(image_size) == 2
    src = np.array([
        [30.2946, 51.6963],
        [65.5318, 51.5014],
        [48.0252, 71.7366],
        [33.5493, 92.3655],
        [62.7299, 92.2041]], dtype=np.float32)
    if image_size[1] == 112:
        src[:, 0] += 8.0
    dst = landmark.astype(np.float32)
    dst = dst.reshape(-1, 2)  # todo, this means dst mast be 5 row
    if dst.shape[0] == 3:
        src = src[[0, 1, 2], :]
    tform = trans.SimilarityTransform()
    tform.estimate(dst, src)
    M = tform.params[0:2, :]
    warped = cv2.warpAffine(img, M, (image_size[1], image_size[0]), borderValue=0.0)
    # tform3 = trans.ProjectiveTransform()
    # tform3.estimate(src, dst)
    # warped = trans.warp(img, tform3, output_shape=_shape)
    return warped


def face_orientation(frame, landmarks):
    size = frame.shape  # (height, width, color_channel)

    image_points = np.array([
        (landmarks[4], landmarks[5]),  # Nose tip
        # (landmarks[10], landmarks[11]),  # Chin
        (landmarks[0], landmarks[1]),  # Left eye left corner
        (landmarks[2], landmarks[3]),  # Right eye right corne
        (landmarks[6], landmarks[7]),  # Left Mouth corner
        (landmarks[8], landmarks[9])  # Right mouth corner
    ], dtype="double")

    model_points = np.array([
        (0.0, 0.0, 0.0),  # Nose tip
        # (0.0, -330.0, -65.0),  # Chin
        (-165.0, 170.0, -135.0),  # Left eye left corner
        (165.0, 170.0, -135.0),  # Right eye right corne
        (-150.0, -150.0, -125.0),  # Left Mouth corner
        (150.0, -150.0, -125.0)  # Right mouth corner
    ])

    # Camera internals

    center = (size[1] / 2, size[0] / 2)
    focal_length = center[0] / np.tan(60 / 2 * np.pi / 180)
    camera_matrix = np.array(
        [[focal_length, 0, center[0]],
         [0, focal_length, center[1]],
         [0, 0, 1]], dtype="double"
    )

    dist_coeffs = np.zeros((4, 1))  # Assuming no lens distortion
    (success, rotation_vector, translation_vector) = cv2.solvePnP(
        model_points, image_points, camera_matrix,
        dist_coeffs,
        # flags=cv2.SOLVEPNP_ITERATIVE
    )

    axis = np.float32([[500, 0, 0],
                       [0, 500, 0],
                       [0, 0, 500]])

    imgpts, jac = cv2.projectPoints(axis, rotation_vector, translation_vector, camera_matrix, dist_coeffs)
    modelpts, jac2 = cv2.projectPoints(model_points, rotation_vector, translation_vector, camera_matrix,
                                       dist_coeffs)
    rvec_matrix = cv2.Rodrigues(rotation_vector)[0]

    proj_matrix = np.hstack((rvec_matrix, translation_vector))
    eulerAngles = cv2.decomposeProjectionMatrix(proj_matrix)[6]

    pitch, yaw, roll = [math.radians(_) for _ in eulerAngles]

    pitch = math.degrees(math.asin(math.sin(pitch)))
    roll = -math.degrees(math.asin(math.sin(roll)))
    yaw = math.degrees(math.asin(math.sin(yaw)))

    return imgpts, modelpts, (str(int(roll)), str(int(pitch)), str(int(yaw))), (landmarks[4], landmarks[5])


def cal_sim(yyfea, yy2fea):
    from scipy.spatial.distance import cdist
    dist = cdist(yyfea, yy2fea, metric='cosine')
    cossim = 1 - dist
    return cossim


def get_normalized_pnt(nose, pnt):
    nose = np.asarray(nose).reshape(2, )
    pnt = np.asarray(pnt).reshape(2, )
    dir = pnt - nose
    norm = np.sqrt((dir ** 2).sum())
    dir /= norm
    pnt = nose + dir * 50
    return pnt


# random_colors = [ tuple(np.random.random_integers(0, 255, size=3)) for i in range(19) ]
random_colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255),
                 (171, 46, 62),
                 (105, 246, 7),
                 (19, 73, 138),
                 (31, 210, 138),
                 (35, 125, 76),
                 (86, 6, 147),
                 (249, 24, 45),
                 (241, 214, 87),
                 (102, 255, 173),
                 (202, 146, 236),
                 (163, 196, 242),
                 (24, 48, 244),
                 (187, 142, 60),
                 (20, 146, 34),
                 (226, 97, 210),
                 (184, 40, 125),
                 (208, 152, 12),
                 (108, 158, 78),
                 (91, 145, 136),
                 ]


def df_unique(df):
    def is_all_same(lst):
        lst = [lsti if not isinstance(lsti, np.ndarray) else lsti.tolist() for lsti in lst]
        res = [lsti == lst[0] for lsti in lst]
        try:
            return np.asarray(res).all()
        except Exception as e:
            print(e)

    res = []
    for j in range(df.shape[1]):
        if not is_all_same(df.iloc[:, j].tolist()):
            res.append(j)
    res = [df.columns[r] for r in res]
    df1 = df[res]
    return df1


class UniformDistribution(object):
    def __init__(self, low, high):
        assert low <= high
        self.low = low
        self.high = high

    def rvs(self, size=None, random_state=None):
        uniform = random_state.uniform if random_state else np.random.uniform
        return uniform(self.low, self.high, size)


class LogUniformDistribution(object):
    def __init__(self, low, high, precision='.1e'):
        assert low <= high
        self.low = low
        self.high = high
        self.precision = precision

    def rvs(self, size=None, random_state=None):
        uniform = random_state.uniform if random_state else np.random.uniform
        res = np.exp(uniform(np.log(self.low), np.log(self.high), size))
        # todo precision
        res = float(f'{res:.1e}')
        return res


from sklearn.model_selection import ParameterSampler, ParameterGrid


def softmax_ch(arr):
    from chainer import cuda
    from chainer import functions as F
    try:
        arr = cuda.to_cpu(arr.array)
    except:
        pass
    arr = np.array(arr, dtype=np.float32).reshape(1, -1)
    arr = F.softmax(arr)
    arr = cuda.to_cpu(arr.array)
    arr = np.array(arr).reshape(-1)
    return arr


def softmax_th(arr, dim=1, temperature=1):
    arr = np.asarray(arr, dtype=np.float32)
    if len(arr.shape) == 1:
        ndims = 1
        arr = arr.reshape(1, -1)
    else:
        ndims = 2
    arr = to_torch(arr)
    arr /= temperature
    res = F.softmax(arr, dim=dim).numpy()
    if ndims == 1:
        res = res.flatten()
    return res


def l2_normalize_th(x):
    # can only handle (128,2048) or (128,2048,8,4)
    shape = x.size()
    x1 = x.view(shape[0], -1)
    x2 = x1 / x1.norm(p=2, dim=1, keepdim=True)
    return x2.view(shape)


def l2_norm(input, axis=1, need_norm=False, ):
    norm = torch.norm(input, 2, axis, True)
    output = torch.div(input, norm)
    if need_norm:
        return output, norm
    else:
        return output


# from numba import  njit
#
# @njit
def l2_normalize_np(x):
    x = np.asarray(x)
    shape = x.shape
    x1 = x.reshape(shape[0], -1)
    norm = np.sqrt((x1 ** 2).sum(axis=1, keepdims=True))
    x2 = x1 / norm
    return x2.reshape(shape)


def get_adv(loss, inp, norm='l2', eps=.1, ):
    features_grad = torch.autograd.grad(
        outputs=loss, inputs=inp,
        create_graph=True, retain_graph=True,
        only_inputs=True
    )[0].detach()
    if 'l2' in norm:
        xa_advtrue = inp + eps * l2_normalize_th(features_grad)
    elif 'linf' in norm:
        xa_advtrue = inp + eps * torch.sign(features_grad)
    elif 'lno' in norm:
        xa_advtrue = inp + eps * (features_grad)
    else:
        raise ValueError(f'no {norm}')
    return xa_advtrue


def img2tensor():
    import io
    from PIL import Image
    buf = io.BytesIO()
    # plt.savefig(buf, format='jpeg')
    plt.savefig(buf, format='png')
    buf.seek(0)
    roc_curve = Image.open(buf)
    roc_curve_tensor = torchvision.transforms.ToTensor()(roc_curve)
    return roc_curve_tensor


class AverageMeter(object):
    """Computes and stores the average and current value"""

    def __init__(self):
        import collections
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0
        self.mem = collections.deque(maxlen=3)  # todo ?

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        ## way 1
        # val = float(val)
        # self.mem.append(val)
        # self.avg = np.mean(list(self.mem))
        ## way 2
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def extend_bbox(img_proc, bbox,
                up=.0,
                down=.0,
                rightleft=0.,
                ):
    x1, y1, x2, y2 = bbox[:4]
    img_shape = img_proc.shape
    row = y1
    col = x1
    height = y2 - y1
    width = x2 - x1
    rowc = row + height / 2
    colc = col + width / 2
    height = (1. + up + down) * height
    width = (1 + 2 * rightleft) * width
    row = rowc - height / (1. + up + down) * (.5 + up / 2 + down / 2)
    col = colc - width / 2
    row = max(row, 0)
    col = max(col, 0)
    height = min(height, img_shape[0] - row)
    width = min(width, img_shape[1] - col)
    row, col, height, width = map(lambda x: int(round(x)), [row, col, height, width])
    img_crop = img_proc[row:row + height, col:col + width, :]
    return img_crop, np.asarray([col, row, col + width, row + height])


def to_landmark5(landmark):
    assert landmark.shape[0] == 68 or landmark.shape[0] == 5
    assert landmark.shape[1] == 2
    if landmark.shape[0] == 68:
        landmark5 = np.zeros((5, 2), dtype=np.float32)
        landmark5[0] = (landmark[36] + landmark[39]) / 2
        landmark5[1] = (landmark[42] + landmark[45]) / 2
        landmark5[2] = landmark[30]
        landmark5[3] = landmark[48]
        landmark5[4] = landmark[54]
    else:
        landmark5 = landmark
    return landmark5


def update_rcparams():
    from matplotlib import rcParams
    params = {
        'axes.labelsize': 20,
        'legend.fontsize': 11,
        'xtick.labelsize': 11,
        'ytick.labelsize': 11,
        'text.usetex': True,
        # 'figure.figsize': [10, 5]
    }
    rcParams.update(params)


class knn_faiss_eu():
    def __init__(self, feats, k, index_path='', index_key='', nprobe=128, verbose=True):
        import faiss
        self.verbose = verbose
        with Timer('[faiss] build index {:3f}', verbose):
            if index_path != '' and os.path.exists(index_path):
                print('[faiss] read index from {}'.format(index_path))
                index = faiss.read_index(index_path)
            else:
                feats = feats.astype('float32')
                size, dim = feats.shape
                index = faiss.IndexFlatL2(dim)
                if index_key != '':
                    assert index_key.find('HNSW') < 0, 'HNSW returns distances insted of sims'
                    metric = faiss.METRIC_L2
                    nlist = min(4096, 8 * round(math.sqrt(size)))
                    if index_key == 'IVF':
                        quantizer = index
                        index = faiss.IndexIVFFlat(quantizer, dim, nlist, metric)
                    else:
                        index = faiss.index_factory(dim, index_key, metric)
                    if index_key.find('Flat') < 0:
                        assert not index.is_trained
                    index.train(feats)
                    index.nprobe = min(nprobe, nlist)
                    assert index.is_trained
                    print('nlist: {}, nprobe: {}'.format(nlist, nprobe))
                index.add(feats)
                if index_path != '':
                    print('[faiss] save index to {}'.format(index_path))
                    mkdir_p(index_path, delete=False)
                    faiss.write_index(index, index_path)
        with Timer('[faiss] query topk {}'.format(k) + ' {:3f} ', verbose):
            knn_ofn = index_path + '.npz'
            if os.path.exists(knn_ofn):
                print('[faiss] read knns from {}'.format(knn_ofn))
                self.knns = [(knn[0, :].astype(np.int32), knn[1, :].astype(np.float32)) \
                             for knn in np.load(knn_ofn)['data']]
            else:
                print(index)
                sims, ners = index.search(feats, k=k)  # this sims is l2 distance in fact
                self.knns = [(np.array(ner, dtype=np.int32), np.array(sim, dtype=np.float32)) \
                             for ner, sim in zip(ners, sims)]
                self.knns2 = [ners, sims]


class knn_faiss():
    def __init__(self, feats, k, probe_feats=None, index_path='', verbose=True):
        import faiss
        feats = np.asarray(feats, np.float32)
        if probe_feats is not None:
            probe_feats = np.asarray(probe_feats, np.float32)
        self.verbose = verbose
        print('-' * 30)
        with Timer('[faiss] build index {:.3f}', verbose):
            if index_path != '' and os.path.exists(index_path):
                print('[faiss] read index from {}'.format(index_path))
                index = faiss.read_index(index_path)
            else:
                size, dim = feats.shape
                index = faiss.IndexFlatL2(dim)
                index.add(feats)
                if index_path != '':
                    print('[faiss] save index to {}'.format(index_path))
                    mkdir_p(index_path, delete=False)
                    faiss.write_index(index, index_path)
        with Timer('[faiss] query topk ' + str(k) + ' {:.3f}', verbose):
            knn_ofn = index_path + '.npz'
            if os.path.exists(knn_ofn):
                print('[faiss] read knns from {}'.format(knn_ofn))
                self.knns = [(knn[0, :].astype(np.int32), knn[1, :].astype(np.float32))
                             for knn in np.load(knn_ofn)['data']]
            else:
                print(index)
                if probe_feats is not None:
                    dists_or_sims, ners = index.search(probe_feats, k=k)
                else:
                    dists_or_sims, ners = index.search(feats, k=k)
                self.knns = [(np.array(ner, dtype=np.int32), np.array(dist_or_sim, dtype=np.float32))
                             for ner, dist_or_sim in zip(ners, dists_or_sims)]
                self.knns2 = [ners, dists_or_sims]


if __name__ == '__main__':
    print(show_dev())
