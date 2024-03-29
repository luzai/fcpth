#!/usr/bin/env python3
# -*- coding: future_fstrings -*-

from lz import *
from config import conf
import argparse
from pathlib import Path

torch.backends.cudnn.benchmark = True


def log_conf(conf):
    conf2 = {k: v for k, v in conf.items() if not isinstance(v, (dict, np.ndarray))}
    logging.info(f'training conf is {conf2}')

from exargs import  parser

if __name__ == '__main__':
    args = parser.parse_args()
    if args.work_path:
        conf.work_path = Path(args.work_path)
        conf.model_path = conf.work_path / 'models'
        conf.log_path = conf.work_path / 'log'
        conf.save_path = conf.work_path / 'save'
    else:
        args.work_path = conf.work_path
    conf.update(args.__dict__)
    if conf.local_rank is not None:
        torch.cuda.set_device(conf.local_rank)
        torch.distributed.init_process_group(backend='nccl',
                                             init_method="env://")
        if torch.distributed.get_rank() != 0:
            set_stream_logger(logging.WARNING)
    from Learner import *

    learner = face_cotching(conf, )
    # learner = face_cotching_head(conf, )
    ress = {}
    for p in [
        # 'mbfc.retina.cl.arc.cotch.cont',
        # 'mbfc.cotch.mual.1e-3',
    ]:
        learner.load_state(
            resume_path=Path(f'work_space/{p}/models/'),
            load_optimizer=False,
            load_head=True,  # todo note !!!
            load_imp=False,
            latest=True,
            load_model2=True,
        )
        # res = learner.validate_ori(conf)
        # ress[p] = res
        # logging.warning(f'{p} res: {res}')
    print(ress)
    # learner.calc_img_feas(out='work_space/casia.r50.arc.h5')
    # exit(0)

    # learner.init_lr()
    # conf.tri_wei = 0
    # log_conf(conf)
    # learner.train(conf, 1, name='xent')

    learner.init_lr()
    log_conf(conf)
    # learner.warmup(conf, conf.warmup)
    # learner.train(conf, conf.epochs)
    # learner.train_dist(conf, conf.epochs)
    # learner.train_simple(conf, conf.epochs)
    # learner.train_cotching(conf, conf.epochs)
    # learner.train_cotching_accbs(conf, conf.epochs)
    if args.train_mode == 'mual':
        learner.train_mual(conf, conf.epochs)
    else:
        learner.train_cotching_accbs_v2(conf, conf.epochs)
    # learner.train_ghm(conf, conf.epochs)
    # learner.train_with_wei(conf, conf.epochs)
    # learner.train_use_test(conf, conf.epochs)
    # res = learner.validate_ori(conf)

    from tools.test_ijbc3 import test_ijbc3

    res = test_ijbc3(conf, learner)

    # log_lrs, losses = learner.find_lr(conf,
    #                                   # final_value=100,
    #                                   num=200,
    #                                   bloding_scale=1000)
    # best_lr = 10 ** (log_lrs[np.argmin(losses)])
    # print(best_lr)
    # conf.lr = best_lr
    # learner.push2redis()
