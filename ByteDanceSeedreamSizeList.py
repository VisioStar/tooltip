# ByteDanceSeedreamSizeList.py
# CATEGORY = "tooltip"
# Seedream 4 尺寸顺序执行节点（修复：可直连 size_preset）
# - 同时输出：
#   1) size_preset (STRING) —— 通用字符串
#   2) width (INT) / height (INT)
#   3) total_count (INT)
#   4) size_preset_enum (SEEDREAM_SIZE_PRESET) —— 与 Seedream 节点的枚举输入类型匹配
# - 三个列表口使用 OUTPUT_IS_LIST=True，ComfyUI 会按顺序逐条执行

import re

class ByteDanceSeedreamSizeList:
    """
    ByteDance Seedream 4 尺寸列表（顺序执行）
    预设与面板一致：
      2048x2048 (1:1)
      2304x1728 (4:3)
      1728x2304 (3:4)
      2560x1440 (16:9)
      1440x2560 (9:16)
      2496x1664 (3:2)
      1664x2496 (2:3)
      3024x1296 (21:9)
      4096x4096 (1:1)

    也支持“自定义尺寸”多行输入：
      2048x2048
      1728*2304
      2304,1728
      2560 1440
    """

    PRESETS = [
        ("2048x2048 (1:1)", 2048, 2048),
        ("2304x1728 (4:3)", 2304, 1728),
        ("1728x2304 (3:4)", 1728, 2304),
        ("2560x1440 (16:9)", 2560, 1440),
        ("1440x2560 (9:16)", 1440, 2560),
        ("2496x1664 (3:2)", 2496, 1664),
        ("1664x2496 (2:3)", 1664, 2496),
        ("3024x1296 (21:9)", 3024, 1296),
        ("4096x4096 (1:1)", 4096, 4096),
    ]

    @classmethod
    def INPUT_TYPES(cls):
        required = {}
        # 预设勾选
        for label, _, _ in cls.PRESETS:
            key = "选_" + re.sub(r"[^\d]+", "_", label).strip("_")
            required[key] = ("BOOLEAN", {"default": False})
        # 默认勾选第一个
        first_key = "选_" + re.sub(r"[^\d]+", "_", cls.PRESETS[0][0]).strip("_")
        required[first_key] = ("BOOLEAN", {"default": True})

        required.update({
            "自定义尺寸": ("STRING", {
                "multiline": True,
                "default": "",
                "placeholder": "每行一个尺寸，支持：\n2048x2048\n1728*2304\n2304,1728\n2560 1440"
            }),
            "自定义尺寸置顶": ("BOOLEAN", {"default": False}),
        })
        return {"required": required}

    # 关键：新增 SEEDREAM_SIZE_PRESET 类型的并行输出口
    RETURN_TYPES = ("STRING", "INT", "INT", "INT", "SEEDREAM_SIZE_PRESET")
    RETURN_NAMES = ("size_preset", "width", "height", "total_count", "size_preset_enum")
    OUTPUT_IS_LIST = (True, True, True, False, True)

    FUNCTION = "build"
    CATEGORY = "tooltip"

    # ------- helpers -------
    def _selected_from_inputs(self, **kwargs):
        out = []
        for label, w, h in self.PRESETS:
            key = "选_" + re.sub(r"[^\d]+", "_", label).strip("_")
            if kwargs.get(key, False):
                out.append((label, w, h))
        return out

    def _parse_custom(self, text: str):
        if not text:
            return []
        lines = re.split(r"[\n;]+", text.strip())
        result = []
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            nums = re.findall(r"\d+", ln)
            if len(nums) >= 2:
                w, h = int(nums[0]), int(nums[1])
                if w > 0 and h > 0:
                    result.append((f"{w}x{h} (Custom)", w, h))
        return result

    # ------- main -------
    def build(self, **kwargs):
        # 1) 预设 + 2) 自定义
        selected = self._selected_from_inputs(**kwargs)
        custom_list = self._parse_custom(kwargs.get("自定义尺寸", ""))

        merged = custom_list + selected if kwargs.get("自定义尺寸置顶", False) else selected + custom_list
        if not merged:
            merged = [self.PRESETS[0]]  # 兜底

        size_preset_list   = [label for (label, _, _) in merged]
        width_list         = [int(w) for (_, w, _) in merged]
        height_list        = [int(h) for (_, _, h) in merged]
        total_count        = len(merged)
        size_preset_enum   = list(size_preset_list)  # 同值，以枚举类型输出

        # 返回顺序需与 RETURN_TYPES/RETURN_NAMES 对齐
        return (size_preset_list, width_list, height_list, total_count, size_preset_enum)


NODE_CLASS_MAPPINGS = {
    "ByteDanceSeedreamSizeList": ByteDanceSeedreamSizeList,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "ByteDanceSeedreamSizeList": "Seedream 尺寸列表（顺序执行）",
}
