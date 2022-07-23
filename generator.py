import jittor.nn as nn
import norms
import jittor


class OASIS_Generator(nn.Module):
    def __init__(self, opt):
        super().__init__()
        self.opt = opt
        # sp_norm = norms.get_spectral_norm(opt)
        ch = opt.channels_G
        self.channels = [16 * ch, 16 * ch, 16 * ch, 8 * ch, 4 * ch, 2 * ch, 1 * ch]
        self.init_W, self.init_H = self.compute_latent_vector_size(opt)
        self.conv_img = nn.Conv2d(self.channels[-1], 3, 3, padding=1)
        self.up = nn.Upsample(scale_factor=2)
        self.body = nn.ModuleList([])
        for i in range(len(self.channels) - 1):
            self.body.append(ResnetBlock_with_SPADE(self.channels[i], self.channels[i + 1], opt))
        if not self.opt.no_3dnoise:
            self.fc = nn.Conv2d(self.opt.semantic_nc + self.opt.z_dim, 16 * ch, 3, padding=1)
        else:
            self.fc = nn.Conv2d(self.opt.semantic_nc, 16 * ch, 3, padding=1)

    def compute_latent_vector_size(self, opt):
        w = opt.crop_size // (2 ** (opt.num_res_blocks - 1))
        h = round(w / opt.aspect_ratio)
        return h, w

    def execute(self, input, z=None):
        seg = input
        if not self.opt.no_3dnoise:
            z = jittor.randn(seg.shape[0], self.opt.z_dim, dtype="float32")
            z = z.view((z.shape[0], self.opt.z_dim, 1, 1))
            z = z.expand(z.shape[0], self.opt.z_dim, seg.shape[2], seg.shape[3])
            seg = jittor.concat((z, seg), dim=1)
        x = jittor.nn.interpolate(X=seg, size=(self.init_W, self.init_H))
        x = self.fc(x)
        for i in range(self.opt.num_res_blocks):
            x = self.body[i](x, seg)
            if i < self.opt.num_res_blocks - 1:
                x = self.up(x)
        x = self.conv_img(nn.leaky_relu(x, 2e-1))
        x = jittor.tanh(x)
        return x


class ResnetBlock_with_SPADE(nn.Module):
    def __init__(self, fin, fout, opt):
        super().__init__()
        self.opt = opt
        self.learned_shortcut = (fin != fout)
        fmiddle = min(fin, fout)
        sp_norm = norms.spectral_norm
        self.conv_0 = nn.Conv2d(fin, fmiddle, kernel_size=3, padding=1)
        self.conv_1 = nn.Conv2d(fmiddle, fout, kernel_size=3, padding=1)
        if self.learned_shortcut:
            self.conv_s = nn.Conv2d(fin, fout, kernel_size=1, bias=False)

        spade_conditional_input_dims = opt.semantic_nc
        if not opt.no_3dnoise:
            spade_conditional_input_dims += opt.z_dim

        self.norm_0 = norms.SPADE(opt, fin, spade_conditional_input_dims)
        self.norm_1 = norms.SPADE(opt, fmiddle, spade_conditional_input_dims)
        if self.learned_shortcut:
            self.norm_s = norms.SPADE(opt, fin, spade_conditional_input_dims)
        self.activ = nn.LeakyReLU(0.2)

    def execute(self, x, seg):
        if self.learned_shortcut:
            x_s = self.conv_s(self.norm_s(x, seg))
        else:
            x_s = x
        dx = self.conv_0(self.activ(self.norm_0(x, seg)))
        dx = self.conv_1(self.activ(self.norm_1(dx, seg)))
        out = x_s + dx
        return out

