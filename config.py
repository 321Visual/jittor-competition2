import argparse
import pickle
import os
import utils.utils as utils


def read_arguments(train=True):
    parser = argparse.ArgumentParser()
    parser = add_all_arguments(parser, train)
    parser.add_argument('--phase', type=str, default='train')
    opt = parser.parse_args()

    # 在这里指定继续训练
    opt.continue_train = False

    if train:
        set_dataset_default_lm(opt, parser)
        if opt.continue_train:
            update_options_from_file(opt, parser)

    opt = parser.parse_args()
    opt.phase = 'train' if train else 'test'
    if train:
        opt.loaded_latest_iter = 0 if not opt.continue_train else load_iter(opt)
    utils.fix_seed(opt.seed)
    opt.no_EMA = False

    #在这里进行训练参数指定，单卡训练可以将batch_size 设置为1

    opt.checkpoints_dir = './checkpoints'
    opt.freq_val = 1500
    opt.which_iter = -1
    opt.batch_size = 6
    opt.lambda_labelmix = 10
    opt.EMA_decay = 0.9999
    opt.lr_d = 0.0004
    opt.lr_g = 0.0001
    opt.freq_save_ckpt = 1500

    print_options(opt, parser)
    if train:
        save_options(opt, parser)
    return opt


def add_all_arguments(parser, train):
    # --- general options ---

    parser.add_argument("--input_path", type=str, default="/data/temp/data/test_b")
    parser.add_argument("--output_path", type=str, default="./results")
    parser.add_argument('--name', type=str, default='competition',
                        help='name of the experiment. It decides where to store samples and models')
    parser.add_argument('--checkpoints_dir', type=str, default='./checkpoints',
                        help='models are saved here')
    # parser.add_argument('--dataroot', type=str, default='/data/temp/data',
    #                     help='path to dataset root')
    parser.add_argument('--seed', type=int, default=41,
                        help='random seed')
    parser.add_argument('--no_spectral_norm', action='store_true',  # todo 不好用就关闭
                        help='this option deactivates spectral norm in all layers')
    parser.add_argument('--batch_size', type=int, default=5,
                        help='input batch size')
    parser.add_argument('--dataset_mode', type=str, default='competition',
                        help='this option indicates which dataset should be loaded')
    parser.add_argument('--no_flip', action='store_true',
                        help='if specified, do not flip the images for data argumentation')
    parser.add_argument('--n_cpu', type=int, default=8,
                        help='num works of dataloader')
    parser.add_argument('--which_iter', type=int, default=0, help='which epoch to load when continue_train')

    parser.add_argument("--img_height", type=int, default=384,  # 384
                        help="size of image height")
    parser.add_argument("--img_width", type=int, default=512,  # 512
                        help="size of image width")
    parser.add_argument("--channels", type=int, default=3,
                        help="number of image channels")

    # for generator
    parser.add_argument('--num_res_blocks', type=int, default=6, help='number of residual blocks in G and D')
    parser.add_argument('--channels_G', type=int, default=64, help='# of gen filters in first conv layer in generator')
    parser.add_argument('--param_free_norm', type=str, default='batch',  # todo 调整这里优化模型  关联在norms中的get_norm_layer
                        help='which norm to use in generator before SPADE')
    parser.add_argument('--spade_ks', type=int, default=3, help='kernel size of convs inside SPADE')
    parser.add_argument('--no_EMA', action='store_true',  # todo 开启ema
                        help='if specified, do *not* compute exponential moving averages')
    parser.add_argument('--EMA_decay', type=float, default=0.9999, help='decay in exponential moving averages')
    parser.add_argument('--no_3dnoise', action='store_true', default=False,
                        help='if specified, do *not* concatenate noise to label maps')
    parser.add_argument('--z_dim', type=int, default=64, help="dimension of the latent z vector")

    if train:
        parser.add_argument('--freq_print', type=int, default=1, help='frequency of showing training results')
        parser.add_argument('--freq_save_ckpt', type=int, default=5, help='frequency of saving the checkpoints')
        parser.add_argument('--freq_save_latest', type=int, default=500, help='frequency of saving the latest model')
        parser.add_argument('--freq_smooth_loss', type=int, default=250, help='smoothing window for loss visualization')
        parser.add_argument('--freq_save_loss', type=int, default=2500, help='frequency of loss plot updates')
        parser.add_argument('--freq_val', type=int, default=100, help='frequency of loss plot updates')
        parser.add_argument('--freq_fid', type=int, default=2,
                            help='frequency of saving the fid score (in training iterations)')
        parser.add_argument('--continue_train', action='store_true', help='resume previously interrupted training')
        parser.add_argument('--num_epochs', type=int, default=200, help='number of epochs to train')
        parser.add_argument('--beta1', type=float, default=0.0, help='momentum term of adam')
        parser.add_argument('--beta2', type=float, default=0.999, help='momentum term of adam')
        parser.add_argument('--lr_g', type=float, default=0.0001, help='G learning rate, default=0.0001')
        parser.add_argument('--lr_d', type=float, default=0.0004, help='D learning rate, default=0.0004')

        parser.add_argument('--channels_D', type=int, default=64,
                            help='# of discrim filters in first conv layer in discriminator')
        parser.add_argument('--add_vgg_loss', action='store_true', help='if specified, add VGG feature matching loss')
        parser.add_argument('--lambda_vgg', type=float, default=10.0, help='weight for VGG loss')
        parser.add_argument('--no_balancing_inloss', action='store_true', default=False,
                            help='if specified, do *not* use class balancing in the loss function')
        parser.add_argument('--no_labelmix', action='store_true', default=False,
                            help='if specified, do *not* use LabelMix')
        parser.add_argument('--lambda_labelmix', type=float, default=10.0, help='weight for LabelMix regularization')
        # parser.add_argument('--no_lambda_pixel', action='store_true', default=False,
        #                     help='if specified, do *not* use lambda_pixel')
        # parser.add_argument('--lambda_pixel', type=float, default=0.0,
        #                     help="Loss weight of L1 pixel-wise loss between translated image and real image")

    else:
        parser.add_argument('--results_dir', type=str, default='./results/', help='saves testing results here.')
        parser.add_argument('--ckpt_iter', type=str, default='best', help='which epoch to load to evaluate a model')
    return parser


