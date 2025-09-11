# AspectLatentSelector.py
# CATEGORY = "VisioStar"
# 尺寸选择器：选择常用比例 → 生成指定尺寸的空Latent（可直接连到采样器的 latent 接口）

import torch

class AspectLatentSelector:
    """
    尺寸选择器（输出 LATENT）
    - 预置比例 -> 固定分辨率（来自你的要求）
      1:1   -> 1328 x 1328
      3:4   -> 1140 x 1472
      4:3   -> 1472 x 1140
      9:16  ->  928 x 1664
      16:9  -> 1664 x  928
    - 输出：LATENT（zeros），shape = [batch, 4, H/8, W/8]
    - 说明：部分分辨率（如 1140）不是8的倍数。为防止报错，提供“对齐到8的倍数”开关（默认开）。
    """

    PRESETS = {
        "1:1 - 1328 x 1328":   (1328, 1328),
        "3:4 - 1140 x 1472":   (1140, 1472),
        "4:3 - 1472 x 1140":   (1472, 1140),
        "9:16 - 928 x 1664":   (928, 1664),
        "16:9 - 1664 x 928":   (1664, 928),
    }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "尺寸预设": (list(cls.PRESETS.keys()), {"default": "1:1 - 1328 x 1328"}),
                "批量张数": ("INT", {"default": 1, "min": 1, "max": 64, "step": 1}),
            },
            "optional": {
                "对齐到8的倍数": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    FUNCTION = "build"
    CATEGORY = "VisioStar"

    # ---- helpers ----
    def _snap_to_multiple_of_8(self, w, h):
        w2 = max(8, (w // 8) * 8)
        h2 = max(8, (h // 8) * 8)
        return w2, h2

    def build(self, 尺寸预设, 批量张数=1, 对齐到8的倍数=True):
        # 读取预设尺寸
        if 尺寸预设 not in self.PRESETS:
            # 回退到默认
            w, h = self.PRESETS["1:1 - 1328 x 1328"]
        else:
            w, h = self.PRESETS[尺寸预设]

        # 对齐到可用的 latent 尺寸（8 的倍数）
        if 对齐到8的倍数:
            w, h = self._snap_to_multiple_of_8(w, h)

        # 生成空 latent（zeros）
        # latent 维度： [batch, 4, H/8, W/8]
        c = 4
        latent_h = max(1, h // 8)
        latent_w = max(1, w // 8)
        samples = torch.zeros((批量张数, c, latent_h, latent_w), dtype=torch.float32, device="cpu")

        return ({"samples": samples},)


NODE_CLASS_MAPPINGS = {
    "AspectLatentSelector": AspectLatentSelector,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "AspectLatentSelector": "尺寸选择器（输出 LATENT）",
}
