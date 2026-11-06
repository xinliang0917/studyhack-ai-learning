from datetime import datetime, time, timedelta

import bcrypt

from app.database import SessionLocal
from app.models.chat import ChatMessage, ChatSession
from app.models.course import Chapter, CourseOutline, LearningProgress
from app.models.knowledge import KnowledgeChunk, KnowledgeDoc
from app.models.quiz import ExamResult, QuizQuestion, WrongQuestion
from app.models.schedule import ScheduleItem
from app.models.user import User
from app.services.vector_store import vector_store

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123456"

DOCS = [
    {
        "filename": "数据结构-绪论.txt",
        "chunks": [
            "数据结构研究数据的逻辑结构、存储结构和运算。常见逻辑结构包括线性结构、树形结构、图结构和集合结构。",
            "算法的复杂度分为时间复杂度和空间复杂度，常用大 O 表示法描述输入规模增长时的资源消耗。",
        ],
    },
    {
        "filename": "数据结构-线性表与栈队列.txt",
        "chunks": [
            "线性表是由 n 个数据元素组成的有限序列，常见存储方式有顺序存储和链式存储。",
            "栈是后进先出（LIFO）的线性表，只允许在栈顶插入和删除元素。",
            "队列是先进先出（FIFO）的线性表，允许在队尾插入、在队头删除元素。",
        ],
    },
    {
        "filename": "数据结构-树与查找.txt",
        "chunks": [
            "二叉树每个结点最多有两个子结点，分别称为左子树和右子树。",
            "二叉搜索树满足左子树结点值小于根结点、右子树结点值大于根结点。",
            "常见查找算法有顺序查找、二分查找和哈希查找。二分查找要求数据有序，时间复杂度为 O(log n)。",
        ],
    },
]


def _build_demo_index(db):
    rows = db.query(
        KnowledgeChunk, KnowledgeDoc.filename, KnowledgeDoc.user_id
    ).join(KnowledgeDoc, KnowledgeChunk.doc_id == KnowledgeDoc.id).all()
    chunks = [
        {
            "content": chunk.content,
            "index": chunk.id,
            "doc_id": chunk.doc_id,
            "chunk_index": chunk.chunk_index,
            "filename": filename,
            "user_id": owner_id,
        }
        for chunk, filename, owner_id in rows
    ]
    if chunks:
        vector_store.build_index(chunks)


