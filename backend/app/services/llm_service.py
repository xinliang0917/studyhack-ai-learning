import json
from typing import Optional
from openai import OpenAI
from app.config import settings


class LLMService:
    _client = None

    @classmethod
    def _get_client(cls) -> OpenAI:
        if cls._client is None:
            cls._client = OpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
            )
        return cls._client

    @classmethod
    def chat(cls, messages: list, model: Optional[str] = None, temperature: float = 0.7) -> str:
        model = model or settings.deepseek_model
        try:
            client = cls._get_client()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[LLM Error: {str(e)}]"

    @staticmethod
    def generate_outline(knowledge_text: str, title: str = "课程大纲") -> dict:
        prompt = f"""你是一个课程设计专家。请根据以下知识库内容，生成一份结构清晰的课程大纲。

知识库内容：
{knowledge_text[:8000]}

请以JSON格式返回大纲，格式如下：
{{
    "title": "{title}",
    "chapters": [
        {{"title": "第一章标题", "sections": [
            {{"title": "1.1 节标题"}},
            {{"title": "1.2 节标题"}}
        ]}},
        {{"title": "第二章标题", "sections": [...]}}
    ]
}}

要求：
1. 至少包含3章，每章至少2节
2. 大纲层级清晰、逻辑合理
3. 与知识库内容紧密相关
4. 只返回JSON，不要其他文字"""

        messages = [
            {"role": "system", "content": "你是一个课程设计专家，擅长从资料中提取知识结构并生成课程大纲。"},
            {"role": "user", "content": prompt},
        ]
        result = LLMService.chat(messages, temperature=0.5)
        result = result.strip().replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(result)
        except:
            return {"title": title, "chapters": [{"title": "默认章节", "sections": [{"title": "1.1 概述"}]}]}

    @staticmethod
    def generate_chapter_content(knowledge_text: str, chapter_title: str, outline: str) -> str:
        prompt = f"""你是一个学科专家。请根据以下知识库内容，为"{chapter_title}"这一章节生成总结性学习内容。

整体大纲：{outline}
知识库内容：{knowledge_text[:6000]}

要求：
1. 内容应覆盖该章节的核心知识点
2. 采用分段式结构，逻辑清晰
3. 用要点形式呈现关键概念
4. 控制在500-1000字以内
5. 用HTML格式输出：标题用<h3>，段落用<p>，列表用<ul><li>，重点用<strong>，不要Markdown符号。"""
        messages = [
            {"role": "system", "content": "你是一个学科专家，擅长将复杂知识整理成易懂的学习内容。"},
            {"role": "user", "content": prompt},
        ]
        return LLMService.chat(messages, temperature=0.6)

    @staticmethod
    def generate_quiz(knowledge_text: str, chapter_title: str, count: int = 5, difficulty: str = "medium") -> list:
        """Generate questions for a single chapter."""
        prompt = f"""你是一个考试出题专家。请根据以下知识内容，为"{chapter_title}"生成{count}道{_difficulty_label(difficulty)}程度的题目。

知识内容：{knowledge_text[:5000]}

要求：
1. 每道题可以是选择题（4个选项）或判断题
2. 每道题需标注正确答案和简要解析
3. 请以JSON数组格式返回

格式：
[
    {{
        "question": "题目内容",
        "type": "choice" 或 "true_false",
        "options": {{"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"}},
        "answer": "A",
        "explanation": "解析内容",
        "difficulty": "easy|medium|hard"
    }}
]

判断题的options格式为：{{"A": "正确", "B": "错误"}}
只返回JSON数组，不要其他文字。"""

        messages = [
            {"role": "system", "content": "你是一个考试出题专家，擅长基于知识内容生成高质量题目。"},
            {"role": "user", "content": prompt},
        ]
        result = LLMService.chat(messages, temperature=0.7)
        result = result.strip().replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(result)
        except:
            return _default_quiz(chapter_title, count)

    @staticmethod
    def generate_bulk_quiz(knowledge_text: str, chapters: list, count_per_chapter: int = 3, difficulty: str = "medium") -> list:
        """Generate questions for ALL chapters in a single LLM call. Returns list of {chapter_index, question, type, options, answer, explanation}."""
        chapters_desc = "\n".join(f"{i+1}. {ch}" for i, ch in enumerate(chapters))
        total_count = max(1, len(chapters)) * count_per_chapter
        prompt = f"""你是一个考试出题专家。请根据以下知识内容，为以下{len(chapters)}个章节批量生成题目，每个章节{count_per_chapter}道，共{total_count}道题。

## 章节列表
{chapters_desc}

## 知识内容
{knowledge_text[:6000]}

## 要求
1. 每道题可以是选择题（4个选项）或判断题
2. 每道题需标注正确答案和简要解析
3. 题目必须与指定章节的知识点强相关
4. 难度均为{_difficulty_label(difficulty)}
5. 请以JSON数组格式返回

## 格式
[
    {{
        "chapter_index": 0,
        "question": "题目内容",
        "type": "choice",
        "options": {{"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"}},
        "answer": "A",
        "explanation": "解析内容",
        "difficulty": "{difficulty}"
    }}
]

注意：chapter_index从0开始，对应章节列表中的索引。判断题的options为{{"A": "正确", "B": "错误"}}。
只返回JSON数组，不要其他文字。"""

        messages = [
            {"role": "system", "content": "你是一个考试出题专家，擅长基于知识内容生成高质量题目。"},
            {"role": "user", "content": prompt},
        ]
        result = LLMService.chat(messages, temperature=0.7)
        result = result.strip().replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(result)
        except:
            # Fallback: generate per chapter individually
            all_qs = []
            for idx, ch in enumerate(chapters):
                qs = _default_quiz(ch, count_per_chapter)
                for q in qs:
                    q["chapter_index"] = idx
                all_qs.extend(qs)
            return all_qs

    @staticmethod
    def generate_wrong_question_explanation(question: str, correct_answer: str, user_answer: str, knowledge_text: str) -> str:
        prompt = f"""题目：{question}
正确答案：{correct_answer}
用户答案：{user_answer}

请根据知识库内容，简要解析这道题的正确思路，帮学生理解为什么正确答案是{correct_answer}。"""
        messages = [
            {"role": "system", "content": "你是一个耐心的学科辅导老师。"},
            {"role": "user", "content": prompt},
        ]
        return LLMService.chat(messages, temperature=0.5)


def _difficulty_label(d: str) -> str:
    return {"easy": "简单", "medium": "中等", "hard": "困难"}.get(d, "中等")


def _default_quiz(chapter: str, count: int) -> list:
    questions = []
    for i in range(count):
        questions.append({
            "question": f"关于{chapter}的第{i+1}道测试题",
            "type": "choice",
            "options": {"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"},
            "answer": "A",
            "explanation": "这是默认解析，请参考课程内容。",
            "difficulty": "medium",
        })
    return questions
