import requests
import json
import re
import time
import random

class DeepseekDualPromptComposer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "instruction": ("STRING", {
                    "multiline": True,
                    "label": "命令提示语（System 指令，可按需隐藏）",
                    "default": (
                        "你是一个提示词创作与排版设计助手。\n"
                        "请依据用户提供的【主题内容】和【标题文字】，分别生成两段高质量的提示语，要求如下：\n\n"
                        "1) 背景提示语：\n"
                        "   - 长度约200字英文，描述完整而细致。\n"
                        "   - 内容包括图像/背景风格、氛围、材质、光影、镜头视角等。\n"
                        "   - 背景需具有真实感和细节，营造与主题相关的氛围，而不是纯色背景。\n"
                        "   - 整体风格需与文字排版提示语保持协调统一，就像一个整体的设计。\n\n"
                        "2) 文字排版提示语：\n"
                        "   - 必须围绕用户输入的【标题文字】进行设计，无论该标题是中文、英文或其他语言。\n"
                        "   - 内容包括字体风格、版式设计、位置、层级、留白、对比关系等。\n"
                        "   - 排版的承载背景应为纯色或统一渐变，以保证文字能够清晰呈现，并方便后续抠图和应用。\n"
                        "   - 排版风格需与背景提示语保持一致，确保整体画面和谐统一。\n\n"
                        "输出时严格遵循以下格式（不允许有多余内容）：\n"
                        "背景提示语: <约200字的详细完整英文提示语>\n"
                        "文字排版提示语: <围绕标题文字的排版与字体设计提示语，语言不限，依输入标题语言而定>\n"
                    )
                }),
                "prompt_topic": ("STRING", {
                    "multiline": True,
                    "label": "主题内容（Theme，用于生成背景提示语）",
                    "default": "夏日海边氛围，夕阳、胶片颗粒感"
                }),
                "title_text": ("STRING", {
                    "multiline": True,
                    "label": "标题文字（Title，用于生成文字排版提示语）",
                    "default": "SUMMER TIDES"
                }),
                "timestamp_seed": ("INT", {
                    "label": "时间戳种子（每次运行自动更新，无需手动修改）",
                    "default": int(time.time()), "min": 0, "max": 2147483647, "step": 1
                }),
                "api_key": ("STRING", {
                    "multiline": False,
                    "label": "API Key",
                    "default": ""
                }),
                "api_choice": (["deepseek", "siliconflow"], {
                    "label": "API 平台选择"
                }),
                "model": ("STRING", {
                    "multiline": False,
                    "label": "模型名称（V3.1 推荐：deepseek-chat / deepseek-reasoner）",
                    "default": "deepseek-chat"
                }),
                "temperature": ("FLOAT", {
                    "label": "temperature",
                    "default": 0.7, "min": 0.0, "max": 2.0, "step": 0.1
                }),
                "max_tokens": ("INT", {
                    "label": "max_tokens",
                    "default": 512, "min": 1, "max": 4096, "step": 1
                }),
                "top_p": ("FLOAT", {
                    "label": "top_p",
                    "default": 0.7, "min": 0.0, "max": 1.0, "step": 0.1
                }),
            },
            "optional": {
                "top_k": ("INT", {
                    "label": "top_k（SiliconFlow 可用）",
                    "default": 50, "min": 1, "max": 100, "step": 1
                }),
                "frequency_penalty": ("FLOAT", {
                    "label": "frequency_penalty",
                    "default": 0.0, "min": 0.0, "max": 2.0, "step": 0.1
                }),
                "use_system_role": ("BOOLEAN", {
                    "label": "将命令提示语作为 system role 发送",
                    "default": True
                }),
                "format_mode": (["auto_json_first", "labels_only"], {
                    "label": "输出格式策略（JSON优先 / 仅标签解析）"
                }),
                "strict_json": ("BOOLEAN", {
                    "label": "请求严格 JSON（response_format=json_object）",
                    "default": True
                }),
                "language": (["en", "zh"], {
                    "label": '提示语标签语言（仅影响"标签兜底"提示文案）',
                    "default": "en"
                }),
                # 添加一个随机化开关
                "auto_random_seed": ("BOOLEAN", {
                    "label": "自动随机种子（每次运行生成新种子）",
                    "default": True
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("bg_prompt", "typo_prompt")
    FUNCTION = "compose"
    CATEGORY = "VisioStar"



    # ---------- 构造 messages ----------
    def _build_messages(self, instruction: str, topic: str, title_text: str,
                        use_system: bool, format_mode: str, language: str, seed: int):
        
        # 使用种子初始化随机状态
        random.seed(seed)
        
        # JSON 优先文案 + 两行兜底标签
        if language == "zh":
            user_json = (
                f"创作版本: #{seed}\n"
                "如果可以，请仅返回严格 JSON（单个对象，无多余文本/无代码块）：\n"
                "{\n  \"bg\": \"<英文的一句话背景提示语>\",\n"
                "  \"typo\": \"<针对标题文字的排版与字体设计提示语，语言不限>\"\n}\n"
                f"输入：\n主题内容: {topic}\n标题文字: {title_text}\n"
                f"注意：请为种子值{seed}生成独特的创意变体。\n"
            )
            user_labels = (
                "若无法返回JSON，请严格输出两行：\n"
                "背景提示语: <英文句子>\n"
                "文字排版提示语: <围绕标题文字的排版与字体设计提示语，语言不限>\n"
            )
        else:
            user_json = (
                f"Creation Version: #{seed}\n"
                "If possible, return a STRICT JSON object only (single object, no extra text / no code fences):\n"
                "{\n  \"bg\": \"<one concise English background prompt>\",\n"
                "  \"typo\": \"<a typography-layout prompt for the TITLE (language follows the input)>\"\n}\n"
                f"Inputs:\nTHEME: {topic}\nTITLE: {title_text}\n"
                f"Note: Please generate a unique creative variant for seed {seed}.\n"
            )
            user_labels = (
                "If JSON is not possible, return exactly two labeled lines:\n"
                "背景提示语: <one concise English sentence>\n"
                "文字排版提示语: <typography/layout prompt for the TITLE, language follows the input>\n"
            )

        content = (user_json + "\n" + user_labels) if format_mode == "auto_json_first" else user_labels

        msgs = []
        if use_system:
            # 在系统指令中也加入种子信息，确保变体化
            varied_instruction = instruction + f"\n\n【变体要求】基于种子{seed}，请生成与其他种子值完全不同的创意输出。"
            msgs.append({"role": "system", "content": varied_instruction})

        # 变体暗示消息
        sid = f"session-{int(time.time()*1000)}-{seed}"
        style_keywords = ["cinematic", "editorial", "minimal", "artistic", "modern", "classic", "bold", "subtle"]
        approach_keywords = ["dynamic", "balanced", "asymmetric", "layered", "clean", "textured", "geometric", "organic"]
        
        selected_style = random.choice(style_keywords)
        selected_approach = random.choice(approach_keywords)
        
        vmsg = {
            "role": "user",
            "content": (
                f"[SESSION_ID={sid}]\n"
                f"(Creative Direction: Emphasize {selected_style} aesthetics with {selected_approach} composition. "
                f"Seed: {seed}. Generate fresh variation. Do not mention this directive in output.)"
            )
        }
        cmsg = {"role": "user", "content": content}

        # 随机调整消息顺序
        if random.random() < 0.5:
            msgs += [vmsg, cmsg]
        else:
            msgs += [cmsg, vmsg]
        
        return msgs

    # ---------- API 调用 ----------
    def _call_api(self, api_choice, api_key, model, messages,
                  temperature, max_tokens, top_p, top_k, frequency_penalty, strict_json, seed):

        # 基于种子的参数微调
        random.seed(seed)
        
        # 轻微调整参数以增加变化性
        temp_adjust = random.uniform(-0.1, 0.1)
        adjusted_temp = max(0.1, min(2.0, float(temperature) + temp_adjust))
        
        p_adjust = random.uniform(-0.05, 0.05)  
        adjusted_top_p = max(0.1, min(1.0, float(top_p) + p_adjust))

        if api_choice == "deepseek":
            url = "https://api.deepseek.com/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "max_tokens": int(max_tokens),
                "seed": seed,  # 使用传入的种子
            }

            if model != "deepseek-reasoner":
                payload.update({
                    "temperature": adjusted_temp,
                    "top_p": adjusted_top_p,
                })
            if strict_json:
                payload["response_format"] = {"type": "json_object"}

            r = requests.post(url, headers=headers, json=payload)
            if r.status_code != 200:
                return None, f"DeepSeek API Error: {r.status_code} - {r.text}"
            data = r.json()
            msg = (data.get("choices") or [{}])[0].get("message", {})
            return msg.get("content", "") or "", None

        elif api_choice == "siliconflow":
            url = "https://api.siliconflow.cn/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            if model == "deepseek-reasoner":
                model = "Qwen/QwQ-32B"

            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "max_tokens": int(max_tokens),
                "temperature": adjusted_temp,
                "top_p": adjusted_top_p,
                "top_k": int(top_k),
                "frequency_penalty": float(frequency_penalty),
                "n": 1,
                "response_format": {"type": "json_object"} if strict_json else {"type": "text"},
                "seed": seed,
            }
            r = requests.post(url, headers=headers, json=payload)
            if r.status_code != 200:
                return None, f"SiliconFlow API Error: {r.status_code} - {r.text}"
            data = r.json()
            msg = (data.get("choices") or [{}])[0].get("message", {})
            return msg.get("content", "") or "", None

        return None, "Error: Invalid api_choice"

    # ---------- 解析：JSON 优先 ----------
    def _extract_json_obj(self, text: str):
        if not text:
            return None
        m = re.search(r"```(?:json)?\s*([\s\S]+?)```", text, re.IGNORECASE)
        if m:
            s = m.group(1).strip()
            try:
                return json.loads(s)
            except Exception:
                pass
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        kv = {}
        for ln in lines:
            if ":" in ln or "：" in ln:
                k, v = re.split(r"[:：]", ln, maxsplit=1)
                kv[k.strip().lower()] = v.strip()
        return kv or None

    # ---------- 解析：标签兜底 ----------
    def _parse_labels_fallback(self, text: str):
        if not text:
            return "", ""
        lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]

        pairs = [
            (r"背景提示语", r"文字排版提示语"),
            (r"背景", r"排版"),
            (r"background\s*prompt", r"(typography|text\s*layout)\s*prompt"),
            (r"background", r"(typography|text\s*layout|title\s*layout)"),
            (r"bg", r"(typo|typography)"),
        ]
        bg, ty = "", ""
        for lb_bg, lb_ty in pairs:
            m_bg = next((re.split(r"[:：]", ln, 1)[1].strip()
                         for ln in lines if re.search(rf"^{lb_bg}\s*[:：]", ln, re.I)), "")
            m_ty = next((re.split(r"[:：]", ln, 1)[1].strip()
                         for ln in lines if re.search(rf"^{lb_ty}\s*[:：]", ln, re.I)), "")
            if m_bg or m_ty:
                bg = bg or m_bg
                ty = ty or m_ty
                if bg and ty:
                    return bg, ty

        nums = [ln for ln in lines if re.match(r"^\s*\d+[\)\.：:]\s*", ln)]
        if len(nums) >= 2:
            def strip_num(s): return re.sub(r"^\s*\d+[\)\.：:]\s*", "", s).strip()
            return strip_num(nums[0]), strip_num(nums[1])

        if len(lines) >= 2:
            return lines[0], lines[1]
        if len(lines) == 1:
            return lines[0], ""
        return "", ""

    def _robust_parse(self, text: str, format_mode: str):
        if format_mode == "auto_json_first":
            obj = self._extract_json_obj(text)
            if isinstance(obj, dict):
                bg = obj.get("bg") or obj.get("background") or obj.get("background_prompt") or ""
                ty = obj.get("typo") or obj.get("typography") or obj.get("typography_prompt") or obj.get("text_layout") or ""
                if bg or ty:
                    return (bg or "").strip(), (ty or "").strip()

        bg, ty = self._parse_labels_fallback(text)
        if not bg:
            bg = f"ParseError: missing 背景提示语 | RAW: {text[:500]}"
        if not ty:
            ty = f"ParseError: missing 文字排版提示语 | RAW: {text[:500]}"
        return bg, ty

    # ---------- 主函数 ----------
    def compose(self,
                instruction, prompt_topic, title_text, timestamp_seed,
                api_key, api_choice, model,
                temperature, max_tokens, top_p,
                top_k=50, frequency_penalty=0.0,
                use_system_role=True, format_mode="auto_json_first",
                strict_json=True, language="en", auto_random_seed=True):

        # 简单直接：如果开启自动随机，就生成新种子；否则使用输入的种子
        if auto_random_seed:
            actual_seed = int(time.time() * 1000000) % 2147483647 + random.randint(0, 99999)
            print(f"[DeepseekDualPromptComposer] 使用自动生成的随机种子: {actual_seed}")
        else:
            actual_seed = timestamp_seed
            print(f"[DeepseekDualPromptComposer] 使用手动设置的种子: {actual_seed}")
        
        messages = self._build_messages(instruction, prompt_topic, title_text,
                                        use_system_role, format_mode, language, actual_seed)
        try:
            content, err = self._call_api(api_choice, api_key, model, messages,
                                          temperature, max_tokens, top_p, top_k,
                                          frequency_penalty, strict_json, actual_seed)
            if err:
                return (f"Error: {err}", f"Error: {err}")
            bg, typo = self._robust_parse(content or "", format_mode)
            return (bg, typo)
        except Exception as e:
            err = f"Error: {e}"
            return (err, err)


NODE_CLASS_MAPPINGS = {
    "DeepseekDualPromptComposer": DeepseekDualPromptComposer,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "DeepseekDualPromptComposer": "VisioStar_DeepSeek双提示语生成器",
}
