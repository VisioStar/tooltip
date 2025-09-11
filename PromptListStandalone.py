# PromptListStandalone.py
# CATEGORY = "VisioStar"
# 说明：
# - 基于你的 PromptListProcessor 逻辑拆出独立节点，功能不变
# - UI 优化：默认展示 5 个提示语（required），其余 6~10 放在 optional
# - 仅按 prompt_count 采集前 N 个提示（与原逻辑一致）

from typing import List

class PromptListStandalone:
    """
    提示词列表1.1
    输出:
      0: prompt_list (LIST of strings)
      1: conditioning_list (LIST of conditioning)  [当 clip 提供时]
      2: total_count (INT)
    逻辑与原 PromptListProcessor 一致，仅做 UI 分组与默认值优化。
    """

    @classmethod
    def INPUT_TYPES(cls):
        # 默认 5 个（可在 UI 调整为 1~10，实际仅采集前 N 个）
        required = {
            "prompt_count": ("INT", {"default": 5, "min": 1, "max": 10, "step": 1}),
            # 前 5 个放在 required，默认显式展示
            "prompt_1": ("STRING", {"multiline": True, "default": "", "placeholder": "输入第1个提示词..."}),
            "prompt_2": ("STRING", {"multiline": True, "default": "", "placeholder": "输入第2个提示词..."}),
            "prompt_3": ("STRING", {"multiline": True, "default": "", "placeholder": "输入第3个提示词..."}),
            "prompt_4": ("STRING", {"multiline": True, "default": "", "placeholder": "输入第4个提示词..."}),
            "prompt_5": ("STRING", {"multiline": True, "default": "", "placeholder": "输入第5个提示词..."}),
        }
        optional = {
            # 其余放 optional，需要时再用；依旧由 prompt_count 决定是否被采集
            "prompt_6": ("STRING", {"multiline": True, "default": "", "placeholder": "输入第6个提示词..."}),
            "prompt_7": ("STRING", {"multiline": True, "default": "", "placeholder": "输入第7个提示词..."}),
            "prompt_8": ("STRING", {"multiline": True, "default": "", "placeholder": "输入第8个提示词..."}),
            "prompt_9": ("STRING", {"multiline": True, "default": "", "placeholder": "输入第9个提示词..."}),
            "prompt_10": ("STRING", {"multiline": True, "default": "", "placeholder": "输入第10个提示词..."}),
            "clip": ("CLIP",),  # 与原实现一致：如提供则批量编码
        }
        return {"required": required, "optional": optional}

    # 与原实现一致：第1、2个输出是“列表”
    RETURN_TYPES = ("STRING", "CONDITIONING", "INT")
    RETURN_NAMES = ("prompt_list", "conditioning_list", "total_count")
    OUTPUT_IS_LIST = (True, True, False)
    FUNCTION = "process_list"
    CATEGORY = "VisioStar"

    # ====== 与原实现一致的内部逻辑 ======
    def _collect_prompts(self, prompt_count: int, **kwargs) -> List[str]:
        prompts = []
        # 仅采集前 N 个（与原逻辑相同）
        for i in range(1, prompt_count + 1):
            key = f"prompt_{i}"
            if key in kwargs:
                text = kwargs[key]
                if text and str(text).strip():
                    prompts.append(str(text).strip())
        return prompts

    def _encode_with_clip(self, clip, prompts: List[str]):
        if clip is None:
            return []
        conditionings = []
        for p in prompts:
            try:
                tokens = clip.tokenize(p)
                cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
                conditionings.append([cond, {"pooled_output": pooled}])
            except Exception as e:
                print(f"[PromptListStandalone] CLIP编码错误 '{p[:30]}...': {e}")
                # 跳过错误项，保持与你原实现一致
                continue
        return conditionings

    def process_list(self,
                     prompt_count: int,
                     prompt_1: str = "", prompt_2: str = "", prompt_3: str = "",
                     prompt_4: str = "", prompt_5: str = "",
                     prompt_6: str = "", prompt_7: str = "", prompt_8: str = "",
                     prompt_9: str = "", prompt_10: str = "",
                     clip=None):
        # 收集
        prompts = self._collect_prompts(prompt_count,
                                        prompt_1=prompt_1, prompt_2=prompt_2, prompt_3=prompt_3,
                                        prompt_4=prompt_4, prompt_5=prompt_5,
                                        prompt_6=prompt_6, prompt_7=prompt_7, prompt_8=prompt_8,
                                        prompt_9=prompt_9, prompt_10=prompt_10)
        total = len(prompts)
        if total == 0:
            return (["No valid prompts"], [], 0)

        # 可选批量 CLIP 编码（与原逻辑一致）
        conds = self._encode_with_clip(clip, prompts) if clip is not None else []

        print(f"[PromptListStandalone] 处理了 {total} 个提示词；生成 {len(conds)} 个 conditioning")
        return (prompts, conds, total)


NODE_CLASS_MAPPINGS = {
    "PromptListStandalone": PromptListStandalone,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptListStandalone": "提示词列表1.1",
}
