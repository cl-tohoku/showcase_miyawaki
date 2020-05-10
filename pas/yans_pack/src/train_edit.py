# coding: utf-8

import argparse
import os
import sys
from os import path
import time
import csv, json, ijson
import math

import torch.nn as nn
from torch import autograd
import torch.nn.functional as F

from arg_edit import *
from model_edit import E2EStackedBiRNN

import numpy as np
from eval_edit import evaluate_multiclass_without_none

max_sentence_length = 90
prediction_model_id = 3


def train(out_dir, data_train, data_dev, model, model_id, epoch, lr_start, lr_min, threshold, iterate_num, loss_type, LOAD, base_model):

    len_train = len(data_train)
    len_dev = len(data_dev)
    pred_count_train = 0
    early_stopping_thres = 4
    early_stopping_count = 0
    best_performance = -1.0
    best_epoch = 0
    best_thres = [0.0, 0.0]
    best_lr = lr_start
    lr = lr_start
    lr_reduce_factor = 0.5
    lr_epsilon = lr_min * 1e-4

    ## load ##
    print("LOAD ... ", LOAD)
    if LOAD:
        LOAD_MODEL = out_dir + "/edit/model-" + get_load_model(model_id) + ".h5"
        if os.path.exists(LOAD_MODEL):
            base_model.load_state_dict(torch.load(LOAD_MODEL))
            base_model.eval()
            print(pycolor.GREEN + "LOAD from: " + str(LOAD_MODEL) + pycolor.END)
        else:
            print("### FileNotFound ###")

    header = ['','p', 'r', 'f1', 'p_p', 'ppnp', 'pppn']
    with open(out_dir + '/edit/log/model-' + model_id + '.csv', 'x') as csv_f:
        writer = csv.writer(csv_f, delimiter='\t')
        writer.writerow(header)
        writer.writerow([])
    print(model_id, end="\n\n", file=open(out_dir + '/edit/log/model-'+model_id+'_loss.txt', 'x'))


    loss_function = nn.NLLLoss()

    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=lr_start)
    losses_total = []

    thres_set_ga = list(map(lambda n: n / 100.0, list(range(10, 71, 1))))
    thres_set_wo = list(map(lambda n: n / 100.0, list(range(20, 86, 1))))
    thres_set_ni = list(map(lambda n: n / 100.0, list(range(0, 61, 1))))
    thres_lists = [thres_set_ga, thres_set_wo, thres_set_ni]
    labels = ["ga", "wo", "ni", "all"]

    for ep in range(epoch):
        start_time = time.time()
        total_loss = torch.Tensor([0])
        early_stopping_count += 1
        # print("### ", ep, " ###", file=open('./result/edit/hoge/'+model_id+'_WRjudge.txt', 'a'))
        print(pycolor.BLUE+model_id, pycolor.YELLOW+'epoch {0}'.format(ep + 1)+pycolor.END, flush=True)

        print('Train...', flush=True)
        data_train.create_batches()
        #random.shuffle(data_train)
        pred_count_train = 0
        arg_count_train = 0
        sent_count = 0
        count = 0
        dic_file = {}

        ### 訓練モード ###
        model.train()
        for xss, yss in tqdm(data_train, total=len_train, mininterval=5):

            if xss[0].size(1) > max_sentence_length:
                continue

            pred_count_train += xss[0].size(0)
            for t in yss:
                arg_count_train += int(torch.sum(t > 0))

            optimizer.zero_grad()   # 勾配初期化
            model.zero_grad()

            if torch.cuda.is_available():
                yss = [autograd.Variable(ys).cuda() for ys in yss]
            else:
                yss = [autograd.Variable(ys) for ys in yss]

            # print("### iterate in epoch ###")
            if LOAD:
                init_vec, _ = base_model(xss, torch.tensor([]), init=True)
                temp = torch.stack([i for i in init_vec])
            else:
                temp = torch.tensor([])
            

            scores, _ = model(xss, temp)     # list[score_0, score_1, ...]

            # print("### loss ###")
            if loss_type == "sum":
                losses = []
                for it in range(iterate_num):
                    loss = 0
                    for batch_idx in range(len(yss)):
                        import ipdb; ipdb.set_trace()
                        loss += loss_function(scores[it][batch_idx], yss[batch_idx])
                    #loss.backward()
                    losses.append(loss)
                loss = sum(losses)
                loss.backward()
            elif loss_type == "last":
                loss = 0
                for batch_idx in range(len(yss)):
                    loss += loss_function(scores[-1][batch_idx], yss[batch_idx])
                loss.backward()

            ### update ###
            torch.nn.utils.clip_grad_norm(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.data.cpu()
            count += 1

        print("loss:", total_loss[0], "lr:", lr, "time:", round(time.time()-start_time,2))
        print(str(float(total_loss[0])), file=open('./result/edit/log/model-'+model_id+'_loss.txt', 'a'))
        losses_total.append(total_loss)
        print("pred_count_train: {}\targs_count_train: {}".format(pred_count_train, arg_count_train), file=open("experiment_settings.txt", "a"), end="\n")

        print('Test...', flush=True)

        ### 評価モード ###
        data_dev.create_batches()
        model.eval()
        if LOAD:
            thres, obj_score, num_test_batch_instance = evaluate_multiclass_without_none(model, data_dev, len_dev, labels,thres_lists, model_id, threshold, iterate_num, ep, base=base_model)
        else:
            thres, obj_score, num_test_batch_instance = evaluate_multiclass_without_none(model, data_dev, len_dev, labels,thres_lists, model_id, threshold, iterate_num, ep)

        f = obj_score * 100
        if f > best_performance:
            best_performance = f
            early_stopping_count = 0
            best_epoch = ep + 1
            best_thres = thres
            best_lr = lr
            print("save model", flush=True)
            torch.save(model.state_dict(), out_dir + "/edit/model-" + model_id + ".h5")
        elif early_stopping_count >= early_stopping_thres:
            # break
            if lr > lr_min + lr_epsilon:
                new_lr = lr * lr_reduce_factor
                lr = max(new_lr, lr_min)
                print("load model: epoch{0}".format(best_epoch), flush=True)
                model.load_state_dict(torch.load(out_dir + "/edit/model-" + model_id + ".h5"))
                optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=lr)
                early_stopping_count = 0
            else:
                break
        print(model_id, "\tcurrent best epoch", best_epoch, "\t", best_thres, "\t", "lr:", best_lr, "\t",
              "f:", best_performance)

    print(model_id, "\tbest in epoch", best_epoch, "\t", best_thres, "\t", "lr:", best_lr, "\t",
          "f:", best_performance)

    return {model_id: {"best_epoch":best_epoch, "best_thres":best_thres, "best_lr":best_lr, "best_preformance":best_performance}}