def seed_demo():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == DEMO_USERNAME).first()
        if existing:
            print("Demo user already exists; skip seeding")
            return

        user = User(
            username=DEMO_USERNAME,
            password_hash=bcrypt.hashpw(
                DEMO_PASSWORD.encode(), bcrypt.gensalt()
            ).decode(),
        )
        db.add(user)
        db.flush()

        docs = []
        for item in DOCS:
            content = "\n".join(item["chunks"])
            doc = KnowledgeDoc(
                user_id=user.id,
                filename=item["filename"],
                file_type="txt",
                file_size=len(content.encode("utf-8")),
                chunk_count=len(item["chunks"]),
                file_path=None,
            )
            db.add(doc)
            db.flush()
            for index, text in enumerate(item["chunks"]):
                db.add(KnowledgeChunk(
                    doc_id=doc.id, chunk_index=index, content=text
                ))
            docs.append(doc)
        db.flush()

        outline = CourseOutline(
            user_id=user.id,
            title="数据结构与算法",
            outline_json={
                "title": "数据结构与算法",
                "chapters": [
                    {"title": "绪论", "sections": [{"title": "基本概念"}, {"title": "算法复杂度"}]},
                    {"title": "线性表", "sections": [{"title": "顺序表"}, {"title": "链表"}]},
                    {"title": "栈与队列", "sections": [{"title": "栈"}, {"title": "队列"}]},
                    {"title": "树与二叉树", "sections": [{"title": "二叉树遍历"}, {"title": "二叉搜索树"}]},
                    {"title": "查找与排序", "sections": [{"title": "二分查找"}, {"title": "排序算法"}]},
                ],
            },
        )
        db.add(outline)
        db.flush()

        chapter_defs = [
            ("绪论", ["基本概念", "算法复杂度"]),
            ("线性表", ["顺序表", "链表"]),
            ("栈与队列", ["栈", "队列"]),
            ("树与二叉树", ["二叉树遍历", "二叉搜索树"]),
            ("查找与排序", ["二分查找", "排序算法"]),
        ]
        chapters = {}
        sort_order = 0
        for title, sections in chapter_defs:
            sort_order += 1
            parent = Chapter(
                outline_id=outline.id,
                parent_id=0,
                title=title,
                sort_order=sort_order,
                content=f"{title}的核心概念、典型操作与常见应用。",
            )
            db.add(parent)
            db.flush()
            chapters[title] = parent
            for section in sections:
                sort_order += 1
                db.add(Chapter(
                    outline_id=outline.id,
                    parent_id=parent.id,
                    title=section,
                    sort_order=sort_order,
                ))
        db.flush()

        progress_status = {
            "绪论": "completed",
            "线性表": "completed",
            "栈与队列": "learning",
            "树与二叉树": "learning",
            "查找与排序": "not_started",
        }
        for title, chapter in chapters.items():
            db.add(LearningProgress(
                user_id=user.id,
                chapter_id=chapter.id,
                status=progress_status[title],
            ))

        question_defs = [
            ("栈与队列", "栈的主要特点是什么？", {"A": "后进先出", "B": "先进先出", "C": "随机访问", "D": "双端插入"}, "A", "栈只允许在栈顶插入和删除，因此是后进先出。", 1, 1),
            ("栈与队列", "队列的主要特点是什么？", {"A": "后进先出", "B": "先进先出", "C": "随机访问", "D": "只能从中间删除"}, "B", "队列在队尾插入、队头删除，因此是先进先出。", 1, 2),
            ("查找与排序", "二分查找对数据的要求是什么？", {"A": "数据必须有序", "B": "数据必须无序", "C": "必须是链表", "D": "必须是哈希表"}, "A", "二分查找每次比较后缩小一半范围，因此要求数据有序。", 2, 2),
            ("树与二叉树", "二叉搜索树左子树结点的值通常满足什么条件？", {"A": "大于根结点", "B": "小于根结点", "C": "等于根结点", "D": "任意大小"}, "B", "二叉搜索树左子树结点值小于根，右子树结点值大于根。", 2, 1),
            ("查找与排序", "二分查找的时间复杂度是？", {"A": "O(n)", "B": "O(n log n)", "C": "O(log n)", "D": "O(1)"}, "C", "二分查找每次排除一半数据，复杂度为 O(log n)。", 2, 2),
        ]
        questions = []
        for chapter_title, text, options, answer, explanation, doc_index, chunk_index in question_defs:
            doc = docs[doc_index]
            source = [{
                "doc_id": doc.id,
                "filename": doc.filename,
                "chunk_index": chunk_index,
                "content": DOCS[doc_index]["chunks"][chunk_index][:300],
            }]
            question = QuizQuestion(
                chapter_id=chapters[chapter_title].id,
                question_text=text,
                options_json=options,
                correct_answer=answer,
                difficulty="medium",
                explanation=explanation,
                source_chunks=source,
            )
            db.add(question)
            db.flush()
            questions.append(question)

        answers = {}
        correct_count = 0
        for index, question in enumerate(questions):
            if index == 3:
                answers[str(question.id)] = "A"
            else:
                answers[str(question.id)] = question.correct_answer
                correct_count += 1
        score = round(correct_count / len(questions) * 100, 1)
        exam = ExamResult(
            user_id=user.id,
            chapter_ids=",".join(str(q.chapter_id) for q in questions),
            score=score,
            total=len(questions),
            time_limit=1800,
            answers_json=answers,
            time_spent=600,
        )
        db.add(exam)
        db.flush()
        for question in questions:
            question.exam_id = exam.id

        db.add(WrongQuestion(
            user_id=user.id,
            question_id=questions[3].id,
            user_answer="A",
            next_review_at=datetime.utcnow() - timedelta(days=1),
            ease_factor=2.5,
            interval_days=0,
            repetitions=0,
        ))

        now = datetime.now()
        task_defs = [
            ("完成栈与队列练习", "homework", "数据结构与算法", 1, "todo", "high", "完成栈和队列的课后习题"),
            ("复习二叉树遍历", "course", "数据结构与算法", 3, "doing", "normal", "重点看前序、中序、后序遍历"),
            ("提交数据结构实验报告", "homework", "数据结构与算法", -1, "todo", "high", "实验报告需要附运行截图"),
            ("阅读二分查找资料", "course", "数据结构与算法", 5, "done", "low", "整理二分查找的边界条件"),
        ]
        for title, item_type, course, offset, status, priority, notes in task_defs:
            due = datetime.combine(
                (now + timedelta(days=offset)).date(), time(hour=20)
            )
            db.add(ScheduleItem(
                user_id=user.id,
                title=title,
                item_type=item_type,
                course=course,
                due_at=due,
                status=status,
                priority=priority,
                notes=notes,
            ))

        session = ChatSession(user_id=user.id, title="数据结构复习")
        db.add(session)
        db.flush()
        db.add(ChatMessage(
            session_id=session.id,
            role="user",
            content="栈和队列有什么区别？",
        ))
        db.add(ChatMessage(
            session_id=session.id,
            role="assistant",
            content=(
                "栈是后进先出（LIFO）的线性表，只允许在栈顶插入和删除 [1]；"
                "队列是先进先出（FIFO）的线性表，在队尾插入、队头删除 [2]。"
            ),
            sources=[
                {
                    "doc_id": docs[1].id,
                    "filename": docs[1].filename,
                    "chunk_index": 1,
                    "content": DOCS[1]["chunks"][1],
                    "score": 0.95,
                },
                {
                    "doc_id": docs[1].id,
                    "filename": docs[1].filename,
                    "chunk_index": 2,
                    "content": DOCS[1]["chunks"][2],
                    "score": 0.93,
                },
            ],
        ))

        db.commit()
        try:
            _build_demo_index(db)
        except Exception as exc:
            print("Demo index build failed:", exc)
        print(f"Demo data seeded: {DEMO_USERNAME} / {DEMO_PASSWORD}")
    except Exception as exc:
        db.rollback()
        print("Demo seed failed:", exc)
    finally:
        db.close()
