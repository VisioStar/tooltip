# SizeListLatentGenerator.py
# CATEGORY = "VisioStar"
# 单节点：把选中的多组尺寸生成为一个 LATENT 列表输出。
# 连接到采样器的 latent/latent_image 接口后，ComfyUI 会按列表顺序逐个出图。

import torch
import re

class SizeListLatentGenerator:
    """
    尺寸列表 → LATENT（顺序执行）
    预设比例与分辨率（按你的要求）：
      1:1   -> 1328 x 1328
      3:4   -> 1140 x 1472
      4:3   -> 1472 x 1140
      9:16  ->  928 x 1664
      16:9  -> 1664 x  928

    说明：
    - 可勾选任意多个预设；也可在“自定义尺寸”里追加多对宽高（逗号/空格/换行分隔，支持 1024x1536 / 1024*1536 / 1024,1536）。
    - latent 尺寸需能被 8 整除；提供“对齐到8的倍数（向下）”开关（默认开启）。
    - 输出：
        0) latent（LIST）：每个尺寸对应一个空 latent（zeros），shape=[batch,4,H/8,W/8]
        1) sizes_list（LIST）：对齐后的 (W,H) 列表（便于命名/调试）
        2) total_count（INT）：尺寸数量
    - 把第一个输出直接接到采样器的 latent/latent_image，点击 Queue Prompt 即可顺序出不同尺寸的图。
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
                # 预设勾选（可多选）
                "选_1_1_1328x1328": ("BOOLEAN", {"default": True}),
                "选_3_4_1140x1472": ("BOOLEAN", {"default": False}),
                "选_4_3_1472x1140": ("BOOLEAN", {"default": False}),
                "选_9_16_928x1664": ("BOOLEAN", {"default": False}),
                "选_16_9_1664x928": ("BOOLEAN", {"default": False}),

                # 自定义尺寸
                "自定义尺寸": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "示例：\n1024x1536\n1216*1216\n1344,1792\n（多条换行或逗号分隔）"
                }),

                # 每个尺寸的 batch
                "每尺寸批量张数": ("INT", {"default": 1, "min": 1, "max": 64, "step": 1}),

                # 对齐到8的倍数（latent/UNet 要求）
                "对齐到8的倍数_向下取整": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("LATENT", "LIST", "INT")
    RETURN_NAMES = ("latent", "sizes_list", "total_count")
    OUTPUT_IS_LIST = (True, False, False)  # ✅ 第一口是列表 → 会被拆分为多次顺序执行
    FUNCTION = "build"
    CATEGORY = "VisioStar"

    # ---------- helpers ----------
    def _snap8(self, w:int, h:int):
        w2 = max(8, (int(w)//8)*8)
        h2 = max(8, (int(h)//8)*8)
        return w2, h2

    def _parse_custom_sizes(self, txt: str):
        """
        支持多种写法：'1024x1536' '1024*1536' '1024,1536' '1024 1536'
        多条可用逗号、空格、分号或换行分隔
        """
        if not txt:
            return []
        items = re.split(r"[,\n;]+", txt.strip())
        out = []
        for it in items:
            it = it.strip()
            if not it:
                continue
            nums = re.findall(r"\d+", it)
            if len(nums) >= 2:
                w, h = int(nums[0]), int(nums[1])
                if w > 0 and h > 0:
                    out.append((w, h))
        return out

    def build(self,
              选_1_1_1328x1328=True,
              选_3_4_1140x1472=False,
              选_4_3_1472x1140=False,
              选_9_16_928x1664=False,
              选_16_9_1664x928=False,
              自定义尺寸="",
              每尺寸批量张数=1,
              对齐到8的倍数_向下取整=True):

        # 1) 汇总尺寸（预设 + 自定义）
        selected = []
        if 选_1_1_1328x1328: selected.append(self.PRESETS["1:1 - 1328 x 1328"])
        if 选_3_4_1140x1472: selected.append(self.PRESETS["3:4 - 1140 x 1472"])
        if 选_4_3_1472x1140: selected.append(self.PRESETS["4:3 - 1472 x 1140"])
        if 选_9_16_928x1664: selected.append(self.PRESETS["9:16 - 928 x 1664"])
        if 选_16_9_1664x928: selected.append(self.PRESETS["16:9 - 1664 x 928"])

        selected.extend(self._parse_custom_sizes(自定义尺寸))

        # 去重且保持顺序
        seen = set()
        uniq = []
        for w, h in selected:
            key = (int(w), int(h))
            if key not in seen:
                seen.add(key)
                uniq.append(key)

        if not uniq:
            # 无选择则回退默认
            uniq = [self.PRESETS["1:1 - 1328 x 1328"]]

        # 2) 对齐到 8 的倍数（可选）
        aligned = []
        for w, h in uniq:
            if 对齐到8的倍数_向下取整:
                w, h = self._snap8(w, h)
            aligned.append((w, h))

        # 3) 生成 LATENT 列表
        latents = []
        for (w, h) in aligned:
            c = 4
            H8 = max(1, h // 8)
            W8 = max(1, w // 8)
            samples = torch.zeros((每尺寸批量张数, c, H8, W8), dtype=torch.float32, device="cpu")
            latents.append({"samples": samples})

        sizes_list = [(int(w), int(h)) for (w, h) in aligned]
        total = len(latents)

        return (latents, sizes_list, total)


NODE_CLASS_MAPPINGS = {
    "SizeListLatentGenerator": SizeListLatentGenerator,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SizeListLatentGenerator": "尺寸列表 → LATENT（顺序执行）",
}
