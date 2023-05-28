import sys
from typing import List, Any

from model.encoder.getencoder import get_encoder
import torch
from torch import nn, Tensor
from model.modules.layers import Conv2dBnReLU
from model.modules.attention import Attention

__all__ = ["DeepSupervisionHead"]


class DeepSupervisionBlock(nn.Sequential):
    def __init__(self, in_channels, attention_name, num_classes, use_separable_conv=False):
        conv = Conv2dBnReLU(in_channels, in_channels // 4, 1, use_depth_wise_separable_conv=use_separable_conv)
        attention = Attention(name=attention_name, in_channels=in_channels // 4)
        cls = nn.Conv2d(in_channels // 4, num_classes, 1)
        super().__init__(conv, attention, cls)


class DeepSupervisionHead(nn.Module):
    def __init__(self, in_channels, attention_name, num_classes: int = 1, use_separable_conv=False):
        super().__init__()
        self.blocks = nn.ModuleList()
        for in_channel in in_channels[::-1][:3]:
            self.blocks.append(DeepSupervisionBlock(in_channel, attention_name, num_classes, use_separable_conv=use_separable_conv))

    def forward(self, features) -> list[Any]:
        outs = []
        for index, feature in enumerate(features[::-1][:3]):
            x = self.blocks[index](feature)
            outs.append(x)
        return outs


if __name__ == '__main__':
    # dict = {"out1": [1, 2, 3],
    #         "out2": [4, 5, 6],
    #         "out3": [7, 8, 9],
    #         }
    # print(**dict)
    # from encoder.resnet import resnet_extract
    backbone = get_encoder("resnet50", predicted=False)
    head = DeepSupervisionHead(backbone.out_channels[:-1], 'cbam', 1)
    x = torch.randn(2, 3, 512, 512)
    features = backbone(x)
    outs = head(features[:-1])
    # print(outs[1].shape)
    print([out.shape for out in outs])
    # outs_f = F.interpolate(out, size=x.shape[-2:], mode='bilinear', align_corners=False)
    # print(out.shape for out in outs_f)