# class ResnetBlock_with_SPADE(nn.Module):
#     def __init__(self, fin, fout, opt):
#         super().__init__()
#         self.opt = opt
#         self.learned_shortcut = (fin != fout)
#         fmiddle = min(fin, fout)
#         sp_norm = norms.spectral_norm
#         self.conv_0 = sp_norm(nn.Conv2d(fin, fmiddle, kernel_size=3, padding=1))
#         self.conv_1 = sp_norm(nn.Conv2d(fmiddle, fout, kernel_size=3, padding=1))
#         if self.learned_shortcut:
#             self.conv_s = sp_norm(nn.Conv2d(fin, fout, kernel_size=1, bias=False))
#
#         spade_conditional_input_dims = opt.semantic_nc
#         if not opt.no_3dnoise:
#             spade_conditional_input_dims += opt.z_dim
#
#         self.norm_0 = norms.SPADE(opt, fin, spade_conditional_input_dims)
#         self.norm_1 = norms.SPADE(opt, fmiddle, spade_conditional_input_dims)
#         if self.learned_shortcut:
#             self.norm_s = norms.SPADE(opt, fin, spade_conditional_input_dims)
#         self.activ = nn.LeakyReLU(0.2)
#
#     def execute(self, x, seg):
#         if self.learned_shortcut:
#             x_s = self.conv_s(self.norm_s(x, seg))
#         else:
#             x_s = x
#         dx = self.conv_0(self.activ(self.norm_0(x, seg)))
#         dx = self.conv_1(self.activ(self.norm_1(dx, seg)))
#         out = x_s + dx
#         return out

# class ResnetBlock_with_SPADE(nn.Module):
#     def __init__(self, fin, fout, opt):
#         super().__init__()
#         self.opt = opt
#         self.learned_shortcut = (fin != fout)
#         fmiddle = min(fin, fout)
#         # sp_norm = norms.get_spectral_norm(opt)
#         self.conv_0 = nn.Conv2d(fin, fmiddle, kernel_size=3, padding=1)
#         # self.bn_0 = nn.BatchNorm2d(num_features=fmiddle, eps=1e-05, momentum=0.1, affine=True)
#         # self.relu_0 = nn.LeakyReLU(0.2)
#         # self.conv_0 = sp_norm(nn.Conv2d(fin, fmiddle, kernel_size=3, padding=1))
#         self.conv_1 = nn.Conv2d(fmiddle, fout, kernel_size=3, padding=1)
#         # self.bn_1 = nn.BatchNorm2d(num_features=fout, eps=1e-05, momentum=0.1, affine=True)
#         # self.relu_1 = nn.LeakyReLU(0.2)
#
#
#         # self.conv_1 = sp_norm(nn.Conv2d(fmiddle, fout, kernel_size=3, padding=1))
#         if self.learned_shortcut:
#             self.conv_s = nn.Conv2d(fin, fout, kernel_size=1, bias=False)
#             # self.bn_s = nn.BatchNorm2d(num_features=fout, eps=1e-05, momentum=0.1, affine=True)
#             # self.relu_s = nn.LeakyReLU(0.2)
#
#             # self.conv_s = sp_norm(nn.Conv2d(fin, fout, kernel_size=1, bias=False))
#
#         spade_conditional_input_dims = opt.semantic_nc
#         if not opt.no_3dnoise:
#             spade_conditional_input_dims += opt.z_dim
#
#         self.norm_0 = norms.SPADE(opt, fin, spade_conditional_input_dims)
#         self.norm_1 = norms.SPADE(opt, fmiddle, spade_conditional_input_dims)
#         if self.learned_shortcut:
#             self.norm_s = norms.SPADE(opt, fin, spade_conditional_input_dims)
#         self.activ = nn.LeakyReLU(0.2)
#
#     def execute(self, x, seg):
#         if self.learned_shortcut:
#             x_s = self.conv_s(self.norm_s(x, seg))
#             # x_s = self.bn_s(x_s)
#             # x_s = self.relu_s(x_s)
#         else:
#             x_s = x
#         dx = self.conv_0(self.activ(self.norm_0(x, seg)))
#         # dx = self.bn_0(dx)
#         # dx = self.relu_0(dx)
#         dx = self.conv_1(self.activ(self.norm_1(dx, seg)))
#         # dx = self.bn_1(dx)
#         # dx = self.relu_1(dx)
#         out = x_s + dx
#         return out