def get_load_model(model_id):
    import re
    base_id = "_th0.0_it1_".join(re.split("_th0\.._it._", model_id)).rsplit("_", 2)[0] + "_preFalse_loss-last"
    print(pycolor.GREEN + base_id + pycolor.END)
    return base_id

def set_log_file(args, tag, model_id):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    fd = os.open(args.out_dir + '/log/log-' + tag + '-' + model_id + ".txt", os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    os.dup2(fd, sys.stdout.fileno())
    os.dup2(fd, sys.stderr.fileno())


def create_pretrained_model_id(args, model_name):
    sub_model_no = "" if args.sub_model_number == -1 \
        else "_sub{0}".format(args.sub_model_number)

    depth = "{0}-{1}-{2}".format(args.depth, args.depth_path, args.depth_arg)

    return "{0}_vu{1}_{2}_{3}_lr{4}_du{5}_ve{6}_b{7}_size{8}{9}".format(
        model_name,
        args.vec_size_u, depth,
        args.optim, 0.0002,
        args.drop_u,
        args.vec_size_e,
        args.batch_size,
        100,
        sub_model_no
    )


def create_model_id(args):
    sub_model_no = "" if args.sub_model_number == -1 \
        else "_sub{0}".format(args.sub_model_number)

    depth = args.depth
    dim = 've{0}_vu{0}'.format(args.vec_size_u)

    return "{0}_{1}_{2}_depth{3}_{4}_lr{5}_du{6}_dh{7}_{8}_size{9}{10}_th{11}_it{12}_rs{13}_pre{14}_loss-{15}_null-{16}".format(
        args.free,
        args.model_name,
        dim, depth,
        args.optim, args.lr,
        args.drop_u,
        args.drop_h,
        args.fixed_word_vec,
        args.data_size,
        sub_model_no,
        args.threshold,
        args.iter,
        SEED, args.load,
        args.loss_type,
        args.null_label
    )


def create_arg_parser():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--data', dest='data_path', type=path.abspath,
                        help='data path')
    parser.add_argument('--model_no', "-mn", dest='sub_model_number', type=int,
                        help='sub-model number for ensembling', default=-1)
    parser.add_argument('--size', '-s', dest='data_size', type=int,
                        default=100,
                        help='data size (%)')
    parser.add_argument('--model', '-m', dest='model_name', type=str,
                        default="path-pair-bin",
                        help='model name')
    parser.add_argument('--iter', '-it', dest='iter', type=int,
                        default=3,
                        help='number of iteration')
    parser.add_argument('--epoch', '-e', dest='max_epoch', type=int,
                        default=150,
                        help='max epoch')
    parser.add_argument('--vec_e', '-ve', dest='vec_size_e', type=int,
                        default=256,
                        help='word embedding size')
    parser.add_argument('--vec_u', '-vu', dest='vec_size_u', type=int,
                        default=256,
                        help='unit vector size in rnn')
    parser.add_argument('--depth', '-dep', '-d', dest='depth', type=int,
                        default=10,
                        help='the number of hidden layer')
    parser.add_argument('--depth-path', '-dp', '-dp', dest='depth_path', type=int,
                        default=2,
                        help='the number of hidden layer')
    parser.add_argument('--optimizer', '-o', dest='optim', type=str,
                        default="adagrad",
                        help='optimizer')
    parser.add_argument('--lr', '-l', dest='lr', type=float,
                        default=0.005,
                        help='learning rate')
    parser.add_argument('--dropout-u', '-du', dest='drop_u', type=float,
                        default=0.2,
                        help='dropout rate of LSTM unit')
    parser.add_argument('--dropout-h', '-dh', dest='drop_h', type=float,
                        default=0.0,
                        help='dropout rate of hidden layers')
    parser.add_argument('--dropout-attention', '-da', dest='drop_a', type=float,
                        default=0.2,
                        help='dropout rate of attention softmax layer')
    parser.add_argument('--threshold', '-th', dest='threshold', type=float,
                        default=10,
                        help='threshold of score')
    parser.add_argument('--batch', '-b', dest='batch_size', type=int,
                        default=128,
                        help='batch size')
    parser.add_argument('--loss', '-loss', dest='loss_type', type=str,
                        default="sum",
                        help='loss_type (sum or last)')
    parser.add_argument('--load', '-load', dest='load', type=str,
                        default="False",
                        help='use pretrained base score into initialized vec')
    parser.add_argument('--null_label', '-null_label', dest='null_label', type=str,
                        default="inc",
                        help="ex / inc null label")
    parser.add_argument('--free', '-free', dest='free', type=str,
                        default="",
                        help='free model name')
    parser.add_argument('--gpu', '-g', dest='gpu', type=int,
                        default='-1',
                        help='GPU ID for execution')
    parser.add_argument('--tune-word-vec', '-twv', dest='fixed_word_vec', action='store_false',
                        help='do not re-train word vec')

    parser.add_argument('--out_dir', type=str, default='result')

    parser.set_defaults(fixed_word_vec=True)

    return parser