def set_dataset_default_lm(opt, parser):
    if opt.dataset_mode == "ade20k":
        parser.set_defaults(lambda_labelmix=10.0)
        parser.set_defaults(EMA_decay=0.9999)
    if opt.dataset_mode == "competition":
        # parser.set_defaults(lr_g=0.0004)
        parser.set_defaults(lambda_labelmix=5.0)
        parser.set_defaults(freq_fid=50)
        parser.set_defaults(EMA_decay=0.999)
    if opt.dataset_mode == "coco":
        parser.set_defaults(lambda_labelmix=10.0)
        parser.set_defaults(EMA_decay=0.9999)
        parser.set_defaults(num_epochs=100)


def save_options(opt, parser):
    path_name = os.path.join(opt.checkpoints_dir, opt.name)
    os.makedirs(path_name, exist_ok=True)
    with open(path_name + '/opt.txt', 'wt') as opt_file:
        for k, v in sorted(vars(opt).items()):
            comment = ''
            default = parser.get_default(k)
            if v != default:
                comment = '\t[default: %s]' % str(default)
            opt_file.write('{:>25}: {:<30}{}\n'.format(str(k), str(v), comment))

    with open(path_name + '/opt.pkl', 'wb') as opt_file:
        pickle.dump(opt, opt_file)


def update_options_from_file(opt, parser):
    new_opt = load_options(opt)
    for k, v in sorted(vars(opt).items()):
        if hasattr(new_opt, k) and v != getattr(new_opt, k):
            new_val = getattr(new_opt, k)
            parser.set_defaults(**{k: new_val})
    return parser


def load_options(opt):
    file_name = os.path.join(opt.checkpoints_dir, opt.name, "opt.pkl")
    new_opt = pickle.load(open(file_name, 'rb'))
    return new_opt


def load_iter(opt):
    if opt.which_iter == -1:
        with open(os.path.join(opt.checkpoints_dir, opt.name, "latest_iter.txt"), "r") as f:
            res = int(f.read())
            return res
    else:
        return int(opt.which_iter)


def print_options(opt, parser):
    message = ''
    message += '----------------- Options ---------------\n'
    for k, v in sorted(vars(opt).items()):
        comment = ''
        default = parser.get_default(k)
        if v != default:
            comment = '\t[default: %s]' % str(default)
        message += '{:>25}: {:<30}{}\n'.format(str(k), str(v), comment)
    message += '----------------- End -------------------'
    print(message)
