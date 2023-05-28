import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), ".")))

from torch import nn, Tensor
from torchvision.ops.misc import Conv2dNormActivation

import torch
import torch.nn as nn

try:
    from inplace_abn import InPlaceABN
except ImportError:
    InPlaceABN = None


class DropPath(nn.Module):
    """Drop paths (Stochastic Depth) per sample (when applied in main path of residual blocks).
    Copied from timm
    This is the same as the DropConnect impl I created for EfficientNet, etc networks, however,
    the original name is misleading as 'Drop Connect' is a different form of dropout in a separate paper...
    See discussion: https://github.com/tensorflow/tpu/issues/494#issuecomment-532968956 ... I've opted for
    changing the layer and argument names to 'drop path' rather than mix DropConnect as a layer name and use
    'survival rate' as the argument.
    """

    def __init__(self, p: float = None):
        super().__init__()
        self.p = p

    def forward(self, x: Tensor) -> Tensor:
        if self.p == 0. or not self.training:
            return x
        kp = 1 - self.p
        shape = (x.shape[0],) + (1,) * (x.ndim - 1)
        random_tensor = kp + torch.rand(shape, dtype=x.dtype, device=x.device)
        random_tensor.floor_()  # binarize
        return x.div(kp) * random_tensor


class Conv2dBnReLU(nn.Sequential):
    def __init__(
            self,
            in_channels,
            out_channels,
            kernel_size,
            padding=0,
            stride=1,
            use_batchnorm=True,
            use_depth_wise_separable_conv=False,
    ):

        if use_batchnorm == "inplace" and InPlaceABN is None:
            raise RuntimeError(
                "In order to use `use_batchnorm='inplace'` inplace_abn package must be installed. "
                + "To install see: https://github.com/mapillary/inplace_abn"
            )

        if use_depth_wise_separable_conv:
            if stride not in [1, 2]:
                raise ValueError(f"if use depth wise separable conv, stride should be 1 or 2 instead of {stride}")
            dws_layers = []
            dws_layers.extend(
                [
                    Conv2dNormActivation(
                        in_channels,
                        in_channels,
                        stride=stride,
                        padding=padding,
                        groups=in_channels,
                        bias=not use_batchnorm,
                        norm_layer=nn.BatchNorm2d,
                        activation_layer=nn.ReLU6,
                        inplace=True
                    ),
                    nn.Conv2d(in_channels, out_channels, 1, 1, 0, bias=False),
                ]
            )
            conv = nn.Sequential(*dws_layers)
        else:
            conv = nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size,
                stride=stride,
                padding=padding,
                bias=not use_batchnorm,
            )
        relu = nn.ReLU(inplace=True)
        conv = nn.Conv2d(
            in_channels,
            out_channels,
            kernel_size,
            stride=stride,
            padding=padding,
            bias=not (use_batchnorm),
        )
        relu = nn.ReLU(inplace=True)

        if use_batchnorm == "inplace":
            bn = InPlaceABN(out_channels, activation="leaky_relu", activation_param=0.0)
            relu = nn.Identity()

        elif use_batchnorm and use_batchnorm != "inplace":
            bn = nn.BatchNorm2d(out_channels)

        else:
            bn = nn.Identity()

        super(Conv2dBnReLU, self).__init__(conv, bn, relu)