class pycolor:
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    PURPLE = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    END = '\033[0m'
    BOLD = '\038[1m'
    UNDERLINE = '\033[4m'
    INVISIBLE = '\033[08m'
    REVERCE = '\033[07m'

def get_bool(string):
    if string == "True":
        return True
    elif string == "False":
        return False

def run():
    parser = create_arg_parser()
    args = parser.parse_args()
    model_id = create_model_id(args)
    gpu_id = 0

    LOAD = get_bool(args.load)

    if not path.exists(args.out_dir):
        os.mkdir(args.out_dir)
        print("# Make directory: {}".format(args.out_dir))
    if not path.exists(args.out_dir + "/log"):
        os.mkdir(args.out_dir + "/log")
        print("# Make directory: {}".format(args.out_dir + "/log"))

    torch.manual_seed(args.sub_model_number)
    # set_log_file(args, "train", model_id)

    data_train = end2end_dataset(args.data_path + "/train.json", args.data_size)
    data_dev = end2end_dataset(args.data_path + "/dev.json", args.data_size)

    model: nn.Module = None
    base_model: nn.Module = []

    if args.model_name == 'e2e-stack':
        data_train = NtcBucketIterator(data_train, args.batch_size, shuffle=True)
        data_dev = NtcBucketIterator(data_dev, args.batch_size)
        #data_train = list(end2end_single_seq_instance(data_train, e2e_single_seq_sentence_batch))
        #data_dev = list(end2end_single_seq_instance(data_dev, e2e_single_seq_sentence_batch))
        word_embedding_matrix = pretrained_word_vecs(args.data_path, "/wordIndex.txt", args.vec_size_e)

        ### load model ###
        model = E2EStackedBiRNN(args.vec_size_u, args.depth, 4, word_embedding_matrix, args.drop_u, args.fixed_word_vec, args.iter, args.threshold, args.null_label)
        base_model = E2EStackedBiRNN(args.vec_size_u, args.depth, 4, word_embedding_matrix, args.drop_u, args.fixed_word_vec, 1, args.threshold, args.null_label)

    if torch.cuda.is_available():
        model = model.cuda()
        with torch.cuda.device(gpu_id):
            result = train(args.out_dir, data_train, data_dev, model, model_id, args.max_epoch, args.lr, args.lr / 20, args.threshold, args.iter, args.loss_type, LOAD, base_model)
    else:
        result = train(args.out_dir, data_train, data_dev, model, model_id, args.max_epoch, args.lr, args.lr / 20, args.threshold, args.iter, args.loss_type, LOAD, base_model)

    return result


if __name__ == '__main__':

    SEEDS = (2016, 2018, 2020)
    RESULTS = []

    for SEED in SEEDS:
        random.seed(SEED)
        np.random.seed(SEED)
        RESULT = run()
        RESULTS.append(RESULT)

    F1s = []
    for SEED, res in zip(SEEDS, RESULTS):
        print(SEED, res)
        for v in res.values():
            F1s.append(v.get("best_performance"))

    from statistics import mean, median,variance,stdev
    print(pycolor.GREEN + "SEED:{}\tF1:{}\tstd:{}".format(len(SEEDS), mean(F1s), stdev(F1s)) + pycolor.END)
